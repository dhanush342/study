import React, { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, AreaChart, Area } from 'recharts'

const COLORS = ['#3B82F6', '#10B981', '#F97316', '#A855F7', '#EC4899', '#FBBF24', '#14B8A6', '#EF4444', '#6366F1', '#84CC16']

export default function AnalyticsPanel({ onClose }) {
  const [overview, setOverview] = useState(null)
  const [sectorData, setSectorData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('overview')

  useEffect(() => {
    Promise.all([
      fetch('/api/entities/analytics/overview').then(r => r.json()),
      fetch('/api/entities/analytics/sectors').then(r => r.json()),
    ]).then(([ov, sd]) => {
      setOverview(ov)
      setSectorData(sd)
      setLoading(false)
    }).catch(console.error)
  }, [])

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null
    return (
      <div className="glass rounded-lg px-3 py-2 text-xs">
        <p className="text-atlas-text font-medium">{label}</p>
        {payload.map((p, i) => (
          <p key={i} style={{ color: p.color }}>{p.name}: {typeof p.value === 'number' ? p.value.toLocaleString() : p.value}</p>
        ))}
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/50 p-2 sm:p-4">
      <div className="glass rounded-2xl shadow-2xl w-full max-w-3xl max-h-[85vh] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-4 sm:px-6 py-3 sm:py-4 border-b border-atlas-border flex-shrink-0">
          <div>
            <h2 className="text-base sm:text-lg font-bold text-atlas-text">📊 Analytics</h2>
            <p className="text-[10px] sm:text-xs text-atlas-muted mt-0.5">Curated dataset — not total Indian ecosystem</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-atlas-surface rounded-lg transition-colors">
            <X size={20} className="text-atlas-muted" />
          </button>
        </div>

        <div className="flex gap-1 px-4 sm:px-6 pt-3 flex-shrink-0 overflow-x-auto">
          {[
            { id: 'overview', label: '🏠 Overview' },
            { id: 'sectors', label: '📊 Sectors' },
            { id: 'geography', label: '🗺️ Geography' },
            { id: 'trends', label: '📈 Trends' },
          ].map(tab => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              className={`px-3 sm:px-4 py-2 rounded-lg text-xs sm:text-sm font-medium transition-colors whitespace-nowrap ${
                activeTab === tab.id ? 'bg-brand-500/15 text-brand-400' : 'text-atlas-muted hover:bg-atlas-surface'
              }`}>{tab.label}</button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
          {loading ? (
            <div className="space-y-4">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-20 bg-atlas-surface/40 rounded-xl animate-pulse" />
              ))}
            </div>
          ) : (
            <>
              {activeTab === 'overview' && overview && (
                <>
                  {/* Disclaimer */}
                  <div className="bg-amber-500/5 border border-amber-500/10 rounded-lg px-3 py-2">
                    <p className="text-[10px] text-amber-400/80">
                      ⚠ Curated dataset of {overview.total_entities?.toLocaleString()} mapped entities.
                      India has 223,000+ DPIIT-recognized startups and 102,000+ women-led ventures.
                      Figures below reflect our database only.
                    </p>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3">
                    <StatCard label="Mapped" value={overview.total_entities?.toLocaleString()} color="#6366F1" />
                    <StatCard label="Unicorns" value={overview.unicorn_count} color="#F97316" />
                    <StatCard label="Women-led*" value={overview.women_led_count} color="#EC4899" />
                    <StatCard label="Funding*" value={overview.total_funding_display} color="#F59E0B" />
                  </div>

                  {/* Entity Type Pie Chart */}
                  <div>
                    <h3 className="text-sm font-semibold text-atlas-muted uppercase mb-3">Entity Distribution</h3>
                    <div className="h-48 sm:h-56">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={Object.entries(overview.by_type || {}).map(([k, v]) => ({ name: k.replace('_', ' '), value: v }))}
                            cx="50%" cy="50%" outerRadius="80%" innerRadius="50%"
                            dataKey="value" nameKey="name"
                            stroke="none"
                          >
                            {Object.keys(overview.by_type || {}).map((_, i) => (
                              <Cell key={i} fill={COLORS[i % COLORS.length]} />
                            ))}
                          </Pie>
                          <Tooltip content={<CustomTooltip />} />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="flex flex-wrap justify-center gap-x-4 gap-y-1 mt-2">
                      {Object.entries(overview.by_type || {}).sort((a, b) => b[1] - a[1]).map(([type, count], i) => (
                        <div key={type} className="flex items-center gap-1.5 text-xs text-atlas-muted">
                          <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                          <span className="capitalize">{type.replace('_', ' ')}</span>
                          <span className="font-mono opacity-60">({count.toLocaleString()})</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {activeTab === 'sectors' && sectorData && (
                <div>
                  <h3 className="text-sm font-semibold text-atlas-muted uppercase mb-3">Mapped Entities by Sector</h3>
                  <div className="h-72 sm:h-96">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={sectorData.slice(0, 15).map(s => ({ name: s.sector.replace('_', ' '), count: s.count, funding: s.total_employees }))} layout="vertical" margin={{ left: 80, right: 20 }}>
                        <XAxis type="number" stroke="#64748B" fontSize={10} />
                        <YAxis dataKey="name" type="category" stroke="#64748B" fontSize={10} width={75} />
                        <Tooltip content={<CustomTooltip />} />
                        <Bar dataKey="count" name="Entities" fill="#3B82F6" radius={[0, 4, 4, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>

                  <div className="space-y-2 mt-4">
                    {sectorData.slice(0, 10).map((s, i) => (
                      <div key={s.sector} className="flex items-center gap-3 bg-atlas-surface/30 rounded-lg px-3 py-2">
                        <span className="text-sm font-bold text-atlas-muted w-6">#{i + 1}</span>
                        <span className="flex-1 text-sm text-atlas-text capitalize">{s.sector.replace('_', ' ')}</span>
                        <span className="text-xs text-atlas-muted font-mono">{s.count}</span>
                        <span className="text-xs text-amber-400">{s.total_funding_display}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {activeTab === 'geography' && overview && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-sm font-semibold text-atlas-muted uppercase mb-3">Top States (mapped)</h3>
                    <div className="h-64 sm:h-80">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={(overview.top_states || []).map(s => ({ name: s.state, count: s.count }))} layout="vertical" margin={{ left: 90, right: 20 }}>
                          <XAxis type="number" stroke="#64748B" fontSize={10} />
                          <YAxis dataKey="name" type="category" stroke="#64748B" fontSize={10} width={85} />
                          <Tooltip content={<CustomTooltip />} />
                          <Bar dataKey="count" name="Entities" radius={[0, 4, 4, 0]}>
                            {(overview.top_states || []).map((_, i) => (
                              <Cell key={i} fill={COLORS[i % COLORS.length]} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  <div>
                    <h3 className="text-sm font-semibold text-atlas-muted uppercase mb-3">Top Cities (mapped)</h3>
                    <div className="grid grid-cols-2 gap-2">
                      {(overview.top_cities || []).map((c, i) => (
                        <div key={c.city} className="bg-atlas-surface/40 rounded-lg px-3 py-2 border border-atlas-border/30">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-brand-500">#{i + 1}</span>
                            <p className="text-sm font-medium text-atlas-text">{c.city}</p>
                          </div>
                          <p className="text-[10px] text-atlas-muted">{c.state} • {c.count.toLocaleString()} entities</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'trends' && overview && (
                <div>
                  <h3 className="text-sm font-semibold text-atlas-muted uppercase mb-3">Founding Trend (mapped entities, 2005–Present)</h3>
                  {overview.founding_trend?.length > 0 && (
                    <div className="h-56 sm:h-72">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={overview.founding_trend} margin={{ left: 10, right: 10, top: 10, bottom: 0 }}>
                          <defs>
                            <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#F97316" stopOpacity={0.3} />
                              <stop offset="95%" stopColor="#F97316" stopOpacity={0} />
                            </linearGradient>
                          </defs>
                          <XAxis dataKey="founded_year" stroke="#64748B" fontSize={10} />
                          <YAxis stroke="#64748B" fontSize={10} />
                          <Tooltip content={<CustomTooltip />} />
                          <Area type="monotone" dataKey="count" name="Founded" stroke="#F97316" strokeWidth={2} fill="url(#colorCount)" />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  )}

                  <div className="grid grid-cols-3 gap-3 mt-6">
                    <StatCard label="Funded" value={overview.funded_count?.toLocaleString()} color="#10B981" />
                    <StatCard label="DPIIT" value={overview.dpiit_recognized?.toLocaleString()} color="#14B8A6" />
                    <StatCard label="NSA Winners" value={overview.nsa_winner_count} color="#F59E0B" />
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

function StatCard({ label, value, color }) {
  return (
    <div className="bg-atlas-surface/40 rounded-xl p-3 border border-atlas-border/30 text-center">
      <p className="text-lg font-bold" style={{ color }}>{value}</p>
      <p className="text-[10px] text-atlas-muted uppercase mt-1">{label}</p>
    </div>
  )
}
