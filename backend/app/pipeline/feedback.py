from typing import List
from pymongo.asynchronous.database import AsyncDatabase
import app.schemas as schemas
from app.services import crud

class FeedbackLoop:
    def __init__(self, db: AsyncDatabase):
        self.db = db

    async def process_feedback(self, feedback: schemas.FeedbackCreate) -> List[str]:
        changes = []
        if feedback.evaluation_id:
            eval_doc = await crud.get_evaluation_by_job_id(self.db, feedback.job_id) if feedback.job_id else None

            if eval_doc:
                eval_data = eval_doc.get("evaluation", {})
                signals_used = eval_data.get("global_signals_used", [])

                # Adjust weights based on result
                adjustment = 0.1 if feedback.result == "success" else -0.1

                current_weights = {w["signal_name"]: w["weight"] for w in await crud.get_signal_weights(self.db)}

                for signal in signals_used:
                    current_weight = current_weights.get(signal, 1.0)
                    new_weight = max(0.1, min(2.0, current_weight + adjustment))  # Clamp between 0.1 and 2.0
                    await crud.update_signal_weight(self.db, signal, new_weight)
                    changes.append(f"Updated {signal} to {new_weight:.2f}")

        if not changes:
            changes.append("No signals found to update")

        return changes
