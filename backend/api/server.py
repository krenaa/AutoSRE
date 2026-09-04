import os
from typing import Optional, List
from fastapi import FastAPI, BackgroundTasks, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.session import engine, Base, get_db, SessionLocal
from backend.db.models.incident import Incident, IncidentAuditLog
from agent.graph import build_remediation_graph
from agent.state import IncidentState

# Auto-create tables on launch
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AutoSRE Webhook & Control Gateway",
    version="1.0.0",
    description="Receives CI failure webhooks, manages database incident audits, and executes repairs.",
)


class IncidentTriggerPayload(BaseModel):
    repo_name: str
    branch_name: str = "main"
    target_file: str = "target/app.py"
    test_target: str = "tests/"
    commit_sha: Optional[str] = None
    error_trace: Optional[str] = None


def execute_agent_job(incident_id: int, payload: IncidentTriggerPayload):
    """Background worker executing the LangGraph agent and updating DB state."""
    db: Session = SessionLocal()
    try:
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return

        incident.status = "INVESTIGATING"
        db.commit()

        # Run LangGraph state machine
        engine = build_remediation_graph()
        initial_state: IncidentState = {
            "target_file": payload.target_file,
            "test_target": payload.test_target,
            "error_trace": payload.error_trace,
            "source_code": None,
            "proposed_patch": None,
            "tests_passed": False,
            "iteration_count": 0,
            "max_iterations": 3,
            "investigation_logs": [f"Incident #{incident_id} initialized for {payload.repo_name}"],
        }
        final_state = engine.invoke(initial_state)

        # Update DB with resolution results
        incident.status = "RESOLVED" if final_state.get("tests_passed") else "FAILED"
        incident.tests_passed = final_state.get("tests_passed", False)
        incident.proposed_patch = final_state.get("proposed_patch")
        incident.iteration_count = final_state.get("iteration_count", 0)

        # Persist audit logs
        for entry in final_state.get("investigation_logs", []):
            db.add(IncidentAuditLog(incident_id=incident_id, message=entry))

        db.commit()
    finally:
        db.close()


@app.get("/healthz")
def health_check():
    return {"status": "healthy", "service": "AutoSRE Gateway"}


@app.post("/api/v1/incidents/trigger")
def trigger_incident(
    payload: IncidentTriggerPayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Creates an incident audit record and triggers background remediation."""
    new_incident = Incident(
        repo_name=payload.repo_name,
        branch_name=payload.branch_name,
        commit_sha=payload.commit_sha,
        target_file=payload.target_file,
        error_trace=payload.error_trace,
        status="QUEUED",
    )
    db.add(new_incident)
    db.commit()
    db.refresh(new_incident)

    background_tasks.add_task(execute_agent_job, new_incident.id, payload)

    return {
        "status": "queued",
        "incident_id": new_incident.id,
        "repo_name": payload.repo_name,
        "target_file": payload.target_file,
    }


@app.get("/api/v1/incidents")
def list_incidents(db: Session = Depends(get_db)):
    """Fetches all incident records and their status."""
    return db.query(Incident).order_by(Incident.id.desc()).all()


@app.get("/api/v1/incidents/{incident_id}")
def get_incident_details(incident_id: int, db: Session = Depends(get_db)):
    """Fetches single incident details along with its full audit trail."""
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        return {"error": "Incident not found"}
    logs = db.query(IncidentAuditLog).filter(IncidentAuditLog.incident_id == incident_id).all()
    return {
        "incident": incident,
        "logs": [log.message for log in logs],
    }