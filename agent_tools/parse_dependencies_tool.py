from langchain_core.tools import tool
from langchain_core.tools import tool
from typing import Annotated
import json
import re

@tool
def parse_dependencies(
    file_path: Annotated[str, "Path of the config file, used to detect format by filename"],
    content: Annotated[str, "The full text content of the config file"],
) -> str:
    """
    Parses dependency files from various package managers and build systems.
    Supports: requirements.txt, pyproject.toml, Pipfile, package.json,
    package-lock.json, yarn.lock, go.mod, pom.xml, build.gradle,
    docker-compose.yml, Dockerfile, .github/workflows/*.yml, .env.example
    Returns a normalized dict with dependencies, versions, and metadata.
    """
    # fix globale: controlla errori e contenuto vuoto
    if not content or (isinstance(content, str) and content.startswith("ERROR:")):
        return _make_result_error(
            file_path.split("/")[-1].lower(),
            content if content else "empty content"
        )

    filename = file_path.split("/")[-1].lower()

    if filename == "requirements.txt":
        return _parse_requirements_txt(content)
    elif filename == "pyproject.toml":
        return _parse_pyproject_toml(content)
    elif filename == "pipfile":
        return _parse_pipfile(content)
    elif filename == "package.json":
        return _parse_package_json(content)
    elif filename == "package-lock.json":
        return _parse_package_lock_json(content)
    elif filename == "yarn.lock":
        return _parse_yarn_lock(content)
    elif filename == "go.mod":
        return _parse_go_mod(content)
    elif filename == "pom.xml":
        return _parse_pom_xml(content)
    elif filename == "build.gradle":
        return _parse_build_gradle(content)
    elif filename in ("docker-compose.yml", "docker-compose.yaml"):
        return _parse_docker_compose(content)
    elif filename == "dockerfile":
        return _parse_dockerfile(content)
    elif file_path.endswith((".yml", ".yaml")) and ".github/workflows" in file_path:
        return _parse_github_actions(content)
    elif filename in (".env.example", ".env.template", ".env.sample"):
        return _parse_env_example(content)
    else:
        return json.dumps({
            "format":           filename,
            "package_manager":  None,
            "dependencies":     [],
            "dev_dependencies": [],
            "metadata":         {},
            "total":            0,
            "skipped":          True,
            "reason":           "configuration file, not a dependency file",
        })

# ── NORMALIZZATORI ────────────────────────────────────────────────────────────

def _make_result(format: str, manager: str, deps: list, dev_deps: list = None, meta: dict = None) -> dict:
    return json.dumps({
        "format":           format,
        "package_manager":  manager,
        "dependencies":     deps,
        "dev_dependencies": dev_deps or [],
        "metadata":         meta or {},
        "total":            len(deps) + len(dev_deps or []),
    })

def _dep(name: str, version: str = "*", type: str = "main", extra: dict = None) -> dict:
    d = {"name": name.strip(), "version": version.strip(), "type": type}
    if extra:
        d.update(extra)
    return d

def _make_result_error(filename: str, reason: str) -> dict:
    return json.dumps({
        "format":           filename,
        "package_manager":  None,
        "dependencies":     [],
        "dev_dependencies": [],
        "metadata":         {},
        "total":            0,
        "skipped":          True,
        "reason":           str(reason)[:200],  # tronca messaggi di errore lunghi
    })


# ── PYTHON ────────────────────────────────────────────────────────────────────

def _parse_requirements_txt(content: str) -> dict:
    # fix: controlla errore prima di parsare
    if content.startswith("ERROR:"):
        return _make_result_error("requirements.txt", content)

    deps = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        line = re.sub(r"\s+#.*$", "", line).strip()
        m = re.match(r"^([A-Za-z0-9_\-\.\[\]]+)\s*([><=!~^][^\s#]*)?", line)
        if m:
            deps.append(_dep(m.group(1), (m.group(2) or "*").strip()))
    return _make_result("requirements.txt", "pip", deps)


def _extract_bracketed_block(content: str, start_pos: int) -> str:
    depth, i, chars = 1, start_pos, []
    while i < len(content) and depth > 0:
        ch = content[i]
        if ch == '[':   depth += 1
        elif ch == ']': depth -= 1
        if depth > 0:   chars.append(ch)
        i += 1
    return "".join(chars)


