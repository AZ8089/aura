import base64
import os
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from reasoning.k2_stylist import get_picks
from search.web_search import build_search_context, get_products
from stt.transcribe import transcribe_audio
from tts.elevenlabs_tts import generate_speech
from vision.gemini_parser import parse_image

app = FastAPI(title="Aura API")

STATIC_DIR = Path(__file__).parent / "static"
AUDIO_OUTPUT_DIR = Path(os.environ.get("AUDIO_OUTPUT_DIR", "/tmp/aura_audio"))
AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ── Serve the frontend ────────────────────────────────────────────────────────

@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── Serve generated audio files ───────────────────────────────────────────────

@app.get("/audio/{filename}")
async def serve_audio(filename: str):
    path = AUDIO_OUTPUT_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(path, media_type="audio/mpeg")


# ── /chat endpoint ────────────────────────────────────────────────────────────

@app.post("/chat")
async def chat(
    audio: UploadFile | None = File(default=None),
    image: UploadFile | None = File(default=None),
    text: str | None = Form(default=None),
    max_budget: float | None = Form(default=None),
):
    """
    Accepts multipart/form-data with optional:
      - audio  (webm/opus voice note)
      - image  (JPEG photo from browser camera)
      - text   (debug / fallback plain-text request)

    Returns JSON:
      {
        picks: [ { id, name, brand, price_usd, url, image_url, justification } ],
        audio_url: "/audio/<filename>"   # OR audio_b64 if you prefer inline
      }
    """
    transcript: str | None = None
    parsed_image: dict | None = None

    # ── STT ───────────────────────────────────────────────────────────────────
    if audio is not None:
        audio_bytes = await audio.read()
        transcript = await transcribe_audio(audio_bytes)

    # ── Vision ────────────────────────────────────────────────────────────────
    if image is not None:
        image_bytes = await image.read()
        parsed_image = await parse_image(image_bytes)

    # ── Build context ─────────────────────────────────────────────────────────
    user_request = " ".join(filter(None, [transcript, text])).strip()
    if not user_request and parsed_image is None:
        raise HTTPException(
            status_code=400,
            detail="Send at least one of: audio, image, or text.",
        )

    # ── Live catalog via Firecrawl ────────────────────────────────────────────
    search_ctx = await build_search_context(user_request or None, parsed_image, max_budget=max_budget)
    catalog = await get_products(search_ctx)

    # ── Reasoning ─────────────────────────────────────────────────────────────
    result = await get_picks(
        user_request=user_request or None,
        parsed_image=parsed_image,
        catalog=catalog,
    )
    # result = { "picks": [...], "aura_script": "..." }

    # ── TTS ───────────────────────────────────────────────────────────────────
    audio_path = await generate_speech(result["aura_script"], output_dir=AUDIO_OUTPUT_DIR)
    audio_url = f"/audio/{audio_path.name}"

    # ── Enrich picks with catalog metadata ───────────────────────────────────
    catalog_by_id = {item["id"]: item for item in catalog}
    enriched_picks = []
    for pick in result["picks"]:
        item = catalog_by_id.get(pick["id"], {})
        enriched_picks.append({
            **item,
            "justification": pick.get("justification", ""),
        })

    return JSONResponse({"picks": enriched_picks, "audio_url": audio_url, "transcript": transcript})
