import React, { useState, useRef, useEffect, useCallback } from 'react'

export default function ChatWidget({ onClose }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: "placeholder" }
  ])
  return <div>ChatWidget placeholder</div>
}
