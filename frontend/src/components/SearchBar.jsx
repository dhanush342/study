import React, { useState, useRef, useEffect, useMemo } from 'react'
import { Search, X, MapPin } from 'lucide-react'
import Fuse from 'fuse.js'

const ENTITY_ICONS = { startup: '🚀', sme: '🏢', college_ecell: '🎓', incubator: '🧪', accelerator: '⚡' }

export default function SearchBar({ value, onChange, onEntitySelect }) {
  const [focused, setFocused] = useState(false)
  const [suggestions, setSuggestions] = useState([])
  const [localCache, setLocalCache] = useState([])
  const inputRef = useRef(null)
  const debounceRef = useRef(null)

  // Build fuse index from cached results for instant sub-filtering
  const fuse = useMemo(() => {
    if (localCache.length === 0) return null
    return new Fuse(localCache, {
      keys: [
        { name: 'name', weight: 0.6 },
        { name: 'city', weight: 0.2 },
        { name: 'description', weight: 0.1 },
        { name: 'state', weight: 0.1 },
      ],
      threshold: 0.4,
      includeScore: true,
    })
  }, [localCache])

  useEffect(() => {
    if (!value || value.length < 2) { setSuggestions([]); return }

    // Instant client-side fuzzy if we have cached results
    if (fuse && value.length >= 3) {
      const results = fuse.search(value).slice(0, 8).map(r => r.item)
      if (results.length > 0) {
        setSuggestions(results)
      }
    }

    // Also fetch from server (debounced) for fresh results
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(async () => {
      try {
        const resp = await fetch(`/api/entities/search?q=${encodeURIComponent(value)}&limit=10`)
        const data = await resp.json()
        const results = data.results || []
        setSuggestions(results)
        // Merge into local cache for future fuzzy queries
        setLocalCache(prev => {
          const ids = new Set(prev.map(p => p.id))
          const newItems = results.filter(r => !ids.has(r.id))
          return [...prev, ...newItems].slice(-200) // keep last 200
        })
      } catch (err) { console.error(err) }
    }, 250)

    return () => clearTimeout(debounceRef.current)
  }, [value, fuse])

  const handleSelect = (entity) => {
    onChange(entity.name)
    setSuggestions([])
    onEntitySelect?.(entity)
    inputRef.current?.blur()
  }

  return (
    <div className="relative flex-1 max-w-xs sm:max-w-md">
      <div className={`glass rounded-xl shadow-lg flex items-center gap-2 px-3 py-2 transition-all ${focused ? 'ring-2 ring-brand-500' : ''}`}>
        <Search size={16} className="text-atlas-muted flex-shrink-0" />
        <input
          ref={inputRef} type="text" value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setTimeout(() => setFocused(false), 200)}
          placeholder="Search startups, cities…"
          className="flex-1 bg-transparent text-sm text-atlas-text placeholder:text-atlas-muted/60 outline-none min-w-0"
        />
        {value && (
          <button onClick={() => { onChange(''); setSuggestions([]); inputRef.current?.focus() }} className="p-0.5 hover:bg-atlas-surface rounded">
            <X size={14} className="text-atlas-muted" />
          </button>
        )}
      </div>

      {focused && suggestions.length > 0 && (
        <div className="absolute top-full left-0 right-0 mt-1 glass rounded-xl shadow-xl overflow-hidden z-50 max-h-80 overflow-y-auto">
          {suggestions.map((s) => (
            <button key={s.id}
              onMouseDown={(e) => { e.preventDefault(); handleSelect(s) }}
              className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-atlas-surface transition-colors text-left">
              <span className="text-sm flex-shrink-0">{ENTITY_ICONS[s.entity_type] || '📍'}</span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-atlas-text truncate">{s.name}</p>
                <div className="flex items-center gap-1.5 text-xs text-atlas-muted">
                  <MapPin size={10} />
                  <span className="truncate">{s.city}, {s.state}</span>
                  {s.unicorn_status === 'unicorn' && <span>🦄</span>}
                  {s.is_women_led === 1 && <span>👩</span>}
                </div>
              </div>
              {s.funding_crores > 0 && (
                <span className="text-[10px] text-atlas-muted/60 flex-shrink-0">
                  {s.funding_crores >= 10000
                    ? `₹${(s.funding_crores / 100000).toFixed(2)} L Cr`
                    : s.funding_crores >= 100
                    ? `₹${s.funding_crores.toLocaleString('en-IN')} Cr`
                    : `₹${s.funding_crores.toFixed(1)} Cr`
                  }
                </span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
