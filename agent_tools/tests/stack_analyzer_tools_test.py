#tool in the agent
from agent_tools.parse_dependencies_tool import parse_dependencies
from agent_tools.classify_stack_tool import classify_stack
from agent_tools.read_file_tool import read_file

# other dep
import json

#extra tool
from agent_tools.get_repo_structure_tool import get_repo_structure
from agent_tools.glob_search_tool import find_files_in_structure

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

repo_name = "rohitg00/ai-engineering-from-scratch"
structure = get_repo_structure.invoke({"repo_full_name": repo_name, "token": "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"})
#print(structure)
#print('-------------------------------------')
config_files = []
for name in CONFIG_FILE_NAMES:
    found = find_files_in_structure.invoke({
        "structure": structure,
        "name_contains": name,
    })
    if found != []:
        config_files.extend(json.loads(found))
print(config_files)
print('-----------------------------------')
parsed_depend = []
for file in config_files:
    #print(file)
    f = read_file.invoke({
        "repo_full_name": repo_name,
        "file_path": file,
    })

    parse = parse_dependencies.invoke({
        "file_path": file,
        "content": f
    })

    parsed_depend.append(parse)

    #print(parse)
    #print('-----------------------')

print(parsed_depend)

res = classify_stack.invoke({
    "parsed_dependencies": json.dumps(parsed_depend),
    "repo_structure": structure
})

print(res)