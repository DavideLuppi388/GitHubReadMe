#tool in the agent
from agent_tools.extract_code_metadata_tool import extract_code_metadata
from agent_tools.analyze_dependencies_flow_tool import analyze_dependencies_flow
from agent_tools.query_code_context_tool import query_code_context
from agent_tools.read_file_tool import read_file
import json

#extra tool
from agent_tools.get_dir_content_tool import get_dir_content

repo_name = "rohitg00/ai-engineering-from-scratch"
cont = get_dir_content.invoke({"repo_full_name": repo_name,"dir_path": "scripts", "token": "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"})
#print(cont)
print('--------------------------------')
cont=json.loads(cont)
metadatas = []
for file in cont:

    content = read_file.invoke({
        "repo_full_name": repo_name,
        "file_path": file["path"],
    })

    metadata = extract_code_metadata.invoke({
        "file_path": file['path'],
        "content": content,
        })
    
    metadatas.append({"file_path": file["path"], "metadata": metadata})

#print(metadatas)
print('-------------------------')

examples = [
    ("", "class"),
    ("main", "function"),
    ("_lib", "import"),
    ("render report", "function"),
    ("to_dict", "function"),
    ("lesson", "any"),
    ("check audit", "any"),
]

for query, search_type in examples:
    result = json.loads(query_code_context.invoke({
        "query": query,
        "files_metadata": json.dumps(metadatas),
        "search_type": search_type,
    }))
    print(f"\n{'='*60}")
    print(f"query='{query}' search_type='{search_type}'")
    print(f"total_matches: {result['total_matches']}")
    for category, items in result.get("results", {}).items():
        print(f"  [{category}]")
        for item in items:
            name = item.get("name") or item.get("module") or item.get("path", "")
            file = item.get("file", "")
            score = item.get("score", 0)
            print(f"    - {name} ({file}) score={score}")

graph = analyze_dependencies_flow.invoke({"files_metadata":json.dumps(metadatas)})

print(graph)

