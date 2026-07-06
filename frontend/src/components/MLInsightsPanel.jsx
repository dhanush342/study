import React, { useState, useCallback, useEffect } from 'react'
import { X, Zap, TrendingUp, Brain, AlertTriangle, CheckCircle } from 'lucide-react'

/**
 * MLInsightsPanel — Interactive ML features panel.
 * - Sector classification: type a description → get predicted sector
 * - Growth predictions: view top startups ranked by growth potential
 * - MLOps health: live model status and drift alerts
 */
export default function MLInsightsPanel({ onClose, onEntityClick }) {
  const [activeTab, setActiveTab] = useState('growth')

  return (
    <div className="fixed inset-y-0 right-0 w-full sm:w-[420px] z-30 pointer-events-auto animate-slide-in-right">
      <div className="h-full bg-atlas-bg/95 backdrop-blur-sm border-l border-atlas-border shadow-2xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-atlas-border flex-shrink-0">
          <div className="flex items-center gap-2">
            <Brain size={18} className="text-brand-500" />
            <span className="text-sm font-bold text-atlas-text">ML Insights</span>
            <span className="text-[10px] bg-brand-500/20 text-brand-400 px-1.5 py-0.5 rounded-full font-medium">LIVE</span>
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-atlas-surface rounded-lg">
            <X size={16} className="text-atlas-muted" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-atlas-border flex-shrink-0">
          {[
            { id: 'growth', label: 'Growth Predictions', icon: TrendingUp },
            { id: 'classify', label: 'Sector Classifier', icon: Brain },
            { id: 'health', label: 'Model Health', icon: Zap },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2.5 text-xs font-medium transition-colors ${
                activeTab === tab.id
                  ? 'text-brand-500 border-b-2 border-brand-500 bg-brand-500/5'
                  : 'text-atlas-muted hover:text-atlas-text'
              }`}
            >
              <tab.icon size={13} />
              <span className="hidden sm:inline">{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {activeTab === 'growth' && <GrowthTab onEntityClick={onEntityClick} />}
          {activeTab === 'classify' && <ClassifyTab />}
          {activeTab === 'health' && <HealthTab />}
        </div>
      </div>
    </div>
  )
}


// ─── Growth Predictions Tab ─────────────────────────────────────────────────

function GrowthTab({ onEntityClick }) {
  const [predictions, setPredictions] = useState([])
  const [loading, setLoading] = useState(false)
  const [filters, setFilters] = useState({ sector: '', state: '' })

  const fetchPredictions = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ limit: '15' })
      if (filters.sector) params.set('sector', filters.sector)
      if (filters.state) params.set('state', filters.state)
      const resp = await fetch(`/api/ml/predict/growth?${params}`)
      const data = await resp.json()
      setPredictions(data.predictions || [])
    } catch (err) {
      console.error('Growth prediction failed:', err)
    }
    setLoading(false)
  }, [filters])

  useEffect(() => { fetchPredictions() }, [fetchPredictions])

  return (
    <div className="p-4 space-y-4">
      {/* Filters */}
      <div className="flex gap-2">
        <select
          value={filters.sector}
          onChange={(e) => setFilters(f => ({ ...f, sector: e.target.value }))}
          className="flex-1 px-2 py-1.5 rounded-lg bg-atlas-surface border border-atlas-border text-xs text-atlas-text"
        >
          <option value="">All Sectors</option>
          <option value="fintech">FinTech</option>
          <option value="ai_ml">AI / ML</option>
          <option value="saas_ai">SaaS</option>
          <option value="healthtech">HealthTech</option>
          <option value="edtech">EdTech</option>
          <option value="ecommerce">E-Commerce</option>
          <option value="cleantech">CleanTech</option>
          <option value="deeptech">DeepTech</option>
        </select>
        <select
          value={filters.state}
          onChange={(e) => setFilters(f => ({ ...f, state: e.target.value }))}
          className="flex-1 px-2 py-1.5 rounded-lg bg-atlas-surface border border-atlas-border text-xs text-atlas-text"
        >
          <option value="">All States</option>
          <option value="Karnataka">Karnataka</option>
          <option value="Maharashtra">Maharashtra</option>
          <option value="Delhi">Delhi</option>
          <option value="Tamil Nadu">Tamil Nadu</option>
          <option value="Telangana">Telangana</option>
          <option value="Gujarat">Gujarat</option>
        </select>
      </div>

      {/* Results */}
      {loading ? (
        <div className="flex items-center justify-center py-8">
          <div className="w-5 h-5 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <div className="space-y-2">
          {predictions.map((p, i) => (
            <div
              key={p.entity_id || i}
              onClick={() => p.slug && onEntityClick?.(p.slug)}
              className="flex items-center gap-3 p-3 rounded-xl bg-atlas-surface/50 border border-atlas-border hover:border-brand-500/30 cursor-pointer transition-all"
            >
              <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold"
                style={{
                  backgroundColor: p.growth_label === 'high' ? 'rgba(34,197,94,0.15)' :
                    p.growth_label === 'medium' ? 'rgba(251,191,36,0.15)' : 'rgba(100,116,139,0.15)',
                  color: p.growth_label === 'high' ? '#22C55E' :
                    p.growth_label === 'medium' ? '#FBBF24' : '#64748B',
                }}>
                {(p.growth_score * 100).toFixed(0)}
              </div>
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-medium text-atlas-text truncate">{p.entity_name}</h4>
                <p className="text-[11px] text-atlas-muted">
                  📍 {p.city}, {p.state}
                  {p.top_factor && <span className="ml-2">⭐ {p.top_factor.factor.replace('_', ' ')}</span>}
                </p>
              </div>
              <div className="flex-shrink-0">
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                  p.growth_label === 'high' ? 'bg-green-500/20 text-green-400' :
                  p.growth_label === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
                  'bg-slate-500/20 text-slate-400'
                }`}>
                  {p.growth_label.toUpperCase()}
                </span>
              </div>
            </div>
          ))}
          {predictions.length === 0 && !loading && (
            <p className="text-center text-xs text-atlas-muted py-8">No predictions available for these filters.</p>
          )}
        </div>
      )}
    </div>
  )
}


