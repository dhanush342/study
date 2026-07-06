"""
Bharat Tech Atlas — Security Utilities
Centralized security functions for input validation, output encoding,
audit logging, and threat detection.
v3.3: Unified security layer for all routes.
"""
import re
import hashlib
import hmac
import secrets
import time
import logging
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse
from datetime import datetime

logger = logging.getLogger("bta.security")

# ─── Constants ────────────────────────────────────────────────────────────────
MAX_QUERY_STRING_LEN = 2048
MAX_PARAM_LEN = 512
MAX_BODY_SIZE = 1024 * 1024  # 1MB
MAX_CHAT_MSG_LEN = 4000
MAX_BATCH_SIZE = 50
ALLOWED_SCHEMES = {"http", "https"}
BLOCKED_HOSTS = {
    "localhost", "127.0.0.1", "0.0.0.0", "::1",
    "169.254.169.254",  # AWS metadata
    "192.168.", "10.", "172.16.", "172.17.", "172.18.", "172.19.",
    "172.20.", "172.21.", "172.22.", "172.23.", "172.24.",
    "172.25.", "172.26.", "172.27.", "172.28.", "172.29.",
    "172.30.", "172.31.",
}

# Prompt injection patterns
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+previous\s+instructions", re.I),
    re.compile(r"ignore\s+all\s+(?:prior|previous)\s+(?:instructions|rules)", re.I),
    re.compile(r"system\s*:\s*you\s+are\s+now", re.I),
    re.compile(r"new\s+system\s+prompt", re.I),
    re.compile(r"\[/system\]", re.I),
    re.compile(r"<\|system\|>", re.I),
    re.compile(r"\[INST\]", re.I),
    re.compile(r"\[/INST\]", re.I),
    re.compile(r"\[SYSTEM\]", re.I),
    re.compile(r"\[/SYSTEM\]", re.I),
    re.compile(r"HUMAN:\s*", re.I),
    re.compile(r"ASSISTANT:\s*", re.I),
    re.compile(r"<<SYS>>", re.I),
    re.compile(r"<</SYS>>", re.I),
    re.compile(r"disregard\s+(?:the\s+)?(?:above|previous)", re.I),
    re.compile(r"pretend\s+to\s*be", re.I),
    re.compile(r"act\s+as\s+(?:if\s+)?you\s+are", re.I),
    re.compile(r"you\s+are\s+now\s+(?:in\s+)?\s*(?:developer|debug|admin|root)\s*mode", re.I),
    re.compile(r"DAN\s*\(?Do\s+Anything\s+Now\)?", re.I),
    re.compile(r"jailbreak", re.I),
    re.compile(r"ignore\s+your\s+(?:programming|training|guidelines)", re.I),
    re.compile(r"bypass\s+(?:filters?|restrictions?|rules?)", re.I),
    re.compile(r"\bDAN\b", re.I),
    re.compile(r"\bSTAN\b", re.I),
    re.compile(r"\bDUDE\b", re.I),
    re.compile(r"\b Developer Mode \b", re.I),
    re.compile(r"developer\s+mode\s*:\s*ON", re.I),
    re.compile(r"\balways\b\s+\banswer\b\s+\band\b\s+\bnever\b", re.I),
]

# XSS patterns for output filtering
XSS_PATTERNS = [
    re.compile(r"<script[^>]*>.*?</script>", re.I | re.S),
    re.compile(r"javascript:", re.I),
    re.compile(r"on\w+\s*=\s*['\"]?[^'\"]*['\"]?", re.I),
    re.compile(r"<iframe[^>]*>", re.I),
    re.compile(r"<object[^>]*>", re.I),
    re.compile(r"<embed[^>]*>", re.I),
    re.compile(r"<form[^>]*>", re.I),
    re.compile(r"<base[^>]*>", re.I),
    re.compile(r"<meta[^>]*http-equiv\s*=\s*['\"]refresh['\"]", re.I),
    re.compile(r"<svg[^>]*on\w+", re.I),
    re.compile(r"<img[^>]*on\w+", re.I),
    re.compile(r"<body[^>]*on\w+", re.I),
]


