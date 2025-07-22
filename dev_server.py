# Local Development Server for FlakeRadar Team Features

from flask import Flask, request, jsonify, render_template_string
from datetime import datetime, timedelta
import json
import os
import sqlite3
from pathlib import Path
import uuid
import secrets
import hashlib
from typing import Dict, List, Optional
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Local database setup
DB_PATH = Path.home() / ".flakeradar" / "local_team_db.sqlite3"
DB_PATH.parent.mkdir(exist_ok=True)

def init_db():
    """Initialize local SQLite database for development"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create tables for local development with token management
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS teams (
            id TEXT PRIMARY KEY,
            team_id TEXT UNIQUE NOT NULL,
            api_token TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS team_tokens (
            id TEXT PRIMARY KEY,
            team_id TEXT NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            permissions TEXT DEFAULT 'write',
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (team_id) REFERENCES teams(team_id)
        );
        
        CREATE TABLE IF NOT EXISTS test_executions (
            id TEXT PRIMARY KEY,
            team_id TEXT,
            project TEXT NOT NULL,
            environment TEXT NOT NULL,
            test_name TEXT NOT NULL,
            status TEXT NOT NULL,
            execution_time TIMESTAMP NOT NULL,
            build_id TEXT,
            commit_sha TEXT,
            jenkins_job TEXT,
            jenkins_build INTEGER,
            contributor TEXT,
            token_id TEXT,
            flaky_confidence REAL,
            failure_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (team_id) REFERENCES teams(team_id),
            FOREIGN KEY (token_id) REFERENCES team_tokens(id)
        );
        
        CREATE TABLE IF NOT EXISTS dashboard_metrics (
            id TEXT PRIMARY KEY,
            team_id TEXT,
            project TEXT,
            total_runs INTEGER DEFAULT 0,
            total_tests INTEGER DEFAULT 0,
            flaky_tests_count INTEGER DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (team_id) REFERENCES teams(team_id)
        );
        
        -- Insert a demo team for local development
        INSERT OR IGNORE INTO teams (id, team_id, api_token) 
        VALUES ('demo-team-id', 'local-dev-team', 'flake_tk_local_dev_demo_token123');
    """)
    
    conn.commit()
    conn.close()

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "service": "FlakeRadar Local Dev Server"})

@app.route('/api/v1/team/validate', methods=['POST'])
def validate_team():
    """Validate team token with enhanced security"""
    data = request.get_json()
    
    # Extract token from Authorization header or JSON
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header.replace('Bearer ', '')
    else:
        token = data.get('api_token') if data else None
    
    if not token:
        return jsonify({"error": "Missing api_token"}), 400
    
    # Validate token using our secure token system
    is_valid, team_id, token_id = validate_token(token)
    
    if is_valid:
        return jsonify({
            "valid": True,
            "team_id": team_id,
            "token_id": token_id,
            "tier": "team",
            "subscription": "TEAM",
            "message": "Token valid",
            "features": {
                "team_collaboration": True,
                "central_dashboard": True,
                "cross_environment": True,
                "jenkins_integration": True
            }
        })
    
    return jsonify({"error": "Invalid or expired token"}), 401

