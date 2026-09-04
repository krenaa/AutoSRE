import json
from agent.graph import build_remediation_graph
from agent.state import IncidentState


def main():
    print("=" * 60)
    print("🚀 INITIALIZING AUTOSRE LANGGRAPH REMEDIATION ENGINE")
    print("=" * 60)

    # 1. Compile the graph
    app = build_remediation_graph()

    # 2. Define initial incident state
    initial_state: IncidentState = {
        "target_file": "target/app.py",
        "test_target": "tests/",
        "error_trace": None,
        "source_code": None,
        "proposed_patch": None,
        "tests_passed": False,
        "iteration_count": 0,
        "max_iterations": 3,
        "investigation_logs": [],
    }

    # 3. Execute the workflow
    final_state = app.invoke(initial_state)

    # 4. Print timeline logs
    print("\n" + "=" * 60)
    print("📋 INVESTIGATION & REMEDIATION TIMELINE")
    print("=" * 60)
    for entry in final_state["investigation_logs"]:
        print(entry)

    print("\n" + "=" * 60)
    if final_state["tests_passed"]:
        print(f"🎉 RESOLUTION SUCCESSFUL in {final_state['iteration_count']} iteration(s)!")
    else:
        print("❌ RESOLUTION FAILED: Escalation required.")
    print("=" * 60)


if __name__ == "__main__":
    main()