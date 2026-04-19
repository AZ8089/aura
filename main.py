import base64
import os
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from config import TO_REVIEW
from reasoning.k2_stylist import get_picks, get_final_picks
from reviews.review_crawler import crawl_products_parallel
from reviews.sizing_analyzer import analyze_sizing_parallel
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
    # User sizing profile (all optional — Phase 3 review intelligence)
    height: str | None = Form(default=None),       # e.g. "5'6"" or "168cm"
    top_size: str | None = Form(default=None),     # US top size, e.g. "S", "M", "8"
    bottom_size: str | None = Form(default=None),  # US bottom size, e.g. "28", "M"
    shoe_size: str | None = Form(default=None),    # US shoe size, e.g. "8.5"
    build: str | None = Form(default=None),        # e.g. "slim", "athletic", "curvy"
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

    # ── Phase 1: K2 initial picks (selects 6 candidates from full catalog) ────
    initial_result = await get_picks(
        user_request=user_request or None,
        parsed_image=parsed_image,
        catalog=catalog,
    )
    # initial_result = { "picks": [...], "aura_script": "..." }

    # Resolve picked products from catalog
    catalog_by_id = {item["id"]: item for item in catalog}
    pre_picks: list[dict] = []
    for pick in initial_result.get("picks", []):
        item = catalog_by_id.get(pick["id"], {})
        if item:
            pre_picks.append({**item, "justification": pick.get("justification", "")})

    # ── Phase 3: Review crawling + sizing (gated by TO_REVIEW env var) ──────
    user_profile = {
        "height": height,
        "top_size": top_size,
        "bottom_size": bottom_size,
        "shoe_size": shoe_size,
        "build": build,
    }

    review_data_list: list[dict | None] = []
    sizing_verdicts: list[dict | None] = []
    final_result = initial_result  # default: skip Phase 3

    if TO_REVIEW and pre_picks:
        print("[main] TO_REVIEW=true — running review crawl + sizing pipeline")

        # Crawl reviews for all 6 picks in parallel
        review_data_list = await crawl_products_parallel(pre_picks)

        # Run sizing analysis in parallel (skips products with null/blocked/failed crawl)
        has_profile = any(v for v in user_profile.values())
        if has_profile:
            sizing_verdicts = await analyze_sizing_parallel(
                products=pre_picks,
                review_data_list=review_data_list,
                user_profile=user_profile,
            )
        else:
            sizing_verdicts = [None] * len(pre_picks)

        # Attach review trust signals to product dicts for final K2 context
        for product, rd in zip(pre_picks, review_data_list):
            if rd:
                product["aggregate_rating"] = rd.get("aggregate_rating")
                product["total_review_count"] = rd.get("total_review_count")

        # Final K2 call — bake sizing verdicts into Aura's script
        final_result = await get_final_picks(
            pre_picks=pre_picks,
            sizing_verdicts=sizing_verdicts,
            user_request=user_request or None,
            parsed_image=parsed_image,
            user_profile=user_profile if any(user_profile.values()) else None,
        )
    else:
        print(f"[main] TO_REVIEW={'true (no picks)' if TO_REVIEW else 'false'} — skipping review pipeline")

    # ── TTS ───────────────────────────────────────────────────────────────────
    audio_path = await generate_speech(final_result["aura_script"], output_dir=AUDIO_OUTPUT_DIR)
    audio_url = f"/audio/{audio_path.name}"

    # ── Enrich final picks with catalog metadata + sizing verdict ─────────────
    picks_by_id = {p["id"]: p for p in pre_picks}
    # Build a map of product_id → sizing_verdict for O(1) lookup
    verdict_by_id: dict[str, dict | None] = {}
    for product, verdict in zip(pre_picks, sizing_verdicts):
        verdict_by_id[product["id"]] = verdict

    enriched_picks = []
    for pick in final_result.get("picks", []):
        pid = pick["id"]
        item = picks_by_id.get(pid) or catalog_by_id.get(pid) or {}
        verdict = verdict_by_id.get(pid)

        sizing_info: dict = {}
        if verdict and any(user_profile.values()):
            sizing_info = {
                "recommended_size": verdict.get("recommended_size"),
                "size_adjustment": verdict.get("size_adjustment"),
                "fit_flags": verdict.get("fit_flags") or [],
                "sizing_confidence": verdict.get("confidence"),
            }

        enriched_picks.append({
            **item,
            "justification": pick.get("justification", ""),
            **sizing_info,
        })

    return JSONResponse({"picks": enriched_picks, "audio_url": audio_url, "transcript": transcript})
