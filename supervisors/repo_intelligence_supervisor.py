from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph_supervisor import create_supervisor
from dotenv import load_dotenv

from agents.repo_scanner_agent import create_repo_scanner_agent
from agents.code_analyzer_agent import create_code_analyzer_agent
from agents.stack_analyzer_agent import create_stack_analyzer_agent

from prompts.repo_intelligent_supervisor_prompt import REPO_INTELLIGENCE_PROMPT

load_dotenv()

from typing import TypedDict, Annotated, List, Any
import operator
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# Definiamo lo stato che verrà passato tra i nodi
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    repo_structure: Any  # Dati dal repo_scanner
    code_analysis: Any   # Dati dal code_analyzer
    stack_info: Any      # Dati dallo stack_analyzer

def create_repo_intelligence_supervisor(llm: BaseChatModel):
    # 1. Inizializza i nodi (agenti)
    repo_scanner = create_repo_scanner_agent(llm)
    code_analyzer = create_code_analyzer_agent(llm)
    stack_analyzer = create_stack_analyzer_agent(llm)

    # 2. Definiamo i nodi del grafo
    def repo_scanner_node(state: AgentState):
        result = repo_scanner.invoke(state)
        return {"repo_structure": result, "messages": [result]}

    def code_analyzer_node(state: AgentState):
        # Il code_analyzer ora riceve automaticamente il repo_structure dallo stato
        context = f"Repo structure: {state['repo_structure']}"
        result = code_analyzer.invoke({"messages": state['messages'] + [HumanMessage(content=context)]})
        return {"code_analysis": result, "messages": [result]}

    def stack_analyzer_node(state: AgentState):
        context = f"Analysis results: {state['code_analysis']}"
        result = stack_analyzer.invoke({"messages": state['messages'] + [HumanMessage(content=context)]})
        return {"stack_info": result, "messages": [result]}

    # 3. Costruiamo il grafo
    workflow = StateGraph(AgentState)
    workflow.add_node("scanner", repo_scanner_node)
    workflow.add_node("analyzer", code_analyzer_node)
    workflow.add_node("stacker", stack_analyzer_node)

    # 4. Creiamo il flusso sequenziale
    workflow.set_entry_point("scanner")
    workflow.add_edge("scanner", "analyzer")
    workflow.add_edge("analyzer", "stacker")
    workflow.add_edge("stacker", END)

    # 5. Compiliamo con memoria (per mantenere lo storico)
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)

"""def create_repo_intelligence_supervisor(llm: BaseChatModel):
    
    Creates a supervisor that orchestrates repo_scanner, code_analyzer and stack_analyzer
    to produce a complete understanding of a GitHub repository.

    Coordinates the agents in the correct order:
    1. repo_scanner  → maps structure and finds file lists
    2. code_analyzer → analyzes source code files
    3. stack_analyzer → classifies the technology stack

    Args:
        llm: The language model to use (e.g. ChatOpenAI, ChatAnthropic)

    Returns:
        A compiled LangGraph supervisor
    
    repo_scanner   = create_repo_scanner_agent(llm)
    code_analyzer  = create_code_analyzer_agent(llm)
    stack_analyzer = create_stack_analyzer_agent(llm)

    return create_supervisor(
        agents=[repo_scanner, code_analyzer, stack_analyzer],
        model=llm,
        prompt=REPO_INTELLIGENCE_PROMPT,
        name="repo_intelligent_supervisor"
    ).compile()"""


if __name__ == "__main__":
    llm        = ChatOpenAI(model="gpt-4.1")
    supervisor = create_repo_intelligence_supervisor(llm)
    config = {"configurable": {"thread_id": "session_1"}}
    result = supervisor.invoke({
        "messages": [
            HumanMessage(content=(
                "   Analyze the repo rohitg00/ai-engineering-from-scratch. "
                "   map ONLY the scripts folder, find .py files there only. "
                "   Config files to find: ONLY requirements.txt at root level. "
                "   analyze ONLY the .py files found in the folder scripts. "
                "   analyze ONLY requirements.txt. "
                "DO NOT explore any other folder. "
                "The scope is intentionally limited to scripts/ only using the requirements.txt file for dependencies."
            ))
        ]
    }, config = config)

    print(result["stack_info"])

    exit()

    for msg in result["messages"]:
        msg_type = getattr(msg, "type", type(msg).__name__)
        if msg_type == "tool":
            print(f"🔧 TOOL [{msg.name}]: {str(msg.content)}...")
        elif msg_type == "ai" and hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                print(f"📞 CALLING: {tc['name']}({list(tc['args'].keys())})")
        elif msg_type == "ai" and msg.content:
            print(f"🤖 AGENT: {msg.content}")