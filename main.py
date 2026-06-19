from langchain_openai import ChatOpenAI
from supervisors.Entry_point_supervisor import create_entry_point_supervisor
import os
from dotenv import load_dotenv

load_dotenv()

def main():
    llm = ChatOpenAI(model="gpt-4o-mini")
    entry_point_supervisor = create_entry_point_supervisor(llm)
    
    result = entry_point_supervisor.invoke({
        "repo_full_name": "DavideLuppi388/GitHubReadMe",
        "token":          os.getenv("GITHUB_TOKEN"),
        "branch":         "main",
        "max_revisions":  3,
    })

    output_path = os.path.join(os.path.dirname(__file__), "res.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result["final_readme"])
    print(f"\n✅ Saved to {output_path}")


if __name__ == "__main__":
    main()
