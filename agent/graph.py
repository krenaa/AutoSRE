import os
from dotenv import load_dotenv
from groq import Groq
from langgraph.graph import StateGraph, END
from agent.state import IncidentState
from agent.mcp_server import (
    run_pytest,
    read_source_file,
    apply_code_patch,
    get_git_diff,
)

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ==========================================
# NODE 1: DETECT & CAPTURE
# ==========================================
def detect_node(state: IncidentState) -> IncidentState:
    test_result = run_pytest(state["test_target"])
    logs = list(state.get("investigation_logs", []))
    
    if test_result["passed"]:
        logs.append("[Detect] All tests passed. System nominal.")
        return {
            **state,
            "tests_passed": True,
            "error_trace": None,
            "investigation_logs": logs,
        }

    logs.append(f"[Detect] Failure detected in test suite '{state['test_target']}'.")
    combined_output = f"{test_result['stdout']}\n{test_result['stderr']}".strip()
    return {
        **state,
        "tests_passed": False,
        "error_trace": combined_output,
        "investigation_logs": logs,
    }


# ==========================================
# NODE 2: DIAGNOSE & READ CODE
# ==========================================
def diagnose_node(state: IncidentState) -> IncidentState:
    logs = list(state.get("investigation_logs", []))
    logs.append(f"[Diagnose] Reading target file '{state['target_file']}'...")

    file_data = read_source_file(state["target_file"])
    raw_code = file_data.get("raw_code", "") if file_data.get("found") else ""

    return {
        **state,
        "source_code": raw_code,
        "investigation_logs": logs,
    }


# ==========================================
# NODE 3: SYNTHESIZE PATCH (LLM)
# ==========================================
def patch_node(state: IncidentState) -> IncidentState:
    logs = list(state.get("investigation_logs", []))
    iteration = state.get("iteration_count", 0) + 1
    logs.append(f"[Patch] Synthesizing repair attempt #{iteration} via Qwen...")

    prompt = f"""You are an autonomous Site Reliability Engineer resolving a pipeline incident.

A test failure occurred:
--- TRACE START ---
{state['error_trace']}
--- TRACE END ---

Current target source code ({state['target_file']}):
--- CODE START ---
{state['source_code']}
--- CODE END ---

Task:
Fix the issue so all unit tests pass cleanly.
Return ONLY the raw Python source code for the target file.
Do NOT enclose your response in Markdown code fences (no ```python).
Do NOT write explanations or commentary.
"""
    response = client.chat.completions.create(
        model="qwen/qwen3.8-27b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )

    patch = response.choices[0].message.content.strip()

    # Clean any unexpected code blocks
    if patch.startswith("```python"):
        patch = patch[len("```python") :]
    elif patch.startswith("```"):
        patch = patch[len("```") :]
    if patch.endswith("```"):
        patch = patch[:-3]

    patch = patch.strip()

    return {
        **state,
        "proposed_patch": patch,
        "iteration_count": iteration,
        "investigation_logs": logs,
    }


# ==========================================
# NODE 4: APPLY & VERIFY
# ==========================================
def verify_node(state: IncidentState) -> IncidentState:
    logs = list(state.get("investigation_logs", []))
    logs.append(f"[Verify] Applying patch to '{state['target_file']}'...")

    write_result = apply_code_patch(state["target_file"], state["proposed_patch"])
    if not write_result.get("success"):
        logs.append(f"[Verify] Patch application error: {write_result.get('error')}")
        return {
            **state,
            "tests_passed": False,
            "investigation_logs": logs,
        }

    # Re-run pytest using MCP tool
    test_result = run_pytest(state["test_target"])
    passed = test_result["passed"]

    if passed:
        logs.append("[Verify] All tests passed! Incident successfully resolved.")
        diff = get_git_diff(state["target_file"])
        logs.append(f"[Verify] Unified Git Diff:\n{diff}")
        return {
            **state,
            "tests_passed": True,
            "error_trace": None,
            "investigation_logs": logs,
        }

    logs.append(f"[Verify] Verification failed on iteration #{state['iteration_count']}.")
    combined_output = f"{test_result['stdout']}\n{test_result['stderr']}".strip()
    return {
        **state,
        "tests_passed": False,
        "error_trace": combined_output,
        "investigation_logs": logs,
    }


# ==========================================
# CONDITIONAL ROUTING EDGES
# ==========================================
def route_after_detect(state: IncidentState) -> str:
    if state.get("tests_passed", False):
        return END
    return "diagnose_node"


def route_after_verify(state: IncidentState) -> str:
    if state.get("tests_passed", False):
        return END
    if state.get("iteration_count", 0) >= state.get("max_iterations", 3):
        return END
    return "diagnose_node"


# ==========================================
# GRAPH ASSEMBLY
# ==========================================
def build_remediation_graph():
    builder = StateGraph(IncidentState)

    # Register nodes
    builder.add_node("detect_node", detect_node)
    builder.add_node("diagnose_node", diagnose_node)
    builder.add_node("patch_node", patch_node)
    builder.add_node("verify_node", verify_node)

    # Entry point
    builder.set_entry_point("detect_node")

    # Edges
    builder.add_conditional_edges(
        "detect_node",
        route_after_detect,
        {"diagnose_node": "diagnose_node", END: END},
    )
    builder.add_edge("diagnose_node", "patch_node")
    builder.add_edge("patch_node", "verify_node")
    builder.add_conditional_edges(
        "verify_node",
        route_after_verify,
        {"diagnose_node": "diagnose_node", END: END},
    )

    return builder.compile()