"""
SEO Directory Pages — server-rendered HTML with Schema.org structured data.
Mounted at /directory/* in main.py (no API prefix).
v3.2: Uses shared utilities from backend.utils (single source of truth)
"""
from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse
from typing import Optional
import json

from .database import get_db
from .utils import row_to_dict, format_funding


DIRECTORY_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="{description}">
  <meta name="keywords" content="{keywords}">
  <meta name="robots" content="index, follow">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{description}">
  <meta property="og:type" content="website">
  <title>{title} — Bharat Tech Atlas</title>
  <link rel="canonical" href="{canonical}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root{{--bg:#0F172A;--surface:#1E293B;--border:#334155;--text:#F8FAFC;--muted:#94A3B8;--brand:#F97316;}}
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{font-family:'Inter',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}}
    .header{{background:var(--bg);border-bottom:1px solid var(--border);padding:1rem 2rem;display:flex;align-items:center;justify-content:space-between;}}
    .header h1{{font-size:1.1rem;font-weight:800;color:var(--brand)}}
    .header a{{color:var(--muted);text-decoration:none;font-size:0.85rem}}
    .header a:hover{{color:var(--brand)}}
    .hero{{padding:3rem 2rem;text-align:center;border-bottom:1px solid var(--border)}}
    .hero h2{{font-size:2rem;font-weight:800;margin-bottom:0.5rem}}
    .hero p{{color:var(--muted);font-size:1.05rem;max-width:700px;margin:0 auto}}
    .stats{{display:flex;gap:1.5rem;justify-content:center;padding:1.5rem 2rem;flex-wrap:wrap}}
    .stat{{text-align:center;padding:1rem 1.5rem;background:var(--surface);border-radius:12px;border:1px solid var(--border)}}
    .stat .num{{font-size:1.4rem;font-weight:700;color:var(--brand)}}
    .stat .label{{font-size:0.75rem;color:var(--muted);margin-top:0.25rem;text-transform:uppercase;letter-spacing:0.5px}}
    .container{{max-width:1100px;margin:0 auto;padding:2rem}}
    .section-title{{font-size:1.1rem;font-weight:700;margin-bottom:1rem;color:var(--muted);text-transform:uppercase;letter-spacing:0.5px}}
    .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:1rem}}
    .card{{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:1.25rem;transition:transform 0.15s,border-color 0.15s}}
    .card:hover{{transform:translateY(-2px);border-color:rgba(249,115,22,0.4)}}
    .card-header{{display:flex;align-items:center;gap:0.75rem;margin-bottom:0.5rem}}
    .card-type{{font-size:0.7rem;font-weight:600;text-transform:uppercase;padding:0.25rem 0.5rem;border-radius:6px}}
    .startup{{background:rgba(59,130,246,0.15);color:#60A5FA}}
    .sme{{background:rgba(16,185,129,0.15);color:#34D399}}
    .ecell{{background:rgba(251,191,36,0.15);color:#FBBF24}}
    .incubator{{background:rgba(168,85,247,0.15);color:#A855F7}}
    .card h3{{font-size:1rem;font-weight:600;margin-bottom:0.25rem}}
    .card p.desc{{font-size:0.8rem;color:var(--muted);margin-bottom:0.75rem;line-height:1.4}}
    .card .meta{{font-size:0.75rem;color:var(--muted);display:flex;gap:1rem;flex-wrap:wrap}}
    .badge{{font-size:0.7rem;padding:0.2rem 0.5rem;border-radius:4px;font-weight:500}}
    .unicorn-badge{{color:var(--brand);font-weight:600}}
    .women-badge{{background:rgba(236,72,153,0.15);color:#F472B6}}
    .rural-badge{{background:rgba(34,197,94,0.15);color:#4ADE80}}
    .dpiit-badge{{background:rgba(59,130,246,0.15);color:#60A5FA}}
    .cta{{text-align:center;padding:2rem;border-top:1px solid var(--border)}}
    .cta a{{display:inline-block;background:var(--brand);color:white;padding:0.75rem 1.5rem;border-radius:10px;text-decoration:none;font-weight:600;font-size:0.9rem}}
    .cta a:hover{{opacity:0.9}}
    .breadcrumb{{padding:0.75rem 2rem;font-size:0.8rem;color:var(--muted);border-bottom:1px solid var(--border)}}
    .breadcrumb a{{color:var(--brand);text-decoration:none}}
    .breadcrumb span{{color:var(--muted);margin:0 0.3rem}}
    footer{{padding:1.5rem;text-align:center;color:var(--muted);font-size:0.8rem;border-top:1px solid var(--border)}}
    .filter-nav{{display:flex;gap:0.75rem;flex-wrap:wrap;margin-bottom:1.5rem;}}
    .filter-nav a{{font-size:0.8rem;padding:0.4rem 0.8rem;border-radius:8px;background:var(--surface);border:1px solid var(--border);color:var(--muted);text-decoration:none}}
    .filter-nav a.active{{border-color:var(--brand);color:var(--brand)}}
  </style>
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "ItemList",
    "itemListElement": {json_list}
  }}
  </script>
</head>
<body>
  <header class="header">
    <h1>Bharat Tech Atlas</h1>
    <a href="/">🗺️ Open Interactive Map</a>
  </header>
  <nav class="breadcrumb">
    <a href="/">Home</a><span>/</span><a href="/directory/startups">Startups</a><span>/</span><span>{breadcrumb_last}</span>
  </nav>
  <div class="hero">
    <h2>{title}</h2>
    <p>{description}</p>
  </div>
  <div class="stats">
    {stats_html}
  </div>
  <div class="container">
    <div class="filter-nav">
      {filter_nav}
    </div>
    <div class="section-title">{list_title}</div>
    <div class="grid">
      {cards_html}
    </div>
    <div class="cta">
      <a href="/">🗺️ Explore the full interactive map</a>
    </div>
  </div>
  <footer>
    Bharat Tech Atlas — Curated dataset. India has 223,000+ DPIIT-registered startups.
    Source: DPIIT, Tracxn, Crunchbase. Data may not reflect real-time changes.
  </footer>
</body>
</html>"""


def _build_directory_page(title, description, keywords, canonical, breadcrumb_last,
                          stats_html, cards_html, list_title, filter_nav, json_list="[]"):
    return DIRECTORY_HTML_TEMPLATE.format(
        title=title,
        description=description,
        keywords=keywords,
        canonical=canonical,
        breadcrumb_last=breadcrumb_last,
        stats_html=stats_html,
        cards_html=cards_html,
        list_title=list_title,
        filter_nav=filter_nav,
        json_list=json_list,
    )


def _build_card(e):
    badges = ""
    if e.get("unicorn_status") == "unicorn":
        badges += '<span class="badge unicorn-badge">🦄 Unicorn</span>'
    if e.get("is_women_led"):
        badges += '<span class="badge women-badge">👩 Women-led</span>'
    if e.get("is_rural_impact"):
        badges += '<span class="badge rural-badge">🌾 Rural Impact</span>'
    if e.get("dpiit_recognized"):
        badges += '<span class="badge dpiit-badge">🏛️ DPIIT</span>'

    t = e.get("entity_type", "startup")
    t_class = {"startup": "startup", "sme": "sme", "college_ecell": "ecell",
                 "incubator": "incubator", "accelerator": "incubator"}.get(t, "startup")
    t_label = {"startup": "Startup", "sme": "SME", "college_ecell": "E-Cell",
               "incubator": "Incubator", "accelerator": "Accelerator"}.get(t, "Startup")

    funding = format_funding(e.get("funding_inr", 0) or 0)
    desc = e.get("description", "") or ""
    if len(desc) > 140:
        desc = desc[:137] + "..."

    meta_items = []
    if e.get("city"):
        meta_items.append(f"📍 {e['city']}, {e.get('state', '')}")
    if e.get("founded_year"):
        meta_items.append(f"📅 {e['founded_year']}")
    if funding != "Bootstrapped":
        meta_items.append(f"💰 {funding}")

    meta = " &nbsp;|&nbsp; ".join(meta_items)

    return f"""<div class="card">
      <div class="card-header">
        <span class="card-type {t_class}">{t_label}</span>
        {badges}
      </div>
      <h3>{e.get('name', '')}</h3>
      <p class="desc">{desc}</p>
      <div class="meta">{meta}</div>
    </div>"""


def _build_json_ld(items):
    arr = []
    for i, e in enumerate(items):
        arr.append({
            "@type": "ListItem",
            "position": i + 1,
            "item": {
                "@type": "Organization",
                "name": e.get("name", ""),
                "description": e.get("description", "") or "",
                "url": e.get("website", ""),
                "address": {"@type": "PostalAddress", "addressLocality": e.get("city", ""), "addressRegion": e.get("state", "")},
            }
        })
    return json.dumps(arr)


router = APIRouter()


@router.get("/startups", response_class=HTMLResponse)
async def directory_startups_root():
    conn = get_db()

    # Live stats from DB
    total_startups = conn.execute("SELECT COUNT(*) FROM entities WHERE entity_type='startup' AND is_active=1").fetchone()[0]
    unicorn_count = conn.execute("SELECT COUNT(*) FROM entities WHERE unicorn_status='unicorn' AND is_active=1").fetchone()[0]
    women_count = conn.execute("SELECT COUNT(*) FROM entities WHERE is_women_led=1 AND is_active=1").fetchone()[0]
    city_count = conn.execute("SELECT COUNT(DISTINCT city) FROM entities WHERE is_active=1").fetchone()[0]

    rows = conn.execute("""
        SELECT * FROM entities
        WHERE entity_type = 'startup' AND is_active = 1
        ORDER BY funding_inr DESC, founded_year DESC
        LIMIT 100
    """).fetchall()
    conn.close()

    items = [row_to_dict(r) for r in rows]

    stats_html = f"""
    <div class="stat"><div class="num">{total_startups:,}</div><div class="label">Startups</div></div>
    <div class="stat"><div class="num">{unicorn_count}</div><div class="label">Unicorns</div></div>
    <div class="stat"><div class="num">{city_count}+</div><div class="label">Cities</div></div>
    <div class="stat"><div class="num">{women_count}</div><div class="label">Women-led</div></div>
    """

    filter_nav = "".join([
        f'<a href="/directory/startups/{s}">{s}</a>'
        for s in ["Karnataka", "Maharashtra", "Delhi", "Tamil Nadu", "Telangana", "Gujarat", "Kerala", "Rajasthan", "Uttar Pradesh", "West Bengal"]
    ])

    cards = "".join(_build_card(e) for e in items)

    html = _build_directory_page(
        title="Indian Startups Directory",
        description=f"Curated directory of {total_startups:,}+ Indian startups — {unicorn_count} unicorns, funded companies, and emerging ventures across fintech, SaaS, AI, edtech, healthtech and more. India has 223,000+ DPIIT-registered startups.",
        keywords="Indian startups, India startup directory, unicorn startups India, funded startups, DPIIT startups, tech startups Bangalore, Mumbai startups",
        canonical="https://huggingface.co/spaces/Ram2005/StartupMap-India/directory/startups",
        breadcrumb_last="Startups",
        stats_html=stats_html,
        cards_html=cards,
        list_title="Top Startups by Funding",
        filter_nav=filter_nav,
        json_list=_build_json_ld(items),
    )
    return html


@router.get("/startups/{state}", response_class=HTMLResponse)
async def directory_startups_by_state(state: str):
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM entities
        WHERE entity_type = 'startup' AND state = ? AND is_active = 1
        ORDER BY funding_inr DESC, founded_year DESC
        LIMIT 80
    """, (state,)).fetchall()
    conn.close()

    items = [row_to_dict(r) for r in rows]
    if not items:
        return HTMLResponse(content=f"<h1>No startups found in {state}</h1>", status_code=404)

    count = len(items)
    unicorns = sum(1 for e in items if e.get("unicorn_status") == "unicorn")
    women = sum(1 for e in items if e.get("is_women_led"))
    dpiit = sum(1 for e in items if e.get("dpiit_recognized"))

    stats_html = f"""
    <div class="stat"><div class="num">{count}</div><div class="label">Startups</div></div>
    <div class="stat"><div class="num">{unicorns}</div><div class="label">Unicorns</div></div>
    <div class="stat"><div class="num">{women}</div><div class="label">Women-led</div></div>
    <div class="stat"><div class="num">{dpiit}</div><div class="label">DPIIT</div></div>
    """

    cards = "".join(_build_card(e) for e in items)

    html = _build_directory_page(
        title=f"Startups in {state}",
        description=f"Explore {count}+ startups in {state}, India — including unicorns, funded companies, and DPIIT-recognized ventures in fintech, SaaS, AI, healthcare and more.",
        keywords=f"startups {state}, {state} startups, {state} tech companies, {state} unicorns, {state} DPIIT",
        canonical=f"https://huggingface.co/spaces/Ram2005/StartupMap-India/directory/startups/{state}",
        breadcrumb_last=state,
        stats_html=stats_html,
        cards_html=cards,
        list_title=f"Top Startups in {state}",
        filter_nav="",
        json_list=_build_json_ld(items),
    )
    return html


@router.get("/startups/{state}/{sector}", response_class=HTMLResponse)
async def directory_startups_by_state_sector(state: str, sector: str):
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM entities
        WHERE entity_type = 'startup' AND state = ? AND (sectors LIKE ? OR dpiit_category = ?) AND is_active = 1
        ORDER BY funding_inr DESC, founded_year DESC
        LIMIT 80
    """, (state, f'%"{sector}"%', sector)).fetchall()
    conn.close()

    items = [row_to_dict(r) for r in rows]
    if not items:
        return HTMLResponse(content=f"<h1>No {sector} startups found in {state}</h1>", status_code=404)

    count = len(items)
    unicorns = sum(1 for e in items if e.get("unicorn_status") == "unicorn")

    stats_html = f"""
    <div class="stat"><div class="num">{count}</div><div class="label">{sector.title()} Startups</div></div>
    <div class="stat"><div class="num">{unicorns}</div><div class="label">Unicorns</div></div>
    """

    cards = "".join(_build_card(e) for e in items)

    html = _build_directory_page(
        title=f"{sector.title()} Startups in {state}",
        description=f"Discover {count}+ {sector.title()} startups in {state}, India — unicorns, funded ventures, and emerging companies in the {sector} ecosystem.",
        keywords=f"{sector} startups {state}, {state} {sector} companies, {sector} India, {sector} ecosystem {state}",
        canonical=f"https://huggingface.co/spaces/Ram2005/StartupMap-India/directory/startups/{state}/{sector}",
        breadcrumb_last=f"{state} / {sector.title()}",
        stats_html=stats_html,
        cards_html=cards,
        list_title=f"{sector.title()} Startups in {state}",
        filter_nav="",
        json_list=_build_json_ld(items),
    )
    return html


@router.get("/unicorns", response_class=HTMLResponse)
async def directory_unicorns():
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM entities
        WHERE unicorn_status = 'unicorn' AND is_active = 1
        ORDER BY funding_inr DESC
        LIMIT 150
    """).fetchall()

    # Live valuation from DB
    val_row = conn.execute("SELECT SUM(valuation_usd) FROM entities WHERE unicorn_status='unicorn' AND is_active=1").fetchone()
    total_valuation_b = round((val_row[0] or 0) / 1e9)
    city_count = conn.execute("SELECT COUNT(DISTINCT city) FROM entities WHERE unicorn_status='unicorn' AND is_active=1").fetchone()[0]
    sector_count = conn.execute("SELECT COUNT(DISTINCT dpiit_category) FROM entities WHERE unicorn_status='unicorn' AND is_active=1").fetchone()[0]
    conn.close()

    items = [row_to_dict(r) for r in rows]

    stats_html = f"""
    <div class="stat"><div class="num">{len(items)}</div><div class="label">Unicorns</div></div>
    <div class="stat"><div class="num">{city_count}+</div><div class="label">Cities</div></div>
    <div class="stat"><div class="num">{sector_count}+</div><div class="label">Sectors</div></div>
    <div class="stat"><div class="num">${total_valuation_b}B+</div><div class="label">Combined Valuation</div></div>
    """

    filter_nav = "".join([
        f'<a href="/directory/unicorns/{s}">{s.title()}</a>'
        for s in ["fintech", "ecommerce", "saas", "healthtech", "edtech", "foodtech", "gaming", "mobility", "proptech", "ai_ml"]
    ])

    cards = "".join(_build_card(e) for e in items)

    html = _build_directory_page(
        title="Indian Unicorns",
        description=f"Directory of {len(items)} Indian unicorn startups — from Flipkart and PhonePe to newer entrants like Zepto and Neysa. Valuations, funding, investors, and locations.",
        keywords="Indian unicorns, Indian unicorn startups, India unicorn list, Flipkart, PhonePe, Zepto, Zomato, Swiggy, unicorn valuation",
        canonical="https://huggingface.co/spaces/Ram2005/StartupMap-India/directory/unicorns",
        breadcrumb_last="Unicorns",
        stats_html=stats_html,
        cards_html=cards,
        list_title="All Indian Unicorns",
        filter_nav=filter_nav,
        json_list=_build_json_ld(items),
    )
    return html


@router.get("/unicorns/{sector}", response_class=HTMLResponse)
async def directory_unicorns_by_sector(sector: str):
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM entities
        WHERE unicorn_status = 'unicorn' AND is_active = 1 AND (sectors LIKE ? OR dpiit_category = ?)
        ORDER BY funding_inr DESC
        LIMIT 50
    """, (f'%"{sector}"%', sector)).fetchall()
    conn.close()

    items = [row_to_dict(r) for r in rows]
    if not items:
        return HTMLResponse(content=f"<h1>No {sector} unicorns found</h1>", status_code=404)

    stats_html = f"""
    <div class="stat"><div class="num">{len(items)}</div><div class="label">{sector.title()} Unicorns</div></div>
    """

    cards = "".join(_build_card(e) for e in items)

    html = _build_directory_page(
        title=f"{sector.title()} Unicorns in India",
        description=f"Complete list of {sector.title()} unicorns in India — valuations, funding, investors, and city locations.",
        keywords=f"{sector} unicorns India, {sector} unicorn startups, India {sector} unicorn companies",
        canonical=f"https://huggingface.co/spaces/Ram2005/StartupMap-India/directory/unicorns/{sector}",
        breadcrumb_last=f"Unicorns / {sector.title()}",
        stats_html=stats_html,
        cards_html=cards,
        list_title=f"{sector.title()} Unicorns",
        filter_nav="",
        json_list=_build_json_ld(items),
    )
    return html
