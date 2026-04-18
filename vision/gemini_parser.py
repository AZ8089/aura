"""
Image parsing via Gemini multimodal.
Accepts raw image bytes (JPEG).
Returns a structured dict describing the garment or the person.
"""

import base64
import json

import httpx

from config import GEMINI_API_KEY

GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-1.5-flash:generateContent"
)

SYSTEM_PROMPT = """
You are a fashion vision AI. Analyze the provided image and return a JSON object.

Determine whether the photo shows:
  (A) A garment or outfit (clothing item, flat-lay, outfit photo), OR
  (B) A person (selfie, full-body, mirror photo).

For (A) — garment/outfit — return exactly this JSON shape:
{
  "subject_type": "garment",
  "garment_type": "<e.g. oversized blazer>",
  "colors": ["<color1>", "<color2>"],
  "material_inference": "<likely fabric based on texture/drape>",
  "styling_cues": "<accessories, silhouette, how it's worn>",
  "vibe": "<inferred aesthetic, e.g. quiet luxury, Y2K, coquette>"
}

For (B) — person — return exactly this JSON shape:
{
  "subject_type": "self",
  "build": "<general body proportions>",
  "coloring": "<skin tone, hair color, visible undertones>",
  "current_style_cues": "<what they're wearing, visible accessories>",
  "vibe": "<aesthetic they seem to be going for>"
}

Return ONLY valid JSON. No markdown fences, no explanation.
""".strip()


async def parse_image(image_bytes: bytes) -> dict:
    """
    Send image bytes to Gemini multimodal and return parsed JSON.
    """
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": SYSTEM_PROMPT},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": image_b64,
                        }
                    },
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 512,
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            GEMINI_API_URL,
            params={"key": GEMINI_API_KEY},
            json=payload,
        )

    response.raise_for_status()
    data = response.json()

    raw_text: str = (
        data["candidates"][0]["content"]["parts"][0]["text"].strip()
    )

    # Strip markdown code fences if Gemini adds them despite instructions
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    parsed: dict = json.loads(raw_text)
    return parsed
