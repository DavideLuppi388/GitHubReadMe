from langchain_core.tools import tool
from typing import Annotated, Optional


@tool
def read_file(
    repo_full_name: Annotated[str, "The full name of the repo, must be 'user/repository'"],
    file_path: Annotated[str, "The path of the file inside the repo, e.g. 'src/main.py'"],
    branch: Annotated[str, "The branch to read from, defaults to 'main'"] = "main",
    token: Annotated[Optional[str], "GitHub Personal Access Token"] = None,
    start_line: Annotated[Optional[int], "Optional: Start line number"] = None,
    end_line: Annotated[Optional[int], "Optional: End line number"] = None,
) -> str:
    """
    Reads the content of a file from a GitHub repository. 
    Supports full file reading or partial reading via line numbers.
    """
    import requests
    import base64

    headers = {"Authorization": f"token {token}"} if token else {}
    
    # Gestione branch fallback (esatta alla tua)
    branches_to_try = list(dict.fromkeys([branch, "main", "master"]))

    for b in branches_to_try:
        url = f"https://api.github.com/repos/{repo_full_name}/contents/{file_path}?ref={b}"
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            
            # Decodifica contenuto
            if data.get("encoding") == "base64":
                content = base64.b64decode(data["content"]).decode("utf-8")
            else:
                content = requests.get(data.get("download_url"), headers=headers).text
            
            # Applicazione filtro linee (se richiesto)
            if start_line is not None or end_line is not None:
                lines = content.splitlines()
                start = (start_line - 1) if start_line else 0
                end = end_line if end_line else len(lines)
                content = "\n".join(lines[start:end])
                
            return content

    return f"ERROR: Cannot read '{file_path}' from '{repo_full_name}' (tried branches: {branches_to_try})"

