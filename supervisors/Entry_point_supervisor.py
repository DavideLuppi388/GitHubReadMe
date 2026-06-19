from supervisors.Readme_generator_supervisor import create_readme_generator_supervisor
from supervisors.repo_intelligence_supervisor import create_repo_intelligent_supervisor

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END

from supervisors.states.GlobalState import GlobalState

def create_entry_point_supervisor(llm:BaseChatModel):
    
    repo_intelligent_supervisor = create_repo_intelligent_supervisor(llm)
    readme_generator_supervisor = create_readme_generator_supervisor(llm)
    
    def repo_intelligent_node(state: GlobalState):
        result = repo_intelligent_supervisor.invoke({
            "repo_full_name" : state["repo_full_name"],
            "branch" : state.get("branch"),
            "token" : state.get("token"),
            "messages" : []
            
        })
        return {
            "scanner_output": result["scanner_output"],
            "documentation": result["documentation"]
        }
    
    def readme_generator_node(state: GlobalState):
        result = readme_generator_supervisor.invoke({
            "blueprint" : state["documentation"],
            "readme" : None,
            "review_result" : None,
            "revision_count": 0,
            "max_revisions": state["max_revisions"],
            "need_revision" : None
            
        })
        
        return {
            "final_readme": result["readme"],
            "review_result": result["review_result"],
            "revision_count": result["revision_count"],   
        }
        
        
    
    graph = StateGraph(GlobalState)
    graph.add_node("repo_intelligent", repo_intelligent_node)
    graph.add_node("readme_generator", readme_generator_node)
    
    graph.add_edge(START, "repo_intelligent")
    graph.add_edge("repo_intelligent", "readme_generator")
    graph.add_edge("readme_generator", END)
    
    return graph.compile()