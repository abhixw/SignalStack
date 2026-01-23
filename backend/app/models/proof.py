from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey
from app.config.database import Base
import datetime

class Proof(Base):
    __tablename__ = "proofs"

    id = Column(Integer, primary_key=True, index=True)
    outcome_id = Column(String, ForeignKey("outcomes.id"))
    candidate_id = Column(String)
    type = Column(String)  # e.g., "github"
    payload_json = Column(JSON)  # e.g., {"repo_url": "..."}
    snapshot_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
