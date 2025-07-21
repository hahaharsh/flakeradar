from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class TestCaseResult:
    full_name: str              # canonical: pkg.Class#method[param]
    suite: Optional[str]
    status: str                 # pass|fail|skipped|error
    duration_ms: Optional[int]
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Optional[str] = None  # full stack trace/log excerpt
    extra: Optional[Dict] = None         # device, browser, tags