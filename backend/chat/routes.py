"""
Bharat Tech Atlas — Chat API Routes
v3.4: Refactored routes layer over engine core.
"""
from fastapi import APIRouter, HTTPException, Request

from ..security import validate_chat_message, detect_prompt_injection, sanitize_response_text, audit_log
from .models import ChatRequest, ChatResponse
from .engine import keyword_response, needs_web_search, web_search, generate_with_model, _get_chat_pipeline

router = APIRouter()


@router.post("/completions", response_model=ChatResponse)
async def chat_completions(request: Request, body: ChatRequest):
    """Main chat completion with optional live web search."""
    req_id = getattr(request.state, "request_id", "unknown")
    user_msg = body.messages[-1]
    if user_msg.role != "user":
        raise HTTPException(status_code=400, detail="Last message must be from user")

    user_text = user_msg.content.strip()

    # Validate + audit
    ok, err = validate_chat_message(user_text)
    if not ok:
        audit_log("chat_message_rejected", req_id,
                  details={"reason": err, "length": len(user_text)}, severity="warning")
        raise HTTPException(status_code=400, detail=err)

    injection_score = detect_prompt_injection(user_text)
    if injection_score > 0.3:
        audit_log("prompt_injection_suspicious", req_id,
                  details={"score": injection_score, "preview": user_text[:80]}, severity="warning")

    # 1. Keyword fallback (instant)
    kw = keyword_response(user_text)
    if kw:
        audit_log("chat_keyword_response", req_id, details={"keyword_match": True}, severity="info")
        return ChatResponse(
            content=kw,
            sources=["bharat-tech-atlas-kb"],
            safety={"keyword_fallback": True, "injection_score": injection_score},
        )

    # 2. Web search if needed
    web_results = None
    sources = ["Qwen/Qwen2.5-0.5B-Instruct", "bharat-tech-atlas-kb"]
    if needs_web_search(user_text):
        web_results = await web_search(f"Indian startup {user_text}", max_results=6)
        if web_results:
            sources.append("duckduckgo-search")

    # 3. LLM generation
    messages = [{"role": m.role, "content": m.content} for m in body.messages]
    answer, safety_info = generate_with_model(messages, web_results, req_id)

    if safety_info.get("xss_detected"):
        audit_log("chat_xss_sanitized", req_id,
                  details={"injection_score": safety_info.get("injection_score")}, severity="warning")

    audit_log("chat_response", req_id, details={
        "model_used": safety_info.get("model_used"),
        "web_search": bool(web_results),
        "injection_score": safety_info.get("injection_score"),
        "length": len(answer),
    }, severity="info")

    return ChatResponse(
        content=answer,
        model="Qwen/Qwen2.5-0.5B-Instruct",
        sources=sources,
        safety=safety_info,
    )


@router.get("/health")
async def chat_health():
    """Check if the chat model is loaded."""
    pipeline = _get_chat_pipeline()
    mode = (
        "gpu" if pipeline and hasattr(pipeline.model, "device") and str(pipeline.model.device).startswith("cuda")
        else "cpu" if pipeline else "none"
    )
    return {
        "status": "ready" if pipeline else "fallback",
        "model": "Qwen/Qwen2.5-0.5B-Instruct",
        "mode": mode,
    }
