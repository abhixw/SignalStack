import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("No API Key found.")
else:
    genai.configure(api_key=api_key)
    
    candidates = [
        "gemini-1.5-flash",
        "models/gemini-1.5-flash",
        "gemini-1.5-flash-001",
        "models/gemini-1.5-flash-001",
        "gemini-1.5-pro",
        "models/gemini-1.5-pro",
        "gemini-1.5-pro-001",
        "models/gemini-1.5-pro-001",
        "gemini-pro",
        "models/gemini-pro"
    ]
    
    print("Testing models...")
    for model_name in candidates:
        print(f"Trying {model_name}...", end=" ")
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content("Hello")
            print("SUCCESS!")
            print(f"WORKING MODEL: {model_name}")
            break
        except Exception as e:
            print(f"Failed: {e}")
