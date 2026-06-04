from langchain_core.tools import tool
from typing import Annotated, Optional, List
import fnmatch
import json

@tool
def find_files_in_structure(
    structure: Annotated[str, "Json string of The repository structure"],
    pattern: Annotated[Optional[str], "Glob pattern to match filenames, e.g. '*.py'"] = None,
    extension: Annotated[Optional[str], "File extension to filter by, e.g. '.py'"] = None,
    name_contains: Annotated[Optional[str], "Substring that the filename must contain"] = None,
    path_contains: Annotated[Optional[str], "Substring that the full path must contain"] = None,
    max_depth: Annotated[Optional[int], "Maximum directory depth (1 = root only)"] = None,
) -> str:
    """
    Searches a repository structure for files matching specific criteria.
    Use this to locate relevant files within the repo's directory tree.
    Returns a JSON string containing a list of file paths.
    """
    if isinstance(structure, str):
        try:
            structure = json.loads(structure)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON input"})
        
    if not isinstance(structure, dict):
        return json.dumps({"error": "structure must be a dict or JSON string"})

    if not any([pattern, extension, name_contains, path_contains]):
        return json.dumps({"error": "At least one search criterion must be provided"})

    
    results: List[str] = []

    def _walk(node: dict, current_path: str, depth: int):
        for name, value in node.items():
            # Costruisce il path relativo
            full_path = f"{current_path}/{name}".lstrip("/")

            if value == "file":
                # Verifica criteri
                if pattern and not fnmatch.fnmatch(name, pattern):
                    continue
                if extension and not name.endswith(extension):
                    continue
                if name_contains and name_contains.lower() not in name.lower():
                    continue
                if path_contains and path_contains.lower() not in full_path.lower():
                    continue
                
                results.append(full_path)

            elif isinstance(value, dict):
                # Esplora sottodirectory solo se entro il limite di profondità
                if max_depth is None or depth < max_depth:
                    _walk(value, full_path, depth + 1)

    _walk(structure, "", 1)
    return json.dumps(results, ensure_ascii=False)
