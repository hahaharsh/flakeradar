from __future__ import annotations
import re
from collections import defaultdict, Counter
from typing import List, Dict, Optional
from .model import TestCaseResult

def cluster_failures_by_root_cause(test_results: List[TestCaseResult]) -> Dict[str, Dict]:
    """
    Cluster failing tests by root cause patterns
    Returns dict with cluster analysis
    """
    failure_patterns = defaultdict(list)
    
    for result in test_results:
        if result.status in ("fail", "error"):
            cluster_key = extract_root_cause_signature(result)
            failure_patterns[cluster_key].append(result)
    
    # Analyze clusters
    clusters = {}
    for cluster_key, failures in failure_patterns.items():
        clusters[cluster_key] = {
            "signature": cluster_key,
            "count": len(failures),
            "affected_tests": list(set(f.full_name for f in failures)),
            "error_types": list(set(f.error_type for f in failures if f.error_type)),
            "common_keywords": extract_common_keywords([f.error_message or "" for f in failures]),
            "stack_trace_pattern": extract_stack_pattern([f.error_details or "" for f in failures]),
            "severity": calculate_cluster_severity(failures)
        }
    
    return clusters

def extract_root_cause_signature(result: TestCaseResult) -> str:
    """Extract a signature that represents the root cause category"""
    
    # Priority 1: Database/Connection issues
    if any(keyword in (result.error_message or "").lower() for keyword in 
           ["connection", "timeout", "pool", "database", "sql", "jdbc"]):
        return "database_connectivity"
    
    # Priority 2: Network/API issues  
    if any(keyword in (result.error_message or "").lower() for keyword in
           ["network", "http", "api", "socket", "connection refused", "unreachable"]):
        return "network_api_issues"
    
    # Priority 3: Timing/Race conditions
    if any(keyword in (result.error_message or "").lower() for keyword in
           ["timeout", "wait", "sleep", "race", "timing", "async", "thread"]):
        return "timing_race_conditions"
    
    # Priority 4: Resource issues
    if any(keyword in (result.error_message or "").lower() for keyword in
           ["memory", "disk", "cpu", "resource", "limit", "quota", "space"]):
        return "resource_constraints"
    
    # Priority 5: Authentication/Authorization
    if any(keyword in (result.error_message or "").lower() for keyword in
           ["auth", "permission", "unauthorized", "forbidden", "token", "credential"]):
        return "auth_permission_issues"
    
    # Priority 6: Data/State issues
    if any(keyword in (result.error_message or "").lower() for keyword in
           ["data", "state", "null", "empty", "missing", "not found", "invalid"]):
        return "data_state_issues"
    
    # Priority 7: Environment/Configuration
    if any(keyword in (result.error_message or "").lower() for keyword in
           ["config", "environment", "property", "setting", "variable"]):
        return "environment_config"
    
    # Fallback: Use error type or generic
    if result.error_type:
        return f"error_type_{result.error_type.split('.')[-1].lower()}"
    
    return "unknown_error_pattern"

def extract_common_keywords(error_messages: List[str]) -> List[str]:
    """Extract most common meaningful words from error messages"""
    all_words = []
    for msg in error_messages:
        if msg:
            # Extract meaningful words (not common English words)
            words = re.findall(r'\b[A-Za-z][A-Za-z0-9_]{2,}\b', msg.lower())
            all_words.extend(words)
    
    # Filter out common words
    common_words = {"the", "and", "for", "are", "but", "not", "you", "all", "can", "her", "was", "one", "our", "had", "but", "with", "have", "this", "will", "his", "they", "from", "been", "said", "each", "which", "their", "time", "were", "way", "about", "would", "there", "could", "other", "after", "first", "well", "water", "been", "call", "who", "may", "down", "side", "been", "now", "find", "head", "long", "way", "too", "any", "may", "say", "she", "use", "her", "all", "how", "when", "much", "go", "me", "so", "these", "your", "many"}
    
    meaningful_words = [word for word in all_words if word not in common_words and len(word) > 2]
    word_counts = Counter(meaningful_words)
    return [word for word, count in word_counts.most_common(5)]

def extract_stack_pattern(stack_traces: List[str]) -> str:
    """Extract common pattern from stack traces"""
    if not stack_traces:
        return "no_stack_trace"
    
    # Find the most common exception class
    exception_classes = []
    for trace in stack_traces:
        if trace:
            # Look for Java exception patterns
            java_exceptions = re.findall(r'\b([A-Z][a-zA-Z]*Exception)\b', trace)
            exception_classes.extend(java_exceptions)
    
    if exception_classes:
        most_common = Counter(exception_classes).most_common(1)[0][0]
        return f"exception_{most_common.lower()}"
    
    return "generic_stack_trace"

def calculate_cluster_severity(failures: List[TestCaseResult]) -> str:
    """Calculate severity based on failure frequency and spread"""
    test_count = len(set(f.full_name for f in failures))
    failure_count = len(failures)
    
    if test_count >= 5 and failure_count >= 10:
        return "critical"
    elif test_count >= 3 and failure_count >= 5:
        return "high"
    elif test_count >= 2 or failure_count >= 3:
        return "medium"
    else:
        return "low"

def get_cluster_recommendations(cluster_signature: str) -> str:
    """Get specific recommendations for each cluster type"""
    recommendations = {
        "database_connectivity": "🗄️ Database: Check connection pool settings, database server health, and network connectivity",
        "network_api_issues": "🌐 Network: Verify API endpoints, check network connectivity, review timeout settings",
        "timing_race_conditions": "⏱️ Timing: Add proper waits, review async operations, check for race conditions",
        "resource_constraints": "💾 Resources: Monitor memory/CPU usage, check disk space, review resource limits",
        "auth_permission_issues": "🔐 Auth: Verify credentials, check permissions, review token expiration",
        "data_state_issues": "📊 Data: Check data consistency, review null handling, verify test data setup",
        "environment_config": "⚙️ Config: Review environment variables, check configuration files, verify settings"
    }
    
    return recommendations.get(cluster_signature, "🔍 Unknown: Manual investigation required")
