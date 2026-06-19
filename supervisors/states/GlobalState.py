
from typing import TypedDict, Annotated, Optional

class GlobalState(TypedDict):
    # ── input iniziale ──────────────────────────────────────────────────────
    repo_full_name: str
    branch:         Optional[str]
    token:          Optional[str]
    max_revisions:  int

    # ── output del repo_intelligent_supervisor ──────────────────────────────
    scanner_output: Optional[str]   # JSON facts (str)
    documentation:  Optional[str]   # blueprint JSON (str) — questo è l'input per il secondo supervisor

    # ── output del readme_generator_supervisor ───────────────────────────────
    readme:          Optional[str]
    review_result:   Optional[dict]
    revision_count:  Optional[int]
    need_revision:   Optional[bool]

    # ── output finale ────────────────────────────────────────────────────────
    final_readme:   Optional[str]
