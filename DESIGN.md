# Aura — Phase 1 Design Doc

## The Core Loop

---

## What Is Aura?

Aura is an AI-powered personal stylist. A user opens the Aura website, takes a photo of themselves (or a garment) with the in-browser camera, and records a voice note describing what they need. Aura responds like a bestie — fast, opinionated, Gen-Z energy — with 3 curated outfit recommendations delivered as a voice note that plays back in the browser, alongside a grid of the picks.

**Persona:** Aura is a D1 Yapper. She doesn't just find clothes — she narrates an arc. She uses Gen-Z slang naturally but is secretly a genius at fabric composition and silhouette theory. Her ElevenLabs voice should sound like a hype bestie, not a customer service rep.

---

## Goal

One working end-to-end flow. User records a voice note and captures a photo in the browser. The backend transcribes the audio, parses the image, reasons over a hardcoded catalog, and returns a voice note with 3 recommendations in Aura's persona that the browser plays back.

---

## Tech Stack (Phase 1 Only)

| Layer                  | Tool                                     |
| ---------------------- | ---------------------------------------- |
| Frontend               | Plain HTML + JS (camera + MediaRecorder) |
| Backend                | FastAPI (Python)                         |
| Speech-to-text         | ElevenLabs STT                           |
| Image & vision parsing | Gemini multimodal                        |
| Reasoning engine       | K2 Think V2                              |
| Voice output           | ElevenLabs TTS                           |

---

## File Structure

```
aura/
├── main.py                  # FastAPI app — serves frontend + /chat endpoint
├── config.py
├── static/
│   └── index.html           # camera + mic capture + audio playback
├── stt/
│   └── transcribe.py
├── vision/
│   └── gemini_parser.py
├── reasoning/
│   └── k2_stylist.py
├── tts/
│   └── elevenlabs_tts.py
└── catalog/
    └── hardcoded.py
```

---

## Module Specs

### config.py

Stores all API keys and constants loaded from environment variables. Keys needed: ElevenLabs API key, ElevenLabs Voice ID, Gemini API key, K2 API key and base URL.

---

### catalog/hardcoded.py

A static list of 15–20 clothing items. Each item must have: a unique ID, name, brand, price in USD, product URL, a list of vibe tags (e.g. "clean girl," "dark academia," "Y2K," "coquette," "streetwear"), garment type, color list, material description, and an image URL. Cover a wide range of vibes and garment types so K2 has real variety to reason over.

---

### static/index.html (frontend)

A single-page browser UI that handles capture and playback. Key responsibilities:

- **Camera capture.** Uses `navigator.mediaDevices.getUserMedia({ video: true })` to stream the camera into a `<video>` element. A "Take Photo" button draws the current video frame onto a hidden `<canvas>` and exports it as a JPEG blob.
- **Voice recording.** Uses `navigator.mediaDevices.getUserMedia({ audio: true })` + `MediaRecorder` to capture the user's voice note. Start/stop buttons control the recording; the resulting audio is stored as a webm/opus blob.
- **Submission.** "Send to Aura" button POSTs a single `multipart/form-data` request to `/chat` with the photo blob and the audio blob.
- **Response playback.** Receives a JSON body with picks metadata and an audio URL (or base64 .mp3) from the backend, pipes the audio into an `<audio>` element and autoplays, and renders the 3 picks as a product grid (image, name, price, product link).

No framework required for Phase 1 — keep it one HTML file so deploy is trivial.

---

### main.py (FastAPI server)

Serves the static frontend at `/` and exposes a `/chat` endpoint. Key responsibilities:

- **Routing.** `POST /chat` accepts `multipart/form-data` with optional fields: `audio` (a blob — voice note), `image` (a blob — photo from camera), and `text` (a plain string, used only for debugging/fallback).
- **Orchestration.**
  - If `audio` is present → pass to `stt/transcribe.py` → transcript string
  - If `image` is present → pass to `vision/gemini_parser.py` → parsed JSON
  - If `text` is present → treat directly as the user request
  - Combine any transcript + parsed JSON + text into one context object
- **Reasoning + TTS.** Pass the context + hardcoded catalog to `reasoning/k2_stylist.py`. Take the returned `aura_script` and pass to `tts/elevenlabs_tts.py`.
- **Response.** Return a JSON body containing the picks metadata and a URL (or base64) for the generated .mp3 so the frontend can both render the outfits and play the audio.

