from __future__ import annotations
import os
from typing import Optional

try:
    from openai import OpenAI
except ImportError:  # user may not use AI
    OpenAI = None

def summarize_failure(error_type: str, error_message: str, error_details: Optional[str]) -> Optional[str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not OpenAI:
        return None
    client = OpenAI(api_key=api_key)

    prompt = (
        "You are a senior QA automation engineer. "
        "Given a test failure type, message, and snippet, produce a one-line root-cause hypothesis "
        "and one suggested fix. Return short text <= 160 chars.\n\n"
        f"Type: {error_type}\n"
        f"Message: {error_message}\n"
        f"Details:\n{error_details[:1000] if error_details else ''}\n\n"
        "Output:"
    )
    try:
        print(f"🔍 Making OpenAI API call for error: {error_type[:50]}...")
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":prompt}],
            max_tokens=80,
            temperature=0.2,
        )
        result = resp.choices[0].message.content.strip()
        print(f"✅ AI analysis complete")
        return result
    except Exception as e:
        print(f"❌ OpenAI API call failed: {str(e)}")
        return None