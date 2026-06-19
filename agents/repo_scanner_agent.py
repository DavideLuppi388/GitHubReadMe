from langchain_core.messages import HumanMessage
from langchain_core.language_models import BaseChatModel
from langchain.agents import create_agent
from agent_tools.get_repo_structure_tool import get_repo_structure
from agent_tools.read_file_tool import read_file
from agent_tools.parse_dependencies_tool import parse_dependencies
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from prompts.repo_scanner_prompt import REPO_SCANNER_PROMPT
import os

load_dotenv()


def create_repo_scanner_agent(llm: BaseChatModel):
    
    tools = [
        get_repo_structure,
        read_file,
        parse_dependencies,
    ]

    return create_agent(
        model=llm,
        tools=tools,
        system_prompt=REPO_SCANNER_PROMPT,
        name="repo_scanner",
    )

if __name__ == '__main__':
    llm = ChatOpenAI(model = "gpt-4.1-mini")
    agent = create_repo_scanner_agent(llm)
    repo_name = "DavideLuppi388/GitHubReadMe"
    token     = os.getenv("GITHUB_TOKEN")
    result = agent.invoke({
        "messages": [
            HumanMessage(content=f"""
                Analyze the repository: {repo_name}
                GitHub token: {token}
                """)
        ]
    })

    for msg in result["messages"]:
        msg_type = getattr(msg, "type", type(msg).__name__)
        if msg_type == "tool":
            print(f"🔧 TOOL [{msg.name}]: {str(msg.content)}...")
        elif msg_type == "ai" and hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                print(f"📞 CALLING: {tc['name']}({list(tc['args'].keys())})")
        elif msg_type == "ai":
            print(f"🤖 AGENT: {msg.content}")