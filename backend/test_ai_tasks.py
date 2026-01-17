import os
from dotenv import load_dotenv
from services import GeminiLLMService

# Load environment variables
load_dotenv()

def test_generate_tasks():
    print("Initializing GeminiLLMService...")
    llm_service = GeminiLLMService()
    
    if not llm_service.api_key:
        print("ERROR: GEMINI_API_KEY not found.")
        return

    description = "We need a scalable backend for a ride-sharing app. It requires real-time location tracking, user authentication, and a matching algorithm for drivers and riders. The system should be built with Python and FastAPI, using Redis for caching and PostgreSQL for persistence."
    
    print(f"\nTesting Task Generation for description:\n'{description}'\n")
    print("-" * 50)
    
    tasks = llm_service.generate_tasks(description)
    
    print("\nGenerated Tasks:")
    import json
    print(json.dumps(tasks, indent=2))

if __name__ == "__main__":
    test_generate_tasks()