def _parse_pyproject_toml(content: str) -> dict:
    deps, dev_deps, meta = [], [], {}

    for key in ("name", "version", "description"):
        m = re.search(rf'^{key}\s*=\s*"([^"]+)"', content, re.MULTILINE)
        if m:
            meta[key] = m.group(1)

    m = re.search(r'python\s*=\s*"([^"]+)"', content)
    if m:
        meta["python"] = m.group(1)

    # PEP 621 / uv
    pep621_match = re.search(r"\[project\].*?(?<!\w)dependencies\s*=\s*\[", content, re.DOTALL)
    if pep621_match:
        block = _extract_bracketed_block(content, pep621_match.end())
        for item in re.findall(r'"([^"]+)"', block):
            m = re.match(r"^([A-Za-z0-9_\-\.]+)(?:\[[^\]]*\])?\s*([><=!~^].*)?$", item)
            if m:
                deps.append(_dep(m.group(1), (m.group(2) or "*").strip()))

    # PEP 621 optional
    opt_match = re.search(r"\[project\.optional-dependencies\](.*?)(?=^\[|\Z)", content, re.DOTALL | re.MULTILINE)
    if opt_match:
        for item in re.findall(r'"([^"]+)"', opt_match.group(1)):
            m = re.match(r"^([A-Za-z0-9_\-\.]+)(?:\[[^\]]*\])?\s*([><=!~^].*)?$", item)
            if m:
                deps.append(_dep(m.group(1), (m.group(2) or "*").strip(), type="optional"))

    # uv dev
    uv_dev_match = re.search(r"\[dependency-groups\](.*?)(?=^\[|\Z)", content, re.DOTALL | re.MULTILINE)
    if uv_dev_match:
        dev_block_match = re.search(r"dev\s*=\s*\[", uv_dev_match.group(1))
        if dev_block_match:
            start = uv_dev_match.start(1) + dev_block_match.end()
            block = _extract_bracketed_block(content, start)
            for item in re.findall(r'"([^"]+)"', block):
                m = re.match(r"^([A-Za-z0-9_\-\.]+)(?:\[[^\]]*\])?\s*([><=!~^].*)?$", item)
                if m:
                    dev_deps.append(_dep(m.group(1), (m.group(2) or "*").strip(), type="dev"))

    if "python" not in meta:
        m = re.search(r'requires-python\s*=\s*"([^"]+)"', content)
        if m:
            meta["python"] = m.group(1)

    def _parse_poetry_block(block_content: str, dep_type: str) -> list:
        result = []
        for line in block_content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if re.match(r'^([a-zA-Z0-9_\-]+)\s*=\s*\{', line):
                name_m = re.match(r'^([a-zA-Z0-9_\-]+)', line)
                ver_m  = re.search(r'version\s*=\s*"([^"]+)"', line)
                if name_m:
                    result.append(_dep(name_m.group(1), ver_m.group(1) if ver_m else "*", type=dep_type))
            else:
                m = re.match(r'^([a-zA-Z0-9_\-]+)\s*=\s*"?[\^~]?([0-9][^\s"#,}]*)', line)
                if m and m.group(1).lower() != "python":
                    result.append(_dep(m.group(1), m.group(2).strip(), type=dep_type))
        return result

    poetry_main = re.search(r"\[tool\.poetry\.dependencies\](.*?)(?=^\[|\Z)", content, re.DOTALL | re.MULTILINE)
    if poetry_main:
        deps.extend(_parse_poetry_block(poetry_main.group(1), "main"))

    for section in ("tool.poetry.dev-dependencies", "tool.poetry.group.dev.dependencies"):
        poetry_dev = re.search(rf"\[{re.escape(section)}\](.*?)(?=^\[|\Z)", content, re.DOTALL | re.MULTILINE)
        if poetry_dev:
            dev_deps.extend(_parse_poetry_block(poetry_dev.group(1), "dev"))

    manager = "poetry" if "[tool.poetry]" in content else "uv" if "[tool.uv]" in content or "[dependency-groups]" in content else "pip/pep621"
    return _make_result("pyproject.toml", manager, deps, dev_deps, meta)


def _parse_pipfile(content: str) -> dict:
    deps, dev_deps, meta = [], [], {}

    m = re.search(r'python_version\s*=\s*"([^"]+)"', content)
    if m:
        meta["python"] = m.group(1)

    main = re.search(r"\[packages\](.*?)(?=^\[|\Z)", content, re.DOTALL | re.MULTILINE)
    if main:
        for line in main.group(1).splitlines():
            m = re.match(r'^([a-zA-Z0-9_\-]+)\s*=\s*"?([^"\n]+)"?', line.strip())
            if m:
                deps.append(_dep(m.group(1), m.group(2).strip()))

    dev = re.search(r"\[dev-packages\](.*?)(?=^\[|\Z)", content, re.DOTALL | re.MULTILINE)
    if dev:
        for line in dev.group(1).splitlines():
            m = re.match(r'^([a-zA-Z0-9_\-]+)\s*=\s*"?([^"\n]+)"?', line.strip())
            if m:
                dev_deps.append(_dep(m.group(1), m.group(2).strip(), type="dev"))

    return _make_result("Pipfile", "pipenv", deps, dev_deps, meta)


