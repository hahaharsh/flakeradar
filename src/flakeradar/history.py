from __future__ import annotations
import os, sqlite3, json, time
from typing import Iterable, List, Tuple, Dict
from .model import TestCaseResult

DEFAULT_DB = os.path.expanduser("~/.flakeradar/history.db")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_ts INTEGER NOT NULL,
  project TEXT,
  build_id TEXT,
  commit_sha TEXT,
  meta_json TEXT
);
CREATE TABLE IF NOT EXISTS test_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id INTEGER NOT NULL,
  full_name TEXT NOT NULL,
  suite TEXT,
  status TEXT,
  duration_ms INTEGER,
  error_type TEXT,
  error_message TEXT,
  error_details TEXT,
  FOREIGN KEY(run_id) REFERENCES runs(id)
);
CREATE TABLE IF NOT EXISTS flaky_test_tracking (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  full_name TEXT NOT NULL,
  project TEXT NOT NULL,
  first_flaky_detected INTEGER NOT NULL,  -- timestamp when flakiness first detected
  last_flaky_seen INTEGER NOT NULL,       -- timestamp when last seen flaky
  fixed_timestamp INTEGER,                -- timestamp when test became stable again
  days_flaky INTEGER,                      -- total days test remained flaky
  total_failures_while_flaky INTEGER,     -- count of failures during flaky period
  root_cause_cluster TEXT,                -- clustered root cause category
  UNIQUE(full_name, project, first_flaky_detected)
);
CREATE INDEX IF NOT EXISTS idx_test_results_fullname ON test_results(full_name);
CREATE INDEX IF NOT EXISTS idx_flaky_tracking_project ON flaky_test_tracking(project);
CREATE INDEX IF NOT EXISTS idx_flaky_tracking_status ON flaky_test_tracking(fixed_timestamp);
"""

def get_conn(db_path: str = DEFAULT_DB) -> sqlite3.Connection:
    # Ensure the directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def ensure_schema(conn: sqlite3.Connection):
    conn.executescript(SCHEMA_SQL)
    conn.commit()

def insert_run(conn, project: str, build_id: str, commit_sha: str, meta: Dict, results: Iterable[TestCaseResult]) -> int:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO runs (run_ts, project, build_id, commit_sha, meta_json) VALUES (?,?,?,?,?)",
        (int(time.time()), project, build_id, commit_sha, json.dumps(meta or {})),
    )
    run_id = cur.lastrowid
    rows = [
        (
            run_id,
            r.full_name,
            r.suite,
            r.status,
            r.duration_ms,
            r.error_type,
            r.error_message,
            r.error_details,
        )
        for r in results
    ]
    cur.executemany(
        """INSERT INTO test_results
           (run_id, full_name, suite, status, duration_ms, error_type, error_message, error_details)
           VALUES (?,?,?,?,?,?,?,?)""",
        rows,
    )
    conn.commit()
    return run_id

def fetch_history(conn, project: str, full_name: str, limit: int = 50):
    cur = conn.cursor()
    cur.execute(
        """SELECT r.run_ts, t.status, t.error_type, t.error_message
             FROM test_results t
             JOIN runs r ON r.id = t.run_id
            WHERE r.project = ? AND t.full_name = ?
            ORDER BY r.run_ts DESC
            LIMIT ?""",
        (project, full_name, limit),
    )
    return cur.fetchall()

def fetch_recent_tests(conn, project: str, limit_runs: int = 10):
    cur = conn.cursor()
    cur.execute(
        """SELECT t.full_name, t.status
             FROM test_results t
             JOIN runs r ON r.id = t.run_id
            WHERE r.project = ?
            ORDER BY r.run_ts DESC
            LIMIT ?""",
        (project, limit_runs * 1000),  # coarse
    )
    return cur.fetchall()

def update_flaky_test_tracking(conn, project: str, flake_stats: Dict, current_timestamp: int):
    """Track lifecycle of flaky tests for time-to-fix analysis"""
    cur = conn.cursor()
    
    # Get currently flaky tests
    currently_flaky = {name: stats for name, stats in flake_stats.items() 
                      if stats.get("truly_flaky", False) or stats.get("always_failing", False)}
    
    # Get previously tracked flaky tests
    cur.execute("""
        SELECT full_name, first_flaky_detected, fixed_timestamp 
        FROM flaky_test_tracking 
        WHERE project = ? AND fixed_timestamp IS NULL
    """, (project,))
    previously_flaky = {row[0]: {"first_detected": row[1], "fixed": row[2]} 
                       for row in cur.fetchall()}
    
    # Update tracking for currently flaky tests
    for test_name, stats in currently_flaky.items():
        if test_name not in previously_flaky:
            # New flaky test detected
            cur.execute("""
                INSERT OR IGNORE INTO flaky_test_tracking 
                (full_name, project, first_flaky_detected, last_flaky_seen, 
                 total_failures_while_flaky, root_cause_cluster)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (test_name, project, current_timestamp, current_timestamp,
                  stats["fail_count"], None))
        else:
            # Update existing flaky test
            cur.execute("""
                UPDATE flaky_test_tracking 
                SET last_flaky_seen = ?, 
                    total_failures_while_flaky = total_failures_while_flaky + ?,
                    days_flaky = CAST((? - first_flaky_detected) / 86400 AS INTEGER)
                WHERE full_name = ? AND project = ? AND fixed_timestamp IS NULL
            """, (current_timestamp, stats["fail_count"], current_timestamp, 
                  test_name, project))
    
    # Mark tests as fixed if they're no longer flaky
    for test_name, tracking_info in previously_flaky.items():
        if test_name not in currently_flaky:
            days_flaky = (current_timestamp - tracking_info["first_detected"]) // 86400
            cur.execute("""
                UPDATE flaky_test_tracking 
                SET fixed_timestamp = ?, 
                    days_flaky = ?
                WHERE full_name = ? AND project = ? AND fixed_timestamp IS NULL
            """, (current_timestamp, days_flaky, test_name, project))
    
    conn.commit()

def get_worst_flaky_offenders(conn, project: str, limit: int = 10):
    """Get tests that have been flaky the longest"""
    cur = conn.cursor()
    cur.execute("""
        SELECT full_name, 
               first_flaky_detected,
               last_flaky_seen,
               fixed_timestamp,
               days_flaky,
               total_failures_while_flaky,
               CASE 
                   WHEN fixed_timestamp IS NULL THEN 'Still Flaky'
                   ELSE 'Fixed'
               END as status,
               CASE 
                   WHEN fixed_timestamp IS NULL 
                   THEN CAST((? - first_flaky_detected) / 86400 AS INTEGER)
                   ELSE days_flaky
               END as current_days_flaky
        FROM flaky_test_tracking 
        WHERE project = ?
        ORDER BY current_days_flaky DESC, total_failures_while_flaky DESC
        LIMIT ?
    """, (int(time.time()), project, limit))
    return cur.fetchall()