"""
Enhanced FlakeRadar Analyzer with Team Features
Supports both local analysis and team collaboration
"""
from __future__ import annotations
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Any
import math
import time
from .team_backend import TeamBackend, FlakeRadarTier
from .config import Config

class TeamAnalyzer:
    """Enhanced analyzer with team collaboration features"""
    
    def __init__(self, config: Config):
        self.config = config
        self.team_backend = None
        
        if config.tier != FlakeRadarTier.FREE and config.team_config.is_team_mode():
            self.team_backend = TeamBackend(config.team_config)
    
    def compute_flakiness_with_team_context(self, raw_rows: List[Tuple[str, str]]) -> Dict[str, Dict]:
        """
        Enhanced flakiness computation with team insights
        """
        # First, compute local flakiness (same as before)
        local_analysis = compute_flakiness(raw_rows)
        
        # If team mode is enabled, enrich with team data
        if self.team_backend and self.config.tier in [FlakeRadarTier.TEAM, FlakeRadarTier.ENTERPRISE]:
            self._enrich_with_team_data(local_analysis)
        
        return local_analysis
    
    def _enrich_with_team_data(self, local_analysis: Dict[str, Dict]) -> None:
        """Enrich local analysis with team-wide insights"""
        
        print("🔍 Fetching team insights...")
        
        for test_name, test_data in local_analysis.items():
            # Get cross-environment data for this test
            cross_env_data = self.team_backend.get_cross_environment_data(test_name)
            
            if cross_env_data:
                # Add team context
                test_data["team_insights"] = {
                    "environments_affected": cross_env_data.get("environments", []),
                    "total_team_failures": cross_env_data.get("total_failures", 0),
                    "team_flakiness_score": cross_env_data.get("team_flakiness_score", 0.0),
                    "first_seen_team_wide": cross_env_data.get("first_seen", None),
                    "affected_team_members": cross_env_data.get("affected_members", []),
                    "cross_env_pattern": cross_env_data.get("pattern", "unknown")
                }
                
                # Adjust confidence based on team data
                team_confidence = cross_env_data.get("team_confidence", 0.0)
                test_data["enhanced_confidence"] = (
                    test_data["confidence_score"] * 0.6 + team_confidence * 0.4
                )
                
                # Tag as team-critical if affects multiple environments
                if len(cross_env_data.get("environments", [])) > 1:
                    test_data["team_critical"] = True
                    test_data["priority"] = "high"
                else:
                    test_data["team_critical"] = False
                    test_data["priority"] = "medium"
            else:
                # No team data available
                test_data["team_insights"] = None
                test_data["enhanced_confidence"] = test_data["confidence_score"]
                test_data["team_critical"] = False
                test_data["priority"] = "low"
    
    def submit_analysis_to_team(self, analysis_results: Dict[str, Any]) -> bool:
        """Submit analysis results to team backend"""
        if not self.team_backend:
            return False
        
        # Prepare team submission data (preserve environment from analysis_results)
        team_data = {
            "project": self.config.project,
            "environment": analysis_results.get("environment", self.config.team_config.environment),
            "build_id": self.config.build_id,
            "commit_sha": self.config.commit_sha,
            "timestamp": time.time(),
            "results": analysis_results,
            "metadata": {
                "total_tests": len(analysis_results.get("test_results", [])),
                "flaky_tests": len([t for t in analysis_results.get("test_results", []) if t.get("suspect_flaky", False)]),
                "runner": "cli",
                "version": "1.1.0"
            }
        }
        
        return self.team_backend.submit_analysis(team_data)
    
    def get_team_dashboard_data(self) -> Optional[Dict[str, Any]]:
        """Get team dashboard insights"""
        if not self.team_backend:
            return None
        
        return self.team_backend.get_team_insights(self.config.project)

    def get_central_dashboard(self, project: str = None) -> Optional[Dict[str, Any]]:
        """
        Get centralized dashboard data that all team members can access
        
        Args:
            project: Optional project to filter dashboard data
            
        Returns:
            Dashboard data with team collaboration metrics
        """
        if not self.team_backend:
            return None
            
        dashboard_data = self.team_backend.get_central_dashboard(project or self.config.project)
        if dashboard_data:
            return dashboard_data.to_dict()
        return None

    def get_team_members(self) -> List[Dict[str, Any]]:
        """
        Get list of active team members who have contributed test data
        
        Returns:
            List of team member information
        """
        if not self.team_backend:
            return []
            
        members = self.team_backend.get_team_members()
        return [
            {
                "username": member.username,
                "display_name": member.display_name,
                "last_contribution": member.last_contribution.isoformat(),
                "total_runs": member.total_runs,
                "environments": member.environments_contributed,
                "avatar_url": member.avatar_url
            }
            for member in members
        ]

    def get_real_time_activity(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get real-time feed of team test activities
        
        Args:
            limit: Maximum number of activities to retrieve
            
        Returns:
            List of recent team activities
        """
        if not self.team_backend:
            return []
            
        return self.team_backend.get_real_time_activity(limit)

    def notify_team_of_completion(self, run_summary: Dict[str, Any]) -> bool:
        """
        Notify team members that test run is complete and data is available
        
        Args:
            run_summary: Summary of the completed test run
            
        Returns:
            True if notification sent successfully
        """
        if not self.team_backend:
            return False
            
        return self.team_backend.notify_test_run_complete(run_summary)

    def get_dashboard_url(self, project: str = None) -> Optional[str]:
        """
        Get URL to the centralized team dashboard
        
        Args:
            project: Optional project for dashboard filtering
            
        Returns:
            Dashboard URL that all team members can access
        """
        if not self.team_backend:
            return None
            
        return self.team_backend.get_dashboard_url(project or self.config.project)

# Legacy function for backwards compatibility
def compute_flakiness(raw_rows: List[Tuple[str, str]]) -> Dict[str, Dict]:
    """
    raw_rows: list of (full_name, status) across many runs (mixed order).
    Return dict: {full_name: {pass_count, fail_count, transitions, flake_rate, suspect_flaky:bool}}
    """
    # Group by test
    history: Dict[str, List[str]] = defaultdict(list)
    for full_name, status in raw_rows:
        history[full_name].append(status)

    out: Dict[str, Dict] = {}
    for name, statuses in history.items():
        pass_count = sum(1 for s in statuses if s == "pass")
        fail_like = sum(1 for s in statuses if s in ("fail","error"))
        total = len(statuses)
        # transitions
        transitions = 0
        for i in range(1, len(statuses)):
            if statuses[i] != statuses[i-1]:
                transitions += 1
        flake_rate = fail_like / total if total else 0
        
        # Statistical significance scoring
        confidence_score = calculate_flakiness_confidence(pass_count, fail_like, total, transitions)
        
        # Updated logic for better classification:
        # - truly_flaky: has both passes and failures (intermittent) with sufficient confidence
        # - always_failing: only failures (100% fail rate)
        # - stable: consistently passes (0% fail rate)
        truly_flaky = pass_count > 0 and fail_like > 0 and confidence_score >= 0.7  # high confidence required
        always_failing = fail_like > 0 and pass_count == 0 and total >= 3  # require minimum runs
        suspect = truly_flaky or always_failing  # both types need attention
        
        out[name] = {
            "pass_count": pass_count,
            "fail_count": fail_like,
            "total_runs": total,
            "transitions": transitions,
            "flake_rate": flake_rate,
            "suspect_flaky": suspect,
            "truly_flaky": truly_flaky,
            "always_failing": always_failing,
            "confidence_score": confidence_score,
        }
    return out


def calculate_flakiness_confidence(pass_count: int, fail_count: int, total: int, transitions: int) -> float:
    """
    Calculate statistical confidence that a test is truly flaky
    Returns 0.0 to 1.0 where 1.0 is high confidence
    """
    if total < 2:
        return 0.0  # insufficient data
    
    # Base confidence on sample size (more runs = higher confidence)
    sample_size_factor = min(1.0, total / 20.0)  # plateau at 20 runs
    
    # Confidence based on transition rate (true flakiness has transitions)
    transition_rate = transitions / max(1, total - 1)
    transition_factor = min(1.0, transition_rate * 2)  # 50%+ transition rate = high confidence
    
    # Handle edge cases: consistent behavior = NOT flaky
    if pass_count == 0 or fail_count == 0:
        # All pass or all fail = definitely NOT flaky
        # High confidence that it's NOT flaky = low flakiness confidence score
        return 0.0
    
    # For mixed results, use binomial confidence interval
    p = fail_count / total
    # Wilson score interval for 95% confidence
    z = 1.96  # 95% confidence
    denominator = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z**2 / (4 * total)) / total) / denominator
    
    # If confidence interval is narrow and away from 0/1, it's likely flaky
    interval_width = 2 * margin
    distance_from_edges = min(center, 1 - center)
    
    # Combine factors
    statistical_confidence = (1 - interval_width) * distance_from_edges * 2
    
    return min(1.0, sample_size_factor * transition_factor * statistical_confidence)
