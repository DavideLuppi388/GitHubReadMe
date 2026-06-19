from langchain_core.language_models import BaseChatModel
from langchain.agents import create_agent
from agent_tools.read_file_tool import read_file
from dotenv import load_dotenv
from prompts.documentation_analysis_prompt import DOCUMENTATION_ANALYST_PROMPT

load_dotenv()


def create_documentation_analyst_agent(llm: BaseChatModel):
    tools = [
        read_file,
    ]

    return create_agent(
        model=llm,
        tools=tools,
        system_prompt=DOCUMENTATION_ANALYST_PROMPT,
        name="documentation_analyst",
    )