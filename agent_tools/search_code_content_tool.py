from langchain_core.tools import tool
from typing import Annotated, Optional, List
import json
import re

@tool
def search_code_content(
    repo_full_name: Annotated[str, "The full name of the repo, must be 'user/repository'"],
    query: Annotated[str, "Text or regex pattern to search for inside file contents"],
    file_paths: Annotated[List[str], "List of file paths to search in (use find_files_in_structure to get them)"],
    branch: Annotated[str, "The branch to search in, defaults to 'main'"] = "main",
    token: Annotated[Optional[str], "GitHub Personal Access Token for authentication"] = None,
    use_regex: Annotated[bool, "If True, treat query as a regex pattern. Default is plain text search."] = False,
    case_sensitive: Annotated[bool, "If False, search is case-insensitive. Default is False."] = False,
    context_lines: Annotated[int, "Number of lines to show before and after each match (like grep -C). Default is 2."] = 2,
) -> str:
    """
    Performs a text or regex search inside the content of files in a GitHub repository.
    Returns a JSON string with matches, file path, line number, matched line, and surrounding context.
    Similar to 'grep -rn' on a local repo.
    """
    import requests
    import base64

    headers = {"Authorization": f"token {token}"} if token else {}
    flags = 0 if case_sensitive else re.IGNORECASE
    pattern = re.compile(query if use_regex else re.escape(query), flags)
    results: List[dict] = []

    def fetch_file(path: str) -> Optional[str]:
        branches_to_try = [branch]
        if branch != "main":   branches_to_try.append("main")
        if branch != "master": branches_to_try.append("master")

        for b in branches_to_try:
            url = f"https://api.github.com/repos/{repo_full_name}/contents/{path}?ref={b}"
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if data.get("encoding") == "base64":
                    return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
                download_url = data.get("download_url")
                if download_url:
                    return requests.get(download_url, headers=headers).text
        return None

    for file_path in file_paths:
        content = fetch_file(file_path)
        if content is None:
            continue

        lines = content.splitlines()
        file_matches = []

        for line_num, line in enumerate(lines, start=1):
            if pattern.search(line):
                # context: righe prima e dopo
                start = max(0, line_num - 1 - context_lines)
                end   = min(len(lines), line_num + context_lines)

                context_before = lines[start : line_num - 1]
                context_after  = lines[line_num : end]

                file_matches.append({
                    "line_number": line_num,
                    "match": line,
                    "context_before": context_before,
                    "context_after": context_after,
                })

        if file_matches:
            results.append({
                "file": file_path,
                "total_matches": len(file_matches),
                "matches": file_matches,
            })

    return json.dumps(results, ensure_ascii=False)