@app.route('/api/v1/team/submit', methods=['POST'])
def submit_team_results():
    """Submit test results to team dashboard"""
    data = request.get_json()
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not token.startswith('flake_tk_'):
        return jsonify({"error": "Invalid token"}), 401
    
    # Validate token and get team_id
    is_valid, team_id, token_id = validate_token(token)
    if not is_valid:
        return jsonify({"error": "Invalid or expired token"}), 401
    
    # Store in local database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Insert test executions (handle both 'executions' and 'tests' for compatibility)
    executions = data.get('executions', data.get('tests', []))
    processed_count = 0
    
    for test in executions:
        execution_id = str(uuid.uuid4())
        # Handle both formats: TestExecution.to_dict() and simple test objects
        test_name = test.get('test_name', test.get('name', 'unknown'))
        status = test.get('status', 'unknown').upper()
        execution_time = test.get('timestamp', test.get('execution_time', datetime.now().isoformat()))
        
        cursor.execute("""
            INSERT INTO test_executions 
            (id, team_id, project, environment, test_name, status, execution_time, 
             build_id, commit_sha, jenkins_job, jenkins_build, contributor, token_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            execution_id, team_id, test.get('project', data.get('project', 'Unknown')),
            test.get('environment', data.get('environment', 'default')), 
            test_name, status, execution_time, 
            test.get('build_id', data.get('build_id')),
            test.get('commit_sha', data.get('commit_sha')), 
            test.get('jenkins_url', data.get('jenkins_job')),
            test.get('jenkins_build', data.get('jenkins_build')), 
            test.get('contributor', data.get('contributor', 'cli-user')),
            token_id
        ))
        processed_count += 1
    
    # Update dashboard metrics
    project = data.get('project', 'Unknown')
    flaky_count = len([t for t in executions if t.get('flaky', False) or t.get('status', '').upper() == 'FAIL'])
    
    cursor.execute("""
        INSERT OR REPLACE INTO dashboard_metrics 
        (id, team_id, project, total_runs, total_tests, flaky_tests_count, last_updated)
        VALUES (?, ?, ?, 
                COALESCE((SELECT total_runs FROM dashboard_metrics WHERE team_id = ? AND project = ?), 0) + 1,
                ?, ?, ?)
    """, (
        str(uuid.uuid4()), team_id, project,
        team_id, project,
        len(executions), flaky_count,
        datetime.now().isoformat()
    ))
    
    conn.commit()
    conn.close()
    
    dashboard_url = f"http://localhost:8000/dashboard/{team_id}?project={project}"
    
    return jsonify({
        "status": "success",
        "team_id": team_id,
        "dashboard_url": dashboard_url,
        "tests_processed": processed_count,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/analysis/submit', methods=['POST'])
def submit_analysis():
    """Submit analysis results to team backend with token validation"""
    data = request.get_json()
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    # Validate token
    is_valid, team_id, token_id = validate_token(token)
    if not is_valid:
        return jsonify({"error": "Invalid or expired token"}), 401
    
    # Get test results from the data (handle nested structure from CLI)
    test_results = data.get('test_results', [])
    if not test_results and 'results' in data:
        # Handle nested structure from team_analyzer
        test_results = data['results'].get('test_results', [])
    
    # Extract metadata with better fallbacks
    project = data.get('project', 'Unknown')
    environment = data.get('environment', 'default')
    build_id = data.get('build_id')
    commit_sha = data.get('commit_sha') 
    
    # Better contributor detection
    contributor = (data.get('contributor') or 
                  data.get('metadata', {}).get('contributor') or
                  os.getenv('USER') or 
                  os.getenv('USERNAME') or
                  'Unknown')
    
    # Better environment detection 
    if environment == 'default':
        # Try to infer from common environment variables
        environment = (os.getenv('CI_ENVIRONMENT_NAME') or 
                      os.getenv('ENVIRONMENT') or 
                      os.getenv('NODE_ENV') or
                      'local')
        
    # Log analysis submission
    print(f"📊 Analysis submitted: {project} - {len(test_results)} tests")
    
    # Save test results to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    analysis_id = str(uuid.uuid4())
    
    # Insert test executions
    for test in test_results:
        test_id = str(uuid.uuid4())
        # Handle different field names from CLI vs other sources
        test_name = (test.get('test_name') or 
                    test.get('full_name') or 
                    test.get('name') or 
                    'Unknown Test')
        
        # Handle status - if suspect_flaky is True, it's likely a failed test
        if test.get('suspect_flaky', False):
            status = 'FAIL'
        elif test.get('status'):
            status = test.get('status').upper()
        elif test.get('fail_count', 0) > 0:
            status = 'FAIL' 
        else:
            status = 'PASS'
            
        # Only store confidence scores for tests that are actually suspect flaky
        # For non-flaky tests, confidence should be NULL (not displayed in dashboard)
        if test.get('suspect_flaky', False):
            flaky_confidence = test.get('confidence', 0.0) or test.get('confidence_score', 0.0)
        else:
            # Non-flaky tests should not have confidence scores displayed
            flaky_confidence = None
            
        failure_reason = test.get('failure_reason') or test.get('error_message')
        
        cursor.execute("""
            INSERT INTO test_executions 
            (id, team_id, project, environment, test_name, status, execution_time, 
             build_id, commit_sha, contributor, token_id, flaky_confidence, failure_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (test_id, team_id, project, environment, test_name, status, 
              datetime.now().isoformat(), build_id, commit_sha, contributor, 
              token_id, flaky_confidence, failure_reason))
    
    # Update dashboard metrics
    cursor.execute("""
        INSERT OR REPLACE INTO dashboard_metrics 
        (team_id, project, total_runs, total_tests, flaky_tests_count, last_updated)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (team_id, project, len(test_results), len(test_results), 
          sum(1 for t in test_results if t.get('suspect_flaky', False)),
          datetime.now().isoformat()))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        "status": "success",
        "analysis_id": analysis_id,
        "team_id": "local-dev-team",
        "tests_stored": len(test_results),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/test/cross-env', methods=['GET'])
def get_cross_env_test():
    """Get cross-environment test data"""
    test_name = request.args.get('test_name')
    
    # Simulate cross-environment data
    return jsonify({
        "test_name": test_name,
        "environments": {
            "staging": {"runs": 5, "failures": 1, "flaky": True},
            "production": {"runs": 3, "failures": 0, "flaky": False},
            "development": {"runs": 8, "failures": 3, "flaky": True}
        },
        "cross_env_flaky": True,
        "flakiness_score": 0.25
    })

@app.route('/insights/team', methods=['GET'])
def get_team_insights():
    """Get team insights"""
    project = request.args.get('project')
    environment = request.args.get('environment')
    
    return jsonify({
        "project": project,
        "environment": environment,
        "team_id": "local-dev-team",
        "insights": {
            "total_team_runs": 15,
            "cross_env_issues": 8,
            "team_members_affected": 3,
            "recent_contributors": ["local-user", "alice", "bob"],
            "flaky_tests_trend": "increasing",
            "recommendation": "Focus on database connectivity issues"
        },
        "timestamp": datetime.now().isoformat()
    })

@app.route('/v1/notifications/send', methods=['POST'])
def send_notification():
    """Send team notification"""
    data = request.get_json()
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not token.startswith('flake_tk_'):
        return jsonify({"error": "Invalid token"}), 401
    
    # Log notification
    print(f"🔔 Team notification: {data.get('message', 'No message')}")
    print(f"   Recipients: {len(data.get('recipients', []))} members")
    print(f"   Type: {data.get('type', 'unknown')}")
    
    return jsonify({
        "status": "success",
        "notification_id": str(uuid.uuid4()),
        "recipients_notified": len(data.get('recipients', [])),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/v1/team/dashboard/<team_id>')
def get_dashboard_data(team_id):
    """Get dashboard data for team"""
    project = request.args.get('project')
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get dashboard metrics
    if project:
        cursor.execute("""
            SELECT team_id, project, total_runs, total_tests, flaky_tests_count, last_updated
            FROM dashboard_metrics 
            WHERE team_id = ? AND project = ?
            ORDER BY last_updated DESC LIMIT 1
        """, (team_id, project))
    else:
        cursor.execute("""
            SELECT team_id, project, total_runs, total_tests, flaky_tests_count, last_updated
            FROM dashboard_metrics 
            WHERE team_id = ?
            ORDER BY last_updated DESC
        """, (team_id,))
    
    metrics_rows = cursor.fetchall()
    metrics_columns = ['team_id', 'project', 'total_runs', 'total_tests', 'flaky_tests_count', 'last_updated']
    
    # Get recent test executions
    cursor.execute("""
        SELECT project, environment, test_name, status, execution_time, 
               jenkins_job, jenkins_build, contributor
        FROM test_executions 
        WHERE team_id = ?
        ORDER BY created_at DESC LIMIT 50
    """, (team_id,))
    
    recent_tests_rows = cursor.fetchall()
    recent_tests_columns = ['project', 'environment', 'test_name', 'status', 'execution_time',
                           'jenkins_job', 'jenkins_build', 'contributor']
    
    conn.close()
    
    # Convert to dictionaries
    metrics = [dict(zip(metrics_columns, row)) for row in metrics_rows]
    recent_activity = [dict(zip(recent_tests_columns, row)) for row in recent_tests_rows]
    
    return jsonify({
        "team_id": team_id,
        "metrics": metrics,
        "recent_activity": recent_activity
    })

@app.route('/dashboard/<team_id>')
def dashboard(team_id):
    """Comprehensive FlakeRadar Team Dashboard"""
    project = request.args.get('project', 'all')
    
    # Get enhanced dashboard data
    dashboard_data = get_enhanced_dashboard_data(team_id, project)
    
    # Get available projects for the dropdown
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT project FROM dashboard_metrics WHERE team_id = ? ORDER BY project", (team_id,))
    available_projects = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    return render_template_string(DASHBOARD_TEMPLATE, 
                                team_id=team_id, 
                                project=project,
                                available_projects=available_projects,
                                **dashboard_data)

def get_enhanced_dashboard_data(team_id: str, project: str = 'all') -> dict:
    """Get comprehensive dashboard data with real insights"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Base metrics with actual calculations
    if project != 'all':
        # Get real test execution data
        cursor.execute("""
            SELECT COUNT(*) as total_executions, 
                   COUNT(DISTINCT test_name) as unique_tests,
                   COUNT(CASE WHEN status = 'FAIL' THEN 1 END) as failures,
                   COUNT(CASE WHEN flaky_confidence > 0.5 THEN 1 END) as flaky_tests,
                   AVG(CASE WHEN flaky_confidence IS NOT NULL THEN flaky_confidence ELSE 0 END) as avg_confidence
            FROM test_executions 
            WHERE team_id = ? AND project = ?
        """, (team_id, project))
        
        execution_stats = cursor.fetchone()
        total_executions = execution_stats[0] or 0
        unique_tests = execution_stats[1] or 0
        failures = execution_stats[2] or 0
        flaky_tests = execution_stats[3] or 0
        avg_confidence = execution_stats[4] or 0
        
        # Calculate real metrics
        pass_rate = ((total_executions - failures) / total_executions * 100) if total_executions > 0 else 100
        flakiness_rate = (flaky_tests / unique_tests * 100) if unique_tests > 0 else 0
        
        # Get recent activity with confidence scores
        cursor.execute("""
            SELECT project, environment, test_name, status, execution_time, 
                   contributor, flaky_confidence, failure_reason, created_at
            FROM test_executions 
            WHERE team_id = ? AND project = ?
            ORDER BY created_at DESC LIMIT 25
        """, (team_id, project))
        
    else:
        # Aggregate data for all projects
        cursor.execute("""
            SELECT COUNT(*) as total_executions, 
                   COUNT(DISTINCT test_name) as unique_tests,
                   COUNT(CASE WHEN status = 'FAIL' THEN 1 END) as failures,
                   COUNT(CASE WHEN flaky_confidence > 0.5 THEN 1 END) as flaky_tests,
                   AVG(CASE WHEN flaky_confidence IS NOT NULL THEN flaky_confidence ELSE 0 END) as avg_confidence
            FROM test_executions 
            WHERE team_id = ?
        """, (team_id,))
        
        execution_stats = cursor.fetchone()
        total_executions = execution_stats[0] or 0
        unique_tests = execution_stats[1] or 0
        failures = execution_stats[2] or 0
        flaky_tests = execution_stats[3] or 0
        avg_confidence = execution_stats[4] or 0
        
        pass_rate = ((total_executions - failures) / total_executions * 100) if total_executions > 0 else 100
        flakiness_rate = (flaky_tests / unique_tests * 100) if unique_tests > 0 else 0
        
        cursor.execute("""
            SELECT project, environment, test_name, status, execution_time, 
                   contributor, flaky_confidence, failure_reason, created_at
            FROM test_executions 
            WHERE team_id = ?
            ORDER BY created_at DESC LIMIT 25
        """, (team_id,))
    
    recent_activity = []
    for row in cursor.fetchall():
        recent_activity.append({
            'project': row[0],
            'environment': row[1] or 'default',
            'test_name': row[2],
            'status': row[3],
            'execution_time': row[4],
            'contributor': row[5] or 'Unknown',
            'flaky_confidence': row[6],
            'failure_reason': row[7],
            'created_at': row[8]
        })
    
    # Get flaky test trends for charts
    cursor.execute("""
        SELECT DATE(created_at) as date, 
               COUNT(*) as total_tests,
               COUNT(CASE WHEN status = 'FAIL' THEN 1 END) as failures,
               COUNT(CASE WHEN flaky_confidence > 0.5 THEN 1 END) as flaky_tests
        FROM test_executions 
        WHERE team_id = ? {}
        AND created_at >= date('now', '-7 days')
        GROUP BY DATE(created_at)
        ORDER BY date
    """.format("AND project = ?" if project != 'all' else ""), 
    (team_id, project) if project != 'all' else (team_id,))
    
    trend_data = cursor.fetchall()
    
    # Get top flaky tests with confidence scores
    cursor.execute("""
        SELECT test_name, 
               COUNT(*) as total_runs,
               COUNT(CASE WHEN status = 'FAIL' THEN 1 END) as failures,
               AVG(CASE WHEN flaky_confidence IS NOT NULL THEN flaky_confidence ELSE 0 END) as avg_confidence,
               MAX(flaky_confidence) as max_confidence
        FROM test_executions 
        WHERE team_id = ? {}
        AND flaky_confidence > 0
        GROUP BY test_name
        ORDER BY avg_confidence DESC, failures DESC
        LIMIT 10
    """.format("AND project = ?" if project != 'all' else ""), 
    (team_id, project) if project != 'all' else (team_id,))
    
    flaky_tests_list = []
    for row in cursor.fetchall():
        failure_rate = (row[2] / row[1] * 100) if row[1] > 0 else 0
        flaky_tests_list.append({
            'test_name': row[0],
            'total_runs': row[1],
            'failures': row[2],
            'failure_rate': failure_rate,
            'avg_confidence': row[3],
            'max_confidence': row[4]
        })
    
    # Get contributors
    cursor.execute("""
        SELECT contributor, 
               COUNT(*) as total_tests,
               COUNT(CASE WHEN status = 'FAIL' THEN 1 END) as failures
        FROM test_executions 
        WHERE team_id = ? {}
        AND contributor IS NOT NULL
        AND created_at >= date('now', '-7 days')
        GROUP BY contributor
        ORDER BY total_tests DESC
        LIMIT 10
    """.format("AND project = ?" if project != 'all' else ""), 
    (team_id, project) if project != 'all' else (team_id,))
    
    contributors = []
    for row in cursor.fetchall():
        success_rate = ((row[1] - row[2]) / row[1] * 100) if row[1] > 0 else 100
        contributors.append({
            'name': row[0],
            'total_tests': row[1],
            'failures': row[2],
            'success_rate': success_rate
        })
    
    # Get environment breakdown 
    cursor.execute("""
        SELECT environment, 
               COUNT(*) as total_tests,
               COUNT(CASE WHEN status = 'FAIL' THEN 1 END) as failures
        FROM test_executions 
        WHERE team_id = ? {}
        AND created_at >= date('now', '-7 days')
        GROUP BY environment
        ORDER BY total_tests DESC
    """.format("AND project = ?" if project != 'all' else ""), 
    (team_id, project) if project != 'all' else (team_id,))
    
    environment_data = cursor.fetchall()
    
    conn.close()
    
    has_data = total_executions > 0
    
    return {
        'has_data': has_data,
        'metrics': {
            'total_executions': total_executions,
            'unique_tests': unique_tests,
            'failures': failures,
            'flaky_tests': flaky_tests,
            'pass_rate': pass_rate,
            'flakiness_rate': flakiness_rate,
            'avg_confidence': avg_confidence * 100  # Convert to percentage
        },
        'recent_activity': recent_activity,
        'trend_data': [{'date': row[0], 'total_tests': row[1], 'failures': row[2], 'flaky_tests': row[3]} for row in trend_data],
        'flaky_tests_list': flaky_tests_list,
        'contributors': contributors,
        'environment_data': environment_data
    }
    
# Comprehensive Dashboard Template
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FlakeRadar Team Dashboard - {{ team_id }}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
:root {
  --primary-color: #6366f1;
  --primary-light: #818cf8;
  --primary-dark: #4f46e5;
  --secondary-color: #06b6d4;
  --success-color: #059669;
  --success-light: #10b981;
  --warning-color: #d97706;
  --warning-light: #f59e0b;
  --danger-color: #dc2626;
  --danger-light: #ef4444;
  --purple-color: #7c3aed;
  --pink-color: #ec4899;
  
  --gray-50: #f8fafc;
  --gray-100: #f1f5f9;
  --gray-200: #e2e8f0;
  --gray-300: #cbd5e1;
  --gray-400: #94a3b8;
  --gray-500: #64748b;
  --gray-600: #475569;
  --gray-700: #334155;
  --gray-800: #1e293b;
  --gray-900: #0f172a;
  
  --border-radius: 16px;
  --border-radius-sm: 8px;
  --border-radius-lg: 24px;
  
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: linear-gradient(135deg, var(--gray-50) 0%, var(--gray-100) 100%);
  color: var(--gray-900);
  line-height: 1.6;
  min-height: 100vh;
}

/* Header */
.header {
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--purple-color) 100%);
  color: white;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: var(--shadow-lg);
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
}

