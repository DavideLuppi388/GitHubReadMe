# state.py

from typing import TypedDict, List, Optional, Annotated
import operator

class RepoIntelligenceState(TypedDict):
    # ── input ─────────────────────────────────────────────────────────────────
    repo_full_name:  str
    branch:          Optional[str]
    token:           Optional[str]
    # ── messaggi accumulati ───────────────────────────────────────────────────
    messages:        Annotated[list, operator.add]
    # ── output repo_scanner ───────────────────────────────────────────────────
    scanner_output:    Optional[str]
    # ── output documentation_analyst ──────────────────────────────────────────
    documentation:   Optional[str]