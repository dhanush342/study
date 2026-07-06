import React, { useRef, useCallback, useState, useEffect, useMemo } from 'react'
import Map, { Source, Layer, NavigationControl, Popup } from 'react-map-gl/maplibre'
import 'maplibre-gl/dist/maplibre-gl.css'

const MAP_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"

const ENTITY_COLORS = {
  startup: '#3B82F6', sme: '#10B981', college_ecell: '#FBBF24',
  incubator: '#A855F7', accelerator: '#EC4899', coworking: '#14B8A6', investor: '#EF4444',
}
const ENTITY_LABELS = {
  startup: '🚀 Startup', sme: '🏢 SME', college_ecell: '🎓 E-Cell',
  incubator: '🧪 Incubator', accelerator: '⚡ Accelerator',
}

// ─── Safe social icons (React elements, not raw HTML) ──────────────────────────
const SafeSocialIcon = ({ icon }) => {
  const icons = {
    linkedin: <span style={{ fontSize: 14 }}>💼</span>,
    twitter: <span style={{ fontSize: 14 }}>𝕏</span>,
    instagram: <span style={{ fontSize: 14 }}>📸</span>,
    facebook: <span style={{ fontSize: 14 }}>📘</span>,
    website: <span style={{ fontSize: 14 }}>🌐</span>,
    google: <span style={{ fontSize: 14 }}>🔍</span>,
  }
  return icons[icon] || <span style={{ fontSize: 14 }}>🔗</span>
}

// ─── URL validation helper ───────────────────────────────────────────────────
function isValidHttpUrl(url) {
  if (!url || typeof url !== 'string') return false
  try {
    const u = new URL(url)
    return u.protocol === 'http:' || u.protocol === 'https:'
  } catch {
    return false
  }
}

function sanitizeUrl(url) {
  if (!url) return ''
  // Remove javascript: and data: prefixes
  const lower = url.trim().toLowerCase()
  if (lower.startsWith('javascript:') || lower.startsWith('data:') || lower.startsWith('vbscript:')) {
    return ''
  }
  return url
}

function SocialLinks({ entity }) {
  const links = []
  const name = entity.name

  if (entity.linkedin_url && isValidHttpUrl(entity.linkedin_url)) links.push({ name: 'LinkedIn', url: sanitizeUrl(entity.linkedin_url), icon: 'linkedin', color: '#0A66C2' })
  if (entity.twitter_url && isValidHttpUrl(entity.twitter_url)) links.push({ name: 'X (Twitter)', url: sanitizeUrl(entity.twitter_url), icon: 'twitter', color: '#000000' })
  if (entity.instagram_url && isValidHttpUrl(entity.instagram_url)) links.push({ name: 'Instagram', url: sanitizeUrl(entity.instagram_url), icon: 'instagram', color: '#E4405F' })
  if (entity.facebook_url && isValidHttpUrl(entity.facebook_url)) links.push({ name: 'Facebook', url: sanitizeUrl(entity.facebook_url), icon: 'facebook', color: '#1877F2' })
  if (entity.website && isValidHttpUrl(entity.website)) links.push({ name: 'Website', url: sanitizeUrl(entity.website), icon: 'website', color: '#6366F1' })

  // Always add search links even if no stored URL
  const encName = encodeURIComponent(name)
  const slug = name.toLowerCase().replace(/\s+/g, '-').replace('.', '')
  if (!entity.linkedin_url) links.push({ name: 'LinkedIn', url: `https://www.linkedin.com/search/results/companies/?keywords=${encName}`, icon: 'linkedin', color: '#0A66C2', search: true })
  if (!entity.twitter_url) links.push({ name: 'X', url: `https://x.com/search?q=${encName}&src=typed_query`, icon: 'twitter', color: '#000000', search: true })
  if (!entity.instagram_url) links.push({ name: 'Instagram', url: `https://www.instagram.com/${slug}`, icon: 'instagram', color: '#E4405F', search: true })
  if (!entity.website) links.push({ name: 'Google', url: `https://www.google.com/search?q=${encName}+company`, icon: 'google', color: '#4285F4', search: true })
  links.push({ name: 'Crunchbase', url: `https://www.crunchbase.com/organization/${slug}`, icon: 'crunchbase', color: '#0288D1', search: true })
  links.push({ name: 'Tracxn', url: `https://tracxn.com/d/companies/${slug}/`, icon: 'tracxn', color: '#FF6F00', search: true })

  return (
    <div className="flex flex-wrap gap-1.5 mt-2">
      {links.filter(l => isValidHttpUrl(l.url)).map(l => (
        <a
          key={l.name + l.url}
          href={l.url}
          target="_blank"
          rel="noopener noreferrer"
          title={`${l.name}${l.search ? ' (search)' : ''}`}
          className="inline-flex items-center gap-1 text-[10px] px-2 py-1 rounded-md font-medium transition-colors hover:opacity-80"
          style={{ backgroundColor: `${l.color}20`, color: l.color }}
        >
          <SafeSocialIcon icon={l.icon === 'crunchbase' || l.icon === 'tracxn' ? 'website' : l.icon} />
          {l.name}
          {l.search && <span className="opacity-50">↗</span>}
        </a>
      ))}
    </div>
  )
}

