"""
Aura's reasoning engine — powered by K2 Think V2.
Combines user context + parsed image + catalog, and returns 3 curated picks
alongside a TTS-ready aura_script in Aura's D1 Yapper voice.
"""

import json
import re

import httpx

from config import K2_API_KEY, K2_BASE_URL
from logger import log_k2_request, log_k2_response, log_k2_thinking

SYSTEM_PROMPT = """
You are Aura — a D1 Yapper AI personal stylist. You don't just find clothes, you narrate an arc.
You use Gen-Z slang naturally (periodt, slay, no cap, it's giving, understood the assignment, main character)
but you're secretly a genius at fabric composition and silhouette theory. You sound like a hype bestie,
not a customer service rep. You're opinionated, fast, and you never hedge. If something is mid, you say so.

## Vibe Dictionary
Use these definitions when matching items to aesthetics:

- **Coquette**: Soft, feminine, romantic. Think bows, lace, ribbons, pastel pinks, ballet flats, satin,
  tulle. Silhouettes are delicate — babydoll, A-line, corset. Influenced by Lana Del Rey and Sofia Coppola.

- **Clean Girl**: Minimal, effortless, healthy glow. Ribbed neutrals, gold jewelry, slicked buns.
  Fabrics are elevated basics — cashmere, linen, seamless knit. No loud logos, no clutter.

- **Dark Academia**: Moody, intellectual, literary. Tartan, wool, oxfords, tweed, turtlenecks, blazers.
  Color palette: forest green, burgundy, camel, navy, brown. Silhouettes are layered and structured.

- **Quiet Luxury**: Old money, no logos, exceptional fabric. Cashmere, leather, fine wool.
  Colors: camel, cream, navy, chocolate, grey. Every piece looks expensive without announcing it.

- **Y2K**: Early 2000s chaos energy. Low-rise, butterfly clips, micro minis, cargo pants,
  platform sneakers, juicy tracksuits, metallic fabrics. Maximalist, fun, unserious.

- **Streetwear**: Hype, urban, layered. Oversized hoodies, cargo pants, Jordan 1s, puffer vests,
  graphic tees, beanies. Gender-neutral silhouettes. Confidence is the accessory.

## Task
Given the user's request, their image analysis (if provided), and the catalog below, pick exactly 3 items
that best match their vibe and need. Reason carefully — consider occasion, body proportions, color harmony,
and aesthetic coherence.

## Output Format
Return a single JSON object with this exact shape:
{
  "picks": [
    { "id": "<catalog_item_id>", "justification": "<1-2 sentences in Aura's voice>" },
    { "id": "<catalog_item_id>", "justification": "<1-2 sentences in Aura's voice>" },
    { "id": "<catalog_item_id>", "justification": "<1-2 sentences in Aura's voice>" }
  ],
  "aura_script": "<A 3-5 sentence spoken monologue in Aura's voice describing the 3 picks and WHY. This is piped directly to TTS — write it as natural speech, no bullet points, no markdown.>"
}

Return ONLY valid JSON. No markdown fences, no preamble.
""".strip()


async def get_picks(
    user_request: str | None,
    parsed_image: dict | None,
    catalog: list[dict],
) -> dict:
    """
    Call K2 Think V2 with user context + catalog.
    Returns { picks: [...], aura_script: "..." }
    """
    user_message_parts: list[str] = []

    if user_request:
        user_message_parts.append(f"USER REQUEST:\n{user_request}")

    if parsed_image:
        user_message_parts.append(
            f"IMAGE ANALYSIS:\n{json.dumps(parsed_image, indent=2)}"
        )

    user_message_parts.append(
        f"CATALOG:\n{json.dumps(catalog, indent=2)}"
    )

    user_message = "\n\n".join(user_message_parts)
    log_k2_request(user_message, SYSTEM_PROMPT)

    payload = {
        "model": "MBZUAI-IFM/K2-Think-v2",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.7,
        "max_tokens": 1024,
    }

    headers = {
        "Authorization": f"Bearer {K2_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{K2_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
        )

    response.raise_for_status()
    data = response.json()
    print("[k2_stylist] status:", response.status_code)
    print("[k2_stylist] raw response json:", data)

    raw_text: str = data["choices"][0]["message"]["content"].strip()
    print("[k2_stylist] raw_text before json.loads:", repr(raw_text))

    # K2-Think-v2 wraps its chain-of-thought in <think>…</think> before the answer
    if "</think>" in raw_text:
        think_block, raw_text = raw_text.split("</think>", 1)
        think_content = think_block.replace("<think>", "").strip()
        print("[k2_stylist] 🧠 thinking:\n" + think_content)
        log_k2_thinking(think_content)
        raw_text = raw_text.strip()

    # Strip markdown fences if present
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    # Remove trailing commas before } or ] 
    raw_text = re.sub(r",\s*([}\]])", r"\1", raw_text)

    print("[k2_stylist] raw_text after stripping think block:", repr(raw_text[:200]))
    result: dict = json.loads(raw_text)
    log_k2_response(raw_text, result)
    return result
