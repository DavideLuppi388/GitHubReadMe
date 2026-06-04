from langchain_core.tools import tool
from typing import Annotated, Optional, List
import json

@tool
def get_dir_content(
    repo_full_name: Annotated[str, "The full name of the repo, must be 'user/repository'"],
    dir_path: Annotated[str, "The path of the directory inside the repo, e.g. 'src/utils'. Use '' for root."],
    branch: Annotated[str, "The branch to read from, defaults to 'main'"] = "main",
    token: Annotated[Optional[str], "GitHub Personal Access Token for authentication"] = None,
) -> str:
    """
    Lists the immediate contents (files and subdirectories) of a single directory
    in a GitHub repository, without recursion.
    Returns a JSON string.
    Each entry contains: name, type ('file' or 'dir'), path, and size (for files).
    """
    import requests

    headers = {"Authorization": f"token {token}"} if token else {}

    branches_to_try = [branch]
    if branch != "main":   branches_to_try.append("main")
    if branch != "master": branches_to_try.append("master")

    for b in branches_to_try:
        url = f"https://api.github.com/repos/{repo_full_name}/contents/{dir_path}?ref={b}"
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()

            if not isinstance(data, list):
                raise Exception(f"'{dir_path}' is a file, not a directory.")

            entries = [
                {
                    "name": item["name"],
                    "type": item["type"],        # "file" | "dir" | "symlink" | "submodule"
                    "path": item["path"],
                    "size": item.get("size", 0), # 0 per le directory
                }
                for item in data
            ]
            return json.dumps(entries, ensure_ascii=False)

    raise Exception(f"Cannot read directory '{dir_path}' from '{repo_full_name}' (tried branches: {branches_to_try})")
