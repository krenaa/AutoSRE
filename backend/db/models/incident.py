import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from backend.db.session import Base


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    repo_name = Column(String(255), nullable=False)
    branch_name = Column(String(100), default="main")
    commit_sha = Column(String(64), nullable=True)
    target_file = Column(String(255), nullable=False)
    status = Column(String(50), default="TRIGGERED")  # TRIGGERED, INVESTIGATING, RESOLVED, FAILED
    error_trace = Column(Text, nullable=True)
    proposed_patch = Column(Text, nullable=True)
    pr_url = Column(String(500), nullable=True)
    tests_passed = Column(Boolean, default=False)
    iteration_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class IncidentAuditLog(Base):
    __tablename__ = "incident_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, index=True, nullable=False)
    log_level = Column(String(20), default="INFO")
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)