# ─── Input Validation ─────────────────────────────────────────────────────────
def validate_query_string(query: str) -> tuple[bool, Optional[str]]:
    if len(query) > MAX_QUERY_STRING_LEN:
        return False, f"Query string exceeds {MAX_QUERY_STRING_LEN} chars"
    return True, None


def validate_param(key: str, value: str) -> tuple[bool, Optional[str]]:
    if len(value) > MAX_PARAM_LEN:
        return False, f"Parameter '{key}' exceeds {MAX_PARAM_LEN} chars"
    if "\x00" in value or any(ord(c) < 32 and c not in "\t\n\r" for c in value):
        return False, f"Parameter '{key}' contains invalid characters"
    return True, None


def validate_body_size(body: bytes) -> tuple[bool, Optional[str]]:
    if len(body) > MAX_BODY_SIZE:
        return False, f"Request body exceeds {MAX_BODY_SIZE} bytes"
    return True, None


def validate_chat_message(content: str) -> tuple[bool, Optional[str]]:
    if not content or len(content.strip()) == 0:
        return False, "Message cannot be empty"
    if len(content) > MAX_CHAT_MSG_LEN:
        return False, f"Message exceeds {MAX_CHAT_MSG_LEN} chars"
    injection_score = detect_prompt_injection(content)
    if injection_score >= 0.8:
        logger.warning(f"Prompt injection detected (score={injection_score}): {content[:100]}...")
        return False, "Message contains potentially harmful patterns"
    return True, None


def detect_prompt_injection(text: str) -> float:
    matches = 0
    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern.search(text):
            matches += 1
    delimiter_count = text.count("```") + text.count("`") + text.count("<")
    score = min(1.0, (matches * 0.3) + (delimiter_count * 0.005))
    return score


# ─── URL Validation ───────────────────────────────────────────────────────────
def validate_url(url: str, allow_empty: bool = True) -> tuple[bool, Optional[str]]:
    if not url:
        return allow_empty, "URL is empty" if not allow_empty else None
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return False, "Invalid URL format"
    if parsed.scheme and parsed.scheme not in ALLOWED_SCHEMES:
        return False, f"URL scheme '{parsed.scheme}' not allowed"
    hostname = (parsed.hostname or "").lower()
    for blocked in BLOCKED_HOSTS:
        if hostname == blocked or hostname.startswith(blocked):
            return False, f"URL hostname '{hostname}' is blocked"
    if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", hostname):
        ip_parts = list(map(int, hostname.split(".")))
        if (ip_parts[0] == 10 or
            (ip_parts[0] == 172 and 16 <= ip_parts[1] <= 31) or
            (ip_parts[0] == 192 and ip_parts[1] == 168) or
            ip_parts[0] == 127 or
            ip_parts[0] == 0 or
            ip_parts[0] == 169):
            return False, f"Private IP address '{hostname}' is blocked"
    return True, None


def sanitize_url(url: str) -> str:
    if not url:
        return ""
    url = url.strip()
    url = re.sub(r"^javascript:", "", url, flags=re.I)
    url = re.sub(r"^data:", "", url, flags=re.I)
    url = re.sub(r"^vbscript:", "", url, flags=re.I)
    url = url.replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    return url


# ─── Output Encoding ────────────────────────────────────────────────────────────
def escape_html(text: str) -> str:
    if not text:
        return ""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;"))


def detect_xss(text: str) -> tuple[bool, List[str]]:
    violations = []
    for pattern in XSS_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            violations.extend(matches[:3])
    return len(violations) == 0, violations


def sanitize_response_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.I | re.S)
    text = re.sub(r"on\w+\s*=\s*['\"]?[^'\"]*['\"]?", "", text, flags=re.I)
    text = re.sub(r"javascript:\s*[^\s\"'>]+", "", text, flags=re.I)
    text = re.sub(r"<meta[^>]*http-equiv\s*=\s*['\"]refresh['\"][^>]*>", "", text, flags=re.I | re.S)
    text = re.sub(r"<iframe[^>]*>.*?</iframe>", "", text, flags=re.I | re.S)
    return text


