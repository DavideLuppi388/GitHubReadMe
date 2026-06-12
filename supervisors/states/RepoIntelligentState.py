# state.py

from typing import TypedDict, List, Optional, Annotated
import operator

class RepoIntelligenceState(TypedDict):
    # ── input ─────────────────────────────────────────────────────────────────
    repo_full_name:  str
    branch:          str
    token:           Optional[str]
    # ── messaggi accumulati ───────────────────────────────────────────────────
    messages:        Annotated[list, operator.add]
    # ── output repo_scanner ───────────────────────────────────────────────────
    source_files:    Optional[List[str]]
    config_files:    Optional[List[str]]
    project_purpose: Optional[str]
    structure:       Optional[str]
    # ── output code_analyzer ─────────────────────────────────────────────────
    code_summary:    Optional[str]
    # ── output stack_analyzer ────────────────────────────────────────────────
    stack_summary:   Optional[str]
    # ── output finale ────────────────────────────────────────────────────────
    final_report:    Optional[str]