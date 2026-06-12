# supervisors/repo_intelligence_supervisor.py

import json
import re
import os
from typing import Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from dotenv import load_dotenv

from agents.repo_scanner_agent  import create_repo_scanner_agent
from agents.code_analyzer_agent import create_code_analyzer_agent
from agents.stack_analyzer_agent import create_stack_analyzer_agent
from supervisors.states.RepoIntelligentState import RepoIntelligenceState

load_dotenv()


def create_repo_intelligence_supervisor(llm: BaseChatModel):

    # ── crea agenti una volta sola ────────────────────────────────────────────
    repo_scanner   = create_repo_scanner_agent(llm)
    code_analyzer  = create_code_analyzer_agent(llm)
    stack_analyzer = create_stack_analyzer_agent(llm)

    def _extract_json(text: str) -> dict:
        """Estrae il primo blocco JSON valido da una stringa di testo."""
        try:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass
        return {}

    # ── nodo 1: repo scanner ──────────────────────────────────────────────────
    def run_repo_scanner(state: RepoIntelligenceState) -> dict:
        print("repo_scanner")
        repo  = state["repo_full_name"]
        token = state.get("token") or ""

        result = repo_scanner.invoke({
            "messages": [HumanMessage(content=f"""
                            Analyze the repository: {repo}
                            GitHub token: {token}

                            IMPORTANT: Execute these steps SEQUENTIALLY. Wait for each step before starting the next.

                            Step 1: Call get_repo_structure with:
                                    - repo_full_name: "{repo}"
                                    - token: "{token}"
                                    WAIT for the result. Store it as STRUCTURE.

                            Step 2: Only after Step 1, call find_files_in_structure with:
                                    - structure: STRUCTURE from step 1
                                    - extension: ".py"

                            Step 3: Only after Step 1, call find_files_in_structure with:
                                    - structure: STRUCTURE from step 1
                                    - name_contains: "requirements.txt"
                                    Repeat for: "pyproject.toml", "package.json", "Dockerfile", "docker-compose.yml", ".env.example", ".env"


                            Step 4: Call read_file with:
                                    - repo_full_name: "{repo}"
                                    - file_path: file_path that you want to read
                                    - token: "{token}"

                            Return ONLY a JSON object with these exact keys (no other text):
                            {{
                                "STRUCTURE": finded structure 
                                "project_purpose": "one paragraph description",
                                "source_files": ["path1", "path2"],
                                "config_files": ["path1", "path2"],
                                "key_directories": [{{"name": "...", "purpose": "..."}}],
                                "notable_files": ["path1", "path2"]
                            }}
            """)]
        })

        last_msg = result["messages"][-1].content
        data     = _extract_json(last_msg)

        # filtra source files non rilevanti
        source_files = [
            f for f in data.get("source_files", [])
            if "__init__" not in f
            and "__pycache__" not in f
        ]

        return {
            "structure": data.get("STRUCTURE"),
            "messages":      [result["messages"][-1]],
            "source_files":  source_files,
            "config_files":  data.get("config_files", []),
            "project_purpose": data.get("project_purpose", ''),
        }

    # ── nodo 2a: code analyzer ────────────────────────────────────────────────
    def run_code_analyzer(state: RepoIntelligenceState) -> dict:
        print('code_analyzer')
        repo     = state["repo_full_name"]
        token    = state.get("token") or ""
        py_files = state.get("source_files") or []
        structure = state.get("structure") or []

        result = code_analyzer.invoke({
            "messages": [HumanMessage(content=f"""
                Analyze the source code of repository: {repo}
                GitHub token: {token}
                Files to analyze: {py_files}
                use this structure: {structure} to identify the path of file

                For EACH file in the list, IN ORDER:
                1. Call read_file with repo_full_name="{repo}", file_path=<path>, token="{token}"
                2. Call extract_code_metadata with file_path=<path> and content from step 1
                Store result as: {{"file_path": "<path>", "metadata": <result>}}

                After ALL files are processed:
                3. Call analyze_dependencies_flow with the complete metadata list
                4. Call query_code_context with query="" and search_type="class"
                5. Call query_code_context with query="main" and search_type="function"

                Return ONLY a JSON object:
                {{
                    "modules": [{{"name": "...", "purpose": "..."}}],
                    "classes": [{{"name": "...", "file": "...", "methods": []}}],
                    "key_functions": [{{"name": "...", "file": "...", "purpose": "..."}}],
                    "hub_modules": ["..."],
                    "entry_points": ["..."],
                    "architecture": "..."
                }}
            """)]
        })

        return {
            "messages":    [result["messages"][-1]],
            "code_summary": result["messages"][-1].content,
        }

    # ── nodo 2b: stack analyzer ───────────────────────────────────────────────
    def run_stack_analyzer(state: RepoIntelligenceState) -> dict:
        print('stack_analyzer')
        repo         = state["repo_full_name"]
        token        = state.get("token") or ""
        config_files = state.get("config_files") or []
        structure = state.get("structure") or []

        result = stack_analyzer.invoke({
            "messages": [HumanMessage(content=f"""
                Analyze the technology stack of repository: {repo}
                GitHub token: {token}
                Config files to analyze: {config_files}
                use this structure: {structure} to identify the path of file

                IMPORTANT: Execute SEQUENTIALLY.

                Step 1: For EACH config file in {config_files}, IN ORDER:
                        a. Call read_file with repo_full_name="{repo}", file_path=<path>, token="{token}"
                        b. Call parse_dependencies with file_path=<path> and content from step a

                Step 2: Call classify_stack ONCE with:
                        - parsed_dependencies: JSON string of ALL parse_dependencies results
                        - repo_structure: output from Step 1

                Return ONLY a JSON object:
                {{
                    "language": {{"name": "...", "version": "..."}},
                    "frameworks": [{{"name": "...", "type": "..."}}],
                    "databases": ["..."],
                    "devops": [{{"name": "...", "category": "..."}}],
                    "architecture": "...",
                    "package_managers": ["..."],
                    "stack_summary": "one line summary"
                }}
            """)]
        })

        return {
            "messages":    [result["messages"][-1]],
            "stack_summary": result["messages"][-1].content,
        }

    # ── nodo 3: aggregazione ──────────────────────────────────────────────────
    def aggregate(state: RepoIntelligenceState) -> dict:
        repo = state["repo_full_name"]

        stack_data = _extract_json(state.get("stack_summary") or "")
        code_data  = _extract_json(state.get("code_summary")  or "")

        report = f"""# Repository Analysis: {repo}

                ## Project Purpose
                {state.get("project_purpose", "N/A")}

                ## Technology Stack
                - Language:      {stack_data.get("language", {}).get("name", "N/A")} {stack_data.get("language", {}).get("version", "")}
                - Architecture:  {stack_data.get("architecture", "N/A")}
                - Frameworks:    {", ".join(f.get("name","") for f in stack_data.get("frameworks", []))}
                - Databases:     {", ".join(stack_data.get("databases", []))}
                - DevOps:        {", ".join(d.get("name","") for d in stack_data.get("devops", []))}
                - Pkg Managers:  {", ".join(stack_data.get("package_managers", []))}
                - Summary:       {stack_data.get("stack_summary", "N/A")}

                ## Code Architecture
                - Architecture:  {code_data.get("architecture", "N/A")}
                - Entry points:  {", ".join(code_data.get("entry_points", []))}
                - Hub modules:   {", ".join(code_data.get("hub_modules", []))}
                - Modules:       {len(code_data.get("modules", []))} found
                - Classes:       {len(code_data.get("classes", []))} found

                ## Files
                - Source files:  {len(state.get("source_files") or [])}
                - Config files:  {len(state.get("config_files") or [])}

                ## Raw Outputs
                ### Stack
                {state.get("stack_summary", "")}

                ### Code
                {state.get("code_summary", "")}
                """
        return {
            "messages":     [AIMessage(content=report)],
            "final_report": report,
        }

    # ── router: dopo scanner lancia code e stack in parallelo ─────────────────
    def route_after_scanner(state: RepoIntelligenceState) -> list:
        """Lancia code_analyzer e stack_analyzer in parallelo con Send."""
        return [
            Send("code_analyzer",  state),
            Send("stack_analyzer", state),
        ]

    # ── costruzione grafo ─────────────────────────────────────────────────────
    graph = StateGraph(RepoIntelligenceState)

    graph.add_node("repo_scanner",   run_repo_scanner)
    graph.add_node("code_analyzer",  run_code_analyzer)
    graph.add_node("stack_analyzer", run_stack_analyzer)
    graph.add_node("aggregate",      aggregate)

    graph.add_edge(START, "repo_scanner")
    graph.add_conditional_edges(
        "repo_scanner",
        route_after_scanner,
        ["code_analyzer", "stack_analyzer"]
    )
    graph.add_edge("code_analyzer",  "aggregate")
    graph.add_edge("stack_analyzer", "aggregate")
    graph.add_edge("aggregate",      END)

    return graph.compile()


if __name__ == "__main__":
    llm        = ChatOpenAI(model="gpt-4.1")
    supervisor = create_repo_intelligence_supervisor(llm)

    repo_name = "DavideLuppi388/GitHubReadMe"
    token     = os.getenv("GITHUB_TOKEN")

    result = supervisor.invoke({
        "repo_full_name": repo_name,
        "branch":         "main",
        "token":          token,
        "messages":       [],
    })

    print(result["final_report"])

    # salva su file
    output_path = os.path.join(os.path.dirname(__file__), "res.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result["final_report"])
    print(f"\n✅ Saved to {output_path}")