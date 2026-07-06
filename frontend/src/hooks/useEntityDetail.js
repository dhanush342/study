import { useState, useCallback } from 'react'

export default function useEntityDetail(isMobile, setSidebarOpen) {
  const [selectedEntity, setSelectedEntity] = useState(null)
  const handleEntityClick = useCallback(async (slug, onFlyTo) => {
    try {
      const resp = await fetch(`/api/entities/detail/${slug}`)
      const data = await resp.json()
      setSelectedEntity(data)
      if (data.latitude && data.longitude && onFlyTo) onFlyTo({ lng: data.longitude, lat: data.latitude, zoom: 14 })
      if (isMobile && setSidebarOpen) setSidebarOpen(false)
      return data
    } catch (err) {
      console.error('Failed to fetch entity:', err)
      return null
    }
  }, [isMobile, setSidebarOpen])
  const handleClose = useCallback(() => setSelectedEntity(null), [])
  return { selectedEntity, setSelectedEntity, handleEntityClick, handleClose }
}
