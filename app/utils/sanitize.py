import re

MAX_LOG_LENGTH = 4000
TRUNCATION_MARK = "...[truncated]"

def truncate_text(text: str, max_length: int = MAX_LOG_LENGTH) -> str:
    if text is None:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(TRUNCATION_MARK)] + TRUNCATION_MARK