---

### stt/transcribe.py

Accepts an audio file. Sends it to the ElevenLabs Speech-to-Text API. Returns a plain text transcript string. This becomes the user's stated request — e.g. "I have a presentation tomorrow and I need something that says powerful but not try-hard."

---

### vision/gemini_parser.py

Accepts an image file. Sends it to Gemini multimodal. Instructs Gemini to return a structured JSON.

If the photo is of a **garment or outfit**, return:

- `garment_type` — what kind of item it is (e.g. "oversized blazer")
- `colors` — list of detected colors
- `material_inference` — likely fabric based on texture/drape in the image
- `styling_cues` — accessories, silhouette, how it's worn
- `vibe` — inferred aesthetic (e.g. "quiet luxury," "Y2K")

If the photo is of the **user themselves**, return:

- `build` — general body proportions the user is working with
- `coloring` — skin tone, hair color, visible undertones
- `current_style_cues` — what they're already wearing, visible accessories
- `vibe` — aesthetic they seem to be going for

A `subject_type` field on the response (`"garment"` or `"self"`) tells the reasoning module which branch it got.

Return this JSON to the caller.

---

### reasoning/k2_stylist.py

Accepts the combined user context (transcript + parsed image JSON if available) and the full catalog list. Calls K2 Think V2 with a system prompt and user message.

**System prompt must define:**
- Aura's identity and tone (the D1 Yapper persona)
- A Vibe Dictionary: what each aesthetic means in concrete fashion terms — specific colors, silhouettes, fabrics, styling details. Must define at least 6 vibes: Coquette, Clean Girl, Dark Academia, Quiet Luxury, Y2K, Streetwear
- Instructions to reason over the catalog and return exactly 3 picks with justification written in Aura's voice — not a bullet list, a monologue
- Output format: a JSON with a `picks` array (each pick has catalog item ID + Aura's justification) and a single `aura_script` string that can be piped directly to TTS

**User message must include:**
- The user's stated request (from STT or plain text)
- The parsed image JSON if a photo was provided
- The full hardcoded catalog as context

---

### tts/elevenlabs_tts.py

Accepts the `aura_script` string returned by K2. Sends it to the ElevenLabs Text-to-Speech API using the configured Voice ID. Returns a path to the generated .mp3 file (or a URL the frontend can GET). This file is played back in the browser via an `<audio>` element.

---

## Data Flow

```
[Browser UI]
    → getUserMedia captures photo (canvas → JPEG blob)
    → MediaRecorder captures voice note (webm/opus blob)
    → POST /chat (multipart/form-data with audio + image)
        → main.py orchestrator
            → [if audio] → transcribe.py → transcript string
            → [if image] → gemini_parser.py → parsed image JSON
            → k2_stylist.py (context + hardcoded catalog) → {picks, aura_script}
            → elevenlabs_tts.py (aura_script) → audio.mp3
        → JSON response: { picks: [...], audio_url: "..." }
    → Browser plays audio via <audio> element + renders picks grid
```

---

## Checklist

- [ ] Browser captures photo from webcam and displays a preview
- [ ] Browser records a voice note via MediaRecorder with stop/playback controls
- [ ] `POST /chat` accepts audio + image and logs both payloads correctly
- [ ] STT correctly transcribes a voice note into text
- [ ] Gemini correctly parses an image (garment OR self) into the expected JSON structure
- [ ] K2 returns 3 picks from the hardcoded catalog with Aura's script in her voice
- [ ] ElevenLabs generates an .mp3 from the script
- [ ] Browser receives the response, plays the .mp3, and renders the 3 picks
- [ ] Full loop tested end-to-end at least 3 times with different types of input

---

## Notes

- **HTTPS requirement.** `getUserMedia` only works over HTTPS (or `localhost`). For a remote demo, deploy behind HTTPS — Render, Fly, or ngrok all work.
- **Audio format.** MediaRecorder defaults to webm/opus in Chrome. Confirm ElevenLabs STT accepts webm; if not, transcode server-side with ffmpeg or record as WAV via a small polyfill.
- **CORS.** Keep the frontend and backend on the same origin (FastAPI serving `static/`) to avoid CORS entirely. If you split them, enable `fastapi.middleware.cors.CORSMiddleware`.
