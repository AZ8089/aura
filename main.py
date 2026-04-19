import os
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from catalog.hardcoded import CATALOG
from config import KNOT_CLIENT_ID, KNOT_ENV
from knot._client import create_session
from knot.agentic_shopping import purchase_picks
from knot.sub_manager import cancel_subscription, get_active_subscriptions
from knot.transaction_link import get_purchase_history
from reasoning.k2_stylist import get_picks
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


# ── Knot session creation (called by frontend before opening the SDK) ─────────

@app.post("/knot/session")
async def knot_session(external_user_id: str = Form(...)):
    """
    Create a Knot session for the given user and return it to the frontend
    so it can initialise the Knot Link SDK.
    """
    if not KNOT_CLIENT_ID:
        raise HTTPException(
            status_code=503,
            detail="Knot not configured. Set KNOT_CLIENT_ID and KNOT_SECRET in .env",
        )
    try:
        session = await create_session("transaction_link", external_user_id)
        return JSONResponse({
            "session": session,
            "client_id": KNOT_CLIENT_ID,
            "environment": KNOT_ENV,
        })
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Knot session error: {exc}")


# ── /chat endpoint ────────────────────────────────────────────────────────────

@app.post("/chat")
async def chat(
    audio: UploadFile | None = File(default=None),
    image: UploadFile | None = File(default=None),
    text: str | None = Form(default=None),
    knot_token: str | None = Form(default=None),
    execute_purchase: str | None = Form(default=None),
):
    """
    Accepts multipart/form-data with optional:
      - audio          (webm/opus voice note)
      - image          (JPEG photo from browser camera)
      - text           (debug / fallback plain-text request)
      - knot_token     (Knot external_user_id from frontend after SDK auth)
      - execute_purchase ("true" to trigger AgenticShopping after picks)

    Returns JSON:
      {
        picks:               [ { id, name, brand, price_usd, url, image_url, justification, amazon_asin? } ],
        audio_url:           "/audio/<filename>",
        purchase_status:     [ { item_id, status, message } ] | null,
        active_subscriptions: [ { id, name, monthly_cost_usd, is_cancellable } ] | null,
      }
    """
    transcript: str | None = None
    parsed_image: dict | None = None
    purchase_history: dict | None = None

    # ── STT ───────────────────────────────────────────────────────────────────
    if audio is not None:
        audio_bytes = await audio.read()
        transcript = await transcribe_audio(audio_bytes)

    # ── Vision ────────────────────────────────────────────────────────────────
    if image is not None:
        image_bytes = await image.read()
        parsed_image = await parse_image(image_bytes)

    # ── Build user request ────────────────────────────────────────────────────
    user_request = " ".join(filter(None, [transcript, text])).strip()
    if not user_request and parsed_image is None:
        raise HTTPException(
            status_code=400,
            detail="Send at least one of: audio, image, or text.",
        )

    # ── Knot TransactionLink ──────────────────────────────────────────────────
    if knot_token:
        purchase_history = await get_purchase_history(knot_token)
        print(f"[main] purchase_history keys: {list(purchase_history.keys())}")

    # ── Reasoning ─────────────────────────────────────────────────────────────
    result = await get_picks(
        user_request=user_request or None,
        parsed_image=parsed_image,
        catalog=CATALOG,
        purchase_history=purchase_history,
    )

    # ── TTS ───────────────────────────────────────────────────────────────────
    audio_path = await generate_speech(result["aura_script"], output_dir=AUDIO_OUTPUT_DIR)
    audio_url = f"/audio/{audio_path.name}"

    # ── Enrich picks with catalog metadata ────────────────────────────────────
    catalog_by_id = {item["id"]: item for item in CATALOG}
    enriched_picks = []
    for pick in result["picks"]:
        item = catalog_by_id.get(pick["id"], {})
        enriched_picks.append({
            **item,
            "justification": pick.get("justification", ""),
        })

    # ── AgenticShopping (only when user explicitly confirms) ──────────────────
    purchase_status: list[dict] | None = None
    if knot_token and execute_purchase == "true":
        purchase_status = await purchase_picks(enriched_picks, external_user_id=knot_token)

    # ── SubManager ────────────────────────────────────────────────────────────
    active_subscriptions: list[dict] | None = None
    if knot_token:
        active_subscriptions = await get_active_subscriptions(knot_token) or None

    return JSONResponse({
        "picks": enriched_picks,
        "audio_url": audio_url,
        "purchase_status": purchase_status,
        "active_subscriptions": active_subscriptions,
    })


# ── /cancel-subscription endpoint ────────────────────────────────────────────

@app.delete("/cancel-subscription/{subscription_id}")
async def cancel_sub(subscription_id: str, knot_token: str | None = Form(default=None)):
    """
    Cancel a specific subscription via Knot SubManager.
    Accepts the subscription ID from the active_subscriptions response.
    """
    result = await cancel_subscription(subscription_id)
    if not result["success"]:
        raise HTTPException(status_code=502, detail=result["message"])
    return JSONResponse(result)
