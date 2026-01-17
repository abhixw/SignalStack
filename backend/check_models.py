import requests
import json

API_KEY = "AIzaSyB6P5EAVEOp13JfWxY6YTGarZRcKjMwnaw"
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"

response = requests.get(url)
data = response.json()

print("Available models:")
for model in data.get("models", []):
    name = model.get("name", "")
    methods = model.get("supportedGenerationMethods", [])
    if "generateContent" in methods:
        print(f"  {name}")