// ─── Sector Classifier Tab ──────────────────────────────────────────────────

function ClassifyTab() {
  const [description, setDescription] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const classify = useCallback(async () => {
    if (description.length < 10) return
    setLoading(true)
    try {
      const resp = await fetch(`/api/ml/classify/sector?description=${encodeURIComponent(description)}&top_k=5`)
      const data = await resp.json()
      setResult(data)
    } catch (err) {
      console.error('Classification failed:', err)
    }
    setLoading(false)
  }, [description])

  const exampleDescriptions = [
    "AI-powered fraud detection platform for digital banking and UPI payments",
    "Online marketplace connecting farmers directly with urban consumers",
    "SaaS platform for hospital management and telemedicine consultations",
    "Electric vehicle charging network for tier-2 cities in India",
    "Gamified coding education platform for school students",
  ]

  return (
    <div className="p-4 space-y-4">
      <div className="space-y-2">
        <label className="text-xs font-medium text-atlas-muted">Describe a startup:</label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="e.g., AI-powered fraud detection for digital payments..."
          className="w-full h-24 px-3 py-2 rounded-xl bg-atlas-surface border border-atlas-border text-sm text-atlas-text placeholder:text-atlas-muted/40 resize-none focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
        <button
          onClick={classify}
          disabled={description.length < 10 || loading}
          className="w-full py-2 rounded-xl bg-brand-500 text-white text-sm font-medium hover:bg-brand-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
        >
          {loading ? (
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <>
              <Brain size={14} />
              Classify Sector
            </>
          )}
        </button>
      </div>

      {/* Quick examples */}
      <div className="space-y-1">
        <p className="text-[10px] text-atlas-muted uppercase tracking-wider font-medium">Try an example:</p>
        <div className="flex flex-wrap gap-1">
          {exampleDescriptions.map((desc, i) => (
            <button
              key={i}
              onClick={() => setDescription(desc)}
              className="text-[10px] px-2 py-1 rounded-lg bg-atlas-surface text-atlas-muted hover:text-atlas-text hover:bg-atlas-border transition-colors truncate max-w-full"
            >
              {desc.slice(0, 50)}...
            </button>
          ))}
        </div>
      </div>

      {/* Result */}
      {result && (
        <div className="space-y-3 p-3 rounded-xl bg-atlas-surface/50 border border-atlas-border">
          <div className="flex items-center gap-2">
            <span className="text-lg">🎯</span>
            <div>
              <p className="text-sm font-bold text-atlas-text capitalize">{result.sector?.replace('_', ' ')}</p>
              <p className="text-[10px] text-atlas-muted">Confidence: {(result.confidence * 100).toFixed(1)}%</p>
            </div>
          </div>

          {result.top_sectors && (
            <div className="space-y-1.5">
              <p className="text-[10px] text-atlas-muted uppercase tracking-wider">All predictions:</p>
              {result.top_sectors.map((s, i) => (
                <div key={i} className="flex items-center gap-2">
                  <div className="flex-1 h-2 rounded-full bg-atlas-border overflow-hidden">
                    <div
                      className="h-full rounded-full bg-brand-500 transition-all"
                      style={{ width: `${s.confidence * 100}%` }}
                    />
                  </div>
                  <span className="text-[11px] text-atlas-muted w-24 text-right capitalize">{s.sector?.replace('_', ' ')}</span>
                  <span className="text-[10px] text-atlas-muted/60 w-10 text-right">{(s.confidence * 100).toFixed(0)}%</span>
                </div>
              ))}
            </div>
          )}

          <p className="text-[9px] text-atlas-muted/50">
            Model: {result.model_version || 'keyword_fallback_v1'}
          </p>
        </div>
      )}
    </div>
  )
}


