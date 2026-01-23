from typing import List
from app.services.llm import GeminiLLMService as LLMService
import app.schemas as schemas

class TaskDecomposer:
    def __init__(self, llm_service: LLMService = None):
        self.llm_service = llm_service or LLMService()

    def split(self, description: str) -> List[schemas.TaskSuggestion]:
        tasks = self.llm_service.generate_tasks(description)
        return [schemas.TaskSuggestion(**t) for t in tasks]
