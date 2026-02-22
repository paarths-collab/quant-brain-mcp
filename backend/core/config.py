import os
from dotenv import load_dotenv
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"

load_dotenv(dotenv_path=env_path)

class Settings:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

settings = Settings()
