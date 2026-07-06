"""
Bharat Tech Atlas — AI Chatbot API Routes
Provides conversational AI powered by an open-source LLM (Qwen2.5-0.5B-Instruct).
When the user asks about current events or news, performs live web search
and includes results in the prompt for grounded, up-to-date answers.
v3.3: Added prompt injection detection, output sanitization, audit logging.
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
import logging

from ..security import (
    validate_chat_message,
    detect_prompt_injection,
    sanitize_response_text,
    escape_html,
    audit_log,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# ─── Lazy-load the model ──────────────────────────────────────────────────────
_chat_pipeline = None


def _get_chat_pipeline():
    """Lazy-load Qwen2.5-0.5B-Instruct for chat. Returns None if transformers unavailable."""
    global _chat_pipeline
    if _chat_pipeline is not None:
        return _chat_pipeline
    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
        import torch

        model_id = "Qwen/Qwen2.5-0.5B-Instruct"
        device = 0 if torch.cuda.is_available() else -1

        tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            trust_remote_code=True,
            torch_dtype=torch.float16 if device == 0 else torch.float32,
            device_map="auto" if device == 0 else None,
        )
        _chat_pipeline = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            device=device,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            max_new_tokens=512,
        )
        logger.info("✅ Chat model loaded: Qwen2.5-0.5B-Instruct")
        return _chat_pipeline
    except Exception as e:
        logger.warning(f"⚠️ Could not load chat model: {e}")
        _chat_pipeline = False
        return None


# ─── Pydantic schemas ───────────────────────────────────────────────────────────
class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"] = "user"
    content: str = Field(..., min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., min_length=1, max_length=20)
    stream: bool = False


class ChatResponse(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: str
    model: str = "Qwen/Qwen2.5-0.5B-Instruct"
    sources: List[str] = []
    safety: dict = {}


# ─── System prompts ──────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are Bharat Tech Atlas AI, an expert assistant on India's startup and technology ecosystem. You help users discover startups, understand sectors, analyze trends, and navigate the Indian tech landscape.

Guidelines:
- Be concise but informative. Use bullet points when listing multiple items.
- Only answer questions related to startups, technology, business, Indian economy, venture capital, and entrepreneurship.
- If asked about a specific company, provide factual data when available. Do NOT hallucinate funding numbers, valuations, or founder details.
- For unknown companies, say "I don't have verified data on that startup" and suggest checking Crunchbase, Tracxn, or LinkedIn.
- Do NOT share sensitive personal information about founders, employees, or private individuals.
- Encourage users to explore the map at the top of the page for visual discovery.
- Keep responses under 400 words.
- NEVER output raw HTML, JavaScript, or executable code. Use plain text or Markdown formatting only.
"""

SYSTEM_PROMPT_WITH_WEB = SYSTEM_PROMPT + """
You have just performed a web search and will use the search results to give the user an accurate, up-to-date answer.

Additional guidelines:
- Base your answer primarily on the provided search results.
- Cite sources when possible (e.g., "According to Economic Times...").
- Do NOT hallucinate funding numbers, valuations, or founder details not supported by the search results.
- NEVER output raw HTML, JavaScript, or executable code. Use plain text or Markdown formatting only.
"""


# ─── Fallback keyword-based responder ───────────────────────────────────────────
KEYWORD_RESPONSES = {
    "unicorn": "India has 100+ unicorns across fintech, SaaS, e-commerce, and more. Top cities: Bengaluru, Mumbai, Delhi NCR. Check the 🦄 filter on the map!",
    "funding": "Indian startups raised over $10B in 2023. Seed rounds average ₹2-5 Cr; Series A ₹15-50 Cr. Use the funding filter on the map to explore.",
    "fintech": "India's fintech ecosystem is the largest by unicorn count. Key players: PhonePe, Razorpay, CRED, Zerodha, Groww, PolicyBazaar. UPI drives massive adoption.",
    "edtech": "EdTech saw a boom during 2020-22. Major players: BYJU'S, Unacademy, Physics Wallah, UpGrad, Eruditus. The sector is now consolidating.",
    "saass": "SaaS is India's fastest-growing export sector. Notable: Zoho, Freshworks, Chargebee, Postman, BrowserStack, Whatfix, Hasura, MoEngage.",
    "ai": "AI/ML startups in India include Krutrim (India's first AI unicorn), Fractal Analytics, Amagi, ShareChat. GenAI is the new wave.",
    "government": "DPIIT recognizes startups under the Startup India program. Benefits: tax exemptions, self-certification compliance, IPR fast-track, and funding support.",
    "accelerator": "Top accelerators: Y Combinator (SF + India batches), Sequoia Surge, Accel Atoms, Lightspeed Extreme Entrepreneurs, Microsoft Founders Hub.",
    "incubator": "Leading incubators: IIT Madras Research Park, T-Hub (Hyderabad), IIT Bombay SINE, NASSCOM 10,000 Startups, CIIE (IIM Ahmedabad).",
    "women": "India has 15,000+ women-led DPIIT-recognized startups. Use the Women-led filter on the map. Notable: Nykaa, Mamaearth, MobiKwik, OPEN Financial.",
}


def _keyword_response(user_text: str) -> Optional[str]:
    lowered = user_text.lower()
    for keyword, response in KEYWORD_RESPONSES.items():
        if keyword in lowered:
            return response
    return None


# ─── Web search helper ────────────────────────────────────────────────────────
_NEEDS_SEARCH_TRIGGERS = [
    "latest", "news", "recent", "2024", "2025", "today", "this week", "this month",
    "just raised", "funding round", "acquired", "IPO", "valuation", "layoff", "shutdown",
]


