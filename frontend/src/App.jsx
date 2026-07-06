import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import StartupMap from './components/StartupMap'
import Sidebar from './components/Sidebar'
import EntityDetail from './components/EntityDetail'
import StatsBar from './components/StatsBar'
import SearchBar from './components/SearchBar'
import AnalyticsPanel from './components/AnalyticsPanel'
import MLInsightsPanel from './components/MLInsightsPanel'
import ChatWidget from './components/ChatWidget'
import ErrorBoundary from './components/ErrorBoundary'

const INITIAL_FILTERS = {
  entity_type: [],
  sector: [],
  stage: [],
  search: '',
  dpiit_only: false,
  dpiit_category: [],
  business_model: [],
  unicorn_status: [],
  is_women_led: false,
  is_rural_impact: false,
  is_campus_startup: false,
  nsa_winner: false,
  state: '',
  city: '',
}

const STATE_COORDS = {
  'Karnataka': { lng: 75.7, lat: 15.3, zoom: 7 },
  'Maharashtra': { lng: 75.7, lat: 19.7, zoom: 6.5 },
  'Delhi': { lng: 77.1, lat: 28.6, zoom: 10 },
  'Tamil Nadu': { lng: 78.6, lat: 11.1, zoom: 7 },
  'Telangana': { lng: 79.0, lat: 17.4, zoom: 8 },
  'Gujarat': { lng: 72.0, lat: 22.3, zoom: 7 },
  'Kerala': { lng: 76.3, lat: 10.8, zoom: 8 },
  'Rajasthan': { lng: 74.2, lat: 27.0, zoom: 6.5 },
  'Uttar Pradesh': { lng: 80.9, lat: 26.8, zoom: 6.5 },
  'West Bengal': { lng: 87.9, lat: 22.9, zoom: 7 },
  'Haryana': { lng: 76.1, lat: 29.0, zoom: 8 },
  'Punjab': { lng: 75.3, lat: 31.1, zoom: 8 },
  'Madhya Pradesh': { lng: 78.6, lat: 23.5, zoom: 6.5 },
  'Bihar': { lng: 85.3, lat: 25.6, zoom: 7 },
  'Odisha': { lng: 84.0, lat: 20.5, zoom: 7 },
  'Assam': { lng: 92.9, lat: 26.2, zoom: 7 },
  'Goa': { lng: 74.1, lat: 15.4, zoom: 10 },
  'Andhra Pradesh': { lng: 79.7, lat: 15.9, zoom: 7 },
}

const ARRAY_KEYS = ['entity_type', 'sector', 'stage', 'dpiit_category', 'business_model', 'unicorn_status']
const BOOL_KEYS = ['dpiit_only', 'is_women_led', 'is_rural_impact', 'is_campus_startup', 'nsa_winner']
const STRING_KEYS = ['search', 'state', 'city']

function filtersFromURL() {
  const params = new URLSearchParams(window.location.search)
  const f = { ...INITIAL_FILTERS }
  ARRAY_KEYS.forEach(k => { const v = params.get(k); if (v) f[k] = v.split(',').filter(Boolean) })
  BOOL_KEYS.forEach(k => { if (params.get(k) === 'true') f[k] = true })
  STRING_KEYS.forEach(k => { const v = params.get(k); if (v) f[k] = v })
  return f
}

function filtersToURL(filters) {
  const params = new URLSearchParams()
  ARRAY_KEYS.forEach(k => { if (filters[k]?.length > 0) params.set(k, filters[k].join(',')) })
  BOOL_KEYS.forEach(k => { if (filters[k]) params.set(k, 'true') })
  STRING_KEYS.forEach(k => { if (filters[k]) params.set(k, filters[k]) })
  const qs = params.toString()
  const url = qs ? `${window.location.pathname}?${qs}` : window.location.pathname
  window.history.replaceState(null, '', url)
}

function useIsMobile() {
  const [isMobile, setIsMobile] = useState(false)
  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])
  return isMobile
}

