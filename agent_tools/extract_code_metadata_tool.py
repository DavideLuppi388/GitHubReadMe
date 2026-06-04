from langchain_core.tools import tool
from typing import Annotated
import ast
import re
import json

@tool
def extract_code_metadata(
    file_path: Annotated[str, "Path of the file (used to detect language by extension)"],
    content: Annotated[str, "The full text content of the file to analyze"],
) -> str:
    """
    Extracts metadata from a source code file in a single call.
    Returns classes, functions, imports, and routes (for web frameworks).
    Supports Python (AST-based) and JavaScript/TypeScript (regex-based).
    """
    ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
    # fix: controlla errori di read_file
    if not content or content.startswith("ERROR:"):
        return json.dumps({
            "language": "unknown",
            "imports": [], "classes": [], "functions": [], "routes": [],
            "error": content or "empty content"
        })
    
    if ext == "py":
        return _extract_python(content)
    elif ext in ("js", "ts", "jsx", "tsx"):
        return _extract_js_ts(content)
    else:
        return _extract_generic(content)


# ── PYTHON ────────────────────────────────────────────────────────────────────

def _extract_python(content: str) -> dict:
    result = {
        "language": "python",
        "imports": [],
        "classes": [],
        "functions": [],
        "routes": [],
    }

    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        result["parse_error"] = str(e)
        return result

    for node in ast.walk(tree):

        # --- imports ---
        if isinstance(node, ast.Import):
            for alias in node.names:
                result["imports"].append({
                    "module": alias.name,
                    "alias": alias.asname,
                    "from": None,
                })
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                result["imports"].append({
                    "module": alias.name,
                    "alias": alias.asname,
                    "from": node.module,
                })

        # --- classes ---
        elif isinstance(node, ast.ClassDef):
            result["classes"].append({
                "name": node.name,
                "line": node.lineno,
                "bases": [ast.unparse(b) for b in node.bases],
                "methods": [
                    {
                        "name": n.name,
                        "line": n.lineno,
                        "args": [a.arg for a in n.args.args],
                        "decorators": [ast.unparse(d) for d in n.decorator_list],
                    }
                    for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                ],
            })

        # --- top-level functions (sync e async) ---
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not _is_method(tree, node):
            decorators = [ast.unparse(d) for d in node.decorator_list]
            result["functions"].append({
                "name": node.name,
                "line": node.lineno,
                "args": [a.arg for a in node.args.args],
                "decorators": decorators,
            })

            # --- routes (Flask / FastAPI) ---
            for dec in decorators:
                route_match = re.search(
                    r'(?:get|post|put|patch|delete|route|head)\s*\(\s*["\']([^"\']+)["\']',
                    dec, re.IGNORECASE
                )
                if route_match:
                    method = re.search(r'\.(\w+)\s*\(', dec)
                    result["routes"].append({
                        "path": route_match.group(1),
                        "method": method.group(1).upper() if method else "ROUTE",
                        "handler": node.name,
                        "line": node.lineno,
                    })

    return json.dumps(result, ensure_ascii=False)


def _is_method(tree: ast.AST, func) -> bool:
    """Returns True if the function is a direct child of a class body."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if func in node.body:  # direct child, non walk ricorsivo
                return True
    return False


# ── JAVASCRIPT / TYPESCRIPT ───────────────────────────────────────────────────

def _extract_js_ts(content: str) -> dict:
    result = {
        "language": "javascript/typescript",
        "imports": [],
        "classes": [],
        "functions": [],
        "routes": [],
    }

    for i, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()

        # imports ES6
        m = re.match(r"import\s+(.+?)\s+from\s+['\"](.+?)['\"]", stripped)
        if m:
            result["imports"].append({"what": m.group(1), "from": m.group(2), "line": i})
            continue

        # imports CommonJS
        m = re.match(r"(?:const|let|var)\s+(.+?)\s*=\s*require\(['\"](.+?)['\"]\)", stripped)
        if m:
            result["imports"].append({"what": m.group(1), "from": m.group(2), "line": i})
            continue

        # classes
        m = re.match(r"(?:export\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?", stripped)
        if m:
            result["classes"].append({"name": m.group(1), "extends": m.group(2), "line": i})
            continue

        # function declaration
        m = re.match(r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)", stripped)
        if m:
            result["functions"].append({"name": m.group(1), "args": m.group(2), "line": i})
            continue

        # arrow function
        m = re.match(r"(?:export\s+)?(?:const|let)\s+(\w+)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*=>", stripped)
        if m:
            result["functions"].append({"name": m.group(1), "args": m.group(2), "line": i})
            continue

        # routes Express.js
        m = re.match(r"(?:router|app)\.(get|post|put|patch|delete)\s*\(\s*['\"]([^'\"]+)['\"]", stripped, re.IGNORECASE)
        if m:
            result["routes"].append({"method": m.group(1).upper(), "path": m.group(2), "line": i})

    return json.dumps(result, ensure_ascii=False)


# ── GENERIC FALLBACK ──────────────────────────────────────────────────────────

def _extract_generic(content: str) -> dict:
    """Minimal regex-based extraction for unsupported languages."""
    result = {
        "language": "unknown",
        "imports": [],
        "classes": [
            {"name": m.group(1), "line": i + 1}
            for i, line in enumerate(content.splitlines())
            if (m := re.search(r'\bclass\s+(\w+)', line))
        ],
        "functions": [
            {"name": m.group(1), "line": i + 1}
            for i, line in enumerate(content.splitlines())
            if (m := re.search(r'\bfunc(?:tion)?\s+(\w+)\s*\(', line))
        ],
        "routes": [],
    }

    return json.dumps(result, ensure_ascii=False)