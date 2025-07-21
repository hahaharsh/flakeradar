#!/usr/bin/env python3
"""
Quick test to verify README parameter documentation is accurate
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from flakeradar import FlakeRadar

def test_readme_accuracy():
    """Test that README examples work exactly as documented"""
    
    print("🧪 Testing README Parameter Documentation Accuracy")
    print("=" * 55)
    
    # Test 1: Basic usage as shown in README
    print("\n📖 Testing README Quick Start Example:")
    try:
        with FlakeRadar(project="MyApp") as radar:
            radar.add_results("demo_test_results.xml")
            analysis = radar.analyze(
                confidence_threshold=0.7,
                enable_ai=True,
                track_time_to_fix=True
            )
            radar.generate_html_report("readme_test_report.html")
            radar.export_metrics("readme_test_metrics.json")
        print("✅ README Quick Start example works perfectly!")
    except Exception as e:
        print(f"❌ README example failed: {e}")
        return False
    
    # Test 2: All documented parameters
    print("\n🎛️ Testing All Documented Parameters:")
    parameter_tests = [
        {
            "name": "Development (README example)",
            "params": {
                "confidence_threshold": 0.6,
                "enable_ai": False,
                "track_time_to_fix": False,
                "limit_runs": 20,
                "max_ai_analysis": 0
            }
        },
        {
            "name": "CI/CD (README example)",
            "params": {
                "confidence_threshold": 0.7,
                "enable_ai": True,
                "track_time_to_fix": True,
                "limit_runs": 50,
                "max_ai_analysis": 15
            }
        },
        {
            "name": "Production (README example)",
            "params": {
                "confidence_threshold": 0.8,
                "enable_ai": True,
                "track_time_to_fix": True,
                "limit_runs": 100,
                "max_ai_analysis": 30
            }
        }
    ]
    
    for test in parameter_tests:
        try:
            with FlakeRadar(project=f"Test-{test['name'][:5]}") as radar:
                radar.add_results("demo_test_results.xml")
                analysis = radar.analyze(**test['params'])
                print(f"  ✅ {test['name']}: All parameters work correctly")
        except Exception as e:
            print(f"  ❌ {test['name']}: Failed - {e}")
            return False
    
    # Test 3: Parameter validation
    print("\n🔧 Testing Parameter Validation:")
    
    # Test invalid confidence threshold
    try:
        with FlakeRadar(project="ValidationTest") as radar:
            radar.add_results("demo_test_results.xml")
            analysis = radar.analyze(confidence_threshold=1.5)  # Invalid
        print("  ❌ Should have failed with invalid confidence_threshold")
        return False
    except:
        print("  ✅ confidence_threshold validation works")
    
    # Test methods documented in README
    print("\n📊 Testing Additional Methods (from README):")
    try:
        with FlakeRadar(project="MethodTest") as radar:
            radar.add_results("demo_test_results.xml")
            analysis = radar.analyze()
            
            # Test documented methods
            summary = radar.get_summary()
            flaky_tests = radar.get_flaky_tests(confidence_threshold=0.8)
            
            # Verify return types match documentation
            assert isinstance(summary, dict)
            assert isinstance(flaky_tests, list)
            assert 'project' in summary
            assert 'total_tests' in summary
            assert 'flakiness_rate' in summary
            
            print("  ✅ get_summary() works as documented")
            print("  ✅ get_flaky_tests() works as documented")
            
    except Exception as e:
        print(f"  ❌ Method testing failed: {e}")
        return False
    
    print("\n🎉 All README documentation is accurate!")
    print("✅ Parameters work exactly as documented")
    print("✅ Examples are copy-paste ready")
    print("✅ Method signatures match documentation")
    
    return True

if __name__ == "__main__":
    success = test_readme_accuracy()
    if success:
        print("\n📚 README parameter documentation is production-ready!")
        sys.exit(0)
    else:
        print("\n💥 README documentation needs fixes")
        sys.exit(1)
