import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { X, ChevronDown, ChevronUp, RotateCcw, Search } from 'lucide-react'

const ENTITY_TYPES = [
  { value: 'startup', label: 'Startups', icon: '🚀', color: '#3B82F6' },
  { value: 'sme', label: 'SMEs', icon: '🏢', color: '#10B981' },
  { value: 'college_ecell', label: 'College E-Cells', icon: '🎓', color: '#FBBF24' },
  { value: 'incubator', label: 'Incubators', icon: '🧪', color: '#A855F7' },
  { value: 'accelerator', label: 'Accelerators', icon: '⚡', color: '#EC4899' },
]

const TOP_SECTORS = [
  { value: 'fintech', label: 'FinTech', icon: '💳', color: '#3B82F6' },
  { value: 'saas_ai', label: 'SaaS / AI', icon: '☁️', color: '#6366F1' },
  { value: 'ecommerce', label: 'E-Commerce', icon: '🛒', color: '#F59E0B' },
  { value: 'healthcare', label: 'Healthcare', icon: '🏥', color: '#10B981' },
  { value: 'manufacturing', label: 'Manufacturing', icon: '🏭', color: '#78716C' },
]

const DPIIT_CATEGORIES = [
  { value: 'cleantech', label: 'CleanTech', icon: '🌿' },
  { value: 'agritech', label: 'AgriTech', icon: '🌾' },
  { value: 'edtech', label: 'EdTech', icon: '📚' },
  { value: 'healthtech', label: 'HealthTech', icon: '💊' },
  { value: 'deeptech', label: 'DeepTech', icon: '🔬' },
  { value: 'ai_ml', label: 'AI / ML', icon: '🤖' },
  { value: 'cybersecurity', label: 'Cybersecurity', icon: '🔒' },
  { value: 'foodtech', label: 'FoodTech', icon: '🍔' },
  { value: 'logistics', label: 'Logistics', icon: '🚛' },
  { value: 'mobility', label: 'Mobility', icon: '🚗' },
  { value: 'proptech', label: 'PropTech', icon: '🏠' },
  { value: 'spacetech', label: 'SpaceTech', icon: '🚀' },
  { value: 'biotech', label: 'BioTech', icon: '🧬' },
  { value: 'ev', label: 'EV / E-Mobility', icon: '🔋' },
  { value: 'gaming', label: 'Gaming', icon: '🎮' },
  { value: 'mediatech', label: 'MediaTech', icon: '📺' },
  { value: 'iot', label: 'IoT', icon: '📡' },
  { value: 'drone_tech', label: 'Drone Tech', icon: '🛸' },
]

const BUSINESS_MODELS = [
  { value: 'lifestyle', label: 'Lifestyle', icon: '🌟', desc: 'Self-funded, profitable' },
  { value: 'scalable', label: 'Scalable', icon: '📈', desc: 'VC-funded, high-growth' },
  { value: 'social', label: 'Social Enterprise', icon: '🌍', desc: 'Impact-first' },
  { value: 'large_company', label: 'Large Company', icon: '🏢', desc: 'Corporate spin-off' },
]

const STAGES = [
  { value: 'ideation', label: 'Ideation', color: '#64748B' },
  { value: 'validation', label: 'Validation', color: '#60A5FA' },
  { value: 'early_traction', label: 'Early Traction', color: '#34D399' },
  { value: 'scaling', label: 'Scaling', color: '#FBBF24' },
  { value: 'mature', label: 'Mature', color: '#F87171' },
]

