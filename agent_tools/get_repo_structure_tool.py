from langchain_core.tools import tool
from typing import Annotated, Optional
import json

# Mappa estensione → categoria
EXTENSION_CATEGORIES = {
    # Source code
    "py": "source", "js": "source", "ts": "source", "jsx": "source", "tsx": "source",
    "java": "source", "kt": "source", "scala": "source", "go": "source", "rs": "source",
    "c": "source", "cpp": "source", "cc": "source", "h": "source", "hpp": "source",
    "cs": "source", "rb": "source", "php": "source", "swift": "source", "m": "source",
    "r": "source", "jl": "source", "lua": "source", "ex": "source", "exs": "source",
    "hs": "source", "ml": "source", "clj": "source", "dart": "source",

    # Config
    "json": "config", "yaml": "config", "yml": "config", "toml": "config",
    "ini": "config", "cfg": "config", "conf": "config", "env": "config",
    "properties": "config", "xml": "config", "plist": "config",

    # Docs
    "md": "docs", "mdx": "docs", "rst": "docs", "txt": "docs", "pdf": "docs",
    "adoc": "docs", "tex": "docs",

    # Test (rilevato anche per path, vedi sotto)
    "test.py": "test", "spec.js": "test", "spec.ts": "test",

    # Build / CI
    "gradle": "build", "maven": "build", "makefile": "build", "cmake": "build",
    "dockerfile": "build", "containerfile": "build",

    # Data
    "csv": "data", "tsv": "data", "parquet": "data", "jsonl": "data",
    "sql": "data", "db": "data", "sqlite": "data",

    # Assets
    "png": "asset", "jpg": "asset", "jpeg": "asset", "gif": "asset", "svg": "asset",
    "ico": "asset", "webp": "asset", "mp4": "asset", "mp3": "asset",
    "woff": "asset", "woff2": "asset", "ttf": "asset", "eot": "asset",

    # Shell / scripts
    "sh": "script", "bash": "script", "zsh": "script", "fish": "script",
    "ps1": "script", "bat": "script", "cmd": "script",

    # Notebooks
    "ipynb": "notebook",

    # Lock files
    "lock": "lock",
}

# Nomi di file speciali senza estensione
SPECIAL_FILENAMES = {
    "dockerfile": "build", "containerfile": "build",
    "makefile": "build", "rakefile": "build", "gemfile": "build",
    "jenkinsfile": "build", "vagrantfile": "build",
    ".env.example": "config", ".env.sample": "config", ".env.test": "config",
    ".env.production": "config", ".gitignore": "config", ".gitattributes": "config", ".editorconfig": "config",
    ".env": "config", ".npmrc": "config", ".nvmrc": "config",
    ".prettierrc": "config", ".eslintrc": "config", ".babelrc": "config",
    "license": "docs", "readme": "docs", "changelog": "docs", "contributing": "docs",
    "requirements.txt": "build", "pipfile": "build", "setup.py": "build",
    "setup.cfg": "build", "pyproject.toml": "build", "package.json": "build",
    "package-lock.json": "lock", "yarn.lock": "lock", "poetry.lock": "lock",
    "cargo.lock": "lock", "go.sum": "lock", "__init__.py": "source"
}

# Segmenti di path che indicano file di test
TEST_PATH_SEGMENTS = {"test", "tests", "spec", "specs", "__tests__", "testing"}


def _classify(path: str) -> dict:
    """Ritorna metadati per un singolo file dato il suo path completo."""
    parts = path.split("/")
    filename = parts[-1].lower()

    # Estensione
    if "." in filename:
        ext = filename.rsplit(".", 1)[-1]
    else:
        ext = ""

    # Categoria: prima controlla nome speciale intero
    category = SPECIAL_FILENAMES.get(filename)

    # Poi controlla suffissi composti tipo .test.py / .spec.ts
    if category is None:
        for suffix, cat in EXTENSION_CATEGORIES.items():
            if filename.endswith("." + suffix) and "." in suffix:
                category = cat
                break

    # Poi estensione semplice
    if category is None:
        category = EXTENSION_CATEGORIES.get(ext)

    # Override: se il path contiene segmenti tipici di test
    if category == "source" and TEST_PATH_SEGMENTS.intersection(p.lower() for p in parts[:-1]):
        category = "test"

    # Fallback
    if category is None:
        category = "other"

    return {
        "extension": ext if ext else None,
        "category": category,
    }

@tool
def get_repo_structure(
    repo_full_name: Annotated[str, "the full name of the repo, it must be 'user/repository'"],
    branch: Annotated[str, "The branch to explore, defaults to 'main' or 'master'"] = "main",
    token: Annotated[Optional[str], "GitHub Personal Access Token for authentication"] = None,
    path_prefix: Annotated[
        Optional[str],
        "Optional repository-relative path prefix used to limit the returned tree. "
        "Examples: 'src/', 'packages/api/', '.github/workflows/'. "
        "If None, returns the full repository tree.",
    ] = None,
    include_categories: Annotated[
        Optional[list[str]],
        "Optional whitelist of categories to return. "
        "Valid values: source, config, docs, test, build, data, asset, script, notebook, lock, other. "
        "If None, all categories are returned. "
        "Example: ['source', 'test'] to get only source and test files.",
    ] = None,
) -> str:
    """
    Explores a GitHub repository and returns a flat mapping of every file path
    to its metadata (extension, category).
    Categories: source | config | docs | test | build | data | asset | script | notebook | lock | other
    """
    import requests

    headers = {"Authorization": f"token {token}"} if token else {}

    data = None
    branches_to_try = [branch]
    if branch != "main":
        branches_to_try.append("main")
    if branch != "master":
        branches_to_try.append("master")

    for b in branches_to_try:
        url = f"https://api.github.com/repos/{repo_full_name}/git/trees/{b}?recursive=1"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            break

    if data is None:
        return json.dumps({
            "error": f"Couldn't access {repo_full_name}. Try adding a token or changing the branch."
        })

    normalized_prefix = path_prefix.strip("/") if path_prefix else None
    category_filter = set(include_categories) if include_categories else None

    result: dict[str, dict] = {}

    for item in data.get("tree", []):
        if item["type"] != "blob":
            continue

        item_path: str = item["path"]

        if normalized_prefix:
            if item_path != normalized_prefix and not item_path.startswith(normalized_prefix + "/"):
                continue

        metadata = _classify(item_path)

        if category_filter and metadata["category"] not in category_filter:
            continue

        result[item_path] = metadata

    return json.dumps(result, ensure_ascii=False)