from sqlalchemy import Column, Integer, String, JSON, Float, DateTime, ForeignKey
from app.config.database import Base
import datetime

class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, ForeignKey("outcomes.id")) # Using outcome_id as job_id for simplicity in MVP
    outcome_id = Column(String, ForeignKey("outcomes.id"))
    evaluation_json = Column(JSON)
    fit_score = Column(Float)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
