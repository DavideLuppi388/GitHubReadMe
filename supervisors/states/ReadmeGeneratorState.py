from typing import TypedDict, Annotated, Optional

class ReadmeGenerationState(TypedDict):
    blueprint:          str              # documentation blueprint dall'analyst
    readme:             Optional[str]    # ultimo README generato
    review_result:      Optional[dict]   # ultimo output del reviewer (parsed)
    revision_count:     int              # per evitare loop infiniti
    max_revisions:      int
    need_revision:      Optional[bool]