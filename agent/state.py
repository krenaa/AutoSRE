from typing import Optional, List
from typing_extensions import TypedDict
from pydantic import BaseModel, Field


class IncidentState(TypedDict):
    """The shared memory state passed between LangGraph nodes."""
    target_file: str
    test_target: str
    error_trace: Optional[str]
    source_code: Optional[str]
    proposed_patch: Optional[str]
    tests_passed: bool
    iteration_count: int
    max_iterations: int
    investigation_logs: List[str]