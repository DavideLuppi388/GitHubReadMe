import os
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from agents.repo_scanner_agent import create_repo_scanner_agent
from agents.code_analyzer_agent import create_code_analyzer_agent
from agents.stack_analyzer_agent import create_stack_analyzer_agent
from dotenv import load_dotenv

load_dotenv()

repo_name = "rohitg00/ai-engineering-from-scratch"
token     = os.getenv("GITHUB_TOKEN")

py_files = [
    "scripts/_lib.py",
    "scripts/audit_lessons.py",
    "scripts/build_catalog.py",
    "scripts/check_readme_counts.py",
    "scripts/install_skills.py",
    "scripts/lesson_run.py",
    "scripts/link_check.py",
    "scripts/scaffold_workbench.py",
]

config_files = [
    "requirements.txt",
    "phases/00-setup-and-tooling/07-docker-for-ai/code/Dockerfile",
    "phases/00-setup-and-tooling/07-docker-for-ai/code/docker-compose.yml",
]

REPO_SCANNER_MSG = HumanMessage(content=f"""
Analyze the repository: {repo_name}
GitHub token: {token}

IMPORTANT: Execute these steps SEQUENTIALLY. Wait for each step to complete before starting the next.

Step 1: Call get_repo_structure with repo_full_name="{repo_name}" and token="{token}"
        WAIT for the result. Store it as STRUCTURE.

Step 2: Only after Step 1 is complete, call find_files_in_structure with:
        - structure: STRUCTURE from step 1
        - name_contains: "requirements.txt"

Step 3: Only after Step 2, call find_files_in_structure with:
        - structure: STRUCTURE from step 1
        - path_contains: "scripts"
        - extension: ".py"  (NOT name_contains)

Step 4: Only after Step 3, call get_dir_content with:
        - repo_full_name: "{repo_name}"
        - dir_path: "scripts"
        - token: "{token}"

Step 5: Only after Step 4, call read_file with:
        - repo_full_name: "{repo_name}"
        - file_path: "README.md"
        - token: "{token}"

DO NOT call multiple tools at the same time.
DO NOT call find_files_in_structure before get_repo_structure has returned a result.

Return:
- PROJECT_PURPOSE: what this repo does
- SOURCE_FILES: list of .py files found in step 3
- CONFIG_FILES: list of config files found in step 2
- KEY_DIRECTORIES: main directories and their purpose
- NOTABLE_FILES: important files
""")

CODE_ANALYZER_MSG = HumanMessage(content=f"""
Analyze the source code of repository: {repo_name}
GitHub token: {token}

Here is the list of Python files to analyze: {py_files}

Please do the following IN ORDER:
1. For EACH file in the list:
   a. Call read_file with repo_full_name="{repo_name}" and the file path
   b. Call extract_code_metadata with the file path and its content
2. Collect ALL metadata results into a list with format:
   [{{"file_path": "path", "metadata": <extract_code_metadata output>}}, ...]
3. Call analyze_dependencies_flow with the full metadata list
4. Call query_code_context with query="" and search_type="class" to list all classes
5. Call query_code_context with query="main" and search_type="function" to find entry points

Return:
- MODULES: list of modules with their purpose
- CLASSES: all classes found with their methods
- KEY_FUNCTIONS: most important functions per module
- DEPENDENCY_GRAPH: which modules import which
- ENTRY_POINTS: files/functions that act as entry points
- ARCHITECTURE: overall code architecture observations
""")

STACK_ANALYZER_MSG = HumanMessage(content=f"""
Analyze the technology stack of repository: {repo_name}
GitHub token: {token}

Here is the list of config files to analyze: {config_files}

Please do the following IN ORDER:
1. Call get_repo_structure with repo_full_name="{repo_name}"
2. For EACH config file in the list:
   a. Call read_file with repo_full_name="{repo_name}" and the file path
   b. Call parse_dependencies with the file path and its content
3. After ALL files are parsed, call classify_stack ONCE with:
   - parsed_dependencies: the list of ALL parse_dependencies outputs as JSON string
   - repo_structure: the output of get_repo_structure

Return:
- LANGUAGE: primary language and version
- FRAMEWORKS: detected frameworks with their type
- DATABASES: detected databases and storage systems
- DEVOPS: containerization, CI/CD, server tools
- ARCHITECTURE: backend-api / fullstack / ml / data / ai-agent
- PACKAGE_MANAGERS: package managers in use
- STACK_SUMMARY: one-line summary
""")

def run_agents():
    llm = ChatOpenAI(model="gpt-4.1")
    output_path = os.path.join(os.path.dirname(__file__), "res.txt")

    output_lines = []

    def log(text: str):
        print(text)
        output_lines.append(text)

    # ── repo scanner ──────────────────────────────────────────────────────────
    log("=" * 60)
    log("REPO SCANNER")
    log("=" * 60)
    for chunk in create_repo_scanner_agent(llm).stream({"messages": [REPO_SCANNER_MSG]}):
        for node, output in chunk.items():
            messages = output.get("messages", [])
            if not messages:
                continue
            last     = messages[-1]
            msg_type = getattr(last, "type", "")
            if msg_type == "tool":
                log(f"🔧 [{node}] TOOL [{last.name}]: {str(last.content)}...")
            elif msg_type == "ai" and hasattr(last, "tool_calls") and last.tool_calls:
                for tc in last.tool_calls:
                    log(f"📞 [{node}] CALLING: {tc['name']}({list(tc['args'].keys())})")
            elif msg_type == "ai" and last.content:
                log(f"🤖 [{node}]: {last.content}")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))

    # ── code analyzer ─────────────────────────────────────────────────────────
    log("\n" + "=" * 60)
    log("CODE ANALYZER")
    log("=" * 60)
    for chunk in create_code_analyzer_agent(llm).stream({"messages": [CODE_ANALYZER_MSG]}):
        for node, output in chunk.items():
            messages = output.get("messages", [])
            if not messages:
                continue
            last     = messages[-1]
            msg_type = getattr(last, "type", "")
            if msg_type == "tool":
                log(f"🔧 [{node}] TOOL [{last.name}]: {str(last.content)}...")
            elif msg_type == "ai" and hasattr(last, "tool_calls") and last.tool_calls:
                for tc in last.tool_calls:
                    log(f"📞 [{node}] CALLING: {tc['name']}({list(tc['args'].keys())})")
            elif msg_type == "ai" and last.content:
                log(f"🤖 [{node}]: {last.content}")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))

    # ── stack analyzer ────────────────────────────────────────────────────────
    log("\n" + "=" * 60)
    log("STACK ANALYZER")
    log("=" * 60)
    for chunk in create_stack_analyzer_agent(llm).stream({"messages": [STACK_ANALYZER_MSG]}):
        for node, output in chunk.items():
            messages = output.get("messages", [])
            if not messages:
                continue
            last     = messages[-1]
            msg_type = getattr(last, "type", "")
            if msg_type == "tool":
                log(f"🔧 [{node}] TOOL [{last.name}]: {str(last.content)}...")
            elif msg_type == "ai" and hasattr(last, "tool_calls") and last.tool_calls:
                for tc in last.tool_calls:
                    log(f"📞 [{node}] CALLING: {tc['name']}({list(tc['args'].keys())})")
            elif msg_type == "ai" and last.content:
                log(f"🤖 [{node}]: {last.content}")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))


if __name__ == "__main__":
    run_agents()