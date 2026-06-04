# agents/code_analyzer_agent.py

from langchain_core.messages import HumanMessage
from langchain_core.language_models import BaseChatModel
from langchain.agents import create_agent
from agent_tools.read_file_tool import read_file
from agent_tools.extract_code_metadata_tool import extract_code_metadata
from agent_tools.analyze_dependencies_flow_tool import analyze_dependencies_flow
from agent_tools.query_code_context_tool import query_code_context
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from prompts.code_analyzer_prompt import CODE_ANALYZER_PROMPT

load_dotenv()

def create_code_analyzer_agent(llm: BaseChatModel):
    """
    Creates a code analyzer agent that extracts structured knowledge from source code.
    
    Receives a list of file paths from the repo scanner (does not do file discovery).
    For each file, reads the content and extracts classes, functions, imports and routes.
    Builds an import dependency graph across all files and answers questions about the codebase.

    Args:
        llm: The language model to use (e.g. ChatOpenAI, ChatAnthropic)

    Returns:
        A compiled LangGraph react agent
    """
    tools = [
        read_file,
        extract_code_metadata,
        analyze_dependencies_flow,
        query_code_context,
    ]
    return create_agent(
        model=llm,
        tools=tools,
        system_prompt=CODE_ANALYZER_PROMPT,
        name="code_analyzer",
    )


if __name__ == "__main__":
    llm   = ChatOpenAI(model="gpt-4o-mini")
    agent = create_code_analyzer_agent(llm)

    # il code_analyzer riceve la lista file già pronta dal repo_scanner
    py_files = [
        "scripts/_lib.py",
        "scripts/audit_lessons.py",
        "scripts/build_catalog.py",
        "scripts/install_skills.py",
        "scripts/lesson_run.py",
        "scripts/link_check.py",
        "scripts/scaffold_workbench.py",
    ]

    result = agent.invoke({
        "messages": [
            HumanMessage(content=(
                f"Analyze the code of the repo rohitg00/ai-engineering-from-scratch. "
                f"Here are the Python files to analyze: {py_files}. "
                f"For each file: read it and extract its metadata (classes, functions, imports, routes). "
                f"Then build the import dependency graph across all files. "
                f"Finally summarize the architecture: main modules, key functions, dependency hubs."
            ))
        ]
    })

    for msg in result["messages"]:
        msg_type = getattr(msg, "type", type(msg).__name__)
        if msg_type == "tool":
            print(f"🔧 TOOL [{msg.name}]: {str(msg.content)[:150]}...")
        elif msg_type == "ai" and hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                print(f"📞 CALLING: {tc['name']}({list(tc['args'].keys())})")
        elif msg_type == "ai":
            print(f"🤖 AGENT: {msg.content[:300]}")

