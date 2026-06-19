from langchain.agents import create_agent
from prompts.readme_reviewer_prompt import README_REVIEWER_PROMPT
from langchain_core.language_models import BaseChatModel

def create_readme_reviewer_agent(llm: BaseChatModel):
    
    return create_agent(
        llm = llm,
        name = "readme_reviewer",
        system_prompt = README_REVIEWER_PROMPT,
    )