.logo {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 1.5rem;
  font-weight: 700;
}

.logo i {
  font-size: 2rem;
  color: var(--warning-light);
}

.project-info {
  text-align: right;
}

.project-name {
  font-size: 1.25rem;
  font-weight: 600;
  margin-bottom: 0.25rem;
}

.generated-time {
  opacity: 0.8;
  font-size: 0.9rem;
}

/* Container */
}

/* Navigation Controls */
.nav-controls {
  background: white;
  border-top: 1px solid var(--gray-200);
  padding: 1rem 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.project-selector {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.project-selector label {
  font-weight: 600;
  color: var(--gray-700);
}

.project-selector select {
  padding: 0.5rem 1rem;
  border: 1px solid var(--gray-300);
  border-radius: var(--border-radius-sm);
  font-size: 0.9rem;
  background: white;
  cursor: pointer;
}

.token-actions {
  display: flex;
  gap: 0.75rem;
}

.btn-primary, .btn-secondary {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: var(--border-radius-sm);
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  transition: all 0.2s ease;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
}

.btn-primary:hover {
  background: var(--primary-dark);
  transform: translateY(-1px);
}

.btn-secondary {
  background: var(--gray-100);
  color: var(--gray-700);
  border: 1px solid var(--gray-300);
}

.btn-secondary:hover {
  background: var(--gray-200);
  transform: translateY(-1px);
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.stat-card {
  background: white;
  border-radius: var(--border-radius);
  padding: 1.5rem;
  box-shadow: var(--shadow-md);
  border: 1px solid var(--gray-200);
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, var(--primary-color), var(--purple-color));
}

.stat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.stat-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--gray-600);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
}

