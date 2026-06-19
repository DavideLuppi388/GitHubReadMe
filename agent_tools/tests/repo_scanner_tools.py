#tool in teh agent
from agent_tools.get_repo_structure_tool import get_repo_structure
from agent_tools.read_file_tool import read_file
from agent_tools.parse_dependencies_tool import parse_dependencies
import json
CONFIG_FILE_NAMES = [
    # python
    "requirements.txt",
    "requirements-dev.txt",
    "requirements-prod.txt",
    "requirements-test.txt",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "Pipfile",
    # javascript
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    # go
    "go.mod",
    # java
    "pom.xml",
    "build.gradle",
    # devops
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    # env
    ".env.example",
    ".env.template",
    ".env.sample",
    # ci/cd
    ".github/workflows",
    ".gitlab-ci.yml",
]

repo_name = "DavideLuppi388/GitHubReadMe"
structure = get_repo_structure.invoke({"repo_full_name": repo_name})
#print("STRUCTURE ----------------------", structure)
files_to_read = [file for file, metadata in json.loads(structure).items() if metadata.get("category") == "config" or metadata.get("category") == "build"]

if type(files_to_read) == str:
    files_to_read = [files_to_read]
    
f = read_file.invoke({
        "repo_full_name": repo_name,
        "file_path": files_to_read,
    })

f = json.loads(f)

for file, content in f.items():
    dep = parse_dependencies.invoke({
        "file_path": file,
        "content": content,
    })
    print("DEPENDENCIES -------------------------", dep)

