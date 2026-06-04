from langchain_core.messages import HumanMessage
from langchain_core.language_models import BaseChatModel
from langchain.agents import create_agent


from agent_tools.get_repo_structure_tool import get_repo_structure
from agent_tools.glob_search_tool import find_files_in_structure
from agent_tools.read_file_tool import read_file
from agent_tools.get_dir_content_tool import get_dir_content
from agent_tools.search_code_content_tool import search_code_content
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from prompts.repo_scanner_prompt import REPO_SCANNER_PROMPT
import os

load_dotenv()


def create_repo_scanner_agent(llm: BaseChatModel):
    """
    Creates a repo scanner agent that maps and explores GitHub repositories.
    
    Args:
        llm: The language model to use (e.g. ChatAnthropic, ChatOpenAI)
    
    Returns:
        A compiled LangGraph react agent
    """
    tools = [
        get_repo_structure,
        find_files_in_structure,
        read_file,
        get_dir_content,
        search_code_content,
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
    repo_name = "rohitg00/ai-engineering-from-scratch"
    token     = os.getenv("GITHUB_TOKEN")
    result = agent.invoke({
        "messages": [
            HumanMessage(content=f"""
                Analyze the repository: {repo_name}
                GitHub token: {token}

                Please do the following:
                1. Call get_repo_structure to map the full repository tree
                2. Call find_files_in_structure to find all .py source files in the scripts/ folder
                3. Call find_files_in_structure to find all config files:
                requirements.txt, pyproject.toml, package.json, Dockerfile, docker-compose.yml, .env.example
                4. Call get_dir_content on the scripts/ folder to list its contents
                5. Call read_file on README.md to understand the project purpose

                Return explicitly:
                - PROJECT_PURPOSE: one paragraph description of what this repo does
                - SOURCE_FILES: the exact list of .py file paths found in scripts/
                - CONFIG_FILES: the exact list of config file paths found
                - KEY_DIRECTORIES: list of main directories and their purpose
                - NOTABLE_FILES: list of important files (README, config, CI/CD, etc.)
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