.icon-total { background: linear-gradient(135deg, var(--primary-color), var(--primary-light)); color: white; }
.icon-flaky { background: linear-gradient(135deg, var(--danger-color), var(--danger-light)); color: white; }
.icon-success { background: linear-gradient(135deg, var(--success-color), var(--success-light)); color: white; }
.icon-confidence { background: linear-gradient(135deg, var(--purple-color), var(--primary-light)); color: white; }
.icon-critical { background: linear-gradient(135deg, var(--warning-color), var(--warning-light)); color: white; }

.stat-value {
  font-size: 2.5rem;
  font-weight: 800;
  color: var(--gray-900);
  margin-bottom: 0.5rem;
}

.stat-change {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
  color: var(--gray-600);
}

/* Charts and Tables */
.section {
  background: white;
  border-radius: var(--border-radius);
  padding: 1.5rem;
  margin-bottom: 2rem;
  box-shadow: var(--shadow-md);
  border: 1px solid var(--gray-200);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--gray-200);
}

.section-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--gray-900);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.section-description {
  color: var(--gray-600);
  font-size: 0.9rem;
  margin-top: 0.25rem;
}

/* Tables */
.table-wrapper {
  overflow-x: auto;
  border-radius: var(--border-radius-sm);
  border: 1px solid var(--gray-200);
}

table {
  width: 100%;
  border-collapse: collapse;
}

th, td {
  padding: 1rem;
  text-align: left;
  border-bottom: 1px solid var(--gray-200);
}

