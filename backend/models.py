from sqlalchemy import Column, Integer, String, JSON, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
import datetime

class Outcome(Base):
    __tablename__ = "outcomes"

    id = Column(String, primary_key=True, index=True)
    title = Column(String)
    description = Column(String)
    tasks_json = Column(JSON)  # List of task objects with id, title, success_criteria
    rubric_json = Column(JSON) # Dict of weights
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Proof(Base):
    __tablename__ = "proofs"

    id = Column(Integer, primary_key=True, index=True)
    outcome_id = Column(String, ForeignKey("outcomes.id"))
    candidate_id = Column(String)
    type = Column(String)  # e.g., "github"
    payload_json = Column(JSON)  # e.g., {"repo_url": "..."}
    snapshot_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, ForeignKey("outcomes.id")) # Using outcome_id as job_id for simplicity in MVP
    outcome_id = Column(String, ForeignKey("outcomes.id"))
    evaluation_json = Column(JSON)
    fit_score = Column(Float)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class SignalWeight(Base):
    __tablename__ = "signal_weights"

    id = Column(Integer, primary_key=True, index=True)
    signal_name = Column(String, index=True)
    task_id = Column(String, nullable=True) # Context specific
    weight = Column(Float)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    evaluation_id = Column(Integer, ForeignKey("evaluations.id"))
    job_id = Column(String)
    result = Column(String) # success | failure
    metrics_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String)
    entity_id = Column(String)
    action = Column(String)
    details_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
