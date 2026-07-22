"""
Output normalization and comparison logic

1. Convert \r\n and \r to \n
2. Remove trailing spaces and tabs from each line
3. Remove trailing empty lines at the end of the file
"""

def normalize_output(text: str) -> str:
    if text is None:
        return ""
    
    # \r\n -> \n, \r -> \n
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    
    # Split into lines
    lines = text.splitlines()
    
    # Remove trailing spaces and tabs from each line
    lines = [line.rstrip(" \t") for line in lines]
    
    # Remove trailing empty lines
    while lines and lines[-1] == "":
        lines.pop()
    
    # Rejoin with \n
    return "\n".join(lines)


def compare_outputs(actual: str, expected: str) -> bool:
    """
    Compare actual output vs expected output after normalization.
    Returns True if they match, False otherwise.
    """
    return normalize_output(actual) == normalize_output(expected)