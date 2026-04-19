import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

config = Config()
