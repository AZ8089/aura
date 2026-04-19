Aura — Phase 2 Design Doc

The Core Loop



What Is Aura?

Aura is an AI-powered personal stylist. A user opens the Aura website, takes a photo of themselves (or a garment) with the in-browser camera, and records a voice note describing what they need. Aura responds like a bestie — fast, opinionated, Gen-Z energy — with curated outfit recommendations delivered as a voice note that plays back in the browser, alongside a grid of the picks.

Phase 2 adds Knot integration: Aura now pulls the user's real purchase history via TransactionLink to personalize recommendations, autonomously purchases the selected items via AgenticShopping, and can surface and cancel irrelevant clothing subscriptions via SubManager.

Persona: Aura is a D1 Yapper. She doesn't just find clothes — she narrates an arc. She uses Gen-Z slang naturally but is secretly a genius at fabric composition and silhouette theory. Her ElevenLabs voice should sound like a hype bestie, not a customer service rep.



Goal

Phase 1 (complete): One working end-to-end flow. User records a voice note and captures a photo in the browser. The backend transcribes the audio, parses the image, reasons over a hardcoded catalog, and returns a voice note with 3 recommendations in Aura's persona that the browser plays back.

Phase 2: Extend the loop with Knot. Aura fetches the user's real purchase history (TransactionLink) before reasoning, uses it to enrich K2's context, and after picks are confirmed autonomously purchases the items on the user's behalf (AgenticShopping). Optionally surfaces active clothing subscriptions and offers to cancel them (SubManager).



Tech Stack



Layer | Tool
Frontend | Plain HTML + JS (camera + MediaRecorder)
Backend | FastAPI (Python)
Speech-to-text | ElevenLabs STT
Image & vision parsing | Gemini multimodal
Reasoning engine | K2 Think V2
Voice output | ElevenLabs TTS
Purchase history | Knot TransactionLink
Autonomous checkout | Knot AgenticShopping
Subscription management | Knot SubManager



File Structure


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
├── catalog/
│   └── hardcoded.py
└── knot/
    ├── transaction_link.py  # fetch SKU-level purchase history
    ├── agentic_shopping.py  # autonomous purchase execution
    └── sub_manager.py       # surface + cancel clothing subscriptions



Module Specs

config.py

Stores all API keys and constants loaded from environment variables. Keys needed: ElevenLabs API key, ElevenLabs Voice ID, Gemini API key, K2 API key and base URL, Knot API key.



catalog/hardcoded.py

A static list of 15–20 clothing items. Each item must have: a unique ID, name, brand, price in USD, product URL, a list of vibe tags (e.g. "clean girl," "dark academia," "Y2K," "coquette," "streetwear"), garment type, color list, material description, and an image URL. Cover a wide range of vibes and garment types so K2 has real variety to reason over.

For Phase 2, prioritize items available on Amazon, as Knot's AgenticShopping and TransactionLink have confirmed Amazon support. Include the Amazon ASIN or product URL for any catalog items that map to Amazon listings so AgenticShopping can execute the purchase directly.



static/index.html (frontend)

A single-page browser UI that handles capture, playback, and purchase confirmation. Key responsibilities:

Camera capture. Uses navigator.mediaDevices.getUserMedia({ video: true }) to stream the camera into a <video> element. A "Take Photo" button draws the current video frame onto a hidden <canvas> and exports it as a JPEG blob.

Voice recording. Uses navigator.mediaDevices.getUserMedia({ audio: true }) + MediaRecorder to capture the user's voice note. Start/stop buttons control the recording; the resulting audio is stored as a webm/opus blob.

Knot auth flow. On first load, renders a "Connect your accounts" step that initializes the Knot Link UI (CardSwitcher/TransactionLink auth). Once connected, the user's Knot access token is stored in memory for the session.

Submission. "Send to Aura" button POSTs a single multipart/form-data request to /chat with the photo blob, the audio blob, and the Knot access token.

Response playback. Receives a JSON body with picks metadata, an audio URL (or base64 .mp3), and a purchase_status field from the backend. Pipes the audio into an <audio> element and autoplays, renders the 3 picks as a product grid (image, name, price, product link), and shows a purchase confirmation card per pick if AgenticShopping executed ("Aura already copped this for you ✓").

Purchase confirmation gate. Before calling /chat, render a "Aura is about to cop these for you — confirm?" modal showing the 3 picks and total cost. User must explicitly confirm before AgenticShopping executes. This prevents accidental purchases during demos.

SubManager prompt. If the backend returns active_subscriptions, render a dismissable banner listing them with a one-tap cancel button per subscription.

