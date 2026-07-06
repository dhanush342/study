import React, { useState } from 'react'
import { X, Globe, ExternalLink } from 'lucide-react'

const ENTITY_COLORS = {
  startup: '#3B82F6', sme: '#10B981', college_ecell: '#FBBF24',
  incubator: '#A855F7', accelerator: '#EC4899',
}
const ENTITY_LABELS = {
  startup: '🚀 Startup', sme: '🏢 SME', college_ecell: '🎓 E-Cell',
  incubator: '🧪 Incubator', accelerator: '⚡ Accelerator',
}

function formatFunding(v) {
  if (!v || v === 0) return 'Bootstrapped'
  const cr = v / 10000000
  if (cr >= 10000) return `₹${(cr/100000).toFixed(2)} Lakh Cr`
  if (cr >= 100) return `₹${cr.toLocaleString('en-IN', { maximumFractionDigits: 0 })} Cr`
  if (cr >= 1) return `₹${cr.toFixed(1)} Cr`
  return `₹${(v/100000).toFixed(0)} L`
}

// ─── URL Validation ───────────────────────────────────────────────────────────
function isValidHttpUrl(url) {
  if (!url || typeof url !== 'string') return false
  try {
    const u = new URL(url.trim())
    const protocol = u.protocol.toLowerCase()
    if (protocol !== 'http:' && protocol !== 'https:') return false
    const hostname = u.hostname.toLowerCase()
    // Block private IPs and localhost
    if (hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '0.0.0.0') return false
    if (hostname.startsWith('192.168.') || hostname.startsWith('10.')) return false
    if (hostname.startsWith('172.')) {
      const parts = hostname.split('.')
      if (parts.length >= 2) {
        const second = parseInt(parts[1], 10)
        if (second >= 16 && second <= 31) return false
      }
    }
    return true
  } catch {
    return false
  }
}

function sanitizeUrl(url) {
  if (!url || typeof url !== 'string') return ''
  const trimmed = url.trim()
  const lower = trimmed.toLowerCase()
  if (lower.startsWith('javascript:') || lower.startsWith('data:') || lower.startsWith('vbscript:')) {
    return ''
  }
  return trimmed
}

const SOCIAL_CONFIG = {
  linkedin: { icon: '💼', color: '#0A66C2', label: 'LinkedIn' },
  twitter: { icon: '𝕏', color: '#000000', label: 'X (Twitter)' },
  instagram: { icon: '📸', color: '#E4405F', label: 'Instagram' },
  facebook: { icon: '📘', color: '#1877F2', label: 'Facebook' },
  website: { icon: '🌐', color: '#6366F1', label: 'Website' },
  crunchbase: { icon: 'CB', color: '#0288D1', label: 'Crunchbase' },
  tracxn: { icon: 'TX', color: '#FF6F00', label: 'Tracxn' },
  google: { icon: '🔍', color: '#4285F4', label: 'Google Search' },
}