th {
  background: var(--gray-50);
  font-weight: 600;
  color: var(--gray-700);
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

tbody tr:hover {
  background: var(--gray-50);
}

.test-name {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.9rem;
  color: var(--gray-800);
  word-break: break-all;
}

.status-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.status-pass { background: var(--success-color); color: white; }
.status-fail { background: var(--danger-color); color: white; }
.status-warn { background: var(--warning-color); color: white; }

.confidence-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.confidence-high { background: var(--danger-color); color: white; }
.confidence-medium { background: var(--warning-color); color: white; }
.confidence-low { background: var(--success-color); color: white; }

.priority-high { color: var(--danger-color); font-weight: 600; }
.priority-medium { color: var(--warning-color); font-weight: 600; }
.priority-low { color: var(--success-color); font-weight: 600; }

/* Charts */
.chart-container {
  position: relative;
  height: 300px;
  margin: 1rem 0;
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: 3rem 1rem;
  color: var(--gray-500);
}

.empty-state i {
  font-size: 4rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.empty-state h3 {
  font-size: 1.25rem;
  margin-bottom: 0.5rem;
  color: var(--gray-700);
}

.empty-state p {
  margin-bottom: 1.5rem;
}

.token-generator {
  background: var(--gray-100);
  border-radius: var(--border-radius-sm);
  padding: 1rem;
  margin: 1rem auto;
  max-width: 600px;
}

.token-generator h4 {
  margin-bottom: 0.5rem;
  color: var(--gray-800);
}

.token-generator button {
  background: var(--primary-color);
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: var(--border-radius-sm);
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s ease;
}

.token-generator button:hover {
  background: var(--primary-dark);
  transform: translateY(-1px);
}

.token-display {
  background: var(--gray-900);
  color: var(--success-light);
  font-family: 'JetBrains Mono', monospace;
  padding: 1rem;
  border-radius: var(--border-radius-sm);
  margin: 1rem 0;
  word-break: break-all;
  font-size: 0.9rem;
}

/* Modal Styles */
.modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: var(--border-radius);
  max-width: 600px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid var(--gray-200);
}

.modal-header h3 {
  margin: 0;
  color: var(--gray-800);
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: var(--gray-500);
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  color: var(--gray-700);
}

.modal-body {
  padding: 1.5rem;
}

.token-form {
  margin: 1rem 0;
}

.token-form label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: var(--gray-700);
}

.token-form input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid var(--gray-300);
  border-radius: var(--border-radius-sm);
  margin-bottom: 1rem;
  font-size: 0.9rem;
}

.command-example {
  background: var(--gray-100);
  border-radius: var(--border-radius-sm);
  padding: 1rem;
  position: relative;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.85rem;
}

.copy-btn {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  background: var(--primary-color);
  color: white;
  border: none;
  padding: 0.25rem 0.5rem;
  border-radius: var(--border-radius-sm);
  cursor: pointer;
  font-size: 0.8rem;
}

.copy-btn:hover {
  background: var(--primary-dark);
}

/* Responsive */
@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    text-align: center;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .stat-value {
    font-size: 2rem;
  }
  
  table {
    font-size: 0.9rem;
  }
  
  th, td {
    padding: 0.75rem 0.5rem;
  }
}

/* Auto-refresh indicator */
.refresh-indicator {
  position: fixed;
  top: 1rem;
  right: 1rem;
  background: var(--success-color);
  color: white;
  padding: 0.5rem 1rem;
  border-radius: var(--border-radius-sm);
  font-size: 0.8rem;
  opacity: 0;
  transition: opacity 0.3s ease;
  z-index: 1000;
}

.refresh-indicator.show {
  opacity: 1;
}

