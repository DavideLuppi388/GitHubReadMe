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
