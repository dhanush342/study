"""
Bharat Tech Atlas — Chat Engine Core
Implements lazy model loading, keyword fallbacks, web search, LLM generation,
and safety checks (prompt injection + XSS sanitization).
"""
import logging
from typing import Optional, List, Tuple

from ..security import (
    validate_chat_message,
    detect_prompt_injection,
    sanitize_response_text,
    escape_html,
    audit_log,
)
from .config import (
    MODEL_ID,
    MAX_NEW_TOKENS,
    TEMPERATURE,
    TOP_P,
    DEVICE_GPU,
    DEVICE_CPU,
    KEYWORD_RESPONSES,
    NEEDS_SEARCH_TRIGGERS,
    WEB_SEARCH_MAX_RESULTS,
    WEB_SEARCH_QUERY_PREFIX,
    SYSTEM_PROMPT,
    SYSTEM_PROMPT_WITH_WEB,
)

logger = logging.getLogger(__name__)

# ─── Lazy-loaded pipeline ───────────────────────────────────────────────────────
_chat_pipeline = None


def _get_chat_pipeline():
    """Lazy-load Qwen2.5-0.5B-Instruct. Returns None if transformers unavailable."""
    global _chat_pipeline
    if _chat_pipeline is not None:
        return _chat_pipeline
    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
        import torch

        device = DEVICE_GPU if torch.cuda.is_available() else DEVICE_CPU
        dtype = torch.float16 if device == 0 else torch.float32

        tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID, trust_remote_code=True, torch_dtype=dtype,
            device_map="auto" if device == 0 else None,
        )
        _chat_pipeline = pipeline(
            "text-generation", model=model, tokenizer=tokenizer,
            device=device, do_sample=True, temperature=TEMPERATURE,
            top_p=TOP_P, max_new_tokens=MAX_NEW_TOKENS,
        )
        logger.info("Chat model loaded: %s", MODEL_ID)
        return _chat_pipeline
    except Exception as e:
        logger.warning("Could not load chat model: %s", e)
        _chat_pipeline = False
        return None


def keyword_response(user_text: str) -> Optional[str]:
    """Return a keyword-match answer without loading the LLM."""
    lowered = user_text.lower()
    for kw, resp in KEYWORD_RESPONSES.items():
        if kw in lowered:
            return resp
    return None


def needs_web_search(text: str) -> bool:
    lowered = text.lower()
    return any(t in lowered for t in NEEDS_SEARCH_TRIGGERS)


async def web_search(query: str, max_results: int = WEB_SEARCH_MAX_RESULTS) -> List[dict]:
    """Search DuckDuckGo for fresh news/articles."""
    results = []
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                title = escape_html(r.get("title", ""))[:200]
                url = r.get("href", "")
                snippet = escape_html(r.get("body", ""))[:400]
                results.append({"title": title, "url": url, "snippet": snippet})
    except Exception as e:
        logger.warning("Web search failed: %s", e)
    return results


def generate_with_model(
    messages: List[dict],
    web_results: Optional[List[dict]] = None,
    req_id: str = "unknown",
) -> Tuple[str, dict]:
    """Generate a response via Qwen. Returns (text, safety_info)."""
    pipeline = _get_chat_pipeline()
    safety = {
        "model_used": False,
        "xss_detected": False,
        "injection_score": 0.0,
    }

    if not pipeline:
        if web_results:
            lines = ["Here are the latest search results:"]
            for r in web_results[:5]:
                lines.append(f"- {r['title']}: {r['snippet'][:200]}...")
            return "\n".join(lines), safety
        return ("I'm running in lightweight mode. Ask about unicorns, fintech, SaaS,",
                safety)

    if web_results:
        search_ctx = "\n\n".join([
            f"[{i+1}] {r['title']}\n{r['snippet']}\nSource: {r['url']}"
            for i, r in enumerate(web_results[:6])
        ])
        chat = [
            {"role": "system", "content": SYSTEM_PROMPT_WITH_WEB + f"\n\nSearch results:\n{search_ctx}\n"},
        ]
    else:
        chat = [{"role": "system", "content": SYSTEM_PROMPT}]

    for m in messages:
        chat.append({"role": m["role"], "content": m["content"]})

    try:
        prompt = pipeline.tokenizer.apply_chat_template(
            chat, tokenize=False, add_generation_prompt=True
        )
        outputs = pipeline(prompt, return_full_text=False, max_new_tokens=MAX_NEW_TOKENS)
        raw = outputs[0]["generated_text"].strip()
        safety["model_used"] = True
        safety["injection_score"] = detect_prompt_injection(raw)
        text = sanitize_response_text(raw)
        safety["xss_detected"] = text != raw
        return text, safety
    except Exception as e:
        logger.error("Chat generation failed: %s", e)
        if web_results:
            lines = ["I found these results but couldn't process them fully:"]
            for r in web_results[:5]:
                lines.append(f"- {r['title']}: {r['snippet'][:200]}...")
            return "\n".join(lines), safety
        return "I'm having trouble processing that. Try asking about Indian startups or sectors.", safety
