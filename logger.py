"""
Shared structured logger for Aura.
Appends NDJSON entries to logs/aura.log so every API call is auditable.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path(__file__).parent / "logs"
LOG_FILE = LOG_DIR / "aura.log"


def _write(entry: dict) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    entry["ts"] = datetime.now(timezone.utc).isoformat()
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def log_gemini_request(image_size_bytes: int, prompt: str) -> None:
    _write({
        "event": "gemini_request",
        "image_bytes": image_size_bytes,
        "prompt": prompt,
    })


def log_gemini_response(raw_text: str, parsed: dict) -> None:
    _write({
        "event": "gemini_response",
        "raw_text": raw_text,
        "parsed": parsed,
    })


def log_k2_request(user_message: str, system_prompt: str) -> None:
    _write({
        "event": "k2_request",
        "system_prompt": system_prompt,
        "user_message": user_message,
    })


def log_k2_thinking(think_content: str) -> None:
    _write({
        "event": "k2_thinking",
        "content": think_content,
    })


def log_k2_response(raw_text: str, result: dict) -> None:
    _write({
        "event": "k2_response",
        "raw_text": raw_text,
        "result": result,
    })


def log_firecrawl_search(query: str, trusted_sites: list[str]) -> None:
    _write({
        "event": "firecrawl_search_request",
        "query": query,
        "trusted_sites": trusted_sites,
    })


def log_firecrawl_search_results(query: str, urls: list[str]) -> None:
    _write({
        "event": "firecrawl_search_results",
        "query": query,
        "n_urls": len(urls),
        "urls": urls,
    })


def log_firecrawl_scrape(url: str) -> None:
    _write({
        "event": "firecrawl_scrape_request",
        "url": url,
    })


def log_firecrawl_scrape_result(url: str, success: bool, markdown_len: int | None = None) -> None:
    _write({
        "event": "firecrawl_scrape_result",
        "url": url,
        "success": success,
        "markdown_len": markdown_len,
    })


def log_search_query(query: str, sources: list[str]) -> None:
    _write({
        "event": "search_query_synthesized",
        "query": query,
        "sources": sources,
    })


def log_web_search_k2(label: str, prompt: str, raw_output: str | None, parsed: dict | None, error: str | None = None) -> None:
    _write({
        "event": "web_search_k2",
        "label": label,
        "prompt": prompt,
        "raw_output": raw_output,
        "parsed": parsed,
        "error": error,
    })
