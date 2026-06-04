# agents/stack_analyzer_agent.py

from langchain_core.messages import HumanMessage
from langchain_core.language_models import BaseChatModel
from langchain.agents import create_agent
from agent_tools.read_file_tool import read_file
from agent_tools.parse_dependencies_tool import parse_dependencies
from agent_tools.classify_stack_tool import classify_stack
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from prompts.stack_analyzer_prompt import STACK_ANALYZER_PROMPT

load_dotenv()

def create_stack_analyzer_agent(llm: BaseChatModel):
    """
    Creates a stack analyzer agent that identifies the technology stack from config files.

    Receives a list of config file paths from the repo scanner (does not do file discovery).
    For each config file, reads the content and parses its dependencies.
    Classifies the full stack once all files have been parsed.

    Args:
        llm: The language model to use (e.g. ChatOpenAI, ChatAnthropic)

    Returns:
        A compiled LangGraph react agent
    """
    tools = [
        read_file,
        parse_dependencies,
        classify_stack,
    ]
    return create_agent(
        model=llm,
        tools=tools,
        system_prompt=STACK_ANALYZER_PROMPT,
        name="stack_analyzer",
    )


if __name__ == "__main__":
    llm   = ChatOpenAI(model="gpt-4o-mini")
    agent = create_stack_analyzer_agent(llm)

    # il stack_analyzer riceve la lista config files già pronta dal repo_scanner
    config_files = [
        "requirements.txt",
    ]

    result = agent.invoke({
        "messages": [
            HumanMessage(content=(
                f"Analyze the technology stack of the repo rohitg00/ai-engineering-from-scratch. "
                f"Here are the config files to analyze: {config_files}. "
                f"For each file: read it and parse its dependencies. "
                f"Then classify the full stack from all parsed outputs."
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