.pulse {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.5; }
  100% { opacity: 1; }
}
</style>
</head>
<body>
  <div class="refresh-indicator" id="refreshIndicator">
    <i class="fas fa-sync"></i> Auto-refreshing...
  </div>

  <header class="header">
    <div class="header-content">
      <div class="logo">
        <i class="fas fa-radar"></i>
        <span>FlakeRadar Team Dashboard</span>
      </div>
      <div class="project-info">
        <div class="project-name">
          Team: {{ team_id }}
          {% if project != 'all' %} | Project: {{ project }}{% endif %}
        </div>
        <div class="generated-time">
          <i class="fas fa-clock"></i>
          Last updated: <span id="lastUpdated">now</span>
        </div>
      </div>
    </div>
    
    <!-- Navigation Controls -->
    <div class="nav-controls">
      <div class="project-selector">
        <label for="projectSelect"><i class="fas fa-folder"></i> Project:</label>
        <select id="projectSelect" onchange="switchProject()">
          <option value="all" {% if project == 'all' %}selected{% endif %}>All Projects</option>
          {% for proj in available_projects %}
          <option value="{{ proj }}" {% if project == proj %}selected{% endif %}>{{ proj }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="token-actions">
        <button onclick="showTokenGenerator()" class="btn-secondary">
          <i class="fas fa-key"></i> Create Token
        </button>
        <button onclick="window.location.reload()" class="btn-primary">
          <i class="fas fa-sync"></i> Refresh
        </button>
      </div>
    </div>
  </header>

  <div class="container">
    {% if has_data %}
    <!-- Stats Overview -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-header">
          <div class="stat-title">Total Tests</div>
          <div class="stat-icon icon-total">
            <i class="fas fa-vials"></i>
          </div>
        </div>
        <div class="stat-value">{{ metrics.unique_tests }}</div>
        <div class="stat-change">
          <i class="fas fa-chart-line"></i>
          {{ metrics.total_executions }} total executions
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-header">
          <div class="stat-title">Flaky Tests</div>
          <div class="stat-icon icon-flaky">
            <i class="fas fa-exclamation-triangle"></i>
          </div>
        </div>
        <div class="stat-value">{{ metrics.flaky_tests }}</div>
        <div class="stat-change">
          <i class="fas fa-percentage"></i>
          {{ "%.1f"|format(metrics.flakiness_rate) }}% flakiness rate
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-header">
          <div class="stat-title">Pass Rate</div>
          <div class="stat-icon icon-success">
            <i class="fas fa-check-circle"></i>
          </div>
        </div>
        <div class="stat-value">{{ "%.1f"|format(metrics.pass_rate) }}%</div>
        <div class="stat-change">
          <i class="fas fa-arrow-up"></i>
          Test reliability
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-header">
          <div class="stat-title">Confidence Score</div>
          <div class="stat-icon icon-confidence">
            <i class="fas fa-bullseye"></i>
          </div>
        </div>
        <div class="stat-value">{{ "%.1f"|format(metrics.avg_confidence) }}%</div>
        <div class="stat-change">
          <i class="fas fa-brain"></i>
          ML prediction accuracy
        </div>
      </div>
        <div class="stat-header">
          <div class="stat-title">Critical Issues</div>
          <div class="stat-icon icon-critical">
            <i class="fas fa-fire"></i>
          </div>
        </div>
        <div class="stat-value">{{ flaky_tests|length }}</div>
        <div class="stat-change">
          <i class="fas fa-exclamation-circle"></i>
          Need attention
        </div>
      </div>
    </div>

    <!-- Trends Chart -->
    {% if trend_data %}
    <div class="section">
      <div class="section-header">
        <div>
          <h2 class="section-title">
            <i class="fas fa-chart-line"></i>
            Test Execution Trends
          </h2>
          <p class="section-description">
            Daily test execution and failure trends over the last 30 days
          </p>
        </div>
      </div>
      <div class="chart-container">
        <canvas id="trendsChart"></canvas>
      </div>
    </div>
    {% endif %}

    <!-- Top Flaky Tests -->
    {% if flaky_tests_list %}
    <div class="section">
      <div class="section-header">
        <div>
          <h2 class="section-title">
            <i class="fas fa-bug"></i>
            Top Flaky Tests (With Confidence Scores)
          </h2>
          <p class="section-description">
            Tests with the highest confidence scores for flakiness - prioritize these for fixes
          </p>
        </div>
      </div>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Test Name</th>
              <th>Total Runs</th>
              <th>Failures</th>
              <th>Failure Rate</th>
              <th>Avg Confidence</th>
              <th>Max Confidence</th>
            </tr>
          </thead>
          <tbody>
            {% for test in flaky_tests_list %}
            <tr>
              <td class="test-name">{{ test.test_name }}</td>
              <td>{{ test.total_runs }}</td>
              <td>{{ test.failures }}</td>
              <td>
                <span class="status-badge {% if test.failure_rate > 50 %}status-fail{% elif test.failure_rate > 25 %}status-warn{% else %}status-pass{% endif %}">
                  {{ "%.1f"|format(test.failure_rate) }}%
                </span>
              </td>
              <td>
                <span class="confidence-badge {% if test.avg_confidence > 0.7 %}confidence-high{% elif test.avg_confidence > 0.4 %}confidence-medium{% else %}confidence-low{% endif %}">
                  {{ "%.1f"|format(test.avg_confidence * 100) }}%
                </span>
              </td>
              <td>
                <span class="confidence-badge {% if test.max_confidence > 0.8 %}confidence-high{% elif test.max_confidence > 0.5 %}confidence-medium{% else %}confidence-low{% endif %}">
                  {{ "%.1f"|format(test.max_confidence * 100) }}%
                </span>
              </td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
    {% endif %}

    <!-- Environment Breakdown -->
    {% if environment_data %}
    <div class="section">
      <div class="section-header">
        <div>
          <h2 class="section-title">
            <i class="fas fa-server"></i>
            Environment Breakdown
          </h2>
          <p class="section-description">
            Test execution across different environments
          </p>
        </div>
      </div>
      <div class="chart-container">
        <canvas id="environmentChart"></canvas>
      </div>
    </div>
    {% endif %}

    <!-- Recent Activity -->
    <div class="section">
      <div class="section-header">
        <div>
          <h2 class="section-title">
            <i class="fas fa-history"></i>
            Recent Test Activity
          </h2>
          <p class="section-description">
            Latest test executions from your team members
          </p>
        </div>
      </div>
      {% if recent_activity %}
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Test Name</th>
              <th>Status</th>
              <th>Environment</th>
              <th>Contributor</th>
              <th>Confidence</th>
              <th>Executed</th>
            </tr>
          </thead>
          <tbody>
            {% for activity in recent_activity[:20] %}
            <tr>
              <td class="test-name">{{ activity.test_name }}</td>
              <td>
                <span class="status-badge status-{{ activity.status.lower() }}">
                  {{ activity.status }}
                </span>
              </td>
              <td>{{ activity.environment }}</td>
              <td>{{ activity.contributor }}</td>
              <td>
                {% if activity.flaky_confidence %}
                  {{ "%.1f"|format(activity.flaky_confidence) }}%
                {% else %}
                  N/A
                {% endif %}
              </td>
              <td>{{ activity.created_at[:16] if activity.created_at else 'N/A' }}</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
      {% else %}
      <div class="empty-state">
        <i class="fas fa-clock"></i>
        <h3>No recent activity</h3>
        <p>Test executions will appear here as your team submits results.</p>
      </div>
      {% endif %}
    </div>

    <!-- Contributors -->
    {% if contributors %}
    <div class="section">
      <div class="section-header">
        <div>
          <h2 class="section-title">
            <i class="fas fa-users"></i>
            Top Contributors (Last 7 Days)
          </h2>
          <p class="section-description">
            Team members contributing test executions
          </p>
        </div>
      </div>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Contributor</th>
              <th>Total Tests</th>
              <th>Failures</th>
              <th>Success Rate</th>
            </tr>
          </thead>
          <tbody>
            {% for contributor in contributors %}
            <tr>
              <td>{{ contributor.name }}</td>
              <td>{{ contributor.total_tests }}</td>
              <td>{{ contributor.failures }}</td>
              <td>
                <span class="status-badge {% if contributor.success_rate > 80 %}status-pass{% else %}status-fail{% endif %}">
                  {{ "%.1f"|format(contributor.success_rate) }}%
                </span>
              </td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
    {% endif %}

    {% else %}
    <!-- Empty State -->
    <div class="section">
      <div class="empty-state">
        <i class="fas fa-radar"></i>
        <h3>Welcome to FlakeRadar Team Dashboard</h3>
        <p>No test data yet. Generate a token below and share it with your team members to start collecting test results.</p>
        
        <div class="token-generator">
          <h4><i class="fas fa-key"></i> Generate Team Token</h4>
          <p>Create a secure token to share with team members for submitting test data.</p>
          <button onclick="generateToken()">
            <i class="fas fa-plus"></i> Generate New Token
          </button>
          <div id="tokenResult" style="display: none;">
            <h5>Your Team Token:</h5>
            <div class="token-display" id="generatedToken"></div>
            <p><strong>Share this token with your team:</strong></p>
            <pre><code>flakeradar --project "YourProject" --team-token "YOUR_TOKEN" --results "*.xml"</code></pre>
          </div>
        </div>
      </div>
    </div>
    {% endif %}
  </div>

  <!-- Token Generator Modal -->
  <div id="tokenModal" class="modal" style="display: none;">
    <div class="modal-content">
      <div class="modal-header">
        <h3><i class="fas fa-key"></i> Generate Team Token</h3>
        <button onclick="hideTokenGenerator()" class="close-btn">&times;</button>
      </div>
      <div class="modal-body">
        <p>Create a secure token to share with team members for submitting test data.</p>
        <div class="token-form">
          <label for="tokenName">Token Name:</label>
          <input type="text" id="tokenName" placeholder="e.g., QA Team, Jenkins CI, John's Token" value="Dashboard Generated Token">
          <button onclick="generateToken()" class="btn-primary">
            <i class="fas fa-plus"></i> Generate New Token
          </button>
        </div>
        <div id="tokenResult" style="display: none;">
          <h4>Your Team Token:</h4>
          <div class="token-display" id="generatedToken"></div>
          <p><strong>Share this command with your team:</strong></p>
          <div class="command-example">
            <code>flakeradar --project "YourProject" --team-token "<span id="tokenInCommand"></span>" --results "*.xml"</code>
            <button onclick="copyToken()" class="copy-btn">
              <i class="fas fa-copy"></i> Copy
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <script>
    // Auto-refresh functionality
    let refreshTimer;
    const REFRESH_INTERVAL = 30000; // 30 seconds

    function showRefreshIndicator() {
      const indicator = document.getElementById('refreshIndicator');
      if (indicator) {
        indicator.classList.add('show');
        setTimeout(() => indicator.classList.remove('show'), 2000);
      }
    }

    function updateLastUpdated() {
      document.getElementById('lastUpdated').textContent = new Date().toLocaleTimeString();
    }

    function startAutoRefresh() {
      refreshTimer = setInterval(() => {
        showRefreshIndicator();
        setTimeout(() => {
          window.location.reload();
        }, 1000);
      }, REFRESH_INTERVAL);
    }

    // Project switching
    function switchProject() {
      const select = document.getElementById('projectSelect');
      const selectedProject = select.value;
      const currentTeamId = '{{ team_id }}';
      
      if (selectedProject === 'all') {
        window.location.href = `/dashboard/${currentTeamId}`;
      } else {
        window.location.href = `/dashboard/${currentTeamId}?project=${encodeURIComponent(selectedProject)}`;
      }
    }

    // Modal management
    function showTokenGenerator() {
      document.getElementById('tokenModal').style.display = 'flex';
      // Set default token name with timestamp
      const now = new Date().toISOString().slice(0, 16);
      document.getElementById('tokenName').value = `Dashboard Generated Token - ${now}`;
    }

    function hideTokenGenerator() {
      document.getElementById('tokenModal').style.display = 'none';
      // Reset form
      document.getElementById('tokenResult').style.display = 'none';
      document.getElementById('generatedToken').textContent = '';
    }

    // Token generation
    async function generateToken() {
      const tokenName = document.getElementById('tokenName').value || 'Unnamed Token';
      
      try {
        const response = await fetch('/api/v1/team/tokens', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            name: tokenName
          })
        });
        
        const data = await response.json();
        
        if (data.token) {
          document.getElementById('generatedToken').textContent = data.token;
          document.getElementById('tokenInCommand').textContent = data.token;
          document.getElementById('tokenResult').style.display = 'block';
        } else {
          alert('Failed to generate token: ' + (data.error || 'Unknown error'));
        }
      } catch (error) {
        alert('Error generating token: ' + error.message);
      }
    }

    // Copy token to clipboard
    function copyToken() {
      const token = document.getElementById('generatedToken').textContent;
      if (navigator.clipboard) {
        navigator.clipboard.writeText(token).then(() => {
          const btn = document.querySelector('.copy-btn');
          btn.innerHTML = '<i class="fas fa-check"></i> Copied!';
          setTimeout(() => {
            btn.innerHTML = '<i class="fas fa-copy"></i> Copy';
          }, 2000);
        });
      } else {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = token;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        alert('Token copied to clipboard!');
      }
    }

    // Close modal on outside click
    window.onclick = function(event) {
      const modal = document.getElementById('tokenModal');
      if (event.target === modal) {
        hideTokenGenerator();
      }
    }

    // Charts
    {% if trend_data %}
    const trendsCtx = document.getElementById('trendsChart').getContext('2d');
    new Chart(trendsCtx, {
      type: 'line',
      data: {
        labels: [{% for day in trend_data %}'{{ day.date }}'{% if not loop.last %},{% endif %}{% endfor %}],
        datasets: [{
          label: 'Total Tests',
          data: [{% for day in trend_data %}{{ day.total_tests }}{% if not loop.last %},{% endif %}{% endfor %}],
          borderColor: 'rgb(99, 102, 241)',
          backgroundColor: 'rgba(99, 102, 241, 0.1)',
          tension: 0.1
        }, {
          label: 'Failed Tests',
          data: [{% for day in trend_data %}{{ day.failures }}{% if not loop.last %},{% endif %}{% endfor %}],
          borderColor: 'rgb(220, 38, 38)',
          backgroundColor: 'rgba(220, 38, 38, 0.1)',
          tension: 0.1
        }, {
          label: 'Flaky Tests',
          data: [{% for day in trend_data %}{{ day.flaky_tests }}{% if not loop.last %},{% endif %}{% endfor %}],
          borderColor: 'rgb(245, 158, 11)',
          backgroundColor: 'rgba(245, 158, 11, 0.1)',
          tension: 0.1
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top',
          }
        },
        scales: {
          y: {
            beginAtZero: true
          }
        }
      }
    });
    {% endif %}

    {% if environment_data %}
    const envCtx = document.getElementById('environmentChart').getContext('2d');
    new Chart(envCtx, {
      type: 'doughnut',
      data: {
        labels: [{% for env in environment_data %}'{{ env[0] }}'{% if not loop.last %},{% endif %}{% endfor %}],
        datasets: [{
          data: [{% for env in environment_data %}{{ env[1] }}{% if not loop.last %},{% endif %}{% endfor %}],
          backgroundColor: [
            'rgb(99, 102, 241)',
            'rgb(6, 182, 212)',
            'rgb(5, 150, 105)',
            'rgb(217, 119, 6)',
            'rgb(220, 38, 38)',
            'rgb(124, 58, 237)',
            'rgb(236, 72, 153)'
          ]
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'right',
          }
        }
      }
    });
    {% endif %}

    // Initialize
    updateLastUpdated();
    startAutoRefresh();

    // Show pulse animation on critical metrics
    {% if metrics.flaky_tests > 0 %}
    document.querySelector('.icon-flaky').classList.add('pulse');
    {% endif %}
  </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Landing page"""
    return '''
    <html>
    <head><title>FlakeRadar Local Development Server</title></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 40px;">
        <h1>🎯 FlakeRadar Local Development Server</h1>
        <p>Local development environment for FlakeRadar team features.</p>
        
        <h2>🚀 Quick Start</h2>
        <pre style="background: #f4f4f4; padding: 15px; border-radius: 5px;">
# Set local development token
export FLAKERADAR_TOKEN="flake_tk_local_dev_demo_token123"

# Run FlakeRadar with team features
flakeradar --project "MyApp" --environment "local" --results "*.xml"
        </pre>
        
        <h2>🌐 Dashboard Access</h2>
        <ul>
            <li><a href="/dashboard/local-dev-team">Team Dashboard</a></li>
            <li><a href="/api/v1/team/dashboard/local-dev-team">Dashboard API</a></li>
            <li><a href="/health">Health Check</a></li>
        </ul>
        
        <h2>🔧 Development Features</h2>
        <ul>
            <li>✅ Local SQLite database</li>
            <li>✅ Team collaboration simulation</li>
            <li>✅ Jenkins integration testing</li>
            <li>✅ Real-time dashboard updates</li>
            <li>✅ API endpoint compatibility</li>
        </ul>
        
        <p><em>This server simulates the team backend for development and testing purposes.</em></p>
    </body>
    </html>
    '''

# Token Management Functions
def generate_team_token(team_id: str, name: str, created_by: str = "system") -> tuple[str, str]:
    """Generate a new team token and return token and token_id"""
    token = f"flake_tk_{secrets.token_urlsafe(32)}"
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    token_id = str(uuid.uuid4())
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO team_tokens (id, team_id, token_hash, name, created_by)
        VALUES (?, ?, ?, ?, ?)
    """, (token_id, team_id, token_hash, name, created_by))
    
    conn.commit()
    conn.close()
    
    return token, token_id

