from typing import List, Optional
from sqlalchemy.orm import Session
import app.models as models
import app.schemas as schemas
from app.services import crud

class OutcomePipeline:
    def __init__(self, db: Session):
        self.db = db

    def create_outcome(self, outcome: schemas.OutcomeCreate) -> models.Outcome:
        return crud.create_outcome(self.db, outcome)

    def get_outcome(self, outcome_id: str) -> Optional[models.Outcome]:
        return crud.get_outcome(self.db, outcome_id)
