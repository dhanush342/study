import React, { useState, useRef, useEffect, useCallback } from 'react'

const SUGGESTIONS = [
  "What are the top fintech unicorns?",
  "Tell me about SaaS startups in Bangalore",
  "What is DPIIT recognition?",
  "Which sectors are growing fastest?",
  "Compare edtech vs healthtech",
  "Latest news about Indian startups 2025",
]

// ─── XSS Prevention: escape HTML special chars ────────────────────────────────
function escapeHtml(text) {
  if (!text) return ''
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
}

// ─── XSS Prevention: strip script tags and event handlers ─────────────────────
function sanitizeChatContent(text) {
  if (!text) return ''
  let t = text
  // Remove script tags
  t = t.replace(/<script[^>]*>.*?<\/script>/gi, '')
  // Remove iframe tags
  t = t.replace(/<iframe[^>]*>.*?<\/iframe>/gi, '')
  // Remove event handlers (onerror, onclick, etc.)
  t = t.replace(/\son\w+\s*=\s*["']?[^"'>]*["']?/gi, '')
  // Remove javascript: and data: URLs
  t = t.replace(/(javascript|data|vbscript):/gi, '')
  // Remove meta refresh
  t = t.replace(/<meta[^>]*http-equiv\s*=\s*["']?refresh["']?[^>]*>/gi, '')
  return t
}

// ─── Render sanitized text with basic Markdown (no raw HTML) ──────────────────
function SafeMarkdown({ text }) {
  if (!text) return null
  const sanitized = sanitizeChatContent(text)
  // Convert **bold**, *italic*, `code`, and bullet points to HTML safely
  let html = escapeHtml(sanitized)
    // Bold
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // Italic
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // Inline code
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // Bullet points (simple)
    .replace(/^\s*-\s+/gm, '• ')
    // Numbered lists
    .replace(/^\s*(\d+)\.\s+/gm, '$1. ')
    // Line breaks
    .replace(/\n/g, '<br>')

  return <span dangerouslySetInnerHTML={{ __html: html }} />
}

export default function ChatWidget({ onClose }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: "👋 Hi! I'm Bharat Tech Atlas AI. Ask me about Indian startups, sectors, funding trends, or any company!" }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const scrollRef = useRef(null)
  // Use a ref to always read the latest messages without stale closure issues
  const messagesRef = useRef(messages)
  useEffect(() => { messagesRef.current = messages }, [messages])

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = useCallback(async (text) => {
    if (!text.trim() || loading) return
    const userMsg = { role: 'user', content: text }

    // 1) Optimistically add user message to UI
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    // 2) Build request body from the ref (guaranteed up-to-date)
    const currentMessages = [...messagesRef.current, userMsg]
    const payload = {
      messages: currentMessages.map(m => ({ role: m.role, content: m.content })),
      stream: false,
    }

    try {
      const resp = await fetch('/api/chat/completions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!resp.ok) {
        const errText = await resp.text()
        throw new Error(`HTTP ${resp.status}: ${errText}`)
      }
      const data = await resp.json()
      // Sanitize response before displaying
      const safeContent = sanitizeChatContent(data.content) || 'Sorry, I had trouble responding. Try again!'
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: safeContent
      }])
    } catch (err) {
      console.error('Chat error:', err)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '⚠️ Network error. Please try again in a moment.'
      }])
    } finally {
      setLoading(false)
    }
  }, [loading])

  return (
    <div className="fixed bottom-4 right-4 z-50 w-[380px] max-w-[calc(100vw-2rem)] h-[520px] max-h-[calc(100vh-2rem)] bg-atlas-bg border border-atlas-border rounded-2xl shadow-2xl flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-atlas-border bg-atlas-surface">
        <div className="flex items-center gap-2">
          <span className="text-lg">🤖</span>
          <div>
            <h3 className="text-sm font-semibold text-atlas-text">Bharat Tech Atlas AI</h3>
            <p className="text-[10px] text-atlas-muted">Powered by Qwen2.5-0.5B + Web Search</p>
          </div>
        </div>
        <button onClick={onClose} className="text-atlas-muted hover:text-atlas-text text-lg" aria-label="Close chat">✕</button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] rounded-xl px-3 py-2 text-xs leading-relaxed whitespace-pre-wrap ${
              m.role === 'user'
                ? 'bg-brand-500/20 text-brand-300 rounded-br-none'
                : 'bg-atlas-surface text-atlas-muted rounded-bl-none'
            }`}>
              {m.role === 'user' ? (
                <span>{m.content}</span>
              ) : (
                <SafeMarkdown text={m.content} />
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-atlas-surface rounded-xl rounded-bl-none px-3 py-2">
              <div className="flex gap-1">
                <span className="w-1.5 h-1.5 bg-atlas-muted rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-1.5 h-1.5 bg-atlas-muted rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-1.5 h-1.5 bg-atlas-muted rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
        <div ref={scrollRef} />
      </div>

      {/* Suggestions */}
      {messages.length < 3 && (
        <div className="px-3 pb-2 flex flex-wrap gap-1.5">
          {SUGGESTIONS.map(s => (
            <button key={s} onClick={() => sendMessage(s)}
              className="text-[10px] px-2 py-1 rounded-full bg-atlas-surface border border-atlas-border text-atlas-muted hover:text-atlas-text hover:border-brand-500/30 transition-colors">
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="px-3 py-2 border-t border-atlas-border flex gap-2">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && sendMessage(input)}
          placeholder="Ask about startups, sectors, funding, latest news..."
          maxLength={2000}
          className="flex-1 bg-atlas-surface border border-atlas-border rounded-lg px-3 py-2 text-xs text-atlas-text placeholder:text-atlas-muted/50 focus:outline-none focus:border-brand-500/50"
        />
        <button onClick={() => sendMessage(input)} disabled={loading || !input.trim()}
          className="px-3 py-2 bg-brand-500/20 text-brand-400 rounded-lg text-xs font-medium hover:bg-brand-500/30 disabled:opacity-30 transition-colors">
          Send
        </button>
      </div>
    </div>
  )
}