function SocialLinksGrid({ entity }) {
  const links = []
  const name = entity.name

  if (entity.linkedin_url && isValidHttpUrl(entity.linkedin_url)) {
    links.push({ ...SOCIAL_CONFIG.linkedin, url: sanitizeUrl(entity.linkedin_url), verified: true })
  }
  if (entity.twitter_url && isValidHttpUrl(entity.twitter_url)) {
    links.push({ ...SOCIAL_CONFIG.twitter, url: sanitizeUrl(entity.twitter_url), verified: true })
  }
  if (entity.instagram_url && isValidHttpUrl(entity.instagram_url)) {
    links.push({ ...SOCIAL_CONFIG.instagram, url: sanitizeUrl(entity.instagram_url), verified: true })
  }
  if (entity.facebook_url && isValidHttpUrl(entity.facebook_url)) {
    links.push({ ...SOCIAL_CONFIG.facebook, url: sanitizeUrl(entity.facebook_url), verified: true })
  }
  if (entity.website && isValidHttpUrl(entity.website)) {
    links.push({ ...SOCIAL_CONFIG.website, url: sanitizeUrl(entity.website), verified: true })
  }

  // Search links (always available, constructed safely)
  const slug = name.toLowerCase().replace(/\s+/g, '-').replace('.', '')
  const encName = encodeURIComponent(name)
  if (!entity.linkedin_url) links.push({ ...SOCIAL_CONFIG.linkedin, url: `https://www.linkedin.com/search/results/companies/?keywords=${encName}`, search: true })
  if (!entity.twitter_url) links.push({ ...SOCIAL_CONFIG.twitter, url: `https://x.com/search?q=${encName}&src=typed_query`, search: true })
  if (!entity.instagram_url) links.push({ ...SOCIAL_CONFIG.instagram, url: `https://www.instagram.com/${slug}`, search: true })
  if (!entity.website) links.push({ ...SOCIAL_CONFIG.website, url: `https://www.google.com/search?q=${encName}+company`, search: true })
  links.push({ ...SOCIAL_CONFIG.crunchbase, url: `https://www.crunchbase.com/organization/${slug}`, search: true })
  links.push({ ...SOCIAL_CONFIG.tracxn, url: `https://tracxn.com/d/companies/${slug}/`, search: true })
  links.push({ ...SOCIAL_CONFIG.google, url: `https://www.google.com/search?q=${encName}+startup+India+news+2024+2025`, search: true })

  return (
    <div className="grid grid-cols-4 gap-1.5">
      {links.filter(l => isValidHttpUrl(l.url)).map(l => (
        <a key={l.label + l.url}
          href={l.url}
          target="_blank"
          rel="noopener noreferrer"
          title={`${l.label}${l.search ? ' (search)' : ''}`}
          className="flex flex-col items-center gap-1 p-2 rounded-lg hover:bg-atlas-surface transition-colors group"
        >
          <span className="text-lg" style={{ color: l.color }}>{l.icon}</span>
          <span className="text-[9px] text-atlas-muted group-hover:text-atlas-text text-center leading-tight">{l.label}</span>
          {l.verified && <span className="w-1 h-1 rounded-full bg-emerald-400" title="Verified" />}
        </a>
      ))}
    </div>
  )
}

