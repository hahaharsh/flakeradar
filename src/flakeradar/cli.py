from __future__ import annotations
import glob, os, sys, time
import click
from tabulate import tabulate
from argparse import Namespace

from .config import config_from_cli
from .parsers.detect import detect_format
from .parsers.junit import parse_junit_xml
from .history import get_conn, ensure_schema, insert_run, fetch_recent_tests, update_flaky_test_tracking, get_worst_flaky_offenders
from .analyzer import compute_flakiness
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
def main(project, results, logs, mode, build, commit, report_out):
    """
    Analyze test results locally; store in SQLite; emit flakiness summary.
    """
    args = click.get_current_context().params
    cfg = config_from_cli(Namespace(**args))  # cheap wrapper
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
        meta={"mode":mode, "files":paths},
        results=all_results,
    )

    # compute across history
    raw_rows = fetch_recent_tests(conn, project, limit_runs=50)
    flake_stats = compute_flakiness(raw_rows)
    
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

    # publish to redis / kafka (non-blocking best-effort)
    summary_payload = {
        "project": project,
        "build_id": build,
        "commit": commit,
        "run_id": run_id,
        "total_tests": len(all_results),
        "flaky_count": sum(1 for r in test_rows if r["suspect_flaky"]),
    }
    publish_to_redis(project, summary_payload)
    send_kafka_event(project, summary_payload)

    # Push mode is not implemented yet; we'll add in Iteration 2
    if mode == "push":
        click.echo("WARNING: push mode not implemented yet; local-only summary generated.", err=True)