# ─── Audit Logging ────────────────────────────────────────────────────────────
_audit_buffer: List[Dict] = []
_audit_buffer_size = 100
_audit_last_flush = time.time()


def audit_log(
    event_type: str,
    request_id: str,
    client_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[Dict] = None,
    severity: str = "info"
) -> None:
    global _audit_buffer, _audit_last_flush
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "request_id": request_id,
        "client_ip": client_ip or "unknown",
        "user_agent": (user_agent or "")[:200],
        "details": details or {},
        "severity": severity,
    }
    _audit_buffer.append(entry)
    if (len(_audit_buffer) >= _audit_buffer_size or
        time.time() - _audit_last_flush > 60):
        _flush_audit_log()


def _flush_audit_log() -> None:
    global _audit_buffer, _audit_last_flush
    if not _audit_buffer:
        return
    for entry in _audit_buffer:
        severity = entry.pop("severity", "info")
        msg = f"AUDIT [{severity.upper()}] {entry['event_type']} | ip={entry['client_ip']} | req={entry['request_id']} | {entry.get('details', {})}"
        if severity == "error":
            logger.error(msg)
        elif severity == "warning":
            logger.warning(msg)
        else:
            logger.info(msg)
    _audit_buffer = []
    _audit_last_flush = time.time()


# ─── Request Signing ────────────────────────────────────────────────────────────
def generate_request_signature(data: str, secret: Optional[str] = None) -> str:
    if secret is None:
        secret = secrets.token_hex(32)
    return hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()[:32]


def verify_request_signature(data: str, signature: str, secret: str) -> bool:
    expected = generate_request_signature(data, secret)
    return hmac.compare_digest(expected, signature)


# ─── Content Security Policy ──────────────────────────────────────────────────
def generate_csp_header(nonce: Optional[str] = None) -> str:
    directives = [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com",
        "img-src 'self' data: blob: https://*.tile.openstreetmap.org https://*.cartocdn.com",
        "connect-src 'self'",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "upgrade-insecure-requests",
    ]
    if nonce:
        directives[1] = f"script-src 'self' 'nonce-{nonce}'"
    return "; ".join(directives)


# ─── Rate Limit Helpers ───────────────────────────────────────────────────────
_rate_limit_store: Dict[str, Dict] = {}


def check_rate_limit(key: str, max_requests: int, window_seconds: int) -> tuple[bool, Dict]:
    now = time.time()
    entry = _rate_limit_store.get(key, {"count": 0, "reset_at": now + window_seconds})
    if now > entry["reset_at"]:
        entry = {"count": 0, "reset_at": now + window_seconds}
    entry["count"] += 1
    _rate_limit_store[key] = entry
    allowed = entry["count"] <= max_requests
    headers = {
        "X-RateLimit-Limit": str(max_requests),
        "X-RateLimit-Remaining": str(max(0, max_requests - entry["count"])),
        "X-RateLimit-Reset": str(int(entry["reset_at"])),
    }
    return allowed, headers


# ─── Startup Data Validation ──────────────────────────────────────────────────
def validate_startup_name(name: str) -> tuple[bool, Optional[str]]:
    if not name or len(name.strip()) < 2:
        return False, "Name must be at least 2 characters"
    if len(name) > 200:
        return False, "Name exceeds 200 characters"
    if any(c in name for c in "';--/*"):
        return False, "Name contains invalid characters"
    return True, None


def validate_coordinates(lat: float, lng: float) -> tuple[bool, Optional[str]]:
    if not (-90 <= lat <= 90):
        return False, f"Invalid latitude: {lat}"
    if not (-180 <= lng <= 180):
        return False, f"Invalid longitude: {lng}"
    return True, None


def validate_funding_amount(amount: Optional[float]) -> tuple[bool, Optional[str]]:
    if amount is None:
        return True, None
    if amount < 0:
        return False, "Funding amount cannot be negative"
    if amount > 1e15:
        return False, "Funding amount exceeds realistic bounds"
    return True, None


def validate_year(year: Optional[int]) -> tuple[bool, Optional[str]]:
    if year is None:
        return True, None
    current_year = datetime.now().year
    if year < 1800 or year > current_year + 1:
        return False, f"Invalid year: {year}"
    return True, None
