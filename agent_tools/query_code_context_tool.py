from langchain_core.tools import tool
from typing import Annotated, List, Optional
import re
import json

@tool
def query_code_context(
    query: Annotated[str, "Natural language or keyword query, e.g. 'authenticate', 'who handles auth', 'POST /login'"],
    files_metadata: Annotated[
        str,
        "JSON str containing a List of dicts with 'file_path' and 'metadata' (output of extract_code_metadata)"
    ],
    search_type: Annotated[
        str,
        "What to search for: 'function', 'class', 'route', 'import', 'any'. Default is 'any'"
    ] = "any",
    max_results: Annotated[int, "Maximum number of results to return. Default is 10"] = 10,
) -> str:
    """
    Queries the extracted metadata to answer questions like:
    - 'Where is function X defined?'
    - 'Which class handles authentication?'
    - 'Who imports module X?'
    """

    # ── deserializza se invoke ha serializzato in stringa ────────────────────
    if isinstance(files_metadata, str):
        try:
            files_metadata = json.loads(files_metadata)
        except json.JSONDecodeError:
            return json.dumps({"error": "files_metadata must be a list of dicts"})

    deserialized = []
    for entry in files_metadata:
        if isinstance(entry, str):
            try:
                entry = json.loads(entry)
            except json.JSONDecodeError:
                continue
        # fix: metadata potrebbe essere stringa JSON (output di extract_code_metadata)
        metadata = entry.get("metadata", {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}
        deserialized.append({
            "file_path": entry["file_path"],
            "metadata": metadata
        })
    files_metadata = deserialized

    # ── estrai keywords ───────────────────────────────────────────────────────
    def extract_keywords(q: str) -> list[str]:
        stopwords = {
            "which", "what", "where", "who", "how", "is", "are", "the", "a",
            "an", "in", "of", "to", "for", "does", "do", "get", "find", "show",
            "me", "method", "file", "module", "route",
            "handle", "handles", "manage", "manages",
            "define", "defines", "use", "uses", "used", "call", "calls"
        }
        words = re.findall(r"[a-zA-Z_/][a-zA-Z0-9_/.-]*", q.lower())
        return [w for w in words if w not in stopwords and len(w) > 1]

    keywords = extract_keywords(query)

    def split_name(name: str) -> list[str]:
        """
        Splitta un nome in parti per evitare falsi positivi.
        'domain_of'   → ['domain', 'of', 'domain_of']
        'render_report' → ['render', 'report', 'render_report']
        'LessonResult'  → ['lesson', 'result', 'lessonresult']
        'CheckResult'   → ['check', 'result', 'checkresult']
        """
        name_lower = name.lower()
        # split snake_case e kebab-case
        parts = re.split(r'[_\-\.]', name_lower)
        # split camelCase: 'LessonResult' → ['lesson', 'result']
        camel_parts = re.sub(r'([A-Z])', r'_\1', name).lower().strip('_').split('_')
        all_parts = set(parts + camel_parts + [name_lower])
        return [p for p in all_parts if p]

    def score(name: str) -> int:
        # fix: match su parti del nome, non substring
        parts = split_name(name)
        return sum(1 for kw in keywords if kw in parts)

    def matches(name: str) -> bool:
        # fix: query vuota → ritorna tutto
        if not keywords:
            return True
        return score(name) > 0

    # ── ricerca ───────────────────────────────────────────────────────────────
    results = {
        "functions": [],
        "classes":   [],
        "routes":    [],
        "imports":   [],
    }

    for entry in files_metadata:
        file_path = entry["file_path"]
        meta      = entry["metadata"]

        # --- functions (top-level) ---
        if search_type in ("function", "any"):
            for fn in meta.get("functions", []):
                if matches(fn["name"]):
                    results["functions"].append({
                        "file":       file_path,
                        "name":       fn["name"],
                        "line":       fn["line"],
                        "args":       fn.get("args", []),
                        "decorators": fn.get("decorators", []),
                        "score":      score(fn["name"]),
                    })

            # --- metodi dentro classi ---
            for cls in meta.get("classes", []):
                for method in cls.get("methods", []):
                    if matches(method["name"]):
                        results["functions"].append({
                            "file":       file_path,
                            "name":       f"{cls['name']}.{method['name']}",
                            "line":       method["line"],
                            "args":       method.get("args", []),
                            "decorators": method.get("decorators", []),
                            "score":      score(method["name"]),
                            "class":      cls["name"],
                        })

        # --- classes ---
        if search_type in ("class", "any"):
            for cls in meta.get("classes", []):
                if matches(cls["name"]):
                    results["classes"].append({
                        "file":    file_path,
                        "name":    cls["name"],
                        "line":    cls["line"],
                        "bases":   cls.get("bases", []),
                        "methods": [m["name"] for m in cls.get("methods", [])],
                        "score":   score(cls["name"]),
                    })

        # --- routes ---
        if search_type in ("route", "any"):
            for route in meta.get("routes", []):
                combined = f"{route['method']} {route['path']} {route.get('handler', '')}"
                if matches(combined) or any(kw in route["path"].lower() for kw in keywords):
                    results["routes"].append({
                        "file":    file_path,
                        "method":  route["method"],
                        "path":    route["path"],
                        "handler": route.get("handler"),
                        "line":    route.get("line"),
                        "score":   score(combined),
                    })

        # --- imports ---
        if search_type in ("import", "any"):
            for imp in meta.get("imports", []):
                imp_str = f"{imp.get('from', '') or ''}.{imp['module']}".strip(".")
                # fix: cerca anche nel campo 'from' direttamente
                from_str = imp.get("from", "") or ""
                module_str = imp.get("module", "") or ""
                if matches(imp_str) or matches(from_str) or matches(module_str):
                    results["imports"].append({
                        "file":   file_path,
                        "module": imp["module"],
                        "from":   imp.get("from"),
                        "alias":  imp.get("alias"),
                        "score":  max(score(imp_str), score(from_str), score(module_str)),
                    })

    # ── ordina e applica max_results ──────────────────────────────────────────
    for key in results:
        results[key] = sorted(results[key], key=lambda x: x["score"], reverse=True)[:max_results]

    total = sum(len(v) for v in results.values())

    return json.dumps({
        "query":         query,
        "keywords":      keywords,
        "total_matches": total,
        "results":       {k: v for k, v in results.items() if v},
    }, ensure_ascii=False)