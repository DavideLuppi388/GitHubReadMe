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



















exit()
print('-------------------scanner giusto------------------')
config_files = []
for name in CONFIG_FILE_NAMES:
    found = find_files_in_structure.invoke({
        "structure": structure,
        "name_contains": name,
    })
    found = json.loads(found)
    config_files.extend(found)

config_files = list(set(config_files))
print(config_files)
print('-----------------------------------')
for file in config_files:
    #print(file)
    f = read_file.invoke({
        "repo_full_name": repo_name,
        "file_path": file,
    })
    #print(f)
    #print('-------------------------------------------')

cont = get_dir_content.invoke({"repo_full_name": repo_name,"dir_path": "scripts"})
print(cont)
print('-------------------------------------')
cont=json.loads(cont)
for file in cont:
    r = read_file.invoke({
        "repo_full_name": repo_name,
        "file_path": file['path'],
    })
    #print(file['name'])
    #print(r)
    #print('-----------------------------------------')

results = search_code_content.invoke({
    "repo_full_name": repo_name,
    "query": "class",
    "file_paths": [file['path'] for file in cont],
})

print(type(results))
    
