import re

MAX_LOG_LENGTH = 4000
TRUNCATION_MARK = "...[truncated]"

def truncate_text(text: str, max_length: int = MAX_LOG_LENGTH) -> str:
    if text is None:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(TRUNCATION_MARK)] + TRUNCATION_MARK

def sanitize_paths(text: str) -> str:
    """Replace absolute paths with placeholders using forward slashes."""
    if not text:
        return text
    # Linux/macOS: /tmp/oj_judge_xxx/ -> <submission>/
    text = re.sub(r'/[^/\s]+/oj_judge_[^/\s]+/', '<submission>/', text)
    # Windows: \some\oj_judge_xxx\ -> <submission>/
    text = re.sub(r'\\[^\\]+\\oj_judge_[^\\]+\\', '<submission>/', text)
    # Windows drive letters: C:\...\oj_judge_xxx\ -> <submission>/
    text = re.sub(r'[A-Za-z]:\\[^\\]+\\oj_judge_[^\\]+\\', '<submission>/', text)
    # File "..." pattern
    text = re.sub(r'File "[^"]+main\.py"', 'File "<submission>/main.py"', text)
    return text

def sanitize_for_student(log_data: dict) -> dict:
    if not log_data:
        return None
    sanitized = log_data.copy()
    cases = sanitized.get("cases", [])
    student_cases = []
    for case in cases:
        if case.get("is_hidden", False):
            continue
        if "stdout" in case:
            case["stdout"] = truncate_text(case["stdout"])
        if "stderr" in case:
            case["stderr"] = sanitize_paths(truncate_text(case["stderr"]))
        if "message" in case:
            case["message"] = sanitize_paths(truncate_text(case["message"]))
        student_cases.append(case)
    sanitized["cases"] = student_cases
    if "error" in sanitized and sanitized["error"]:
        sanitized["error"] = sanitize_paths(truncate_text(sanitized["error"]))
    return sanitized

def sanitize_for_teacher(log_data: dict) -> dict:
    if not log_data:
        return None
    sanitized = log_data.copy()
    cases = sanitized.get("cases", [])
    for case in cases:
        if "stdout" in case:
            case["stdout"] = truncate_text(case["stdout"])
        if "stderr" in case:
            case["stderr"] = sanitize_paths(truncate_text(case["stderr"]))
        if "message" in case:
            case["message"] = sanitize_paths(truncate_text(case["message"]))
    if "error" in sanitized and sanitized["error"]:
        sanitized["error"] = sanitize_paths(truncate_text(sanitized["error"]))
    return sanitized