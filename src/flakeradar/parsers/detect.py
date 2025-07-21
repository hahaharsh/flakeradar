import os

def detect_format(path: str) -> str:
    # Naive: inspect filename / root tag
    lower = os.path.basename(path).lower()
    if lower.endswith(".xml"):
        # Most TestNG & JUnit outputs are JUnit-ish. We'll parse w/ junit.py
        return "junit"
    # TODO: json / allure detection
    return "unknown"