No framework required — keep it one HTML file so deploy is trivial.



main.py (FastAPI server)

Serves the static frontend at / and exposes a /chat endpoint and a /cancel-subscription endpoint. Key responsibilities:

Routing. POST /chat accepts multipart/form-data with optional fields: audio (a blob — voice note), image (a blob — photo from camera), text (a plain string, used only for debugging/fallback), and knot_token (the user's Knot session token from the frontend).

Orchestration.

If audio is present → pass to stt/transcribe.py → transcript string

If image is present → pass to vision/gemini_parser.py → parsed JSON

If text is present → treat directly as the user request

If knot_token is present → pass to knot/transaction_link.py → purchase history JSON

Combine transcript + parsed image JSON + text + purchase history into one context object

Reasoning + TTS. Pass the enriched context + hardcoded catalog to reasoning/k2_stylist.py. Take the returned aura_script and pass to tts/elevenlabs_tts.py.

AgenticShopping. After picks are returned by K2, pass each pick's product identifier + knot_token to knot/agentic_shopping.py to execute autonomous purchase. Collect purchase_status per item.

SubManager (optional). If knot_token is present, call knot/sub_manager.py to fetch active clothing-related subscriptions and include them in the response.

Response. Return a JSON body containing the picks metadata, a URL (or base64) for the generated .mp3, purchase_status per pick, and optionally active_subscriptions.

DELETE /cancel-subscription accepts a cancellation action token and knot_token, calls sub_manager.py to cancel the subscription, and returns a success/failure status.



stt/transcribe.py

Accepts an audio file. Sends it to the ElevenLabs Speech-to-Text API. Returns a plain text transcript string. This becomes the user's stated request — e.g. "I have a presentation tomorrow and I need something that says powerful but not try-hard."



vision/gemini_parser.py

Accepts an image file. Sends it to Gemini multimodal. Instructs Gemini to return a structured JSON.

If the photo is of a garment or outfit, return:

garment_type — what kind of item it is (e.g. "oversized blazer")

colors — list of detected colors

material_inference — likely fabric based on texture/drape in the image

styling_cues — accessories, silhouette, how it's worn

vibe — inferred aesthetic (e.g. "quiet luxury," "Y2K")

If the photo is of the user themselves, return:

build — general body proportions the user is working with

coloring — skin tone, hair color, visible undertones

current_style_cues — what they're already wearing, visible accessories

vibe — aesthetic they seem to be going for

A subject_type field on the response ("garment" or "self") tells the reasoning module which branch it got.

Return this JSON to the caller.



reasoning/k2_stylist.py

Accepts the combined user context (transcript + parsed image JSON if available + purchase history JSON if available) and the full catalog list. Calls K2 Think V2 with a system prompt and user message.

System prompt must define:

Aura's identity and tone (the D1 Yapper persona)

A Vibe Dictionary: what each aesthetic means in concrete fashion terms — specific colors, silhouettes, fabrics, styling details. Must define at least 6 vibes: Coquette, Clean Girl, Dark Academia, Quiet Luxury, Y2K, Streetwear

Instructions to reason over the catalog and return exactly 3 picks with justification written in Aura's voice — not a bullet list, a monologue

Instructions to use purchase history (if provided) to infer sizing, budget range, and brand preferences before selecting picks

Output format: a JSON with a picks array (each pick has catalog item ID, Aura's justification, and the product's purchase identifier for Knot) and a single aura_script string that can be piped directly to TTS

User message must include:

The user's stated request (from STT or plain text)

The parsed image JSON if a photo was provided

The full hardcoded catalog as context

The user's purchase history JSON from TransactionLink if available, formatted as a concise summary of past items, brands, price points, and inferred sizing



tts/elevenlabs_tts.py

Accepts the aura_script string returned by K2. Sends it to the ElevenLabs Text-to-Speech API using the configured Voice ID. Returns a path to the generated .mp3 file (or a URL the frontend can GET). This file is played back in the browser via an <audio> element.



knot/transaction_link.py

Accepts a Knot user access token. Calls the Knot TransactionLink API to retrieve SKU-level purchase history from connected merchants (prioritize Amazon). Returns a structured JSON summary containing: recent items purchased (name, category, price, brand), inferred size signals (e.g. clothing sizes from past orders), price range the user typically shops in, and brand affinities. This summary is passed as context to k2_stylist.py before reasoning so picks are grounded in the user's real taste and budget rather than guesswork.



knot/agentic_shopping.py

Accepts a list of picks (each with a product identifier — Amazon ASIN or equivalent) and a Knot user access token. For each pick, calls the Knot AgenticShopping API to autonomously execute the purchase on the user's behalf using their connected payment method. Returns a purchase_status object per pick: { item_id, status: "purchased" | "failed" | "skipped", order_confirmation }. Handles errors gracefully — if a purchase fails, flag it and continue with remaining picks rather than halting the entire flow.



knot/sub_manager.py

Accepts a Knot user access token. Calls the Knot SubManager API to retrieve the user's active subscriptions. Filters for fashion-relevant services (Stitch Fix, FabFitFun, Rent the Runway, Nuuly, etc.) and returns them as a list with name, monthly cost, and a cancellation action token. The frontend uses this to render a "Aura noticed you're paying for X — want me to cancel it?" banner. The DELETE /cancel-subscription endpoint in main.py accepts the cancellation action token and calls SubManager to cancel.



Data Flow

[Browser UI]
    → Knot Link UI (first-time auth) → knot_token stored in session
    → getUserMedia captures photo (canvas → JPEG blob)
    → MediaRecorder captures voice note (webm/opus blob)
    → POST /chat (multipart/form-data with audio + image + knot_token)
        → main.py orchestrator
            → [if audio] → transcribe.py → transcript string
            → [if image] → gemini_parser.py → parsed image JSON
            → [if knot_token] → transaction_link.py → purchase history JSON
            → k2_stylist.py (context + purchase history + catalog) → {picks, aura_script}
            → elevenlabs_tts.py (aura_script) → audio.mp3
            → [user confirms purchase] → agentic_shopping.py (picks + knot_token) → purchase_status
            → [optional] sub_manager.py (knot_token) → active_subscriptions
        → JSON response: { picks: [...], audio_url: "...", purchase_status: {...}, active_subscriptions: [...] }
    → Browser plays audio + renders picks grid + purchase confirmations
    → [if active_subscriptions] → renders subscription cancel banner



Checklist

Phase 1 (complete)

Browser captures photo from webcam and displays a preview

Browser records a voice note via MediaRecorder with stop/playback controls

POST /chat accepts audio + image and logs both payloads correctly

STT correctly transcribes a voice note into text

Gemini correctly parses an image (garment OR self) into the expected JSON structure

K2 returns 3 picks from the hardcoded catalog with Aura's script in her voice

ElevenLabs generates an .mp3 from the script

Browser receives the response, plays the .mp3, and renders the 3 picks

Full loop tested end-to-end at least 3 times with different types of input

Phase 2 (Knot integration)

Knot Link UI initializes correctly in the browser and returns a valid access token

TransactionLink returns SKU-level purchase history for a connected Amazon account

K2 reasoning uses purchase history to infer sizing and budget — picks are noticeably more personalized than without history

AgenticShopping successfully executes a purchase for at least one catalog item

purchase_status is returned in the JSON response and rendered as a confirmation card in the UI

SubManager returns at least one active subscription for a test account

Cancel flow works end-to-end: user taps cancel, SubManager cancels, banner dismisses

Full loop tested end-to-end: voice + photo → enriched reasoning → autonomous purchase → confirmation



Notes

HTTPS requirement. getUserMedia only works over HTTPS (or localhost). For a remote demo, deploy behind HTTPS — Render, Fly, or ngrok all work.

Audio format. MediaRecorder defaults to webm/opus in Chrome. Confirm ElevenLabs STT accepts webm; if not, transcode server-side with ffmpeg or record as WAV via a small polyfill.

CORS. Keep the frontend and backend on the same origin (FastAPI serving static/) to avoid CORS entirely. If you split them, enable fastapi.middleware.cors.CORSMiddleware.

Knot merchant support. Knot's TransactionLink and AgenticShopping have confirmed support for Amazon. Prioritize Amazon ASINs in the catalog for Phase 2 demo reliability. Verify support for other merchants (Gap, Fashion Nova) directly against Knot's merchant list before including them in the purchase flow.

Purchase confirmation UX. AgenticShopping acts on the user's behalf with real money — make the confirmation step explicit in the UI before executing. Show the 3 picks and total cost, require an explicit tap to confirm, then call agentic_shopping.py. This is especially important during demos.

Knot auth scope. Request only the scopes needed: transaction_read for TransactionLink, purchase for AgenticShopping, subscription_read + subscription_cancel for SubManager. Don't over-request.

Demo catalog strategy. For the hackathon demo, seed the hardcoded catalog with 5–8 items that are definitely purchasable via Knot/Amazon. The remaining slots can be non-purchasable items that fall back to product links as in Phase 1.
