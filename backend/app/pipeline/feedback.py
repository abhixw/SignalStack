from typing import List
from sqlalchemy.orm import Session
import app.models as models
from app.services import crud

class FeedbackLoop:
    def __init__(self, db: Session):
        self.db = db

    def process_feedback(self, feedback: models.Feedback) -> List[str]:
        changes = []
        if feedback.evaluation_id:
            eval_id = int(feedback.evaluation_id) if feedback.evaluation_id and feedback.evaluation_id.isdigit() else None
            
            eval_db = None
            if eval_id:
                eval_db = self.db.query(models.Evaluation).filter(models.Evaluation.id == eval_id).first()
            
            if not eval_db and feedback.job_id:
                 eval_db = self.db.query(models.Evaluation).filter(models.Evaluation.job_id == feedback.job_id).first()
                 
            if eval_db:
                eval_data = eval_db.evaluation_json
                signals_used = eval_data.get("global_signals_used", [])
                
                # Adjust weights based on result
                adjustment = 0.1 if feedback.result == "success" else -0.1
                
                for signal in signals_used:
                    # Get current weight (default 1.0 if not found)
                    current_weight_obj = self.db.query(models.SignalWeight).filter(models.SignalWeight.signal_name == signal).first()
                    current_weight = current_weight_obj.weight if current_weight_obj else 1.0
                    
                    new_weight = max(0.1, min(2.0, current_weight + adjustment)) # Clamp between 0.1 and 2.0
                    crud.update_signal_weight(self.db, signal, new_weight)
                    changes.append(f"Updated {signal} to {new_weight:.2f}")
        
        if not changes:
            changes.append("No signals found to update")
            
        return changes