# ── JAVASCRIPT / TYPESCRIPT ───────────────────────────────────────────────────

def _parse_package_json(content: str) -> dict:
    # fix: controlla errore e contenuto vuoto
    if not content or content.startswith("ERROR:"):
        return _make_result_error("package.json", content or "empty content")

    content = content.strip()
    if not content:
        return _make_result_error("package.json", "empty content")

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        return _make_result_error("package.json", f"JSON parse error: {e}")

    meta = {k: data.get(k) for k in ("name", "version", "description", "main", "license") if k in data}

    deps      = [_dep(n, v)              for n, v in data.get("dependencies", {}).items()]
    dev_deps  = [_dep(n, v, type="dev")  for n, v in data.get("devDependencies", {}).items()]
    peer_deps = [_dep(n, v, type="peer") for n, v in data.get("peerDependencies", {}).items()]

    manager = "yarn" if "workspaces" in data else "npm"
    return _make_result("package.json", manager, deps + peer_deps, dev_deps, meta)


def _parse_package_lock_json(content: str) -> dict:
    if not content or content.startswith("ERROR:"):
        return _make_result_error("package-lock.json", content or "empty content")

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        return _make_result_error("package-lock.json", f"JSON parse error: {e}")

    deps = []
    lockfile_version = data.get("lockfileVersion", 1)

    if lockfile_version >= 2 and "packages" in data:
        for name, info in data.get("packages", {}).items():
            if not name:
                continue
            clean_name = re.sub(r"^node_modules/", "", name)
            deps.append(_dep(clean_name, info.get("version", "*"),
                             type="dev" if info.get("dev") else "main"))
    else:
        for name, info in data.get("dependencies", {}).items():
            deps.append(_dep(name, info.get("version", "*"),
                             extra={"resolved": "bundled" if info.get("bundled") else "registry"}))

    return _make_result("package-lock.json", "npm", deps,
                        meta={"lockfile_version": lockfile_version})


def _parse_yarn_lock(content: str) -> dict:
    if not content or content.startswith("ERROR:"):
        return _make_result_error("yarn.lock", content or "empty content")

    deps = []
    for m in re.finditer(r'^"?([^@\n"]+)@[^:]+:\n\s+version\s+"([^"]+)"', content, re.MULTILINE):
        deps.append(_dep(m.group(1).strip(), m.group(2)))
    return _make_result("yarn.lock", "yarn", deps)


# ── GO ────────────────────────────────────────────────────────────────────────

def _parse_go_mod(content: str) -> dict:
    if not content or content.startswith("ERROR:"):
        return _make_result_error("go.mod", content or "empty content")

    meta = {}
    m = re.search(r"^module\s+(\S+)", content, re.MULTILINE)
    if m:
        meta["module"] = m.group(1)
    m = re.search(r"^go\s+(\S+)", content, re.MULTILINE)
    if m:
        meta["go_version"] = m.group(1)

    deps = []
    require_block = re.search(r"require\s*\((.*?)\)", content, re.DOTALL)
    if require_block:
        for line in require_block.group(1).splitlines():
            m = re.match(r"\s+(\S+)\s+(\S+)", line)
            if m:
                deps.append(_dep(m.group(1), m.group(2),
                                 extra={"indirect": "// indirect" in line}))
    for m in re.finditer(r"^require\s+(\S+)\s+(\S+)", content, re.MULTILINE):
        deps.append(_dep(m.group(1), m.group(2)))

    return _make_result("go.mod", "go modules", deps, meta=meta)


# ── JAVA ──────────────────────────────────────────────────────────────────────

def _parse_pom_xml(content: str) -> dict:
    if not content or content.startswith("ERROR:"):
        return _make_result_error("pom.xml", content or "empty content")

    meta = {}
    for tag in ("groupId", "artifactId", "version"):
        m = re.search(rf"<{tag}>([^<]+)</{tag}>", content)
        if m:
            meta[tag] = m.group(1)

    deps = []
    for block in re.finditer(r"<dependency>(.*?)</dependency>", content, re.DOTALL):
        b        = block.group(1)
        group    = re.search(r"<groupId>([^<]+)</groupId>", b)
        artifact = re.search(r"<artifactId>([^<]+)</artifactId>", b)
        version  = re.search(r"<version>([^<]+)</version>", b)
        scope    = re.search(r"<scope>([^<]+)</scope>", b)
        if group and artifact:
            deps.append(_dep(
                f"{group.group(1)}:{artifact.group(1)}",
                version.group(1) if version else "*",
                type=scope.group(1) if scope else "main"
            ))

    return _make_result("pom.xml", "maven", deps, meta=meta)


