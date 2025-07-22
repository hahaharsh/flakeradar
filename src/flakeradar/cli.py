from __future__ import annotations
import glob
import os
import sys
import time
from datetime import datetime
import click
from tabulate import tabulate
from argparse import Namespace

from .config import config_from_cli, FlakeRadarTier
from .team_analyzer import TeamAnalyzer, compute_flakiness
from .team_backend import JenkinsIntegration
from .parsers.detect import detect_format
from .parsers.junit import parse_junit_xml
from .history import get_conn, ensure_schema, insert_run, fetch_recent_tests, update_flaky_test_tracking, get_worst_flaky_offenders
from .summarize import summarize_failure
from .html_report import render_report
from .send_redis import publish_to_redis
from .send_kafka import send_kafka_event
from .root_cause_clustering import cluster_failures_by_root_cause, get_cluster_recommendations

@click.command()
@click.option("--project", required=True, help="Project name label.")
@click.option("--results", required=True, help="Glob for TestNG/JUnit XML results.")
@click.option("--logs", default=None, help="Glob for logs (ignored in local MVP; future).")
@click.option("--mode", default="local", type=click.Choice(["local","push"]), help="Analysis mode.")
@click.option("--build", default="local-build", help="Build ID (CI).")
@click.option("--commit", default="local", help="Git commit SHA.")
@click.option("--report-out", default="flakeradar_report.html", help="HTML report path.")
@click.option("--environment", default=None, help="Environment name for team features (e.g., staging, prod).")
@click.option("--team-token", default=None, help="Team collaboration token for sharing test data.")
def cli(project, results, logs, mode, build, commit, report_out, environment, team_token):
    """
    Analyze test results locally; store in SQLite; emit flakiness summary.
    Enhanced with team collaboration features.
    """
    args = click.get_current_context().params
    cfg = config_from_cli(Namespace(**args))  # cheap wrapper
    
    # Early environment detection for use throughout the function
    detected_environment = cfg.team_config.environment
    if detected_environment == 'default':
        # Detect from CI/CD environment variables
        import os
        if os.getenv('JENKINS_URL'):
            detected_environment = 'jenkins'
        elif os.getenv('GITHUB_ACTIONS'):
            detected_environment = 'github-actions'
        elif os.getenv('GITLAB_CI'):
            detected_environment = 'gitlab-ci'
        elif os.getenv('CIRCLECI'):
            detected_environment = 'circle-ci'
        elif os.getenv('TRAVIS'):
            detected_environment = 'travis-ci'
        elif os.getenv('CI'):
            detected_environment = 'ci'
        else:
            detected_environment = 'local'
    
    # Detect Jenkins environment
    import os as os_module  # Ensure we have the os module
    is_jenkins = bool(os_module.getenv("JENKINS_URL"))
    jenkins_data = None
    if is_jenkins:
        jenkins_data = JenkinsIntegration.from_jenkins_env()
        click.echo(f"🏗️  Jenkins detected: {jenkins_data.job_name} build #{jenkins_data.build_number}")
        click.echo(f"   🌍 Environment: {detected_environment}")
        click.echo(f"   🔗 Build URL: {jenkins_data.build_url}")
        
        # Use Jenkins data for build/commit if not explicitly provided
        if build == "local-build" and jenkins_data.build_number:
            cfg.build_id = f"jenkins-{jenkins_data.build_number}"
        if commit == "local" and jenkins_data.git_commit != "unknown":
            cfg.commit_sha = jenkins_data.git_commit
    
    # Initialize team analyzer
    team_analyzer = TeamAnalyzer(cfg)
    
    # Expand glob
    paths = sorted(glob.glob(results))
    if not paths:
        click.echo(f"No result files found for glob: {results}", err=True)
        sys.exit(1)

    all_results = []
    for p in paths:
        fmt = detect_format(p)
        if fmt == "junit":  # includes TestNG
            all_results.extend(parse_junit_xml(p, default_suite=project))
        else:
            click.echo(f"Skipping unknown format file: {p}", err=True)

    # store in sqlite
    conn = get_conn(cfg.db_path)
    ensure_schema(conn)
    run_id = insert_run(
        conn,
        project=project,
        build_id=build,
        commit_sha=commit,
        meta={"mode":mode, "files":paths, "tier": cfg.tier.value, "environment": cfg.team_config.environment},
        results=all_results,
    )

    # compute across history (enhanced with team context)
    raw_rows = fetch_recent_tests(conn, project, limit_runs=50)
    flake_stats = team_analyzer.compute_flakiness_with_team_context(raw_rows)
    
    # Update flaky test tracking for time-to-fix analysis
    current_timestamp = int(time.time())
    update_flaky_test_tracking(conn, project, flake_stats, current_timestamp)
    
    # Get worst offenders (tests flaky longest)
    worst_offenders = get_worst_flaky_offenders(conn, project, limit=10)
    if worst_offenders:
        click.echo("\n🚨 Worst Flaky Test Offenders (Time-to-Fix Analysis):")
        for test_name, first_detected, last_seen, fixed, days_flaky, failures, status, current_days in worst_offenders[:5]:
            click.echo(f"  📅 {test_name}: {current_days} days flaky, {failures} failures ({status})")
    
    # Root cause clustering analysis
    cluster_analysis = cluster_failures_by_root_cause(all_results)
    if cluster_analysis:
        click.echo("\n🔍 Root Cause Clustering Analysis:")
        sorted_clusters = sorted(cluster_analysis.items(), 
                               key=lambda x: (x[1]['severity'], x[1]['count']), reverse=True)
        for cluster_key, cluster_info in sorted_clusters[:3]:
            severity_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
            emoji = severity_emoji.get(cluster_info['severity'], "⚪")
            click.echo(f"  {emoji} {cluster_info['signature']}: {cluster_info['count']} failures, "
                      f"{len(cluster_info['affected_tests'])} tests affected")
            recommendation = get_cluster_recommendations(cluster_key)
            click.echo(f"     💡 {recommendation}")
    
    # Display team insights if available
    if cfg.tier != FlakeRadarTier.FREE:
        team_insights = team_analyzer.get_team_dashboard_data()
        if team_insights:
            click.echo(f"\n🏢 Team Insights ({detected_environment} environment):")
            click.echo(f"  • Total team flaky tests: {team_insights.get('team_flaky_count', 'N/A')}")
            click.echo(f"  • Cross-environment issues: {team_insights.get('cross_env_issues', 'N/A')}")
            click.echo(f"  • Team members affected: {len(team_insights.get('affected_members', []))}")
            
            # Show dashboard URL for team collaboration
            dashboard_url = team_analyzer.get_dashboard_url(project)
            if dashboard_url:
                click.echo(f"  • 🌐 Team Dashboard: {dashboard_url}")
                click.echo(f"  • 👥 Active Contributors: {len(team_insights.get('contributors', []))}")
                
                # Show recent team activity
                recent_activity = team_insights.get('recent_activity', [])
                if recent_activity:
                    click.echo(f"  • 📈 Recent Activity:")
                    for activity in recent_activity[:3]:  # Show last 3 activities
                        contributor = activity.get('contributor', 'Unknown')
                        env = activity.get('environment', 'unknown')
                        test_count = activity.get('test_count', 0)
                        time_ago = activity.get('time_ago', 'recently')
                        click.echo(f"    - {contributor} ran {test_count} tests in {env} ({time_ago})")

    # augment AI suggestions for top N failers
    ai_cache = {}
    MAX_AI = 20
    failers_sorted = sorted(flake_stats.items(), key=lambda kv: kv[1]["fail_count"], reverse=True)[:MAX_AI]
    
    # Check if AI analysis is enabled
    import os
    ai_enabled = os.getenv("OPENAI_API_KEY") is not None
    if ai_enabled and failers_sorted:
        click.echo(f"🤖 Analyzing {len(failers_sorted)} failing tests with AI...")
    elif not ai_enabled:
        click.echo("ℹ️  AI analysis disabled (set OPENAI_API_KEY to enable)")
    
    for name, stats in failers_sorted:
        # find the first fail entry to pass to AI
        fail_cases = [r for r in all_results if r.full_name == name and r.status in ("fail","error")]
        if not fail_cases:
            continue
        case = fail_cases[0]
        ai = summarize_failure(case.error_type or "", case.error_message or "", case.error_details or "")
        ai_cache[name] = ai

    # flatten for report
    test_rows = []
    for name, stats in sorted(flake_stats.items(), key=lambda kv: kv[1]["flake_rate"], reverse=True):
        row = stats.copy()
        row["full_name"] = name
        row["ai"] = ai_cache.get(name)
        test_rows.append(row)

    # render HTML
    out_path = render_report(project, test_rows, report_out, worst_offenders, cluster_analysis)
    click.echo(f"Report written: {out_path}")

    # Pretty CLI summary table
    table = [
        [r["full_name"], r["pass_count"], r["fail_count"], r["total_runs"],
         r["transitions"], f"{r['flake_rate']*100:.1f}%", "YES" if r["suspect_flaky"] else "NO"]
        for r in test_rows[:50]
    ]
    click.echo(tabulate(table, headers=["Test","Pass","Fail","Total","Trans","Rate","Flaky?"], tablefmt="github"))

    # Submit to team backend (if enabled)
    if cfg.tier != FlakeRadarTier.FREE:
        # Get contributor information
        contributor_name = os.getenv("USER", "unknown")
        
        # Enhanced contributor info for Jenkins
        if is_jenkins and jenkins_data:
            contributor_name = f"{jenkins_data.triggered_by} (Jenkins)"
            
        analysis_data = {
            "project": project,
            "build_id": build,
            "commit_sha": commit,
            "environment": detected_environment,  # Use detected environment
            "contributor": contributor_name,  # Add contributor here
            "total_tests": len(all_results),
            "flaky_count": sum(1 for r in test_rows if r["suspect_flaky"]),
            "test_results": test_rows,
            "worst_offenders": worst_offenders,
            "cluster_analysis": cluster_analysis,
        }
        try:
            submitted = team_analyzer.submit_analysis_to_team(analysis_data)
            if submitted:
                # Send real-time notification to team dashboard  
                # Use the contributor we already determined
                
                # Enhanced contributor info for Jenkins
                if is_jenkins and jenkins_data:
                    contributor_name = f"{jenkins_data.triggered_by} (Jenkins)"
                
                run_summary = {
                    "contributor": contributor_name,
                    "project": project,
                    "environment": detected_environment,  # Use detected environment
                    "total_tests": len(all_results),
                    "flaky_tests": sum(1 for r in test_rows if r["suspect_flaky"]),
                    "build_id": build,
                    "commit_sha": commit,
                    "completion_time": datetime.utcnow().isoformat(),
                    "dashboard_update": True,
                    "source": "jenkins" if is_jenkins else "cli"
                }
                
                # Add Jenkins-specific data
                if is_jenkins and jenkins_data:
                    run_summary.update({
                        "jenkins_job": jenkins_data.job_name,
                        "jenkins_build": jenkins_data.build_number,
                        "jenkins_url": jenkins_data.build_url,
                        "git_branch": jenkins_data.git_branch,
                        "build_duration": jenkins_data.build_duration,
                        "build_status": jenkins_data.build_status
                    })
                
                # Notify team members via central dashboard
                notification_sent = team_analyzer.notify_team_of_completion(run_summary)
                if notification_sent:
                    click.echo("🔔 Team dashboard updated - results visible to all team members")
                    if is_jenkins and jenkins_data:
                        click.echo(f"🏗️  Jenkins build #{jenkins_data.build_number} results now in team dashboard")
                    dashboard_url = team_analyzer.get_dashboard_url(project)
                    if dashboard_url:
                        click.echo(f"📊 View team insights: {dashboard_url}")
                else:
                    click.echo("✅ Results submitted to team backend")
            else:
                click.echo("⚠️  Team submission failed (analysis completed locally)", err=True)
        except Exception as e:
            click.echo(f"⚠️  Team backend error: {e}", err=True)

    # publish to redis / kafka (non-blocking best-effort)
    summary_payload = {
        "project": project,
        "build_id": build,
        "commit": commit,
        "run_id": run_id,
        "total_tests": len(all_results),
        "flaky_count": sum(1 for r in test_rows if r["suspect_flaky"]),
        "tier": cfg.tier.value,
        "environment": detected_environment,
    }
    publish_to_redis(project, summary_payload)
    send_kafka_event(project, summary_payload)

    # Push mode is not implemented yet; we'll add in Iteration 2
    if mode == "push":
        click.echo("WARNING: push mode not implemented yet; local-only summary generated.", err=True)


def main():
    """Legacy entry point for backward compatibility."""
    cli()


if __name__ == "__main__":
    cli()