function PopupContent({ properties, onDetailClick }) {
  const p = properties
  const color = ENTITY_COLORS[p.entity_type] || '#64748B'
  const label = ENTITY_LABELS[p.entity_type] || p.entity_type
  let sectors = p.sectors
  if (typeof sectors === 'string') { try { sectors = JSON.parse(sectors) } catch { sectors = [] } }

  return (
    <div className="w-[300px] sm:w-80">
      <div className="px-4 py-3 border-b border-atlas-border" style={{ borderTop: `3px solid ${color}` }}>
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h3 className="font-semibold text-atlas-text text-sm leading-tight truncate">{p.name}</h3>
            <p className="text-xs text-atlas-muted mt-0.5">📍 {p.city}, {p.state}</p>
          </div>
          <span className="text-xs font-medium px-2 py-0.5 rounded-full whitespace-nowrap flex-shrink-0"
                style={{ backgroundColor: `${color}20`, color }}>{label}</span>
        </div>
      </div>
      <div className="px-4 py-2.5 space-y-2">
        {p.description && <p className="text-xs text-atlas-muted line-clamp-2">{p.description}</p>}
        <div className="flex flex-wrap gap-1">
          {p.dpiit_recognized && <span className="text-xs bg-emerald-500/20 text-emerald-300 px-1.5 py-0.5 rounded ring-1 ring-emerald-500/20">✅ Verified</span>}
          {p.unicorn_status === 'unicorn' && <span className="text-xs font-bold unicorn-badge">🦄 Unicorn</span>}
          {p.is_women_led && <span className="text-xs bg-pink-500/20 text-pink-300 px-1.5 py-0.5 rounded">👩 Women-led</span>}
          {p.nsa_winner && <span className="text-xs bg-amber-500/20 text-amber-300 px-1.5 py-0.5 rounded">🏆 NSA</span>}
        </div>
        <div className="flex flex-wrap gap-1">
          {(Array.isArray(sectors) ? sectors : []).slice(0, 4).map(s => (
            <span key={s} className="text-xs bg-atlas-border text-atlas-muted px-2 py-0.5 rounded-full">{s}</span>
          ))}
        </div>
        <div className="flex items-center gap-3 text-xs text-atlas-muted">
          {p.founded_year && <span>📅 {p.founded_year}</span>}
          {p.linkedin_team_size && <span>👥 {p.linkedin_team_size}</span>}
          {p.funding_display && p.funding_display !== 'Bootstrapped' && <span>💰 {p.funding_display}</span>}
        </div>

        {/* Social Media Links */}
        <SocialLinks entity={p} />

        {/* AI Analysis button */}
        <div className="pt-1">
          <a
            href={`/api/agent/analyze-startup?company_name=${encodeURIComponent(p.name)}&sector=${encodeURIComponent((Array.isArray(sectors) ? sectors[0] : '') || '')}&city=${encodeURIComponent(p.city || '')}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-[10px] px-2 py-1 rounded-md bg-brand-500/10 text-brand-400 hover:bg-brand-500/20 transition-colors"
          >
            🤖 AI Analysis
          </a>
          <a
            href={`/api/agent/social-links/${encodeURIComponent(p.slug || '')}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-[10px] px-2 py-1 rounded-md bg-atlas-surface text-atlas-muted hover:text-atlas-text transition-colors ml-1"
          >
            🔗 All Profiles
          </a>
        </div>
      </div>
      <div className="px-4 py-2.5 border-t border-atlas-border">
        <button onClick={onDetailClick}
          className="w-full text-center text-sm font-medium text-brand-500 hover:text-brand-400 hover:bg-brand-500/10 rounded-lg py-1.5 transition-colors">
          View Full Profile →
        </button>
      </div>
    </div>
  )
}

export default function StartupMap({ geojson, onViewportChange, onEntityClick, loading, mapMode, zoom: currentZoom, flyTo, onFlyToConsumed }) {
  const mapRef = useRef(null)
  const [popup, setPopup] = useState(null)

  useEffect(() => {
    if (flyTo && mapRef.current) {
      mapRef.current.flyTo({
        center: [flyTo.lng, flyTo.lat],
        zoom: flyTo.zoom || 8,
        duration: 1800,
        essential: true,
        curve: 1.42,
      })
      onFlyToConsumed?.()
    }
  }, [flyTo, onFlyToConsumed])

  const onMoveEnd = useCallback((evt) => {
    const map = evt.target
    const bounds = map.getBounds()
    const z = map.getZoom()
    onViewportChange({
      min_lng: bounds.getWest(),
      max_lng: bounds.getEast(),
      min_lat: bounds.getSouth(),
      max_lat: bounds.getNorth(),
    }, z)
  }, [onViewportChange])

  const isClusterMode = useMemo(() => geojson?.cluster_mode === true, [geojson])

  const onMapClick = useCallback((evt) => {
    const pf = evt.target.queryRenderedFeatures(evt.point, { layers: ['entity-points', 'entity-icons'] })
    if (pf.length > 0) {
      const feature = pf[0]
      const props = feature.properties
      let sectors = props.sectors
      if (typeof sectors === 'string') { try { sectors = JSON.parse(sectors) } catch { sectors = [] } }
      setPopup({
        longitude: feature.geometry.coordinates[0],
        latitude: feature.geometry.coordinates[1],
        properties: { ...props, sectors },
        isCluster: false,
      })
      return
    }
    const cf = evt.target.queryRenderedFeatures(evt.point, { layers: ['server-clusters'] })
    if (cf.length > 0) {
      const cluster = cf[0]
      const targetZoom = Math.min((cluster.properties.expansion_zoom || currentZoom + 2), 18)
      evt.target.flyTo({ center: cluster.geometry.coordinates, zoom: targetZoom, duration: 800 })
      return
    }
    const ccf = evt.target.queryRenderedFeatures(evt.point, { layers: ['client-clusters'] })
    if (ccf.length > 0) {
      const src = evt.target.getSource('entities')
      if (src?.getClusterExpansionZoom) {
        src.getClusterExpansionZoom(ccf[0].properties.cluster_id, (err, z) => {
          if (!err) evt.target.flyTo({ center: ccf[0].geometry.coordinates, zoom: z + 1, duration: 800 })
        })
      }
    }
  }, [currentZoom])

  const onMouseEnter = useCallback(() => {
    if (mapRef.current) mapRef.current.getCanvas().style.cursor = 'pointer'
  }, [])
  const onMouseLeave = useCallback(() => {
    if (mapRef.current) mapRef.current.getCanvas().style.cursor = ''
  }, [])

  const showHeatmap = mapMode === 'heatmap'
  const showClusters = mapMode === 'clusters'
  const showPoints = mapMode === 'points'

  const { clusterFeatures, pointFeatures } = useMemo(() => {
    if (!geojson?.features) return { clusterFeatures: null, pointFeatures: null }
    if (isClusterMode) return { clusterFeatures: { type: 'FeatureCollection', features: geojson.features }, pointFeatures: null }
    return { clusterFeatures: null, pointFeatures: geojson }
  }, [geojson, isClusterMode])

  const interactiveLayers = useMemo(() => {
    const l = ['entity-points', 'entity-icons']
    if (isClusterMode) l.push('server-clusters')
    if (showPoints) l.push('client-clusters')
    return l
  }, [isClusterMode, showPoints])

  return (
    <Map
      ref={mapRef}
      initialViewState={{ longitude: 78.5, latitude: 22.0, zoom: 4.5 }}
      style={{ width: '100%', height: '100%' }}
      mapStyle={MAP_STYLE}
      onMoveEnd={onMoveEnd}
      onClick={onMapClick}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      interactiveLayerIds={interactiveLayers}
      maxBounds={[[60, 2], [100, 40]]}
    >
      <NavigationControl position="bottom-right" showCompass={false} />

      {showClusters && clusterFeatures && (
        <Source id="server-clusters" type="geojson" data={clusterFeatures}>
          <Layer id="server-clusters" type="circle" paint={{
            'circle-color': ['step', ['get', 'point_count'], '#7C3AED', 10, '#A855F7', 50, '#EC4899', 200, '#F97316', 500, '#FBBF24'],
            'circle-radius': ['interpolate', ['linear'], ['get', 'point_count'], 1, 18, 10, 24, 50, 32, 200, 40, 500, 50, 1000, 58],
            'circle-stroke-width': 3,
            'circle-stroke-color': ['step', ['get', 'point_count'], 'rgba(124,58,237,0.4)', 10, 'rgba(168,85,247,0.4)', 50, 'rgba(236,72,153,0.4)', 200, 'rgba(249,115,22,0.4)', 500, 'rgba(251,191,36,0.4)'],
            'circle-opacity': 0.92,
            'circle-blur': 0.05,
          }} />
          <Layer id="server-clusters-glow" type="circle" paint={{
            'circle-color': 'transparent',
            'circle-radius': ['interpolate', ['linear'], ['get', 'point_count'], 1, 24, 10, 30, 50, 40, 200, 50, 500, 62, 1000, 72],
            'circle-stroke-width': 1.5,
            'circle-stroke-color': ['step', ['get', 'point_count'], 'rgba(124,58,237,0.15)', 50, 'rgba(236,72,153,0.15)', 200, 'rgba(249,115,22,0.15)', 500, 'rgba(251,191,36,0.2)'],
            'circle-stroke-opacity': 0.6,
          }} />
          <Layer id="server-cluster-count" type="symbol" layout={{
            'text-field': ['get', 'point_count_abbreviated'],
            'text-font': ['Open Sans Bold'],
            'text-size': ['interpolate', ['linear'], ['get', 'point_count'], 1, 12, 50, 14, 200, 16, 1000, 18],
            'text-allow-overlap': true,
          }} paint={{ 'text-color': '#fff', 'text-halo-color': 'rgba(0,0,0,0.3)', 'text-halo-width': 1 }} />
          <Layer id="server-cluster-label" type="symbol" layout={{
            'text-field': ['get', 'city_label'],
            'text-font': ['Open Sans Semibold'],
            'text-size': 10, 'text-offset': [0, 3.5], 'text-anchor': 'top', 'text-max-width': 12, 'text-optional': true,
          }} paint={{ 'text-color': '#94A3B8', 'text-halo-color': '#0F172A', 'text-halo-width': 2, 'text-opacity': 0.8 }} />
        </Source>
      )}

      {pointFeatures && (showClusters || showPoints || showHeatmap) && (
        <Source id="entities" type="geojson" data={pointFeatures}
          cluster={showPoints} clusterMaxZoom={14} clusterRadius={50}
          clusterProperties={{ sum_startup: ['+', ['case', ['==', ['get', 'entity_type'], 'startup'], 1, 0]] }}
        >
          {showPoints && (<>
            <Layer id="client-clusters" type="circle" filter={['has', 'point_count']} paint={{
              'circle-color': ['step', ['get', 'point_count'], '#7C3AED', 10, '#A855F7', 50, '#EC4899', 200, '#F97316', 500, '#FBBF24'],
              'circle-radius': ['step', ['get', 'point_count'], 20, 10, 26, 50, 32, 200, 40, 500, 48],
              'circle-stroke-width': 2, 'circle-stroke-color': 'rgba(255,255,255,0.3)', 'circle-opacity': 0.9,
            }} />
            <Layer id="client-cluster-count" type="symbol" filter={['has', 'point_count']} layout={{
              'text-field': '{point_count_abbreviated}', 'text-font': ['Open Sans Bold'],
              'text-size': ['step', ['get', 'point_count'], 13, 50, 15, 500, 17],
            }} paint={{ 'text-color': '#ffffff' }} />
          </>)}

          {showHeatmap && (
            <Layer id="heatmap-layer" type="heatmap" paint={{
              'heatmap-weight': ['interpolate', ['linear'], ['coalesce', ['get', 'funding_weight'], 0.1], 0, 0.1, 1, 1],
              'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 0, 1, 9, 3],
              'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 0, 4, 5, 20, 9, 40, 12, 60],
              'heatmap-color': ['interpolate', ['linear'], ['heatmap-density'], 0, 'rgba(0,0,0,0)', 0.1, 'rgba(15,23,42,0.3)', 0.2, 'rgb(49,46,129)', 0.4, 'rgb(124,58,237)', 0.6, 'rgb(236,72,153)', 0.8, 'rgb(249,115,22)', 1.0, 'rgb(253,224,71)'],
              'heatmap-opacity': ['interpolate', ['linear'], ['zoom'], 5, 0.9, 10, 0.7, 14, 0.3],
            }} />
          )}

          <Layer id="entity-points" type="circle"
            filter={showPoints ? ['!', ['has', 'point_count']] : ['all']}
            paint={{
              'circle-color': ['match', ['get', 'entity_type'], 'startup', '#3B82F6', 'sme', '#10B981', 'college_ecell', '#FBBF24', 'incubator', '#A855F7', 'accelerator', '#EC4899', '#64748B'],
              'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, showHeatmap ? 2 : 4, 8, showHeatmap ? 3 : 6, 12, showHeatmap ? 5 : 9, 16, showHeatmap ? 8 : 14],
              'circle-stroke-width': ['case', ['==', ['get', 'unicorn_status'], 'unicorn'], 3, 1.5],
              'circle-stroke-color': ['case', ['==', ['get', 'unicorn_status'], 'unicorn'], '#FBBF24', 'rgba(255,255,255,0.3)'],
              'circle-opacity': showHeatmap ? ['interpolate', ['linear'], ['zoom'], 5, 0, 10, 0.5, 14, 1] : 0.9,
            }}
          />

          <Layer id="entity-icons" type="symbol"
            filter={['all', showPoints ? ['!', ['has', 'point_count']] : ['all'], ['>=', ['zoom'], 10]]}
            layout={{
              'text-field': ['match', ['get', 'entity_type'], 'startup', '🚀', 'sme', '🏢', 'college_ecell', '🎓', 'incubator', '🧪', 'accelerator', '⚡', '📍'],
              'text-size': ['interpolate', ['linear'], ['zoom'], 10, 12, 14, 18, 18, 24],
              'text-allow-overlap': false,
              'text-ignore-placement': false,
              'symbol-sort-key': ['case', ['==', ['get', 'unicorn_status'], 'unicorn'], 0, ['==', ['get', 'entity_type'], 'incubator'], 1, 5],
            }}
            paint={{
              'text-opacity': ['interpolate', ['linear'], ['zoom'], 10, 0, 11, 0.8, 13, 1],
            }}
          />

          <Layer id="entity-labels" type="symbol"
            filter={['all', showPoints ? ['!', ['has', 'point_count']] : ['all'], ['>=', ['zoom'], 13]]}
            layout={{
              'text-field': ['get', 'name'], 'text-font': ['Open Sans Semibold'],
              'text-size': 11, 'text-offset': [0, 1.6], 'text-anchor': 'top', 'text-max-width': 10,
            }}
            paint={{ 'text-color': '#E2E8F0', 'text-halo-color': '#0F172A', 'text-halo-width': 2 }}
          />
        </Source>
      )}

      {popup && !popup.isCluster && (
        <Popup longitude={popup.longitude} latitude={popup.latitude}
          onClose={() => setPopup(null)} closeOnClick={false} maxWidth="400px" offset={15}>
          <PopupContent properties={popup.properties} onDetailClick={() => { onEntityClick(popup.properties.slug); setPopup(null) }} />
        </Popup>
      )}

      {loading && (
        <div className="absolute top-20 left-1/2 -translate-x-1/2 z-10">
          <div className="glass rounded-full px-4 py-2 shadow-lg flex items-center gap-2">
            <div className="w-4 h-4 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
            <span className="text-sm text-atlas-muted">Loading…</span>
          </div>
        </div>
      )}

      {!geojson && loading && (
        <div className="absolute inset-0 z-[5] flex items-center justify-center pointer-events-none">
          <div className="space-y-3 w-64">
            <div className="h-3 bg-atlas-surface/60 rounded-full animate-pulse" />
            <div className="h-3 bg-atlas-surface/40 rounded-full animate-pulse w-3/4" />
            <div className="h-3 bg-atlas-surface/30 rounded-full animate-pulse w-1/2" />
            <div className="flex gap-2 justify-center mt-4">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="w-10 h-10 bg-atlas-surface/40 rounded-full animate-pulse" />
              ))}
            </div>
            <p className="text-xs text-atlas-muted/60 text-center mt-2">Loading startup data…</p>
          </div>
        </div>
      )}
    </Map>
  )
}