def _parse_build_gradle(content: str) -> dict:
    if not content or content.startswith("ERROR:"):
        return _make_result_error("build.gradle", content or "empty content")

    deps, dev_deps = [], []
    for m in re.finditer(
        r"(implementation|api|compileOnly|runtimeOnly|testImplementation|annotationProcessor)"
        r"\s+['\"]([^'\"]+)['\"]", content
    ):
        config, coord = m.group(1), m.group(2)
        parts  = coord.split(":")
        name   = ":".join(parts[:2]) if len(parts) >= 2 else coord
        ver    = parts[2] if len(parts) >= 3 else "*"
        is_dev = "test" in config.lower()
        dep    = _dep(name, ver, type="dev" if is_dev else "main")
        (dev_deps if is_dev else deps).append(dep)

    return _make_result("build.gradle", "gradle", deps, dev_deps)


# ── DEVOPS ────────────────────────────────────────────────────────────────────

def _parse_docker_compose(content: str) -> dict:
    if not content or content.startswith("ERROR:"):
        return _make_result_error("docker-compose.yml", content or "empty content")

    services, images, build_services = [], [], []

    NON_SERVICE_KEYS = {
        "build", "deploy", "volumes", "ports", "environment", "depends_on",
        "networks", "command", "entrypoint", "image", "restart", "stdin_open",
        "tty", "labels", "env_file", "healthcheck", "logging", "extra_hosts"
    }

    services_block = re.search(r"^services:(.*?)(?=^\w|\Z)", content, re.MULTILINE | re.DOTALL)
    if services_block:
        block = services_block.group(1)
        for m in re.finditer(r"^\s{2}([\w][\w\-]*):", block, re.MULTILINE):
            name = m.group(1)
            if name not in NON_SERVICE_KEYS:
                services.append(name)

        # servizi con build locale (senza image)
        for m in re.finditer(r"^\s{2}([\w][\w\-]*):\s*\n(?:(?!\s{2}\w).*\n)*?\s+build:", block, re.MULTILINE):
            name = m.group(1)
            if name not in NON_SERVICE_KEYS and name not in build_services:
                build_services.append(name)

    for m in re.finditer(r"image:\s*(.+)", content):
        images.append(m.group(1).strip())

    return _make_result(
        "docker-compose.yml", "docker-compose",
        deps=[_dep(img, "*", type="service") for img in images],
        meta={"services": services, "build_services": build_services}
    )


def _parse_dockerfile(content: str) -> dict:
    if not content or content.startswith("ERROR:"):
        return _make_result_error("Dockerfile", content or "empty content")

    deps = []
    base_image = re.search(r"^FROM\s+(\S+)", content, re.MULTILINE)
    meta = {"base_image": base_image.group(1) if base_image else "unknown"}

    normalized = re.sub(r"\\\n\s*", " ", content)

    for m in re.finditer(
        r"RUN\s+(?:"
        r"apt(?:-get)?\s+install\s+(?:-y\s+)?([^;\n]+)"
        r"|pip\s+install\s+([^\n;]+)"
        r"|npm\s+install\s+([^\n;]*)"
        r")", normalized
    ):
        pkgs = (m.group(1) or m.group(2) or m.group(3) or "").strip()
        for pkg in pkgs.split():
            if pkg and not pkg.startswith("-"):
                deps.append(_dep(pkg))

    return _make_result("Dockerfile", "docker", deps, meta=meta)


def _parse_github_actions(content: str) -> dict:
    if not content or content.startswith("ERROR:"):
        return _make_result_error("github-actions", content or "empty content")

    actions = []
    for m in re.finditer(r"uses:\s*([^\s@]+)@(\S+)", content):
        actions.append(_dep(m.group(1), m.group(2), type="action"))

    workflow_name = re.search(r"^name:\s*(.+)", content, re.MULTILINE)
    return _make_result(
        "github-actions", "github-actions", actions,
        meta={"workflow": workflow_name.group(1).strip() if workflow_name else "unknown"}
    )


def _parse_env_example(content: str) -> dict:
    if not content or content.startswith("ERROR:"):
        return _make_result_error(".env.example", content or "empty content")

    variables = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            variables.append({"key": line, "value_type": "no_value"})
            continue
        key, _, raw_value = line.partition("=")
        key       = key.strip()
        raw_value = raw_value.strip()

        if not raw_value:
            value_type = "empty"
        elif re.match(r"^[<\[{].*[>\]}]$", raw_value):
            value_type = "placeholder"
        elif re.match(r"^(your_|CHANGE_ME|xxx|todo|example|insert)", raw_value, re.IGNORECASE):
            value_type = "placeholder"
        else:
            value_type = "example"

        variables.append({"key": key, "value_type": value_type})

    return _make_result(
        format=".env.example",
        manager="env",
        deps=[],
        meta={"total_variables": len(variables), "variables": variables}
    )