#!/usr/bin/env python3
"""
FlakeRadar Python API Examples

This script demonstrates various ways to use the FlakeRadar Python API.
"""

import os
import sys
from pathlib import Path

# Add the src directory to Python path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from flakeradar import FlakeRadar

def example_basic_usage():
    """Basic usage example as shown in README"""
    print("📖 Example 1: Basic Usage")
    print("-" * 30)
    
    # Initialize analyzer
    radar = FlakeRadar(project="MyApp")
    
    # Add test results
    radar.add_results("demo_test_results.xml")
    
    # Analyze flakiness
    analysis = radar.analyze(
        confidence_threshold=0.7,
        enable_ai=True,
        track_time_to_fix=True
    )
    
    print(f"Total tests: {analysis['total_tests']}")
    print(f"Flaky tests: {analysis['flaky_tests']}")
    print(f"AI analyzed: {analysis['ai_analyzed_count']} tests")
    
    # Generate reports
    radar.generate_html_report("example1_report.html")
    radar.export_metrics("example1_metrics.json")
    
    print("✅ Reports generated successfully\n")


def example_context_manager():
    """Using FlakeRadar with context manager for automatic cleanup"""
    print("🔒 Example 2: Context Manager")
    print("-" * 30)
    
    with FlakeRadar(project="ContextExample", db_path="context_test.db") as radar:
        radar.add_results("demo_test_results.xml")
        analysis = radar.analyze(confidence_threshold=0.5)
        
        summary = radar.get_summary()
        print(f"Project: {summary['project']}")
        print(f"Flakiness rate: {summary['flakiness_rate']:.1f}%")
        print(f"Total clusters: {summary['cluster_count']}")
    
    print("✅ Database connection automatically closed\n")


def example_detailed_analysis():
    """Detailed analysis with custom settings"""
    print("🔍 Example 3: Detailed Analysis")
    print("-" * 30)
    
    radar = FlakeRadar(
        project="DetailedAnalysis",
        build_id="build-123", 
        commit_sha="abc123def"
    )
    
    # Add multiple result files (if they existed)
    try:
        radar.add_results("test-results/*.xml")
    except FileNotFoundError:
        # Fallback to demo file
        radar.add_results("demo_test_results.xml")
    
    # Perform analysis with custom settings
    analysis = radar.analyze(
        confidence_threshold=0.8,  # Higher confidence threshold
        enable_ai=False,           # Disable AI for faster processing
        track_time_to_fix=True,
        limit_runs=100,            # Look at more historical runs
        max_ai_analysis=5          # Limit AI analysis
    )
    
    # Get detailed information
    flaky_tests = radar.get_flaky_tests(confidence_threshold=0.8)
    print(f"High-confidence flaky tests: {len(flaky_tests)}")
    
    for test in flaky_tests[:3]:  # Show top 3
        print(f"  • {test['full_name']}: {test['flake_rate']*100:.1f}% failure rate")
        print(f"    Confidence: {test['confidence_score']:.2f}")
        print(f"    Runs: {test['pass_count']} pass, {test['fail_count']} fail")
    
    radar.close()
    print("✅ Detailed analysis completed\n")


def example_batch_processing():
    """Process multiple projects in batch"""
    print("📊 Example 4: Batch Processing")
    print("-" * 30)
    
    projects = ["ProjectA", "ProjectB", "ProjectC"]
    results = {}
    
    for project in projects:
        with FlakeRadar(project=project, db_path=f"{project.lower()}.db") as radar:
            radar.add_results("demo_test_results.xml")
            analysis = radar.analyze()
            
            summary = radar.get_summary()
            results[project] = summary
            
            # Generate project-specific report
            radar.generate_html_report(f"{project.lower()}_report.html")
    
    # Summary across all projects
    print("Batch processing results:")
    for project, summary in results.items():
        print(f"  {project}: {summary['flakiness_rate']:.1f}% flaky ({summary['total_tests']} tests)")
    
    print("✅ Batch processing completed\n")


def example_error_handling():
    """Demonstrate proper error handling"""
    print("🛡️ Example 5: Error Handling")
    print("-" * 30)
    
    try:
        radar = FlakeRadar(project="ErrorDemo")
        
        # Try to analyze without loading results
        try:
            radar.analyze()
        except ValueError as e:
            print(f"Expected error: {e}")
        
        # Try to load non-existent file
        try:
            radar.add_results("nonexistent/*.xml")
        except FileNotFoundError as e:
            print(f"Expected error: {e}")
        
        # Load valid results and continue
        radar.add_results("demo_test_results.xml")
        analysis = radar.analyze()
        
        # Try to get summary before analysis (this should work now)
        summary = radar.get_summary()
        print(f"✅ Analysis succeeded: {summary['total_tests']} tests")
        
        radar.close()
        
    except Exception as e:
        print(f"Unexpected error: {e}")
    
    print("✅ Error handling demonstration completed\n")


def example_api_integration():
    """Show how to integrate with other systems"""
    print("🔗 Example 6: API Integration")
    print("-" * 30)
    
    with FlakeRadar(project="IntegrationTest") as radar:
        radar.add_results("demo_test_results.xml")
        analysis = radar.analyze()
        
        # Get data for external systems
        summary = radar.get_summary()
        flaky_tests = radar.get_flaky_tests()
        
        # Example: Send to monitoring system
        monitoring_data = {
            "timestamp": analysis["run_id"],
            "project": summary["project"],
            "flakiness_rate": summary["flakiness_rate"],
            "total_tests": summary["total_tests"],
            "flaky_count": summary["flaky_tests"],
            "critical_tests": [t["full_name"] for t in flaky_tests if t["confidence_score"] > 0.9]
        }
        
        print("Data ready for external systems:")
        print(f"  Flakiness rate: {monitoring_data['flakiness_rate']:.1f}%")
        print(f"  Critical tests: {len(monitoring_data['critical_tests'])}")
        
        # Example: Publish results (commented out as it requires external services)
        # radar.publish_results()
    
    print("✅ Integration example completed\n")


if __name__ == "__main__":
    print("🔍 FlakeRadar Python API - Comprehensive Examples")
    print("=" * 60)
    print()
    
    # Run all examples
    example_basic_usage()
    example_context_manager()
    example_detailed_analysis()
    example_batch_processing()
    example_error_handling()
    example_api_integration()
    
    print("🎉 All examples completed successfully!")
    print("\nGenerated files:")
    generated_files = [
        "example1_report.html", "example1_metrics.json",
        "projecta_report.html", "projectb_report.html", "projectc_report.html",
        "context_test.db", "projecta.db", "projectb.db", "projectc.db"
    ]
    
    for filename in generated_files:
        if Path(filename).exists():
            print(f"  ✅ {filename}")
    
    print("\n📚 The FlakeRadar Python API is fully functional and ready for use in your scripts!")
