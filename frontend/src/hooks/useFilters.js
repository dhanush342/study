import { useState, useEffect, useCallback } from 'react'

export const INITIAL_FILTERS = {
  entity_type: [], sector: [], stage: [], search: '', dpiit_only: false,
  dpiit_category: [], business_model: [], unicorn_status: [],
  is_women_led: false, is_rural_impact: false, is_campus_startup: false,
  nsa_winner: false, state: '', city: '',
}
const ARRAY_KEYS = ['entity_type','sector','stage','dpiit_category','business_model','unicorn_status']
const BOOL_KEYS = ['dpiit_only','is_women_led','is_rural_impact','is_campus_startup','nsa_winner']
const STRING_KEYS = ['search','state','city']

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
  window.history.replaceState(null, '', qs ? `${window.location.pathname}?${qs}` : window.location.pathname)
}

export default function useFilters() {
  const [filters, setFilters] = useState(() => filtersFromURL())
  useEffect(() => { filtersToURL(filters) }, [filters])
  const handleFilterChange = useCallback((key, value) => setFilters(prev => ({ ...prev, [key]: value })), [])
  const handleResetFilters = useCallback(() => setFilters(INITIAL_FILTERS), [])
  const buildFilterParams = useCallback((params) => {
    ARRAY_KEYS.forEach(k => { if (filters[k]?.length > 0) params.set(k, filters[k].join(',')) })
    BOOL_KEYS.forEach(k => { if (filters[k]) params.set(k, 'true') })
    STRING_KEYS.forEach(k => { if (filters[k]) params.set(k, filters[k]) })
    return params
  }, [filters])
  return { filters, setFilters, handleFilterChange, handleResetFilters, buildFilterParams }
}
