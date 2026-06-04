from langchain_core.tools import tool
from typing import Annotated, Optional
import json

@tool
def get_repo_structure(repo_full_name: Annotated[str, "the full name of the repo, it must be 'user/repository' "],
                        branch: Annotated[str, "The branch to explore, defaults to 'main' or 'master'"] = "main",
                        token: Annotated[Optional[str], "GitHub Personal Access Token for authentication"] = None,
                        path_prefix: Annotated[Optional[str], "Optional repository-relative path prefix used to limit the returned tree. Examples: 'src/', 'packages/api/', '.github/workflows/'. If None, returns the full repository tree."] = None
) -> dict:
    """
    Explores a GitHub repository and returns its entire file and directory structure 
    as a nested dictionary. Useful for understanding project architecture.
    """
    import requests

    headers = {"Authorization": f"token {token}"} if token else {}

    data = None
    branch_to_try = [branch]
    if branch != "main": branch_to_try.append("main")
    if branch != "master": branch_to_try.append("master")
    for b in branch_to_try:
        base_url = f"https://api.github.com/repos/{repo_full_name}/git/trees/{b}?recursive=1"
        response = requests.get(base_url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            break
    
    if data == None:
        return f"cuoldn't get acces to {repo_full_name}, try to add a token or change the branch"
    
    structure = {}
    
    for item in data.get('tree', []):
        item_path = item["path"]

        if path_prefix:
            normalized_prefix = path_prefix.strip("/")
            if item_path != normalized_prefix and not item_path.startswith(normalized_prefix + "/"):
                continue
        path_parts = item['path'].split('/')
        current_level = structure
        
        # Naviga o crea il dizionario per ogni parte del percorso
        for part in path_parts[:-1]:
            current_level = current_level.setdefault(part, {})
            
        # Aggiungi il file o la directory finale
        name = path_parts[-1]
        if item['type'] == 'blob':
            current_level[name] = "file"
        else:
            current_level[name] = {}
            
    return json.dumps(structure, ensure_ascii=False)