function useMapData(filters, viewport, zoom, mapMode) {
  const [geojson, setGeojson] = useState(null)
  const [loading, setLoading] = useState(true)
  const [totalInViewport, setTotalInViewport] = useState(0)
  const abortRef = useRef(null)
  const debounceRef = useRef(null)

  const buildFilterParams = useCallback((params) => {
    if (filters.entity_type.length > 0) params.set('entity_type', filters.entity_type.join(','))
    if (filters.sector.length > 0) params.set('sector', filters.sector.join(','))
    if (filters.stage.length > 0) params.set('stage', filters.stage.join(','))
    if (filters.dpiit_only) params.set('dpiit_only', 'true')
    if (filters.dpiit_category.length > 0) params.set('dpiit_category', filters.dpiit_category.join(','))
    if (filters.business_model.length > 0) params.set('business_model', filters.business_model.join(','))
    if (filters.unicorn_status.length > 0) params.set('unicorn_status', filters.unicorn_status.join(','))
    if (filters.is_women_led) params.set('is_women_led', 'true')
    if (filters.is_rural_impact) params.set('is_rural_impact', 'true')
    if (filters.is_campus_startup) params.set('is_campus_startup', 'true')
    if (filters.nsa_winner) params.set('nsa_winner', 'true')
    if (filters.search) params.set('search', filters.search)
    if (filters.state) params.set('state', filters.state)
    return params
  }, [filters])

  const fetchData = useCallback(async () => {
    if (abortRef.current) abortRef.current.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setLoading(true)
    try {
      const params = new URLSearchParams()
      params.set('min_lng', viewport.min_lng)
      params.set('max_lng', viewport.max_lng)
      params.set('min_lat', viewport.min_lat)
      params.set('max_lat', viewport.max_lat)
      params.set('zoom', zoom)
      buildFilterParams(params)

      const endpoint = mapMode === 'heatmap'
        ? `/api/entities/geojson?${params}&max_features=5000`
        : `/api/entities/clusters?${params}`

      const resp = await fetch(endpoint, { signal: controller.signal })
      const data = await resp.json()
      setGeojson(data)
      setTotalInViewport(data.total_count || data.features?.length || 0)
    } catch (err) {
      if (err.name !== 'AbortError') console.error('Failed to fetch data:', err)
    }
    setLoading(false)
  }, [viewport, zoom, filters, mapMode, buildFilterParams])

  useEffect(() => {
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => { fetchData() }, 200)
    return () => clearTimeout(debounceRef.current)
  }, [fetchData])

  return { geojson, loading, totalInViewport, fetchData }
}

function useViewportSummary(viewport, filters) {
  const [viewportSummary, setViewportSummary] = useState(null)

  const fetchViewportSummary = useCallback(async () => {
    try {
      const params = new URLSearchParams()
      params.set('min_lng', viewport.min_lng)
      params.set('max_lng', viewport.max_lng)
      params.set('min_lat', viewport.min_lat)
      params.set('max_lat', viewport.max_lat)
      if (filters.entity_type.length > 0) params.set('entity_type', filters.entity_type.join(','))
      const resp = await fetch(`/api/entities/viewport/summary?${params}`)
      const data = await resp.json()
      setViewportSummary(data)
    } catch (err) {
      console.error('Viewport summary failed:', err)
    }
  }, [viewport, filters.entity_type])

  useEffect(() => { fetchViewportSummary() }, [fetchViewportSummary])

  return viewportSummary
}

function useFacets(filters) {
  const [facets, setFacets] = useState(null)

  const fetchFacets = useCallback(async () => {
    try {
      const params = new URLSearchParams()
      if (filters.entity_type.length > 0) params.set('entity_type', filters.entity_type.join(','))
      if (filters.sector.length > 0) params.set('sector', filters.sector.join(','))
      if (filters.search) params.set('search', filters.search)
      const resp = await fetch(`/api/entities/facets?${params}`)
      const data = await resp.json()
      setFacets(data)
    } catch (err) {
      console.error('Failed to fetch facets:', err)
    }
  }, [filters])

  useEffect(() => { fetchFacets() }, [fetchFacets])

  return facets
}

