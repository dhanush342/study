import React, { useState } from 'react'

export default function StatsBar({ overview, viewportSummary, featureCount, loading, isMobile }) {
  const [collapsed, setCollapsed] = useState(false)

  if (!overview) return null

  const cards = [
    {
      label: 'In View',
      value: viewportSummary?.count || featureCount,
      icon: '📍',
      desc: 'Entities visible on map',
    },
    {
      label: 'Mapped',
      value: overview.total_entities,
      icon: '🏢',
      desc: 'Curated entities in our database',
    },
    {
      label: 'Startups',
      value: overview.by_type?.startup || 0,
      icon: '🚀',
      desc: 'Mapped startups (India has 223K+ DPIIT-registered)',
    },
    {
      label: 'Unicorns',
      value: overview.unicorn_count || 0,
      icon: '🦄',
      desc: 'Valued >$1B',
    },
    {
      label: 'Women-led',
      value: overview.women_led_count || 0,
      icon: '👩',
      desc: 'In our dataset (India has 102K+ women-led startups)',
    },
    {
      label: 'Funding',
      value: overview.total_funding_display,
      icon: '💰',
      desc: 'Mapped entities only — not total Indian startup funding',
      isText: true,
    },
  ]

  return (
    <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-20 pointer-events-none">
      {/* Collapse toggle */}
      <div className="flex justify-center mb-2">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="pointer-events-auto glass rounded-full px-3 py-1 text-xs text-atlas-muted hover:text-atlas-text transition-colors shadow-lg"
        >
          {collapsed ? '▲ Show Stats' : '▼ Hide'}
        </button>
      </div>

      {!collapsed && (
        <div className={`flex items-stretch gap-2 sm:gap-3 px-3 sm:px-4 pointer-events-auto animate-fade-in ${isMobile ? 'overflow-x-auto pb-1 scrollbar-thin' : ''}`}>
          {cards.map((card) => (
            <div
              key={card.label}
              className="relative rounded-2xl border border-atlas-border bg-atlas-bg/90 shadow-lg px-3 sm:px-4 py-2.5 sm:py-3 min-w-[100px] sm:min-w-[120px] cursor-default"
              title={card.desc}
            >
              <div className="flex items-start gap-2.5">
                <span className="text-lg mt-0.5">{card.icon}</span>
                <div>
                  <p className="text-base font-bold text-atlas-text leading-none tabular-nums">
                    {typeof card.value === 'number' ? card.value.toLocaleString() : card.value}
                  </p>
                  <p className="text-[10px] text-atlas-muted leading-none mt-1.5 uppercase tracking-wider font-medium">
                    {card.label}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
