#!/usr/bin/env python3
"""
FlakeRadar Team Collaboration Example

This example demonstrates how to use FlakeRadar's enterprise team collaboration 
features for cross-environment analysis and team insights.
"""

import os
from flakeradar import FlakeRadar


def basic_team_analysis():
    """Basic team analysis with cross-environment detection"""
    print("🚀 Basic Team Analysis Example")
    print("=" * 50)
    
    # Team-enabled analysis
    with FlakeRadar(
        project="MyApp",
        team_id="backend-team",
        environment="staging",
        api_token=os.getenv("FLAKERADAR_TOKEN")  # Load from environment
    ) as radar:
        # Add test results
        radar.add_results("test-results/*.xml")
        
        # Analyze with team context
        analysis = radar.analyze(
            confidence_threshold=0.7,
            enable_team_context=True,
            enable_ai=True
        )
        
        # Display team insights
        if analysis.team_insights:
            print(f"📊 Cross-environment flaky tests: {len(analysis.team_insights.cross_environment_flaky)}")
            print(f"🎯 Team impact score: {analysis.team_insights.team_impact_score}")
            print(f"🌐 Environments analyzed: {analysis.team_insights.environments}")
            
            # Environment-specific patterns
            for env, patterns in analysis.team_insights.environment_patterns.items():
                print(f"🔍 {env.title()} environment issues:")
                for pattern, count in patterns.items():
                    print(f"   - {pattern}: {count} tests")
        
        # Generate enhanced report with team insights
        radar.generate_html_report("team_analysis_report.html")
        print("\n✅ Team analysis report generated: team_analysis_report.html")


def multi_environment_comparison():
    """Compare flakiness across multiple environments"""
    print("\n🌐 Multi-Environment Comparison")
    print("=" * 50)
    
    environments = ["development", "staging", "production"]
    results = {}
    
    for env in environments:
        with FlakeRadar(
            project="MyApp",
            team_id="backend-team",
            environment=env,
            api_token=os.getenv("FLAKERADAR_TOKEN")
        ) as radar:
            radar.add_results(f"test-results/{env}/*.xml")
            analysis = radar.analyze(enable_team_context=True)
            
            results[env] = {
                "total_tests": len(analysis.test_results),
                "flaky_tests": len(analysis.flaky_tests),
                "flakiness_rate": len(analysis.flaky_tests) / len(analysis.test_results) * 100
            }
            
            print(f"📊 {env.title()}: {results[env]['flaky_tests']}/{results[env]['total_tests']} flaky ({results[env]['flakiness_rate']:.1f}%)")
    
    # Find environment with highest flakiness
    worst_env = max(results.keys(), key=lambda k: results[k]['flakiness_rate'])
    print(f"\n🔴 Highest flakiness in: {worst_env.title()} ({results[worst_env]['flakiness_rate']:.1f}%)")


def ci_cd_integration_example():
    """Example for CI/CD pipeline integration"""
    print("\n🔄 CI/CD Integration Example")
    print("=" * 50)
    
    # Environment variables from CI/CD
    project = os.getenv("CI_PROJECT_NAME", "MyApp")
    environment = os.getenv("CI_ENVIRONMENT_NAME", "staging")
    build_id = os.getenv("CI_BUILD_ID", "unknown")
    
    with FlakeRadar(
        project=project,
        team_id="ci-team",
        environment=environment,
        api_token=os.getenv("FLAKERADAR_TOKEN")
    ) as radar:
        radar.add_results("test-results/*.xml")
        
        analysis = radar.analyze(
            confidence_threshold=0.8,  # High confidence for CI/CD
            enable_team_context=True,
            enable_ai=False  # Fast analysis for CI/CD
        )
        
        print(f"🏗️ Build: {build_id}")
        print(f"🌍 Environment: {environment}")
        print(f"📊 Tests analyzed: {len(analysis.test_results)}")
        print(f"🔴 Flaky tests detected: {len(analysis.flaky_tests)}")
        
        # Export metrics for CI/CD reporting
        radar.export_metrics(f"flakeradar-metrics-{build_id}.json")
        print(f"✅ Metrics exported: flakeradar-metrics-{build_id}.json")
        
        # Fail build if too many flaky tests
        flakiness_rate = len(analysis.flaky_tests) / len(analysis.test_results) * 100
        if flakiness_rate > 10:  # 10% threshold
            print(f"❌ Build failed: Flakiness rate {flakiness_rate:.1f}% exceeds 10% threshold")
            return False
        else:
            print(f"✅ Build passed: Flakiness rate {flakiness_rate:.1f}% within acceptable limits")
            return True


def main():
    """Run all team collaboration examples"""
    print("🤝 FlakeRadar Team Collaboration Examples")
    print("=" * 60)
    
    # Check for team token
    if not os.getenv("FLAKERADAR_TOKEN"):
        print("⚠️  FLAKERADAR_TOKEN not found. Some features will be limited.")
        print("   Set your team token: export FLAKERADAR_TOKEN='flake_tk_your_token'")
        print()
    
    try:
        # Run examples
        basic_team_analysis()
        multi_environment_comparison()
        success = ci_cd_integration_example()
        
        print(f"\n🎉 All examples completed!")
        print("\nNext steps:")
        print("1. Sign up for FlakeRadar team account at api.flakeradar.io")
        print("2. Get your team token and set FLAKERADAR_TOKEN")
        print("3. Configure your CI/CD pipeline with team analysis")
        print("4. View unified team insights across environments")
        
    except Exception as e:
        print(f"❌ Error running examples: {e}")
        print("   This is expected without a valid team token")


if __name__ == "__main__":
    main()
