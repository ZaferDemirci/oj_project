import ast
import hashlib
from typing import List, Tuple, Set
from difflib import SequenceMatcher


def normalize_ast_for_similarity(source_code: str) -> str:
    """
    Normalize Python code by:
    1. Removing docstrings and comments (AST strips comments).
    2. Renaming all variable/function/class names to placeholders.
    3. Removing constant literals (numbers, strings).
    This allows us to compare the structure of the code.
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        # If code doesn't parse, return a hash of the raw string as fallback
        return hashlib.md5(source_code.encode()).hexdigest()

    class NameNormalizer(ast.NodeTransformer):
        def __init__(self):
            self.counter = 0
            self.name_map = {}

        def _get_name(self, name):
            if name not in self.name_map:
                self.name_map[name] = f"var_{self.counter}"
                self.counter += 1
            return self.name_map[name]

        def visit_Name(self, node):
            # Only rename variables, not keywords like 'True', 'False', 'None'
            if isinstance(node.ctx, (ast.Store, ast.Load, ast.Del)):
                node.id = self._get_name(node.id)
            return node

        def visit_FunctionDef(self, node):
            node.name = self._get_name(node.name)
            self.generic_visit(node)
            return node

        def visit_ClassDef(self, node):
            node.name = self._get_name(node.name)
            self.generic_visit(node)
            return node

        def visit_Constant(self, node):
            # Replace all literals with a placeholder string
            # (so `print(1)` and `print(2)` are structurally identical)
            node.value = "LITERAL"
            return node

    normalizer = NameNormalizer()
    try:
        normalized_tree = normalizer.visit(tree)
        ast.fix_missing_locations(normalized_tree)
    except Exception:
        # If normalisation fails, fallback to raw hash
        return hashlib.md5(source_code.encode()).hexdigest()

    # Use ast.dump to get a string representation of the structure
    return ast.dump(normalized_tree)


def compute_similarity(code_a: str, code_b: str) -> float:
    """
    Compute similarity score between two code snippets.
    Returns a float between 0.0 and 1.0.
    """
    if not code_a or not code_b:
        return 0.0

    try:
        norm_a = normalize_ast_for_similarity(code_a)
        norm_b = normalize_ast_for_similarity(code_b)
    except Exception:
        # On any error, fallback to character set overlap
        set_a = set(code_a.strip())
        set_b = set(code_b.strip())
        if not set_a or not set_b:
            return 0.0
        overlap = len(set_a.intersection(set_b))
        total = len(set_a.union(set_b))
        return overlap / total

    # Use SequenceMatcher on the normalized AST dumps
    return SequenceMatcher(None, norm_a, norm_b).ratio()


def find_similar_pairs(submissions: List[dict], threshold: float = 0.8) -> List[dict]:
    """
    Find similar pairs among a list of submissions.
    submissions: List of dicts with keys: 'id', 'source_code', 'user_id'
    """
    pairs = []
    n = len(submissions)
    for i in range(n):
        for j in range(i + 1, n):
            # Skip if same user (self)
            if submissions[i]['user_id'] == submissions[j]['user_id']:
                continue
            sim = compute_similarity(submissions[i]['source_code'], submissions[j]['source_code'])
            if sim >= threshold:
                pairs.append({
                    "submission_a": submissions[i]['id'],
                    "submission_b": submissions[j]['id'],
                    "similarity": round(sim, 4),
                    "method": "ast"
                })
    return pairs