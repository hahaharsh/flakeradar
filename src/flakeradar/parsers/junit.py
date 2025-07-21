from __future__ import annotations
from typing import List, Optional
from lxml import etree
from ..model import TestCaseResult

def parse_junit_xml(path: str, default_suite: Optional[str]=None) -> List[TestCaseResult]:
    tree = etree.parse(path)
    root = tree.getroot()

    # root may be testsuite or testsuites
    suites = []
    if root.tag in ("testsuite", "testng-results"):
        suites = [root]
    else:
        suites = root.findall(".//testsuite")

    results: List[TestCaseResult] = []
    for s in suites:
        suite_name = s.get("name") or default_suite
        for tc in s.findall(".//testcase"):
            classname  = tc.get("classname") or tc.get("class") or suite_name or "unknown"
            name       = tc.get("name") or "unknown"
            time       = tc.get("time")
            duration_ms = int(float(time) * 1000) if time else None

            status = "pass"
            err_type = err_msg = err_details = None

            # Failure/Skipped nodes differ across frameworks
            failure = tc.find("failure")
            error   = tc.find("error")
            skipped = tc.find("skipped")

            if failure is not None:
                status = "fail"
                err_type = failure.get("type")
                err_msg  = failure.get("message")
                err_details = (failure.text or "").strip()
            elif error is not None:
                status = "error"
                err_type = error.get("type")
                err_msg  = error.get("message")
                err_details = (error.text or "").strip()
            elif skipped is not None:
                status = "skipped"

            full_name = f"{classname}#{name}"

            results.append(
                TestCaseResult(
                    full_name=full_name,
                    suite=suite_name,
                    status=status,
                    duration_ms=duration_ms,
                    error_type=err_type,
                    error_message=err_msg,
                    error_details=err_details,
                    extra=None,
                )
            )

    return results