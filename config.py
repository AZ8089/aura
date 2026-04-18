import os
from dotenv import load_dotenv

load_dotenv()

# ElevenLabs
ELEVENLABS_API_KEY: str = os.environ["ELEVENLABS_API_KEY"]
ELEVENLABS_VOICE_ID: str = os.environ["ELEVENLABS_VOICE_ID"]

# Google Gemini
GEMINI_API_KEY: str = os.environ["GEMINI_API_KEY"]

# K2 (Think V2)
K2_API_KEY: str = os.environ["K2_API_KEY"]
K2_BASE_URL: str = os.environ.get("K2_BASE_URL", "https://api.k2think.ai/v1")

# Misc
AUDIO_OUTPUT_DIR: str = os.environ.get("AUDIO_OUTPUT_DIR", "/tmp/aura_audio")
