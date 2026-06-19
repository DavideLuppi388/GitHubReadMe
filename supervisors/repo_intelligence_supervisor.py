# supervisors/repo_intelligence_supervisor.py

import json
import os

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv

from agents.repo_scanner_agent  import create_repo_scanner_agent
from agents.doc_analyzer_agent import create_documentation_analyst_agent
from supervisors.states.RepoIntelligentState import RepoIntelligenceState

load_dotenv()

def create_repo_intelligent_supervisor(llm: BaseChatModel):
    
    repo_scanner = create_repo_scanner_agent(llm)
    doc_analyst = create_documentation_analyst_agent(llm)
    
    def repo_scanner_node(state: RepoIntelligenceState):
        repo  = state["repo_full_name"]
        token = state.get("token") or ""
        branch = state.get("branch") or "main"
        
        result = repo_scanner.invoke({"messages": [HumanMessage(content= 
            f"Analyze the following GitHub repository and return the structured JSON output as described in your instructions.\n\n"
            f"Repository: {repo}\n"
            f"Branch: {branch}\n"
            f"Token: {token}\n\n"
            f"Start by calling get_repo_structure, then parse dependencies, then read the necessary files.\n"
            f"Return only the JSON object. No prose, no markdown.")]})
        
        scanner_output = result["messages"][-1].content
        return {"scanner_output": scanner_output, "messages": result["messages"]}

    def documentation_analyst_node(state: RepoIntelligenceState):
        
        scanner_output = state.get("scanner_output") or ""
        
        if scanner_output == "":
            documentation = "No documentation available"
            return {"documentation": documentation}
        
        result = doc_analyst.invoke({"messages": [
            HumanMessage(content=
            "You are receiving the output of a repository scanner agent. "
            "Your job is to transform this structured data into a documentation blueprint.\n\n"
            "Scanner output:\n"
            f"{scanner_output}\n\n"
            "Produce the documentation blueprint now. "
            "Use read_file only if the scanner flagged incomplete data in 'observations' or"
            "'existing_documentation.readme_quality' is 'stub' or 'partial'.\n"
            "Return only the JSON object. No prose, no markdown."
            ),
        ]})
        documentation = result["messages"][-1].content
        
        return {"documentation": documentation, "messages": result["messages"]}
        
    
    graph = StateGraph(RepoIntelligenceState)

    graph.add_node("repo_scanner",   repo_scanner_node)
    graph.add_node("documentation_analyst",  documentation_analyst_node)

    graph.add_edge(START, "repo_scanner")
    graph.add_edge("repo_scanner", "documentation_analyst")
    graph.add_edge("documentation_analyst", END)

    return graph.compile()


if __name__ == "__main__":
    llm        = ChatOpenAI(model="gpt-4o-mini")
    supervisor = create_repo_intelligent_supervisor(llm)

    repo_name = "DavideLuppi388/GitHubReadMe"
    token     = os.getenv("GITHUB_TOKEN")

    result = supervisor.invoke({
        "repo_full_name": repo_name,
        "token":          token,
        "messages":       [],
    })

    # salva su file
    output_path = os.path.join(os.path.dirname(__file__), "res.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result["scanner_output"])
        f.write("\n")
        f.write(result["documentation"])
    print(f"\n✅ Saved to {output_path}")
