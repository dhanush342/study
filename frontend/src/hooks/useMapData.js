import { useState, useEffect, useRef, useCallback } from 'react'

export default function useMapData(filters, viewport, zoom, mapMode, buildFilterParams) {
  const [geojson, setGeojson] = useState(null)
  const [loading, setLoading] = useState(true)
  const [totalInViewport, setTotalInViewport] = useState(0)
  const abortRef = useRef(null)
  const debounceRef = useRef(null)

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
      const endpoint = mapMode === 'heatmap' ? `/api/entities/geojson?${params}&max_features=5000` : `/api/entities/clusters?${params}`
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
    debounceRef.current = setTimeout(fetchData, 200)
    return () => clearTimeout(debounceRef.current)
  }, [fetchData])

  return { geojson, loading, totalInViewport, fetchData }
}
