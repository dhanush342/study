"""
Bharat Tech Atlas — Chat Module
Modular AI chatbot powered by Qwen2.5-0.5B-Instruct with keyword fallbacks,
web search integration, prompt injection detection, and XSS-safe output.
v3.4: Refactored from chat_routes.py into engine/models/config/routes split.
"""
from .routes import router

__all__ = ["router"]
