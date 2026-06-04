from langchain_core.tools import tool
from typing import Annotated, List
import re
import json

@tool
def classify_stack(
    parsed_dependencies: Annotated[
        str,
        "List of outputs from parse_dependencies, one per config file found in the repo"
    ],
    repo_structure: Annotated[
        str,
        "Output of get_repo_structure, used to infer stack from file extensions and folder names"
    ] = {},
) -> str:
    """
    Classifies the technology stack of a repository from parsed dependencies
    and repo structure. Returns language, frameworks, databases, devops tools,
    architecture type, and package manager.
    """
    if isinstance(parsed_dependencies, str):
        try:
            parsed_dependencies = json.loads(parsed_dependencies)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON for parsed_dependencies"})

    # deserializza ogni elemento se è stringa JSON (output di parse_dependencies)
    deserialized = []
    for item in parsed_dependencies:
        if isinstance(item, str):
            try:
                deserialized.append(json.loads(item))
            except json.JSONDecodeError:
                continue
        elif isinstance(item, dict):
            deserialized.append(item)
    parsed_dependencies = deserialized
    
    if isinstance(repo_structure, str):
        try:
            repo_structure = json.loads(repo_structure)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON input"})
        
    if not isinstance(repo_structure, dict):
        return json.dumps({"error": "structure must be a dict or JSON string"})

    # ── Knowledge base ────────────────────────────────────────────────────────

    FRAMEWORKS = {
        "fastapi":       ("python",     "web_framework",  "backend-api"),
        "flask":         ("python",     "web_framework",  "backend-api"),
        "django":        ("python",     "web_framework",  "fullstack"),
        "tornado":       ("python",     "web_framework",  "backend-api"),
        "starlette":     ("python",     "web_framework",  "backend-api"),
        "litestar":      ("python",     "web_framework",  "backend-api"),
        "torch":         ("python",     "ml_framework",   "ml"),
        "tensorflow":    ("python",     "ml_framework",   "ml"),
        "keras":         ("python",     "ml_framework",   "ml"),
        "transformers":  ("python",     "ml_framework",   "ml"),
        "scikit-learn":  ("python",     "ml_framework",   "ml"),
        "langchain":     ("python",     "ai_framework",   "ai-agent"),
        "langgraph":     ("python",     "ai_framework",   "ai-agent"),
        "llamaindex":    ("python",     "ai_framework",   "ai-agent"),
        "openai":        ("python",     "ai_client",      "ai-agent"),
        "anthropic":     ("python",     "ai_client",      "ai-agent"),
        "celery":        ("python",     "task_queue",     "backend-api"),
        "pandas":        ("python",     "data",           "data"),
        "numpy":         ("python",     "data",           "data"),
        "pyspark":       ("python",     "data",           "data"),
        "react":         ("javascript", "ui_framework",   "frontend"),
        "vue":           ("javascript", "ui_framework",   "frontend"),
        "angular":       ("javascript", "ui_framework",   "frontend"),
        "svelte":        ("javascript", "ui_framework",   "frontend"),
        "next":          ("javascript", "web_framework",  "fullstack"),
        "nuxt":          ("javascript", "web_framework",  "fullstack"),
        "remix":         ("javascript", "web_framework",  "fullstack"),
        "express":       ("javascript", "web_framework",  "backend-api"),
        "fastify":       ("javascript", "web_framework",  "backend-api"),
        "nestjs":        ("javascript", "web_framework",  "backend-api"),
        "hono":          ("javascript", "web_framework",  "backend-api"),
        "gin":           ("go",         "web_framework",  "backend-api"),
        "echo":          ("go",         "web_framework",  "backend-api"),
        "fiber":         ("go",         "web_framework",  "backend-api"),
        "spring-boot":   ("java",       "web_framework",  "backend-api"),
        "quarkus":       ("java",       "web_framework",  "backend-api"),
        "micronaut":     ("java",       "web_framework",  "backend-api"),
    }

    DATABASES = {
        "sqlalchemy":    "postgresql",
        "sqlmodel":      "postgresql",
        "psycopg2":      "postgresql",
        "psycopg":       "postgresql",
        "asyncpg":       "postgresql",
        "pymongo":       "mongodb",
        "motor":         "mongodb",
        "redis":         "redis",
        "aioredis":      "redis",
        "elasticsearch": "elasticsearch",
        "pymysql":       "mysql",
        "aiomysql":      "mysql",
        "tortoise-orm":  "postgresql",
        "beanie":        "mongodb",
        "prisma":        "postgresql",
        "mongoose":      "mongodb",
        "sequelize":     "postgresql",
        "typeorm":       "postgresql",
        "pg":            "postgresql",
        "mysql2":        "mysql",
        "ioredis":       "redis",
        "sqlite3":       "sqlite",
        "better-sqlite3":"sqlite",
    }

    DEVOPS = {
        "docker":           "containerization",
        "docker-compose":   "containerization",
        "kubernetes":       "orchestration",
        "github-actions":   "ci_cd",
        "gitlab-ci":        "ci_cd",
        "terraform":        "iac",
        "ansible":          "iac",
        "nginx":            "server",
        "gunicorn":         "server",
        "uvicorn":          "server",
        "caddy":            "server",
    }

    LANGUAGES_FROM_MANAGER = {
        "pip":        "python",
        "poetry":     "python",
        "pipenv":     "python",
        "pip/pep621": "python",
        "uv":         "python",
        "npm":        "javascript",
        "yarn":       "javascript",
        "go modules": "go",
        "maven":      "java",
        "gradle":     "java",
    }

    EXT_TO_LANG = {
        "py":   "python",
        "js":   "javascript",
        "ts":   "typescript",
        "go":   "go",
        "java": "java",
        "rb":   "ruby",
        "rs":   "rust",
        "cs":   "csharp",
        "kt":   "kotlin",
    }

    # priorità linguaggio a parità di voti
    LANGUAGE_PRIORITY = ["python", "go", "java", "rust", "javascript", "typescript"]

    # ── Struttura repo ────────────────────────────────────────────────────────

    def walk_structure(node: dict, path: str = "") -> list[str]:
        paths = []
        for name, value in node.items():
            full = f"{path}/{name}" if path else name
            paths.append(full)
            if isinstance(value, dict):
                paths.extend(walk_structure(value, full))
        return paths

    all_paths = walk_structure(repo_structure)

    # ── Raccolta dati ─────────────────────────────────────────────────────────

    all_dep_names:      set[str]       = set()
    detected_languages: dict[str, int] = {}
    package_managers:   list[str]      = []
    config_files:       list[str]      = []
    env_variables:      list[str]      = []
    language_version:   str | None     = None

    for parsed in parsed_dependencies:
        if not isinstance(parsed, dict):
            continue
        if parsed.get("error") or parsed.get("skipped"):
            config_files.append(parsed.get("format", ""))
            continue

        pm = parsed.get("package_manager")
        if pm and pm not in ("docker", "docker-compose", "github-actions", "env"):
            package_managers.append(pm)
            # peso 1 per package manager
            if pm in LANGUAGES_FROM_MANAGER:
                lang = LANGUAGES_FROM_MANAGER[pm]
                detected_languages[lang] = detected_languages.get(lang, 0) + 1

        # inferisci da base_image
        base_image = parsed.get("metadata", {}).get("base_image", "")
        if "python" in base_image.lower():
            detected_languages["python"] = detected_languages.get("python", 0) + 1
        elif "node" in base_image.lower() or "bun" in base_image.lower():
            detected_languages["javascript"] = detected_languages.get("javascript", 0) + 1

        deps     = parsed.get("dependencies", [])
        dev_deps = parsed.get("dev_dependencies", [])
        if not isinstance(deps, list):     deps = []
        if not isinstance(dev_deps, list): dev_deps = []

        for dep in deps + dev_deps:
            if isinstance(dep, dict) and "name" in dep:
                all_dep_names.add(dep["name"].lower())

        for var in parsed.get("metadata", {}).get("variables", []):
            if isinstance(var, dict):
                env_variables.append(var.get("key", "").lower())

    # ── Linguaggio — peso 2 per file sorgente ────────────────────────────────

    extensions = [p.rsplit(".", 1)[-1].lower() for p in all_paths if "." in p]
    ext_counter = {e: extensions.count(e) for e in set(extensions)}

    for ext, count in ext_counter.items():
        if ext in EXT_TO_LANG:
            lang = EXT_TO_LANG[ext]
            # peso 2 per file sorgente — supera i package manager
            detected_languages[lang] = detected_languages.get(lang, 0) + count * 2

    # typescript → javascript se non ci sono file .js
    if "typescript" in detected_languages and "javascript" not in detected_languages:
        detected_languages["javascript"] = detected_languages.pop("typescript")
    elif "typescript" in detected_languages:
        detected_languages["javascript"] = detected_languages.get("javascript", 0) + detected_languages.pop("typescript")

    language = None
    if detected_languages:
        language = max(
            detected_languages,
            key=lambda l: (
                detected_languages[l],
                -(LANGUAGE_PRIORITY.index(l) if l in LANGUAGE_PRIORITY else 99)
            )
        )

    # versione solo se il linguaggio rilevato è python
    for parsed in parsed_dependencies:
        if not isinstance(parsed, dict):
            continue
        ver = parsed.get("metadata", {}).get("python")
        if ver and language == "python":
            language_version = ver
            break

    # ── Frameworks ───────────────────────────────────────────────────────────

    detected_frameworks = []
    architecture_votes: dict[str, int] = {}
    seen_frameworks: set[str] = set()

    for dep in all_dep_names:
        if dep.startswith("@types/") or dep.startswith("@types-"):
            continue

        target = dep
        if dep not in FRAMEWORKS:
            target = re.sub(r"^@[\w-]+/", "", dep).split(".")[0]

        if target in FRAMEWORKS and target not in seen_frameworks:
            lang, ftype, arch = FRAMEWORKS[target]
            detected_frameworks.append({"name": target, "type": ftype, "language": lang})
            architecture_votes[arch] = architecture_votes.get(arch, 0) + 1
            seen_frameworks.add(target)

    # ── Database ──────────────────────────────────────────────────────────────

    detected_databases: set[str] = set()
    for dep in all_dep_names:
        if dep in DATABASES:
            detected_databases.add(DATABASES[dep])

    ENV_DB_HINTS = {
        "postgres": "postgresql", "mysql": "mysql",  "mongo": "mongodb",
        "redis":    "redis",      "sqlite": "sqlite", "elastic": "elasticsearch",
        "database_url": "postgresql",
    }
    for var in env_variables:
        for hint, db in ENV_DB_HINTS.items():
            if hint in var:
                detected_databases.add(db)

    # ── DevOps ────────────────────────────────────────────────────────────────

    detected_devops: dict[str, str] = {}

    for parsed in parsed_dependencies:
        if not isinstance(parsed, dict):
            continue
        pm  = parsed.get("package_manager", "")
        fmt = parsed.get("format", "")
        if pm in DEVOPS:
            detected_devops[pm] = DEVOPS[pm]
        if fmt in DEVOPS:
            detected_devops[fmt] = DEVOPS[fmt]

    for dep in all_dep_names:
        if dep in DEVOPS:
            detected_devops[dep] = DEVOPS[dep]

    STRUCTURE_DEVOPS = {
        "dockerfile":          ("docker",         "containerization"),
        "docker-compose.yml":  ("docker-compose", "containerization"),
        "docker-compose.yaml": ("docker-compose", "containerization"),
        "k8s":                 ("kubernetes",     "orchestration"),
        "helm":                ("kubernetes",     "orchestration"),
        "terraform":           ("terraform",      "iac"),
        ".github":             ("github-actions", "ci_cd"),
        ".gitlab-ci.yml":      ("gitlab-ci",      "ci_cd"),
        "nginx.conf":          ("nginx",          "server"),
    }
    for path in all_paths:
        path_lower = path.lower()
        for keyword, (tool_name, category) in STRUCTURE_DEVOPS.items():
            if keyword in path_lower and tool_name not in detected_devops:
                detected_devops[tool_name] = category
                break

    # ── Architettura ──────────────────────────────────────────────────────────

    architecture = "unknown"
    if architecture_votes:
        architecture = max(architecture_votes, key=architecture_votes.get)

    types = {f["type"] for f in detected_frameworks}
    if "ui_framework" in types and ("web_framework" in types or architecture == "backend-api"):
        architecture = "fullstack"

    # ── Output ────────────────────────────────────────────────────────────────

    return json.dumps({
        "language": {
            "name":    language or "unknown",
            "version": language_version,
        },
        "frameworks":      detected_frameworks,
        "databases":       sorted(detected_databases),
        "devops": [
            {"name": name, "category": category}
            for name, category in detected_devops.items()
        ],
        "architecture":    architecture,
        "package_manager": list(set(package_managers)),
        "config_files":    [f for f in config_files if f],
        "summary": (
            f"{language or 'unknown'} {architecture} app"
            + (f" with {', '.join(sorted(detected_databases)[:3])}" if detected_databases else "")
            + (f" — {', '.join(f['name'] for f in detected_frameworks[:3])}" if detected_frameworks else "")
        )
    })