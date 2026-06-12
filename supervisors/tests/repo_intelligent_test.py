import os
from supervisors.repo_intelligence_supervisor import create_repo_intelligence_supervisor
from langchain_openai import ChatOpenAI

if __name__ == "__main__":
    llm        = ChatOpenAI(model="gpt-4o-mini")
    supervisor = create_repo_intelligence_supervisor(llm)

    repo_name = "DavideLuppi388/GitHubReadMe"
    token     = os.getenv("GITHUB_TOKEN")

    result = supervisor.invoke({
        "repo_full_name": repo_name,
        "branch":         "main",
        "token":          token,
        "messages":       [],
    })

    # salva su file
    output_path = os.path.join(os.path.dirname(__file__), "res.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result["final_report"])
    print(f"\n✅ Saved to {output_path}")