def validate_token(token: str) -> tuple[bool, str, str]:
    """Validate token and return (is_valid, team_id, token_id)"""
    if not token or not token.startswith('flake_tk_'):
        return False, "", ""
    
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT tt.id, tt.team_id, tt.is_active 
        FROM team_tokens tt
        WHERE tt.token_hash = ? AND tt.is_active = 1
    """, (token_hash,))
    
    result = cursor.fetchone()
    
    if result:
        token_id, team_id, is_active = result
        # Update last_used timestamp
        cursor.execute("""
            UPDATE team_tokens SET last_used = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (token_id,))
        conn.commit()
        conn.close()
        return True, team_id, token_id
    
    conn.close()
    return False, "", ""

@app.route('/api/v1/team/tokens', methods=['POST'])
def create_team_token():
    """Create a new team token for sharing"""
    data = request.get_json()
    team_id = data.get('team_id', 'local-dev-team')
    token_name = data.get('name', f'Token-{datetime.now().strftime("%Y%m%d-%H%M")}')
    created_by = data.get('created_by', 'admin')
    
    try:
        token, token_id = generate_team_token(team_id, token_name, created_by)
        return jsonify({
            "status": "success",
            "token": token,
            "token_id": token_id,
            "team_id": team_id,
            "name": token_name,
            "message": "Token created successfully. Share this token with team members to allow them to submit test data."
        })
    except Exception as e:
        return jsonify({"error": f"Failed to create token: {str(e)}"}), 500

