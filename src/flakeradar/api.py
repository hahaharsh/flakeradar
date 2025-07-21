"""
FlakeRadar Python API

Provides a programmatic interface to FlakeRadar's test analysis capabilities.
"""

from __future__ import annotations
import glob
import json
import os
import time
from typing import Dict, List, Optional, Any
from pathlib import Path

from .config import config_from_cli
from .parsers.detect import detect_format
from .parsers.junit import parse_junit_xml
from .history import (
    get_conn, 
    ensure_schema, 
    insert_run, 
    fetch_recent_tests, 
    update_flaky_test_tracking, 
    get_worst_flaky_offenders
)
from .analyzer import compute_flakiness
from .summarize import summarize_failure
from .html_report import render_report
from .send_redis import publish_to_redis
from .send_kafka import send_kafka_event
from .root_cause_clustering import cluster_failures_by_root_cause, get_cluster_recommendations


class FlakeRadar:
    """
    FlakeRadar Python API for programmatic test analysis.
    
    Example:
        >>> from flakeradar import FlakeRadar
        >>> radar = FlakeRadar(project="MyApp")
        >>> radar.add_results("test-results/*.xml")
        >>> analysis = radar.analyze()
        >>> radar.generate_html_report("report.html")
    """
    
    def __init__(self, 
                 project: str,
                 db_path: Optional[str] = None,
                 build_id: Optional[str] = None,
                 commit_sha: Optional[str] = None):
        """
        Initialize FlakeRadar analyzer.
        
        Args:
            project: Project name for test analysis
            db_path: Path to SQLite database (defaults to ~/.flakeradar/history.db)
            build_id: Build identifier (defaults to timestamp)
            commit_sha: Git commit SHA (defaults to "unknown")
        """
        self.project = project
        
        # Use the same default path as the CLI
        if db_path is None:
            db_path = os.getenv("FLAKERADAR_DB_PATH", os.path.expanduser("~/.flakeradar/history.db"))
        self.db_path = db_path
        
        self.build_id = build_id or f"api-{int(time.time())}"
        self.commit_sha = commit_sha or "unknown"
        
        # Ensure the directory exists (only if it's not current directory)
        db_dir = os.path.dirname(self.db_path)
        if db_dir:  # Only create directory if it's not empty (not current dir)
            os.makedirs(db_dir, exist_ok=True)
        
        # Initialize database
        self.conn = get_conn(self.db_path)
        ensure_schema(self.conn)
        
        # Storage for results
        self.all_results = []
        self.analysis_data = None
        self.worst_offenders = []
        self.cluster_analysis = {}
        
    def add_results(self, results_glob: str) -> int:
        """
        Add test results from files matching the glob pattern.
        
        Args:
            results_glob: Glob pattern for XML result files (e.g., "test-results/*.xml")
            
        Returns:
            Number of result files processed
            
        Raises:
            FileNotFoundError: If no files match the glob pattern
        """
        paths = sorted(glob.glob(results_glob))
        if not paths:
            raise FileNotFoundError(f"No result files found for glob: {results_glob}")
        
        file_count = 0
        for path in paths:
            fmt = detect_format(path)
            if fmt == "junit":  # includes TestNG
                self.all_results.extend(parse_junit_xml(path, default_suite=self.project))
                file_count += 1
        
        return file_count
    
    def add_result_file(self, file_path: str) -> None:
        """
        Add a single test result file.
        
        Args:
            file_path: Path to XML result file
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is not supported
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Result file not found: {file_path}")
        
        fmt = detect_format(file_path)
        if fmt == "junit":
            self.all_results.extend(parse_junit_xml(file_path, default_suite=self.project))
        else:
            raise ValueError(f"Unsupported file format: {file_path}")
    
    def analyze(self, 
                confidence_threshold: float = 0.7,
                enable_ai: bool = None,
                track_time_to_fix: bool = True,
                limit_runs: int = 50,
                max_ai_analysis: int = 20) -> Dict[str, Any]:
        """
        Perform flakiness analysis on loaded test results.
        
        Args:
            confidence_threshold: Minimum confidence score for flaky classification (0.0-1.0)
            enable_ai: Enable AI-powered failure analysis (auto-detects if OPENAI_API_KEY is set)
            track_time_to_fix: Track how long tests have been flaky
            limit_runs: Number of recent test runs to include in analysis
            max_ai_analysis: Maximum number of tests to analyze with AI
            
        Returns:
            Dictionary containing analysis results
            
        Raises:
            ValueError: If parameters are invalid
        """
        if not self.all_results:
            raise ValueError("No test results loaded. Call add_results() first.")
        
        # Parameter validation
        if not 0.0 <= confidence_threshold <= 1.0:
            raise ValueError("confidence_threshold must be between 0.0 and 1.0")
        
        if limit_runs < 1:
            raise ValueError("limit_runs must be at least 1")
            
        if max_ai_analysis < 0:
            raise ValueError("max_ai_analysis must be non-negative")
        
        # Store results in database
        run_id = insert_run(
            self.conn,
            project=self.project,
            build_id=self.build_id,
            commit_sha=self.commit_sha,
            meta={"mode": "api", "total_tests": len(self.all_results)},
            results=self.all_results,
        )
        
        # Compute flakiness across history
        raw_rows = fetch_recent_tests(self.conn, self.project, limit_runs=limit_runs)
        flake_stats = compute_flakiness(raw_rows)
        
        # Apply confidence threshold filter
        filtered_stats = {
            name: stats for name, stats in flake_stats.items()
            if stats["suspect_flaky"] and stats["confidence_score"] >= confidence_threshold
        }
        
        # Update flaky test tracking for time-to-fix analysis
        if track_time_to_fix:
            current_timestamp = int(time.time())
            update_flaky_test_tracking(self.conn, self.project, flake_stats, current_timestamp)
            self.worst_offenders = get_worst_flaky_offenders(self.conn, self.project, limit=10)
        
        # Root cause clustering analysis
        self.cluster_analysis = cluster_failures_by_root_cause(self.all_results)
        
        # AI analysis (if enabled)
        ai_cache = {}
        if enable_ai is None:
            enable_ai = os.getenv("OPENAI_API_KEY") is not None
        
        if enable_ai:
            failers_sorted = sorted(
                flake_stats.items(), 
                key=lambda kv: kv[1]["fail_count"], 
                reverse=True
            )[:max_ai_analysis]
            
            for name, stats in failers_sorted:
                # Find the first fail entry to pass to AI
                fail_cases = [r for r in self.all_results 
                            if r.full_name == name and r.status in ("fail", "error")]
                if not fail_cases:
                    continue
                case = fail_cases[0]
                ai = summarize_failure(
                    case.error_type or "", 
                    case.error_message or "", 
                    case.error_details or ""
                )
                ai_cache[name] = ai
        
        # Prepare analysis data
        test_rows = []
        for name, stats in sorted(flake_stats.items(), key=lambda kv: kv[1]["flake_rate"], reverse=True):
            row = stats.copy()
            row["full_name"] = name
            row["ai"] = ai_cache.get(name)
            test_rows.append(row)
        
        self.analysis_data = {
            "run_id": run_id,
            "project": self.project,
            "build_id": self.build_id,
            "commit_sha": self.commit_sha,
            "total_tests": len(self.all_results),
            "flaky_tests": len([r for r in test_rows if r["suspect_flaky"]]),
            "high_confidence_flaky": len(filtered_stats),
            "confidence_threshold": confidence_threshold,
            "ai_enabled": enable_ai,
            "ai_analyzed_count": len(ai_cache),
            "test_results": test_rows,
            "worst_offenders": self.worst_offenders,
            "cluster_analysis": self.cluster_analysis,
        }
        
        return self.analysis_data
    
    def generate_html_report(self, output_path: str = "flakeradar_report.html") -> str:
        """
        Generate HTML report from analysis results.
        
        Args:
            output_path: Path for output HTML file
            
        Returns:
            Absolute path to generated report
            
        Raises:
            ValueError: If analyze() hasn't been called yet
        """
        if not self.analysis_data:
            raise ValueError("No analysis data available. Call analyze() first.")
        
        out_path = render_report(
            self.project,
            self.analysis_data["test_results"],
            output_path,
            self.worst_offenders,
            self.cluster_analysis
        )
        
        return os.path.abspath(out_path)
    
    def export_metrics(self, output_path: str) -> str:
        """
        Export analysis metrics to JSON file.
        
        Args:
            output_path: Path for output JSON file
            
        Returns:
            Absolute path to exported file
            
        Raises:
            ValueError: If analyze() hasn't been called yet
        """
        if not self.analysis_data:
            raise ValueError("No analysis data available. Call analyze() first.")
        
        # Create exportable metrics (remove non-serializable items)
        export_data = self.analysis_data.copy()
        
        # Convert complex objects to serializable format
        if "test_results" in export_data:
            for test in export_data["test_results"]:
                if "ai" in test and test["ai"]:
                    # Convert AI response to string if it's an object
                    if hasattr(test["ai"], "__dict__"):
                        test["ai"] = str(test["ai"])
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, default=str)
        
        return os.path.abspath(output_path)
    
    def get_flaky_tests(self, 
                       confidence_threshold: float = 0.7,
                       include_always_failing: bool = True) -> List[Dict[str, Any]]:
        """
        Get list of flaky tests above confidence threshold.
        
        Args:
            confidence_threshold: Minimum confidence score (0.0-1.0)
            include_always_failing: Include tests that always fail
            
        Returns:
            List of flaky test dictionaries
            
        Raises:
            ValueError: If analyze() hasn't been called yet
        """
        if not self.analysis_data:
            raise ValueError("No analysis data available. Call analyze() first.")
        
        flaky_tests = []
        for test in self.analysis_data["test_results"]:
            if test["confidence_score"] >= confidence_threshold:
                if test["truly_flaky"] or (include_always_failing and test["always_failing"]):
                    flaky_tests.append(test)
        
        return flaky_tests
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics from analysis.
        
        Returns:
            Dictionary with summary metrics
            
        Raises:
            ValueError: If analyze() hasn't been called yet
        """
        if not self.analysis_data:
            raise ValueError("No analysis data available. Call analyze() first.")
        
        return {
            "project": self.analysis_data["project"],
            "total_tests": self.analysis_data["total_tests"],
            "flaky_tests": self.analysis_data["flaky_tests"],
            "high_confidence_flaky": self.analysis_data["high_confidence_flaky"],
            "flakiness_rate": (self.analysis_data["flaky_tests"] / self.analysis_data["total_tests"]) * 100 
                             if self.analysis_data["total_tests"] > 0 else 0,
            "ai_enabled": self.analysis_data["ai_enabled"],
            "cluster_count": len(self.analysis_data["cluster_analysis"]),
            "worst_offender_count": len(self.analysis_data["worst_offenders"]),
        }
    
    def publish_results(self, redis_config: Optional[Dict] = None, kafka_config: Optional[Dict] = None) -> None:
        """
        Publish analysis results to Redis and/or Kafka.
        
        Args:
            redis_config: Redis configuration (uses defaults if None)
            kafka_config: Kafka configuration (uses defaults if None)
        """
        if not self.analysis_data:
            raise ValueError("No analysis data available. Call analyze() first.")
        
        summary_payload = {
            "project": self.project,
            "build_id": self.build_id,
            "commit": self.commit_sha,
            "run_id": self.analysis_data["run_id"],
            "total_tests": self.analysis_data["total_tests"],
            "flaky_count": self.analysis_data["flaky_tests"],
        }
        
        # Publish to Redis (best effort)
        try:
            publish_to_redis(self.project, summary_payload)
        except Exception:
            pass  # Non-blocking
        
        # Send to Kafka (best effort)
        try:
            send_kafka_event(self.project, summary_payload)
        except Exception:
            pass  # Non-blocking
    
    def close(self) -> None:
        """Close database connection."""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