function AIAnalysisSection({ entity }) {
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(false)

  const runAnalysis = async () => {
    setLoading(true)
    try {
      const resp = await fetch('/api/agent/analyze-startup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company_name: entity.name,
          sector: Array.isArray(entity.sectors) ? entity.sectors[0] : entity.dpiit_category || '',
          city: entity.city || '',
        }),
      })
      const data = await resp.json()
      setAnalysis(data)
    } catch (e) {
      setAnalysis({ summary: 'Analysis temporarily unavailable. Try again later.', latest_news: [], confidence: 'low' })
    }
    setLoading(false)
  }

  return (
    <div className="border-t border-atlas-border/30 pt-3">
      {!analysis && (
        <button onClick={runAnalysis} disabled={loading}
          className="w-full flex items-center justify-center gap-2 py-2 rounded-lg bg-brand-500/10 text-brand-400 hover:bg-brand-500/20 transition-colors text-xs font-medium">
          {loading ? (
            <><span className="w-3 h-3 border-2 border-brand-400 border-t-transparent rounded-full animate-spin" /> Analyzing...</>
          ) : (
            <><span>🤖</span> AI Web Analysis — Latest News & Trends</>
          )}
        </button>
      )}
      {analysis && (
        <div className="space-y-2">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold text-atlas-muted">🤖 AI Analysis</span>
            <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${
              analysis.confidence === 'high' ? 'bg-emerald-500/15 text-emerald-300' :
              analysis.confidence === 'medium' ? 'bg-amber-500/15 text-amber-300' :
              'bg-red-500/15 text-red-300'
            }`}>{analysis.confidence} confidence</span>
          </div>
          <p className="text-xs text-atlas-muted leading-relaxed">{analysis.summary}</p>
          {analysis.latest_news?.length > 0 && (
            <div className="space-y-1.5">
              <span className="text-[10px] font-semibold text-atlas-muted/70 uppercase">Latest News</span>
              {analysis.latest_news.slice(0, 3).map((n, i) => (
                <a key={i} href={n.url} target="_blank" rel="noopener noreferrer"
                  className="block text-xs text-brand-400 hover:text-brand-300 hover:bg-brand-500/5 rounded px-2 py-1.5 transition-colors truncate">
                  • {n.title}
                </a>
              ))}
            </div>
          )}
          <button onClick={() => setAnalysis(null)}
            className="text-[10px] text-atlas-muted/60 hover:text-atlas-muted transition-colors">
            ↻ Run again
          </button>
        </div>
      )}
    </div>
  )
}

export default function EntityDetail({ entity, onClose, onEntityClick, isMobile }) {
  if (!entity) return null

  const e = entity
  const color = ENTITY_COLORS[e.entity_type] || '#64748B'
  const label = ENTITY_LABELS[e.entity_type] || e.entity_type
  const sectors = Array.isArray(e.sectors) ? e.sectors : []
  const investors = Array.isArray(e.investors) ? e.investors : []
  const nearby = Array.isArray(e.nearby) ? e.nearby : []

  return (
    <div className={
      isMobile
        ? "fixed inset-x-0 bottom-0 z-40 max-h-[80vh] pointer-events-auto animate-slide-up"
        : "absolute top-16 right-3 bottom-4 w-96 z-30 animate-slide-in-right pointer-events-none"
    }>
      <div className={
        isMobile
          ? "bg-atlas-bg/95 border-t border-atlas-border rounded-t-2xl shadow-2xl flex flex-col overflow-hidden max-h-[80vh]"
          : "glass rounded-2xl shadow-2xl flex flex-col overflow-hidden pointer-events-auto max-h-full"
      }>
        {/* Header */}
        <div className="relative px-5 pt-5 pb-4 border-b border-atlas-border flex-shrink-0"
             style={{ borderTop: `3px solid ${color}` }}>
          <button onClick={onClose}
            className="absolute top-3 right-3 p-1.5 hover:bg-atlas-surface rounded-lg transition-colors">
            <X size={18} className="text-atlas-muted" />
          </button>

          <div className="flex items-start gap-3">
            <div className="w-12 h-12 rounded-xl bg-atlas-surface flex items-center justify-center text-2xl border border-atlas-border">
              {e.entity_type === 'startup' ? '🚀' : e.entity_type === 'sme' ? '🏢' :
               e.entity_type === 'college_ecell' ? '🎓' : e.entity_type === 'incubator' ? '🧪' : '⚡'}
            </div>
            <div className="flex-1">
              <h2 className="text-lg font-bold text-atlas-text leading-tight">{e.name}</h2>
              <p className="text-sm text-atlas-muted mt-0.5">📍 {e.city}, {e.state}</p>
              <span className="inline-block text-xs font-medium px-2 py-0.5 rounded-full mt-1"
                    style={{ backgroundColor: `${color}20`, color }}>
                {label}
              </span>
            </div>
          </div>

          {/* Badges */}
          <div className="flex flex-wrap gap-1.5 mt-3">
            {e.dpiit_recognized && <Badge text="✅ Verified (DPIIT)" cls="bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-500/20" />}
            {e.unicorn_status === 'unicorn' && <Badge text="🦄 Unicorn" cls="bg-purple-500/20 text-purple-300" />}
            {e.unicorn_status === 'soonicorn' && <Badge text="🌟 Soonicorn" cls="bg-purple-500/15 text-purple-300" />}
            {e.is_women_led && <Badge text="👩 Women-led" cls="bg-pink-500/15 text-pink-300" />}
            {e.is_rural_impact && <Badge text="🌾 Rural Impact" cls="bg-green-500/15 text-green-300" />}
            {e.is_campus_startup && <Badge text="🎓 Campus" cls="bg-blue-500/15 text-blue-300" />}
            {e.nsa_winner && <Badge text="🏆 NSA Winner" cls="bg-amber-500/15 text-amber-300" />}
            {!e.dpiit_recognized && <Badge text="⚠️ Unverified" cls="bg-atlas-surface text-atlas-muted/60" />}
          </div>
        </div>

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4 scrollbar-thin">
          {/* Social Media Links */}
          <div>
            <h4 className="text-xs font-semibold text-atlas-muted uppercase tracking-wider mb-2">Social & Profiles</h4>
            <SocialLinksGrid entity={e} />
          </div>

          {/* Description */}
          {e.description && (
            <p className="text-sm text-atlas-muted leading-relaxed">{e.description}</p>
          )}

          {/* Key Metrics */}
          <div className="grid grid-cols-3 gap-2">
            <MetricCard label="Founded" value={e.founded_year || '—'} icon="📅" />
            <MetricCard label="Team" value={e.linkedin_team_size || e.employee_count || '—'} icon="👥" />
            <MetricCard label="Funding" value={formatFunding(e.funding_inr)} icon="💰" />
          </div>

          {/* Sectors */}
          {sectors.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-atlas-muted uppercase tracking-wider mb-2">Sectors</h4>
              <div className="flex flex-wrap gap-1.5">
                {sectors.map(s => (
                  <span key={s} className="text-xs bg-atlas-surface text-atlas-muted px-2.5 py-1 rounded-lg border border-atlas-border">{s}</span>
                ))}
              </div>
            </div>
          )}

          {/* Additional Info */}
          <div className="space-y-2">
            {e.stage && <InfoRow label="Stage" value={e.stage.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())} />}
            {e.business_model && <InfoRow label="Business Model" value={e.business_model.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())} />}
            {e.dpiit_category && <InfoRow label="DPIIT Category" value={e.dpiit_category} />}
            {e.college_name && <InfoRow label="College" value={e.college_name} />}
            {e.funding_stage && <InfoRow label="Funding Stage" value={e.funding_stage} />}
            {e.valuation_usd && <InfoRow label="Valuation" value={`$${(e.valuation_usd / 1e9).toFixed(1)}B`} />}
          </div>

          {/* Investors */}
          {investors.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-atlas-muted uppercase tracking-wider mb-2">Investors</h4>
              <div className="flex flex-wrap gap-1.5">
                {investors.map((inv, i) => (
                  <span key={i} className="text-xs bg-indigo-500/10 text-indigo-300 px-2.5 py-1 rounded-lg">{inv}</span>
                ))}
              </div>
            </div>
          )}

          {/* AI Web Analysis */}
          <AIAnalysisSection entity={e} />

          {/* Nearby Entities */}
          {nearby.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-atlas-muted uppercase tracking-wider mb-2">Nearby ({nearby.length})</h4>
              <div className="space-y-1">
                {nearby.slice(0, 5).map(n => (
                  <button key={n.id} onClick={() => onEntityClick(n.slug)}
                    className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-atlas-surface transition-colors text-left">
                    <span className="text-sm">
                      {n.entity_type === 'startup' ? '🚀' : n.entity_type === 'sme' ? '🏢' : '🧪'}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-atlas-text truncate">{n.name}</p>
                      <p className="text-[10px] text-atlas-muted">{n.city} • {n.distance_km} km</p>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Report Error */}
          <div className="pt-2 border-t border-atlas-border/30">
            <a
              href={`mailto:ram2005.dev@gmail.com?subject=Data%20Error%20Report%3A%20${encodeURIComponent(e.name)}&body=Entity%3A%20${encodeURIComponent(e.name)}%0ASlug%3A%20${encodeURIComponent(e.slug)}%0A%0AWhat%20is%20incorrect%3A%0A`}
              className="flex items-center justify-center gap-1.5 text-xs text-atlas-muted/60 hover:text-red-400 transition-colors py-2 rounded-lg hover:bg-red-500/5"
            >
              <span>🚩</span>
              <span>Report an error in this data</span>
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}

function Badge({ text, cls }) {
  return <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${cls}`}>{text}</span>
}

function MetricCard({ label, value, icon }) {
  return (
    <div className="bg-atlas-surface/60 border border-atlas-border/50 rounded-xl px-3 py-2.5 text-center">
      <span className="text-base">{icon}</span>
      <p className="text-sm font-bold text-atlas-text mt-1 leading-none">{value}</p>
      <p className="text-[10px] text-atlas-muted mt-1 uppercase">{label}</p>
    </div>
  )
}

function InfoRow({ label, value }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-atlas-muted">{label}</span>
      <span className="text-atlas-text font-medium">{value}</span>
    </div>
  )
}
