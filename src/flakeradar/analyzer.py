from __future__ import annotations
from collections import defaultdict
from typing import Dict, List, Tuple
import math

def compute_flakiness(raw_rows: List[Tuple[str, str]]) -> Dict[str, Dict]:
    """
    raw_rows: list of (full_name, status) across many runs (mixed order).
    Return dict: {full_name: {pass_count, fail_count, transitions, flake_rate, suspect_flaky:bool}}
    """
    # Group by test
    history: Dict[str, List[str]] = defaultdict(list)
    for full_name, status in raw_rows:
        history[full_name].append(status)

    out: Dict[str, Dict] = {}
    for name, statuses in history.items():
        pass_count = sum(1 for s in statuses if s == "pass")
        fail_like = sum(1 for s in statuses if s in ("fail","error"))
        total = len(statuses)
        # transitions
        transitions = 0
        for i in range(1, len(statuses)):
            if statuses[i] != statuses[i-1]:
                transitions += 1
        flake_rate = fail_like / total if total else 0
        
        # Statistical significance scoring
        confidence_score = calculate_flakiness_confidence(pass_count, fail_like, total, transitions)
        
        # Updated logic for better classification:
        # - truly_flaky: has both passes and failures (intermittent) with sufficient confidence
        # - always_failing: only failures (100% fail rate)
        # - stable: consistently passes (0% fail rate)
        truly_flaky = pass_count > 0 and fail_like > 0 and confidence_score >= 0.7  # high confidence required
        always_failing = fail_like > 0 and pass_count == 0 and total >= 3  # require minimum runs
        suspect = truly_flaky or always_failing  # both types need attention
        
        out[name] = {
            "pass_count": pass_count,
            "fail_count": fail_like,
            "total_runs": total,
            "transitions": transitions,
            "flake_rate": flake_rate,
            "suspect_flaky": suspect,
            "truly_flaky": truly_flaky,
            "always_failing": always_failing,
            "confidence_score": confidence_score,
        }
    return out

def calculate_flakiness_confidence(pass_count: int, fail_count: int, total: int, transitions: int) -> float:
    """
    Calculate statistical confidence that a test is truly flaky
    Returns 0.0 to 1.0 where 1.0 is high confidence
    """
    if total < 2:
        return 0.0  # insufficient data
    
    # Base confidence on sample size (more runs = higher confidence)
    sample_size_factor = min(1.0, total / 20.0)  # plateau at 20 runs
    
    # Confidence based on transition rate (true flakiness has transitions)
    transition_rate = transitions / max(1, total - 1)
    transition_factor = min(1.0, transition_rate * 2)  # 50%+ transition rate = high confidence
    
    # Handle edge cases: consistent behavior = NOT flaky
    if pass_count == 0 or fail_count == 0:
        # All pass or all fail = definitely NOT flaky
        # High confidence that it's NOT flaky = low flakiness confidence score
        return 0.0
    
    # For mixed results, use binomial confidence interval
    p = fail_count / total
    # Wilson score interval for 95% confidence
    z = 1.96  # 95% confidence
    denominator = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z**2 / (4 * total)) / total) / denominator
    
    # If confidence interval is narrow and away from 0/1, it's likely flaky
    interval_width = 2 * margin
    distance_from_edges = min(center, 1 - center)
    
    # Combine factors
    statistical_confidence = (1 - interval_width) * distance_from_edges * 2
    
    return min(1.0, sample_size_factor * transition_factor * statistical_confidence)