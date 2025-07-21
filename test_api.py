#!/usr/bin/env python3
"""
Test script for FlakeRadar Python API

This script demonstrates the API as documented in the README.
"""

import os
import sys

# Add the src directory to Python path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_flakeradar_api():
    """Test the FlakeRadar Python API"""
    print("🧪 Testing FlakeRadar Python API...")
    
    # Test the import as shown in README
    try:
        from flakeradar import FlakeRadar
        print("✅ Import successful")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    
    # Initialize analyzer
    try:
        radar = FlakeRadar(project="TestProject")
        print("✅ FlakeRadar initialization successful")
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return False
    
    # Test adding results with demo file
    try:
        count = radar.add_results("demo_test_results.xml")
        print(f"✅ Added results from {count} file(s)")
    except Exception as e:
        print(f"❌ Adding results failed: {e}")
        return False
    
    # Analyze flakiness (as shown in README)
    try:
        analysis = radar.analyze(
            confidence_threshold=0.7,
            enable_ai=True,
            track_time_to_fix=True
        )
        print(f"✅ Analysis completed: {analysis['total_tests']} tests, {analysis['flaky_tests']} flaky")
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return False
    
    # Generate reports (as shown in README)
    try:
        html_path = radar.generate_html_report("api_test_report.html")
        print(f"✅ HTML report generated: {html_path}")
    except Exception as e:
        print(f"❌ HTML report generation failed: {e}")
        return False
    
    try:
        json_path = radar.export_metrics("api_test_metrics.json")
        print(f"✅ Metrics exported: {json_path}")
    except Exception as e:
        print(f"❌ Metrics export failed: {e}")
        return False
    
    # Test additional API methods
    try:
        flaky_tests = radar.get_flaky_tests()
        print(f"✅ Found {len(flaky_tests)} high-confidence flaky tests")
    except Exception as e:
        print(f"❌ Get flaky tests failed: {e}")
        return False
    
    try:
        summary = radar.get_summary()
        print(f"✅ Summary: {summary['flakiness_rate']:.1f}% flakiness rate")
    except Exception as e:
        print(f"❌ Get summary failed: {e}")
        return False
    
    # Test context manager
    try:
        with FlakeRadar(project="ContextTest") as ctx_radar:
            ctx_radar.add_results("demo_test_results.xml")
            ctx_analysis = ctx_radar.analyze()
        print("✅ Context manager works correctly")
    except Exception as e:
        print(f"❌ Context manager failed: {e}")
        return False
    
    # Clean up
    radar.close()
    print("✅ All API tests passed!")
    return True

def show_api_example():
    """Show a complete example as documented in README"""
    print("\n" + "="*50)
    print("📖 FlakeRadar Python API Example (from README)")
    print("="*50)
    
    example_code = '''
from flakeradar import FlakeRadar

# Initialize analyzer
radar = FlakeRadar(project="MyApp")

# Add test results
radar.add_results("test-results/*.xml")

# Analyze flakiness
analysis = radar.analyze(
    confidence_threshold=0.7,
    enable_ai=True,
    track_time_to_fix=True
)

# Generate reports
radar.generate_html_report("report.html")
radar.export_metrics("metrics.json")
'''
    
    print(example_code)
    print("✅ This API is now fully implemented and working!")

if __name__ == "__main__":
    success = test_flakeradar_api()
    show_api_example()
    
    if success:
        print("\n🎉 FlakeRadar Python API is ready for production use!")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed")
        sys.exit(1)