// ─── Model Health Tab ───────────────────────────────────────────────────────

function HealthTab() {
  const [health, setHealth] = useState(null)
  const [drift, setDrift] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const [hRes, dRes] = await Promise.all([
          fetch('/api/ml/health'),
          fetch('/api/mlops/drift/check?sample_size=50'),
        ])
        setHealth(await hRes.json())
        setDrift(await dRes.json())
      } catch (err) {
        console.error('Health check failed:', err)
      }
      setLoading(false)
    }
    fetchHealth()
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="w-5 h-5 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="p-4 space-y-4">
      {/* Model Status */}
      <div className="space-y-2">
        <h3 className="text-xs font-medium text-atlas-muted uppercase tracking-wider">Model Status</h3>
        {health?.models && Object.entries(health.models).map(([name, info]) => (
          <div key={name} className="flex items-center gap-3 p-3 rounded-xl bg-atlas-surface/50 border border-atlas-border">
            <div className={`w-2.5 h-2.5 rounded-full ${info.loaded ? 'bg-green-500' : 'bg-red-500'}`} />
            <div className="flex-1">
              <p className="text-sm font-medium text-atlas-text capitalize">{name.replace('_', ' ')}</p>
              <p className="text-[10px] text-atlas-muted">
                {info.model || info.model_path || 'Active'}
                {info.mode && ` · ${info.mode}`}
              </p>
            </div>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
              info.loaded ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
            }`}>
              {info.loaded ? 'ACTIVE' : 'DOWN'}
            </span>
          </div>
        ))}
      </div>

      {/* Data Drift */}
      <div className="space-y-2">
        <h3 className="text-xs font-medium text-atlas-muted uppercase tracking-wider">Data Drift Detection</h3>
        {drift?.summary && (
          <div className={`flex items-center gap-2 p-3 rounded-xl border ${
            drift.summary.recommendation === 'OK'
              ? 'bg-green-500/5 border-green-500/20'
              : 'bg-amber-500/5 border-amber-500/20'
          }`}>
            {drift.summary.recommendation === 'OK' ? (
              <CheckCircle size={16} className="text-green-400" />
            ) : (
              <AlertTriangle size={16} className="text-amber-400" />
            )}
            <div>
              <p className="text-sm font-medium text-atlas-text">
                {drift.summary.recommendation === 'OK' ? 'No Drift Detected' : 'Drift Detected'}
              </p>
              <p className="text-[10px] text-atlas-muted">
                {drift.summary.features_checked} features checked · {drift.summary.drifted_features} drifted
              </p>
            </div>
          </div>
        )}

        {drift?.drift_reports?.map((report, i) => (
          <div key={i} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-atlas-surface/30">
            <div className={`w-2 h-2 rounded-full ${report.drift_detected ? 'bg-amber-500' : 'bg-green-500'}`} />
            <span className="text-xs text-atlas-muted flex-1 capitalize">{report.feature.replace('_', ' ')}</span>
            <span className="text-[10px] text-atlas-muted/60">{report.method}</span>
            <span className={`text-[10px] font-mono ${report.drift_detected ? 'text-amber-400' : 'text-green-400'}`}>
              {(report.drift_score * 100).toFixed(1)}%
            </span>
          </div>
        ))}
      </div>

      {/* System Info */}
      <div className="p-3 rounded-xl bg-atlas-surface/30 border border-atlas-border/50">
        <p className="text-[10px] text-atlas-muted/60">
          🔄 Models are loaded on first request. ONNX optimization available for production.
          <br />📊 Drift checks run against reference distribution from training data.
          <br />🚀 CI/CD: GitHub Actions → test → validate → deploy to HF Spaces.
        </p>
      </div>
    </div>
  )
}