export default function Sidebar({ filters, facets, onFilterChange, onReset, onClose, isMobile }) {
  const [sectors, setSectors] = useState([])
  const [states, setStates] = useState([])
  const [expandedSections, setExpandedSections] = useState({
    type: true,
    top_sector: false,
    dpiit_cat: false,
    biz_model: false,
    awards: false,
    stage: false,
    location: false,
    unicorn: false,
  })

  // In-filter search states for all searchable sections
  const [searchTerms, setSearchTerms] = useState({
    dpiit: '',
    sector: '',
    stage: '',
    location: '',
    biz_model: '',
    type: '',
  })

  useEffect(() => {
    fetch('/api/entities/sectors').then(r => r.json()).then(setSectors).catch(console.error)
    fetch('/api/entities/locations/states').then(r => r.json()).then(setStates).catch(console.error)
  }, [])

  const toggleSection = (key) => setExpandedSections(prev => ({ ...prev, [key]: !prev[key] }))

  const updateSearch = (key, value) => setSearchTerms(prev => ({ ...prev, [key]: value }))

  const toggleArrayFilter = useCallback((key, value) => {
    const current = filters[key]
    const next = current.includes(value) ? current.filter(v => v !== value) : [...current, value]
    onFilterChange(key, next)
  }, [filters, onFilterChange])

  const activeFilterCount = [
    filters.entity_type.length, filters.sector.length, filters.stage.length,
    filters.dpiit_category.length, filters.business_model.length, filters.unicorn_status.length,
    filters.dpiit_only ? 1 : 0, filters.is_women_led ? 1 : 0,
    filters.is_rural_impact ? 1 : 0, filters.is_campus_startup ? 1 : 0,
    filters.nsa_winner ? 1 : 0, filters.state ? 1 : 0,
  ].reduce((a, b) => a + b, 0)

  // Filtered lists
  const filteredDpiitCats = useMemo(() => {
    const q = searchTerms.dpiit.toLowerCase()
    return q ? DPIIT_CATEGORIES.filter(c =>
      c.label.toLowerCase().includes(q) || c.value.includes(q)
    ) : DPIIT_CATEGORIES
  }, [searchTerms.dpiit])

  const filteredTypes = useMemo(() => {
    const q = searchTerms.type.toLowerCase()
    return q ? ENTITY_TYPES.filter(t =>
      t.label.toLowerCase().includes(q) || t.value.includes(q)
    ) : ENTITY_TYPES
  }, [searchTerms.type])

  const filteredStages = useMemo(() => {
    const q = searchTerms.stage.toLowerCase()
    return q ? STAGES.filter(s =>
      s.label.toLowerCase().includes(q) || s.value.includes(q)
    ) : STAGES
  }, [searchTerms.stage])

  const filteredStates = useMemo(() => {
    const q = searchTerms.location.toLowerCase()
    return q ? states.filter(s =>
      s.state.toLowerCase().includes(q)
    ) : states
  }, [searchTerms.location, states])

  const filteredBizModels = useMemo(() => {
    const q = searchTerms.biz_model.toLowerCase()
    return q ? BUSINESS_MODELS.filter(b =>
      b.label.toLowerCase().includes(q) || b.value.includes(q)
    ) : BUSINESS_MODELS
  }, [searchTerms.biz_model])

  // Helper: count active filters in a section (shows badge on collapsed sections)
  const sectionBadge = (count) => count > 0 ? (
    <span className="bg-brand-500 text-white text-[10px] font-bold w-4 h-4 rounded-full flex items-center justify-center">{count}</span>
  ) : null

  return (
    <div className={
      isMobile
        ? "fixed inset-x-0 bottom-0 z-30 max-h-[75vh] flex flex-col pointer-events-auto animate-slide-up"
        : "absolute top-16 left-3 bottom-4 w-80 z-20 animate-slide-in-left flex flex-col pointer-events-none"
    }>
      <div className={
        isMobile
          ? "bg-atlas-bg/95 border-t border-atlas-border rounded-t-2xl shadow-2xl flex flex-col overflow-hidden max-h-[75vh]"
          : "glass rounded-2xl shadow-2xl flex flex-col overflow-hidden pointer-events-auto max-h-full"
      }>
        {/* Mobile drag handle */}
        {isMobile && (
          <div className="flex justify-center py-2 flex-shrink-0">
            <div className="w-10 h-1 rounded-full bg-atlas-border" />
          </div>
        )}
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-atlas-border flex-shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-atlas-text">Filters</span>
            {activeFilterCount > 0 && (
              <span className="bg-brand-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">{activeFilterCount}</span>
            )}
          </div>
          <div className="flex items-center gap-1">
            {activeFilterCount > 0 && (
              <button onClick={onReset} className="text-xs text-brand-500 hover:text-brand-400 flex items-center gap-1 px-2 py-1 rounded hover:bg-brand-500/10">
                <RotateCcw size={12} /> Reset
              </button>
            )}
            <button onClick={onClose} className="p-1 hover:bg-atlas-surface rounded-lg transition-colors">
              <X size={16} className="text-atlas-muted" />
            </button>
          </div>
        </div>

        {/* Quick filters bar — always visible, no scroll needed */}
        <div className="px-3 py-2 border-b border-atlas-border/50 flex-shrink-0">
          <div className="flex flex-wrap gap-1.5">
            {/* Quick toggle pills */}
            <QuickPill
              active={filters.unicorn_status.includes('unicorn')}
              onClick={() => toggleArrayFilter('unicorn_status', 'unicorn')}
              icon="🦄" label="Unicorns"
              count={facets?.awards?.unicorns}
            />
            <QuickPill
              active={filters.is_women_led}
              onClick={() => onFilterChange('is_women_led', !filters.is_women_led)}
              icon="👩" label="Women-led"
              count={facets?.awards?.women_led}
            />
            <QuickPill
              active={filters.dpiit_only}
              onClick={() => onFilterChange('dpiit_only', !filters.dpiit_only)}
              icon="🏛️" label="DPIIT"
            />
            <QuickPill
              active={filters.nsa_winner}
              onClick={() => onFilterChange('nsa_winner', !filters.nsa_winner)}
              icon="🏆" label="NSA"
              count={facets?.awards?.nsa_winners}
            />
          </div>
        </div>

        {/* Scrollable filter sections */}
        <div className="flex-1 overflow-y-auto px-4 py-2 space-y-0.5 scrollbar-thin">

          {/* Entity Type */}
          <FilterSection
            title="Entity Type"
            expanded={expandedSections.type}
            onToggle={() => toggleSection('type')}
            badge={sectionBadge(filters.entity_type.length)}
          >
            <div className="space-y-1">
              {filteredTypes.map(type => {
                const count = facets?.entity_type?.[type.value] || 0
                const active = filters.entity_type.includes(type.value)
                return (
                  <button key={type.value} onClick={() => toggleArrayFilter('entity_type', type.value)}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm transition-all ${
                      active ? 'bg-brand-500/15 ring-1 ring-brand-500/30 text-brand-400' : 'hover:bg-atlas-surface text-atlas-muted'
                    }`}>
                    <span className="text-base">{type.icon}</span>
                    <span className="flex-1 text-left font-medium">{type.label}</span>
                    <span className={`text-xs font-mono ${active ? 'text-brand-500' : 'text-atlas-muted/60'}`}>{count.toLocaleString()}</span>
                  </button>
                )
              })}
            </div>
          </FilterSection>

          {/* Top Sectors */}
          <FilterSection
            title="Sectors"
            expanded={expandedSections.top_sector}
            onToggle={() => toggleSection('top_sector')}
            badge={sectionBadge(filters.sector.length)}
          >
            <InFilterSearch value={searchTerms.sector} onChange={(v) => updateSearch('sector', v)} placeholder="Search sectors..." />
            <div className="flex flex-wrap gap-1.5">
              {TOP_SECTORS.filter(s =>
                !searchTerms.sector || s.label.toLowerCase().includes(searchTerms.sector.toLowerCase()) || s.value.includes(searchTerms.sector.toLowerCase())
              ).map(s => {
                const active = filters.sector.includes(s.value)
                return (
                  <button key={s.value} onClick={() => toggleArrayFilter('sector', s.value)}
                    className={`inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      active ? 'ring-1 text-white shadow-sm' : 'bg-atlas-surface text-atlas-muted hover:bg-atlas-border'
                    }`}
                    style={active ? { backgroundColor: s.color, ringColor: s.color } : {}}>
                    <span>{s.icon}</span><span>{s.label}</span>
                  </button>
                )
              })}
              {/* Show DPIIT categories matching search */}
              {searchTerms.sector && sectors.filter(s => s.category === 'dpiit_category' &&
                (s.label.toLowerCase().includes(searchTerms.sector.toLowerCase()) || s.slug.includes(searchTerms.sector.toLowerCase())) &&
                !TOP_SECTORS.find(ts => ts.value === s.slug)
              ).slice(0, 8).map(s => {
                const active = filters.sector.includes(s.slug)
                return (
                  <button key={s.slug} onClick={() => toggleArrayFilter('sector', s.slug)}
                    className={`inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      active ? 'ring-1 text-white shadow-sm bg-brand-500' : 'bg-atlas-surface text-atlas-muted hover:bg-atlas-border'
                    }`}>
                    <span>{s.icon || '🏷️'}</span><span>{s.label}</span>
                  </button>
                )
              })}
            </div>
          </FilterSection>

          {/* DPIIT Categories */}
          <FilterSection
            title="DPIIT Categories"
            expanded={expandedSections.dpiit_cat}
            onToggle={() => toggleSection('dpiit_cat')}
            badge={sectionBadge(filters.dpiit_category.length)}
          >
            <InFilterSearch value={searchTerms.dpiit} onChange={(v) => updateSearch('dpiit', v)} placeholder="Search DPIIT categories..." />
            <div className="flex flex-wrap gap-1.5">
              {filteredDpiitCats.map(cat => {
                const active = filters.dpiit_category.includes(cat.value)
                const count = facets?.dpiit_category?.[cat.value] || 0
                return (
                  <button key={cat.value} onClick={() => toggleArrayFilter('dpiit_category', cat.value)}
                    className={`inline-flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      active ? 'bg-brand-500/20 ring-1 ring-brand-500/30 text-brand-400' : 'bg-atlas-surface text-atlas-muted hover:bg-atlas-border'
                    }`}>
                    <span>{cat.icon}</span>
                    <span>{cat.label}</span>
                    {count > 0 && <span className="text-[10px] opacity-60">({count.toLocaleString()})</span>}
                  </button>
                )
              })}
              {searchTerms.dpiit && filteredDpiitCats.length === 0 && (
                <p className="text-xs text-atlas-muted/50 py-1">No categories match "{searchTerms.dpiit}"</p>
              )}
            </div>
          </FilterSection>

          {/* Business Models */}
          <FilterSection
            title="Business Model"
            expanded={expandedSections.biz_model}
            onToggle={() => toggleSection('biz_model')}
            badge={sectionBadge(filters.business_model.length)}
          >
            <div className="space-y-1">
              {filteredBizModels.map(bm => {
                const active = filters.business_model.includes(bm.value)
                const count = facets?.business_model?.[bm.value] || 0
                return (
                  <button key={bm.value} onClick={() => toggleArrayFilter('business_model', bm.value)}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm transition-all ${
                      active ? 'bg-brand-500/15 ring-1 ring-brand-500/30 text-brand-400' : 'hover:bg-atlas-surface text-atlas-muted'
                    }`}>
                    <span>{bm.icon}</span>
                    <div className="flex-1 text-left">
                      <span className="font-medium">{bm.label}</span>
                      <p className="text-[10px] opacity-60 mt-0.5">{bm.desc}</p>
                    </div>
                    <span className="text-xs font-mono opacity-60">{count.toLocaleString()}</span>
                  </button>
                )
              })}
            </div>
          </FilterSection>

          {/* Awards & Recognition — merged unicorn + special */}
          <FilterSection
            title="Awards & Recognition"
            expanded={expandedSections.awards}
            onToggle={() => toggleSection('awards')}
            badge={sectionBadge(
              (filters.is_women_led ? 1 : 0) + (filters.is_rural_impact ? 1 : 0) +
              (filters.is_campus_startup ? 1 : 0) + (filters.nsa_winner ? 1 : 0) +
              filters.unicorn_status.length
            )}
          >
            <div className="space-y-1">
              {/* Unicorn status */}
              {[
                { value: 'unicorn', label: 'Unicorns', icon: '🦄', count: facets?.awards?.unicorns || 0 },
                { value: 'soonicorn', label: 'Soonicorns', icon: '🌟', count: facets?.awards?.soonicorns || 0 },
              ].map(u => {
                const active = filters.unicorn_status.includes(u.value)
                return (
                  <button key={u.value} onClick={() => toggleArrayFilter('unicorn_status', u.value)}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm transition-all ${
                      active ? 'bg-purple-500/15 ring-1 ring-purple-500/30 text-purple-400' : 'hover:bg-atlas-surface text-atlas-muted'
                    }`}>
                    <span>{u.icon}</span>
                    <span className="flex-1 text-left font-medium">{u.label}</span>
                    <span className="text-xs font-mono opacity-60">{u.count.toLocaleString()}</span>
                  </button>
                )
              })}

              <div className="h-px bg-atlas-border/30 my-1" />

              <ToggleButton
                active={filters.is_women_led}
                onClick={() => onFilterChange('is_women_led', !filters.is_women_led)}
                icon="👩" label="Women-led Startups"
                count={facets?.awards?.women_led || 0}
                activeColor="bg-pink-500/15 ring-pink-500/30 text-pink-400"
              />
              <ToggleButton
                active={filters.is_rural_impact}
                onClick={() => onFilterChange('is_rural_impact', !filters.is_rural_impact)}
                icon="🌾" label="Rural Impact"
                count={facets?.awards?.rural_impact || 0}
                activeColor="bg-green-500/15 ring-green-500/30 text-green-400"
              />
              <ToggleButton
                active={filters.is_campus_startup}
                onClick={() => onFilterChange('is_campus_startup', !filters.is_campus_startup)}
                icon="🎓" label="Campus Startups"
                count={facets?.awards?.campus_startup || 0}
                activeColor="bg-blue-500/15 ring-blue-500/30 text-blue-400"
              />
              <ToggleButton
                active={filters.nsa_winner}
                onClick={() => onFilterChange('nsa_winner', !filters.nsa_winner)}
                icon="🏆" label="NSA 5.0 Winners"
                count={facets?.awards?.nsa_winners || 0}
                activeColor="bg-amber-500/15 ring-amber-500/30 text-amber-400"
              />
            </div>
          </FilterSection>

          {/* Stage */}
          <FilterSection
            title="Startup Stage"
            expanded={expandedSections.stage}
            onToggle={() => toggleSection('stage')}
            badge={sectionBadge(filters.stage.length)}
          >
            <div className="space-y-1">
              {filteredStages.map(stage => {
                const count = facets?.stage?.[stage.value] || 0
                const active = filters.stage.includes(stage.value)
                return (
                  <button key={stage.value} onClick={() => toggleArrayFilter('stage', stage.value)}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm transition-all ${
                      active ? 'bg-brand-500/15 ring-1 ring-brand-500/30' : 'hover:bg-atlas-surface'
                    }`}>
                    <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: stage.color }} />
                    <span className="flex-1 text-left text-atlas-muted font-medium">{stage.label}</span>
                    <span className="text-xs text-atlas-muted/60 font-mono">{count.toLocaleString()}</span>
                  </button>
                )
              })}
            </div>
          </FilterSection>

          {/* Location */}
          <FilterSection
            title="Location"
            expanded={expandedSections.location}
            onToggle={() => toggleSection('location')}
            badge={sectionBadge(filters.state ? 1 : 0)}
          >
            <InFilterSearch value={searchTerms.location} onChange={(v) => updateSearch('location', v)} placeholder="Search states..." />
            <select value={filters.state} onChange={(e) => onFilterChange('state', e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-atlas-border bg-atlas-surface text-atlas-text text-sm focus:ring-2 focus:ring-brand-500 outline-none">
              <option value="">All States</option>
              {filteredStates.map(s => (
                <option key={s.state} value={s.state}>{s.state} ({s.count.toLocaleString()})</option>
              ))}
            </select>
          </FilterSection>
        </div>

        {/* Legend — compact */}
        <div className="px-4 py-2 border-t border-atlas-border flex-shrink-0">
          <div className="flex flex-wrap gap-x-3 gap-y-1">
            {ENTITY_TYPES.map(t => (
              <div key={t.value} className="flex items-center gap-1.5 text-[10px] text-atlas-muted">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: t.color }} />
                {t.label}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}


/* ── Subcomponents ── */

function FilterSection({ title, expanded, onToggle, children, badge }) {
  return (
    <div className="border-b border-atlas-border/30 last:border-0">
      <button onClick={onToggle}
        className="w-full flex items-center justify-between py-2.5 text-xs font-semibold text-atlas-muted uppercase tracking-wider hover:text-atlas-text transition-colors">
        <span className="flex items-center gap-2">
          {title}
          {!expanded && badge}
        </span>
        {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>
      {expanded && (
        <div className="pb-2 animate-fade-in">
          {children}
        </div>
      )}
    </div>
  )
}

function InFilterSearch({ value, onChange, placeholder }) {
  return (
    <div className="relative mb-2">
      <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-atlas-muted/50" />
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full pl-7 pr-3 py-1.5 rounded-lg bg-atlas-surface border border-atlas-border text-xs text-atlas-text placeholder:text-atlas-muted/40 focus:outline-none focus:ring-1 focus:ring-brand-500"
      />
      {value && (
        <button onClick={() => onChange('')} className="absolute right-2 top-1/2 -translate-y-1/2">
          <X size={10} className="text-atlas-muted/50 hover:text-atlas-muted" />
        </button>
      )}
    </div>
  )
}

function QuickPill({ active, onClick, icon, label, count }) {
  return (
    <button onClick={onClick}
      className={`inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] font-medium transition-all ${
        active
          ? 'bg-brand-500/20 ring-1 ring-brand-500/40 text-brand-400'
          : 'bg-atlas-surface/60 text-atlas-muted hover:bg-atlas-surface hover:text-atlas-text'
      }`}>
      <span>{icon}</span>
      <span>{label}</span>
      {count > 0 && <span className="text-[9px] opacity-60">{count.toLocaleString()}</span>}
    </button>
  )
}

function ToggleButton({ active, onClick, icon, label, count, activeColor }) {
  return (
    <button onClick={onClick}
      className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm transition-all ${
        active ? `${activeColor} ring-1` : 'hover:bg-atlas-surface text-atlas-muted'
      }`}>
      <span>{icon}</span>
      <span className="flex-1 text-left font-medium">{label}</span>
      <span className="text-xs font-mono opacity-60">{count.toLocaleString()}</span>
    </button>
  )
}
