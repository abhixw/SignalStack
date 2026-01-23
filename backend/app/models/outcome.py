from sqlalchemy import Column, String, JSON, DateTime
from app.config.database import Base
import datetime

class Outcome(Base):
    __tablename__ = "outcomes"

    id = Column(String, primary_key=True, index=True)
    title = Column(String)
    description = Column(String)
    tasks_json = Column(JSON)  # List of task objects with id, title, success_criteria
    rubric_json = Column(JSON) # Dict of weights
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
