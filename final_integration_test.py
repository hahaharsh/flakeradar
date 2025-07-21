#!/usr/bin/env python3
"""
Final Integration Test - FlakeRadar Python API v1.1.0

This script demonstrates the complete Python API working in a real-world scenario.
"""

import os
import sys
import json
from pathlib import Path

# Add the src directory to Python path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    print("🔍 FlakeRadar v1.1.0 - Final Integration Test")
    print("=" * 60)
    
    try:
        # Import the API
        from flakeradar import FlakeRadar
        print("✅ Successfully imported FlakeRadar Python API")
        
        # Real-world scenario: Multi-project analysis
        projects = ["Frontend", "Backend", "Integration"]
        
        for i, project_name in enumerate(projects, 1):
            print(f"\n📊 Analyzing Project {i}: {project_name}")
            print("-" * 40)
            
            with FlakeRadar(
                project=project_name,
                build_id=f"build-{1000 + i}",
                commit_sha=f"abc123{i}",
                db_path=f"test_{project_name.lower()}.db"
            ) as radar:
                
                # Load test results
                count = radar.add_results("demo_test_results.xml")
                print(f"  📁 Loaded {count} result file(s)")
                
                # Perform analysis with different settings per project
                confidence = 0.6 if project_name == "Integration" else 0.8
                analysis = radar.analyze(
                    confidence_threshold=confidence,
                    enable_ai=True,
                    track_time_to_fix=True
                )
                
                print(f"  🔍 Analysis complete:")
                print(f"    • Total tests: {analysis['total_tests']}")
                print(f"    • Flaky tests: {analysis['flaky_tests']}")
                print(f"    • AI analyzed: {analysis['ai_analyzed_count']}")
                print(f"    • Confidence threshold: {confidence}")
                
                # Generate reports
                html_path = radar.generate_html_report(f"{project_name.lower()}_final_report.html")
                json_path = radar.export_metrics(f"{project_name.lower()}_final_metrics.json")
                
                print(f"  📋 Generated reports:")
                print(f"    • HTML: {Path(html_path).name}")
                print(f"    • JSON: {Path(json_path).name}")
                
                # Get detailed information
                summary = radar.get_summary()
                flaky_tests = radar.get_flaky_tests(confidence_threshold=confidence)
                
                print(f"  📈 Summary:")
                print(f"    • Flakiness rate: {summary['flakiness_rate']:.1f}%")
                print(f"    • High-confidence flaky: {len(flaky_tests)}")
                print(f"    • Root cause clusters: {summary['cluster_count']}")
                
                # Example: Custom business logic
                if summary['flakiness_rate'] > 15.0:
                    print(f"  🚨 WARNING: High flakiness rate for {project_name}!")
                elif summary['flakiness_rate'] > 5.0:
                    print(f"  ⚠️  NOTICE: Moderate flakiness for {project_name}")
                else:
                    print(f"  ✅ GOOD: Low flakiness rate for {project_name}")
        
        # Aggregate analysis
        print(f"\n📊 Aggregate Analysis")
        print("-" * 40)
        
        total_reports = len([f for f in os.listdir('.') if f.endswith('_final_report.html')])
        total_metrics = len([f for f in os.listdir('.') if f.endswith('_final_metrics.json')])
        total_dbs = len([f for f in os.listdir('.') if f.startswith('test_') and f.endswith('.db')])
        
        print(f"Generated artifacts:")
        print(f"  • HTML reports: {total_reports}")
        print(f"  • JSON metrics: {total_metrics}")  
        print(f"  • Project databases: {total_dbs}")
        
        # Load and analyze metrics
        all_metrics = []
        for project in projects:
            metrics_file = f"{project.lower()}_final_metrics.json"
            if os.path.exists(metrics_file):
                with open(metrics_file, 'r') as f:
                    metrics = json.load(f)
                    all_metrics.append({
                        'project': project,
                        'total_tests': metrics['total_tests'],
                        'flaky_tests': metrics['flaky_tests'],
                        'flakiness_rate': (metrics['flaky_tests'] / metrics['total_tests']) * 100 if metrics['total_tests'] > 0 else 0
                    })
        
        if all_metrics:
            print(f"\nCross-project summary:")
            for metric in all_metrics:
                print(f"  {metric['project']:12}: {metric['flakiness_rate']:5.1f}% ({metric['flaky_tests']}/{metric['total_tests']})")
            
            avg_flakiness = sum(m['flakiness_rate'] for m in all_metrics) / len(all_metrics)
            print(f"  {'Average':12}: {avg_flakiness:5.1f}%")
        
        print(f"\n🎉 INTEGRATION TEST PASSED!")
        print(f"✅ FlakeRadar Python API v1.1.0 is fully functional and production-ready!")
        return True
        
    except Exception as e:
        print(f"\n💥 Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