@app.route('/api/v1/team/tokens', methods=['GET'])
def list_team_tokens():
    """List all tokens for a team"""
    team_id = request.args.get('team_id', 'local-dev-team')
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, name, created_by, created_at, last_used, is_active
        FROM team_tokens 
        WHERE team_id = ? 
        ORDER BY created_at DESC
    """, (team_id,))
    
    tokens = cursor.fetchall()
    conn.close()
    
    return jsonify({
        "tokens": [
            {
                "id": token[0],
                "name": token[1],
                "created_by": token[2],
                "created_at": token[3],
                "last_used": token[4],
                "is_active": bool(token[5])
            }
            for token in tokens
        ]
    })

@app.route('/api/v1/projects/<team_id>')
def get_team_projects(team_id):
    """Get list of projects for a team"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT DISTINCT project, COUNT(*) as execution_count,
               MAX(created_at) as last_execution
        FROM test_executions 
        WHERE team_id = ? 
        GROUP BY project
        ORDER BY last_execution DESC
    """, (team_id,))
    
    projects = cursor.fetchall()
    conn.close()
    
    return jsonify({
        "projects": [
            {
                "name": project[0],
                "execution_count": project[1],
                "last_execution": project[2]
            }
            for project in projects
        ]
    })

if __name__ == '__main__':
    init_db()
    print("🎯 FlakeRadar Local Development Server")
    print("📊 Dashboard: http://localhost:8000/dashboard/local-dev-team")
    print("🔧 API Base: http://localhost:8000/api/v1")
    print("💾 Database: ~/.flakeradar/local_team_db.sqlite3")
    
    app.run(host='0.0.0.0', port=8000, debug=True)
