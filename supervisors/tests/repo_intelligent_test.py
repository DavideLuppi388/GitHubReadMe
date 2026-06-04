import json
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from supervisors.repo_intelligence_supervisor import create_repo_intelligence_supervisor

load_dotenv()

def debug_messages(messages):
    """Ispeziona i messaggi cercando tipi non supportati da OpenAI."""
    for i, msg in enumerate(messages):
        content = getattr(msg, "content", "")
        msg_type = getattr(msg, "type", type(msg).__name__)
        if isinstance(content, list):
            for j, block in enumerate(content):
                if isinstance(block, dict):
                    block_type = block.get("type", "unknown")
                    if block_type not in ("text", "refusal", "image_url", "input_audio"):
                        print(f"⚠️  messages[{i}] ({msg_type}).content[{j}] has unsupported type='{block_type}'")
                        print(f"   block: {json.dumps(block, indent=2)[:300]}")

llm        = ChatOpenAI(model="gpt-4.1-nano")
supervisor = create_repo_intelligence_supervisor(llm)

# usa stream invece di invoke per vedere i messaggi prima del crash
"""for chunk in supervisor.stream({
    "messages": [
        HumanMessage(content=(
            "Analyze the repo rohitg00/ai-engineering-from-scratch. "
            "STRICT CONSTRAINTS: "
            "1. repo_scanner: use get_repo_structure with max_depth=2. "
            "   Find .py files ONLY in scripts/ folder. "
            "   Config files: ONLY requirements.txt at root. "
            "2. code_analyzer: analyze ONLY scripts/*.py files. "
            "3. stack_analyzer: analyze ONLY requirements.txt. "
            "DO NOT explore phases/ or any other deep folder."
        ))
    ]
}):
    # ogni chunk contiene lo stato parziale
    for node_name, node_output in chunk.items():
        messages = node_output.get("messages", [])
        if messages:
            print(f"\n--- node: {node_name} ---")
            debug_messages(messages)
            # stampa anche l'ultimo messaggio
            last = messages[-1]
            msg_type = getattr(last, "type", "")
            if msg_type == "ai" and getattr(last, "content", ""):
                print(f"🤖 {last.content[:200]}")"""

for chunk in supervisor.stream({
    "messages": [HumanMessage(content="Analyze the repo rohitg00/ai-engineering-from-scratch. Map ONLY scripts/ folder.")]
}):
    for node_name, node_output in chunk.items():
        messages = node_output.get("messages", [])
        for i, msg in enumerate(messages):
            content = getattr(msg, "content", "")
            if isinstance(content, list):
                for j, block in enumerate(content):
                    if isinstance(block, dict):
                        print(f"[{node_name}] msg[{i}].content[{j}] type='{block.get('type')}' keys={list(block.keys())}")