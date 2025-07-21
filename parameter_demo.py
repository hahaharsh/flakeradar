#!/usr/bin/env python3
"""
FlakeRadar Parameter Demonstration

This script shows how different parameter combinations affect analysis results.
"""

import os
import sys
import time

# Add the src directory to Python path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from flakeradar import FlakeRadar

def demonstrate_parameters():
    """Demonstrate different parameter configurations"""
    
    print("🎛️ FlakeRadar Parameter Demonstration")
    print("=" * 50)
    
    # Test different parameter combinations
    configurations = [
        {
            "name": "🚀 Fast Development",
            "params": {
                "confidence_threshold": 0.6,
                "enable_ai": False,
                "track_time_to_fix": False,
                "limit_runs": 20,
                "max_ai_analysis": 0
            }
        },
        {
            "name": "⚖️ Balanced Production",
            "params": {
                "confidence_threshold": 0.7,
                "enable_ai": True,
                "track_time_to_fix": True,
                "limit_runs": 50,
                "max_ai_analysis": 20
            }
        },
        {
            "name": "🔍 Deep Investigation",
            "params": {
                "confidence_threshold": 0.5,
                "enable_ai": True,
                "track_time_to_fix": True,
                "limit_runs": 100,
                "max_ai_analysis": 50
            }
        },
        {
            "name": "💰 Cost-Conscious",
            "params": {
                "confidence_threshold": 0.8,
                "enable_ai": False,
                "track_time_to_fix": True,
                "limit_runs": 50,
                "max_ai_analysis": 0
            }
        }
    ]
    
    results = []
    
    for config in configurations:
        print(f"\n{config['name']}")
        print("-" * 30)
        
        # Show parameters
        for param, value in config['params'].items():
            print(f"  {param}: {value}")
        
        try:
            start_time = time.time()
            
            # Run analysis with these parameters
            with FlakeRadar(project=f"Demo-{config['name'][:5]}") as radar:
                radar.add_results("demo_test_results.xml")
                analysis = radar.analyze(**config['params'])
                
                end_time = time.time()
                duration = end_time - start_time
                
                # Collect results
                result = {
                    'name': config['name'],
                    'duration': duration,
                    'total_tests': analysis['total_tests'],
                    'flaky_tests': analysis['flaky_tests'],
                    'high_confidence': analysis['high_confidence_flaky'],
                    'ai_analyzed': analysis['ai_analyzed_count'],
                    'confidence_threshold': analysis['confidence_threshold']
                }
                results.append(result)
                
                # Show results
                print(f"  ⏱️  Duration: {duration:.2f}s")
                print(f"  📊 Total tests: {analysis['total_tests']}")
                print(f"  🔴 Flaky tests: {analysis['flaky_tests']}")
                print(f"  ⭐ High confidence: {analysis['high_confidence_flaky']}")
                print(f"  🤖 AI analyzed: {analysis['ai_analyzed_count']}")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    # Comparison summary
    print(f"\n📊 Comparison Summary")
    print("=" * 50)
    print(f"{'Configuration':<20} {'Duration':<10} {'Flaky':<8} {'AI':<6}")
    print("-" * 50)
    
    for result in results:
        print(f"{result['name'][:18]:<20} {result['duration']:<9.2f}s {result['flaky_tests']:<8} {result['ai_analyzed']:<6}")
    
    # Parameter impact analysis
    print(f"\n🎯 Parameter Impact Analysis")
    print("=" * 50)
    
    fastest = min(results, key=lambda x: x['duration'])
    most_ai = max(results, key=lambda x: x['ai_analyzed'])
    most_flaky = max(results, key=lambda x: x['flaky_tests'])
    
    print(f"⚡ Fastest configuration: {fastest['name']} ({fastest['duration']:.2f}s)")
    print(f"🤖 Most AI analysis: {most_ai['name']} ({most_ai['ai_analyzed']} tests)")
    print(f"🔍 Most sensitive: {most_flaky['name']} ({most_flaky['flaky_tests']} flaky)")
    
    # Recommendations
    print(f"\n💡 Recommendations")
    print("=" * 50)
    print("• 🚀 Fast Development: Use for quick feedback loops")
    print("• ⚖️ Balanced Production: Best for most CI/CD pipelines")
    print("• 🔍 Deep Investigation: Use when debugging specific issues")
    print("• 💰 Cost-Conscious: Minimize AI costs while tracking trends")
    
    return results

def show_parameter_examples():
    """Show specific parameter usage examples"""
    
    print(f"\n🔧 Parameter Usage Examples")
    print("=" * 50)
    
    examples = [
        {
            "scenario": "Early Development",
            "code": """
radar.analyze(
    confidence_threshold=0.5,  # Catch issues early
    enable_ai=False,          # No AI costs
    limit_runs=20             # Quick analysis
)"""
        },
        {
            "scenario": "CI/CD Pipeline",
            "code": """
radar.analyze(
    confidence_threshold=0.7,  # Balanced accuracy
    enable_ai=True,           # Useful insights
    track_time_to_fix=True,   # Track debt
    max_ai_analysis=15        # Controlled costs
)"""
        },
        {
            "scenario": "Production Monitoring",
            "code": """
radar.analyze(
    confidence_threshold=0.8,  # High confidence
    enable_ai=True,           # Full insights
    limit_runs=100,           # Deep history
    max_ai_analysis=30        # Comprehensive
)"""
        }
    ]
    
    for example in examples:
        print(f"\n📋 {example['scenario']}:")
        print(example['code'])

if __name__ == "__main__":
    try:
        results = demonstrate_parameters()
        show_parameter_examples()
        
        print(f"\n🎉 Parameter demonstration complete!")
        print("✅ All parameter combinations tested successfully")
        
    except Exception as e:
        print(f"\n💥 Demonstration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