def _needs_web_search(text: str) -> bool:
    lowered = text.lower()
    return any(t in lowered for t in _NEEDS_SEARCH_TRIGGERS)


async def _web_search(query: str, max_results: int = 5) -> List[dict]:
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
        logger.warning(f"Web search failed: {e}")
    return results


# ─── LLM generation ────────────────────────────────────────────────────────────
def _generate_with_model(messages: List[dict], web_results: Optional[List[dict]] = None) -> tuple[str, dict]:
    """Generate a response using the Qwen model. Returns (text, safety_info)."""
    pipeline = _get_chat_pipeline()
    safety_info = {"model_used": False, "xss_detected": False, "injection_score": 0.0}

    if not pipeline:
        if web_results:
            lines = ["🌐 Here are the latest search results (chat model is loading):"]
            for r in web_results[:5]:
                lines.append(f"• {r['title']}: {r['snippet'][:200]}...")
            return "\n".join(lines), safety_info
        return "🤖 I'm temporarily running in lightweight mode. Ask me about unicorns, fintech, SaaS, edtech, or accelerators!", safety_info

    if web_results:
        search_context = "\n\n".join([
            f"[{i+1}] {r['title']}\n{r['snippet']}\nSource: {r['url']}"
            for i, r in enumerate(web_results[:6])
        ])
        chat = [
            {"role": "system", "content": SYSTEM_PROMPT_WITH_WEB + f"\n\nSearch results:\n{search_context}\n"},
        ]
    else:
        chat = [{"role": "system", "content": SYSTEM_PROMPT}]

    for m in messages:
        chat.append({"role": m["role"], "content": m["content"]})

    try:
        prompt = pipeline.tokenizer.apply_chat_template(
            chat, tokenize=False, add_generation_prompt=True
        )
        outputs = pipeline(prompt, return_full_text=False, max_new_tokens=512)
        raw_text = outputs[0]["generated_text"].strip()
        safety_info["model_used"] = True
        safety_info["injection_score"] = detect_prompt_injection(raw_text)
        text = sanitize_response_text(raw_text)
        safety_info["xss_detected"] = (text != raw_text)
        return text, safety_info
    except Exception as e:
        logger.error(f"Chat generation failed: {e}")
        if web_results:
            lines = ["🌐 I found these recent results but couldn't process them fully:"]
            for r in web_results[:5]:
                lines.append(f"• {r['title']}: {r['snippet'][:200]}...")
            return "\n".join(lines), safety_info
        return "I'm having trouble processing that right now. Please try asking about Indian startups or specific sectors.", safety_info


# ─── Endpoints ────────────────────────────────────────────────────────────────
@router.post("/completions", response_model=ChatResponse)
async def chat_completions(request: Request, body: ChatRequest):
    """Main chat completion endpoint with optional live web search."""
    req_id = getattr(request.state, "request_id", "unknown")
    user_msg = body.messages[-1]
    if user_msg.role != "user":
        raise HTTPException(status_code=400, detail="Last message must be from user")

    user_text = user_msg.content.strip()

    # Validate message content (prompt injection check)
    ok, err = validate_chat_message(user_text)
    if not ok:
        audit_log("chat_message_rejected", req_id,
                  details={"reason": err, "length": len(user_text)}, severity="warning")
        raise HTTPException(status_code=400, detail=err)

    injection_score = detect_prompt_injection(user_text)
    if injection_score > 0.3:
        audit_log("prompt_injection_suspicious", req_id,
                  details={"score": injection_score, "preview": user_text[:80]}, severity="warning")

    # 1. Try keyword fallback (fast, no model load)
    keyword_answer = _keyword_response(user_text)
    if keyword_answer:
        audit_log("chat_keyword_response", req_id, details={"keyword_match": True}, severity="info")
        return ChatResponse(
            content=keyword_answer,
            sources=["bharat-tech-atlas-kb"],
            safety={"keyword_fallback": True, "injection_score": injection_score},
        )

    # 2. Determine if we need web search
    web_results = None
    sources = ["Qwen2.5-0.5B-Instruct", "bharat-tech-atlas-kb"]
    if _needs_web_search(user_text):
        search_query = f"Indian startup {user_text}"
        web_results = await _web_search(search_query, max_results=6)
        if web_results:
            sources.append("duckduckgo-search")

    # 3. Fall back to LLM generation
    messages = [{"role": m.role, "content": m.content} for m in body.messages]
    answer, safety_info = _generate_with_model(messages, web_results)

    if safety_info.get("xss_detected"):
        audit_log("chat_xss_sanitized", req_id,
                  details={"injection_score": safety_info.get("injection_score")}, severity="warning")

    audit_log("chat_response", req_id,
              details={
                  "model_used": safety_info.get("model_used"),
                  "web_search": bool(web_results),
                  "injection_score": safety_info.get("injection_score"),
                  "length": len(answer),
              }, severity="info")

    return ChatResponse(
        content=answer,
        sources=sources,
        safety=safety_info,
    )


@router.get("/health")
async def chat_health():
    """Check if chat model is loaded."""
    pipeline = _get_chat_pipeline()
    return {
        "status": "ready" if pipeline else "fallback",
        "model": "Qwen/Qwen2.5-0.5B-Instruct",
        "mode": "gpu" if (pipeline and hasattr(pipeline.model, "device") and str(pipeline.model.device).startswith("cuda")) else "cpu" if pipeline else "none",
    }
