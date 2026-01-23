from app.services.llm import GeminiLLMService
from app.pipeline.extractor import SignalExtractor
from app.pipeline.engine import AllocationEngine

# Initialize singletons
llm_service = GeminiLLMService()
signal_extractor = SignalExtractor()
allocation_engine = AllocationEngine(llm_service=llm_service)
