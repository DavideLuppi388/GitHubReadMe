from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from prompts.readme_writer_prompt import README_WRITER_PROMPT

def create_readme_writer_agent(llm: BaseChatModel):
    
    return create_agent(
        llm = llm,
        name = "readme_writer",
        system_prompt = README_WRITER_PROMPT,
    )