from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv

from supervisors.states.ReadmeGeneratorState import ReadmeGenerationState

load_dotenv()

from agents.readme_reviewer import create_readme_reviewer_agent
from agents.readme_writer import create_readme_writer_agent
import json

def create_readme_generator_supervisor(llm: BaseChatModel):
    
    writer = create_readme_writer_agent(llm)
    reviewer = create_readme_reviewer_agent(llm)
    
    def write_readme(state: ReadmeGenerationState):
        blueprint = state["blueprint"]
        is_first_pass = state.get("need_revision") is None
        
        if is_first_pass:
            prompt = (
                "Produce the README based on the following documentation blueprint.\n\n"
                f"Blueprint:\n{blueprint}\n\n"
                "Return only the final README in Markdown."
            )
        
        else:
            
            issues = state.get("review_result")
            prompt = ("Revise the following README based on the issues found during review.\n\n"
                f"Original blueprint:\n{blueprint}\n\n"
                f"Previous README:\n{state['readme']}\n\n"
                f"Issues to fix:\n{issues}\n\n"
                "Return only the corrected README in Markdown.")
            
        result = writer.invoke({"messages" : [HumanMessage(content=prompt)]})
        return {"readme" : result["messages"][-1].content,
                "revision_count" : state["revision_count"] + 1
        }
        
    
    def review_readme(state: ReadmeGenerationState):
        blueprint = state["blueprint"]
        readme = state["readme"]
        prompt = (
            "Review the following README against the blueprint it was generated from.\n\n"
            f"Blueprint:\n{blueprint}\n\n"
            f"README:\n{readme}\n\n"
            "Return only the JSON review object."
        )
        
        result = reviewer.invoke({"messages": [HumanMessage(content = prompt)]})
        msg = result["messages"][0].content
        need_review = json.loads(msg)
        
        return {"review_result" : result["messages"][-1].content,
                "need_revision" : not need_review.get("approved")}
    
    def router_writer_or_end(state: ReadmeGenerationState):
        
        need_revision = state.get("need_revision")
        revision_count = state["revision_count"]
        max_revisions = state["max_revisions"]
        
        if revision_count >= max_revisions:
            return "end"
        
        if need_revision:
            return "writer"
        
        return "end"    
    
    graph = StateGraph(ReadmeGenerationState)
    graph.add_node("writer", write_readme)
    graph.add_node("reviewer", review_readme)
    
    graph.add_edge(START, "writer")
    graph.add_edge("writer", "reviewer")
    graph.add_conditional_edges("reviewer", router_writer_or_end,{
        
        "writer": "writer",
        "end": END    
    })
    
    return graph.compile()
    