export default function App() {
  const [filters, setFilters] = useState(() => filtersFromURL())
  const [viewport, setViewport] = useState({ min_lng: 68, max_lng: 97, min_lat: 6, max_lat: 37 })
  const [zoom, setZoom] = useState(4.5)
  const [mapMode, setMapMode] = useState('clusters')
  const [selectedEntity, setSelectedEntity] = useState(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [analyticsOpen, setAnalyticsOpen] = useState(false)
  const [mlInsightsOpen, setMlInsightsOpen] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)
  const [flyTo, setFlyTo] = useState(null)
  const [nearMeLoading, setNearMeLoading] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [overview, setOverview] = useState(null)
  const isMobile = useIsMobile()

  const { geojson, loading, totalInViewport } = useMapData(filters, viewport, zoom, mapMode)
  const viewportSummary = useViewportSummary(viewport, filters)
  const facets = useFacets(filters)

  useEffect(() => {
    if (!isMobile) setSidebarOpen(true)
  }, [isMobile])

  useEffect(() => {
    filtersToURL(filters)
  }, [filters])

  useEffect(() => {
    fetch('/api/entities/analytics/overview')
      .then(r => r.json())
      .then(setOverview)
      .catch(console.error)
  }, [])

  const handleFilterChange = useCallback((key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }))
    if (key === 'state' && value && STATE_COORDS[value]) {
      const c = STATE_COORDS[value]
      setFlyTo({ lng: c.lng, lat: c.lat, zoom: c.zoom })
    } else if (key === 'state' && !value) {
      setFlyTo({ lng: 78.5, lat: 22.0, zoom: 4.5 })
    }
  }, [])

  const handleResetFilters = useCallback(() => {
    setFilters(INITIAL_FILTERS)
    setFlyTo({ lng: 78.5, lat: 22.0, zoom: 4.5 })
  }, [])

  const handleEntityClick = useCallback(async (slug) => {
    try {
      const resp = await fetch(`/api/entities/detail/${slug}`)
      const data = await resp.json()
      setSelectedEntity(data)
      if (data.latitude && data.longitude) {
        setFlyTo({ lng: data.longitude, lat: data.latitude, zoom: 14 })
      }
      if (window.innerWidth < 768) setSidebarOpen(false)
    } catch (err) {
      console.error('Failed to fetch entity:', err)
    }
  }, [])

  const handleViewportChange = useCallback((vp, z) => {
    setViewport(vp)
    setZoom(z || 4.5)
  }, [])

  const handleFlyToConsumed = useCallback(() => setFlyTo(null), [])

  const handleNearMe = useCallback(() => {
    if (!navigator.geolocation) { alert('Geolocation not supported by your browser.'); return }
    setNearMeLoading(true)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setFlyTo({ lng: pos.coords.longitude, lat: pos.coords.latitude, zoom: 12 })
        setNearMeLoading(false)
      },
      () => {
        alert('Could not get your location. Please allow location access.')
        setNearMeLoading(false)
      },
      { enableHighAccuracy: false, timeout: 8000 }
    )
  }, [])

  const handleExport = useCallback(async (format = 'csv') => {
    setExporting(true)
    try {
      const params = new URLSearchParams()
      params.set('min_lng', viewport.min_lng); params.set('max_lng', viewport.max_lng)
      params.set('min_lat', viewport.min_lat); params.set('max_lat', viewport.max_lat)
      ARRAY_KEYS.forEach(k => { if (filters[k]?.length > 0) params.set(k, filters[k].join(',')) })
      BOOL_KEYS.forEach(k => { if (filters[k]) params.set(k, 'true') })
      STRING_KEYS.forEach(k => { if (filters[k]) params.set(k, filters[k]) })
      params.set('format', format)
      const resp = await fetch(`/api/entities/export?${params}`)
      if (!resp.ok) throw new Error('Export failed')
      const blob = await resp.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url; a.download = `bharat-tech-atlas-export.${format}`
      document.body.appendChild(a); a.click(); document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Export failed:', err)
      alert('Export failed. Try a smaller viewport or fewer filters.')
    }
    setExporting(false)
  }, [viewport, filters])

  const handleShareLink = useCallback(() => {
    navigator.clipboard.writeText(window.location.href)
      .then(() => alert('Link copied to clipboard!'))
      .catch(() => alert(window.location.href))
  }, [])

  const featureCount = geojson?.features?.length || 0
  const displayCount = viewportSummary?.count || totalInViewport || featureCount

  return (
    <ErrorBoundary>
      <div className="relative w-full h-screen overflow-hidden bg-atlas-bg">
        <StartupMap
          geojson={geojson}
          onViewportChange={handleViewportChange}
          onEntityClick={handleEntityClick}
          loading={loading}
          mapMode={mapMode}
          zoom={zoom}
          flyTo={flyTo}
          onFlyToConsumed={handleFlyToConsumed}
        />

        {/* Top Bar */}
        <div className="absolute top-0 left-0 right-0 z-20 pointer-events-none">
          <div className="flex items-start gap-2 sm:gap-3 p-2 sm:p-3">
            <div className="pointer-events-auto flex items-center gap-2 sm:gap-3 flex-1 min-w-0">
              <button onClick={() => setSidebarOpen(!sidebarOpen)}
                className="glass rounded-xl px-2.5 sm:px-3 py-2 sm:py-2.5 shadow-lg hover:bg-atlas-surface transition-colors flex items-center gap-2 flex-shrink-0">
                {isMobile ? (<span className="text-lg">{sidebarOpen ? '✕' : '☰'}</span>) : (<>
                  <span className="text-xl">🗺️</span>
                  <span className="font-bold text-brand-500 hidden sm:inline text-sm">Bharat Tech Atlas</span>
                </>)}
              </button>
              <SearchBar value={filters.search} onChange={(v) => handleFilterChange('search', v)}
                onEntitySelect={(entity) => handleEntityClick(entity.slug)} />
            </div>

            <div className="pointer-events-auto flex items-center gap-1.5 sm:gap-2 flex-shrink-0">
              <div className="glass rounded-xl shadow-lg flex overflow-hidden">
                {[{id:'clusters',label:'⭕',title:'Clusters'},{id:'points',label:'📍',title:'Points'},{id:'heatmap',label:'🔥',title:'Heatmap'}].map(mode => (
                  <button key={mode.id} onClick={() => setMapMode(mode.id)} title={mode.title}
                    className={`px-2.5 sm:px-3 py-2 sm:py-2.5 text-sm transition-colors ${mapMode===mode.id?'bg-brand-600 text-white':'text-atlas-muted hover:text-atlas-text hover:bg-atlas-surface'}`}>
                    {mode.label}
                  </button>
                ))}
              </div>
              <button onClick={handleNearMe} disabled={nearMeLoading} title="Startups near me"
                className="glass rounded-xl px-2.5 sm:px-3 py-2 sm:py-2.5 shadow-lg hover:bg-atlas-surface transition-colors text-sm text-atlas-muted hover:text-atlas-text">
                {nearMeLoading ? <span className="w-4 h-4 border-2 border-brand-500 border-t-transparent rounded-full animate-spin inline-block" /> : '📍'}
              </button>
              <div className="hidden sm:flex items-center gap-1.5">
                <button onClick={() => handleExport('csv')} disabled={exporting} title="Export CSV"
                  className="glass rounded-xl px-2.5 py-2 shadow-lg hover:bg-atlas-surface transition-colors text-sm text-atlas-muted hover:text-atlas-text">
                  {exporting ? '⏳' : '⬇️'}
                </button>
                <button onClick={handleShareLink} title="Copy share link"
                  className="glass rounded-xl px-2.5 py-2 shadow-lg hover:bg-atlas-surface transition-colors text-sm text-atlas-muted hover:text-atlas-text">
                  🔗
                </button>
                <button onClick={() => setAnalyticsOpen(!analyticsOpen)} title="Analytics"
                  className="glass rounded-xl px-2.5 py-2 shadow-lg hover:bg-atlas-surface transition-colors text-sm font-medium text-atlas-muted hover:text-atlas-text">
                  📊
                </button>
                <button onClick={() => setMlInsightsOpen(!mlInsightsOpen)} title="ML Insights"
                  className={`glass rounded-xl px-2.5 py-2 shadow-lg transition-colors text-sm font-medium ${mlInsightsOpen ? 'bg-brand-500/20 text-brand-400' : 'text-atlas-muted hover:text-atlas-text hover:bg-atlas-surface'}`}>
                  🧠
                </button>
                <button onClick={() => setChatOpen(!chatOpen)} title="AI Chatbot"
                  className={`glass rounded-xl px-2.5 py-2 shadow-lg transition-colors text-sm font-medium ${chatOpen ? 'bg-brand-500/20 text-brand-400' : 'text-atlas-muted hover:text-atlas-text hover:bg-atlas-surface'}`}>
                  🤖
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Data Disclaimer */}
        {overview && (
          <div className="absolute bottom-[90px] sm:bottom-[100px] left-1/2 -translate-x-1/2 z-10 pointer-events-none max-w-lg px-2">
            <div className="glass rounded-lg px-3 py-1.5 text-center">
              <p className="text-[10px] text-atlas-muted/80 leading-relaxed">
                Curated dataset of <span className="text-atlas-text font-medium">{overview.total_entities?.toLocaleString()}</span> mapped entities.
                India has <span className="text-atlas-text font-medium">2.23 lakh+</span> DPIIT-registered startups and <span className="text-atlas-text font-medium">1.02 lakh+</span> women-led ventures.
                <span className="text-atlas-muted/50"> · Source: DPIIT, Tracxn, Crunchbase</span>
              </p>
            </div>
          </div>
        )}

        <StatsBar overview={overview} viewportSummary={viewportSummary} featureCount={displayCount} loading={loading} isMobile={isMobile} />

        {sidebarOpen && (
          <>
            {isMobile && <div className="fixed inset-0 bg-black/40 z-20 md:hidden" onClick={() => setSidebarOpen(false)} />}
            <Sidebar filters={filters} facets={facets} onFilterChange={handleFilterChange}
              onReset={handleResetFilters} onClose={() => setSidebarOpen(false)} isMobile={isMobile} />
          </>
        )}

        {selectedEntity && (
          <EntityDetail entity={selectedEntity} onClose={() => setSelectedEntity(null)}
            onEntityClick={handleEntityClick} isMobile={isMobile} />
        )}

        {analyticsOpen && <AnalyticsPanel onClose={() => setAnalyticsOpen(false)} />}
        {mlInsightsOpen && <MLInsightsPanel onClose={() => setMlInsightsOpen(false)} onEntityClick={handleEntityClick} />}
        {chatOpen && <ChatWidget onClose={() => setChatOpen(false)} />}

        {/* Mobile: floating buttons */}
        {isMobile && !analyticsOpen && !mlInsightsOpen && !chatOpen && !sidebarOpen && !selectedEntity && (
          <div className="fixed bottom-20 right-3 z-20 flex flex-col gap-2">
            <button onClick={() => handleExport('csv')} disabled={exporting} title="Export CSV"
              className="glass rounded-full w-10 h-10 flex items-center justify-center shadow-lg pointer-events-auto text-sm">
              {exporting ? '⏳' : '⬇️'}
            </button>
            <button onClick={handleShareLink} title="Share link"
              className="glass rounded-full w-10 h-10 flex items-center justify-center shadow-lg pointer-events-auto text-sm">
              🔗
            </button>
            <button onClick={() => setChatOpen(true)} title="AI Chatbot"
              className="glass rounded-full w-10 h-10 flex items-center justify-center shadow-lg pointer-events-auto text-sm">
              🤖
            </button>
            <button onClick={() => setMlInsightsOpen(true)} title="ML Insights"
              className="glass rounded-full w-10 h-10 flex items-center justify-center shadow-lg pointer-events-auto text-sm">
              🧠
            </button>
            <button onClick={() => setAnalyticsOpen(true)}
              className="glass rounded-full w-10 h-10 flex items-center justify-center shadow-lg pointer-events-auto text-sm">
              📊
            </button>
          </div>
        )}
      </div>
    </ErrorBoundary>
  )
}
