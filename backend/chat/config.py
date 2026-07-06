"""
Bharat Tech Atlas — Chat Configuration
Centralized constants for the AI chat system.
"""

# ─── Model config ─────────────────────────────────────────────────────────────
MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
MAX_NEW_TOKENS = 512
TEMPERATURE = 0.7
TOP_P = 0.9
DEVICE_GPU = 0
DEVICE_CPU = -1
MAX_CHAT_MSG_LEN = 4000

# ─── System prompts ───────────────────────────────────────────────────────────
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

# ─── Keyword responses (fast, no model load) ──────────────────────────────────
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

# ─── Web search triggers ──────────────────────────────────────────────────────
NEEDS_SEARCH_TRIGGERS = [
    "latest", "news", "recent", "2024", "2025", "today", "this week", "this month",
    "just raised", "funding round", "acquired", "IPO", "valuation", "layoff", "shutdown",
]

# ─── Search config ──────────────────────────────────────────────────────────────
WEB_SEARCH_MAX_RESULTS = 6
WEB_SEARCH_QUERY_PREFIX = "Indian startup"
