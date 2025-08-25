import React, { useMemo, useRef, useState } from 'react'
import { Button, Card, Input, List, message as antdMessage } from 'antd'
import { generate } from '@/services/llm'
import { useChatStore } from '@/stores/chat'

export default function ChatInterface() {
  const { msgs, add } = useChatStore()
  const [input, setInput] = useState('')
  const listRef = useRef<HTMLDivElement | null>(null)

  const [loading, setLoading] = useState(false)

  const send = async () => {
    if (!input.trim()) return
    const userMsg = { id: Date.now(), role: 'user' as const, text: input }
    add(userMsg)
    const toSend = input
    setInput('')
    setLoading(true)
    try {
      // First try streaming
      const res = await fetch('/api/llm/generate_stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: [{ role: 'user', content: toSend }] }),
      })
      if (!res.ok || !res.body) {
        const reply = await generate([{ role: 'user', content: toSend }])
        add({ id: Date.now() + 1, role: 'assistant', text: reply || '(no response)' })
      } else {
        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        // create a placeholder assistant message and update it incrementally
        const msgId = Date.now() + 1
        add({ id: msgId, role: 'assistant', text: '' })
        let acc = ''
        while (true) {
          const { value, done } = await reader.read()
          if (done) break
          const chunk = decoder.decode(value, { stream: true })
          acc += chunk
          let consumed = ''
          // Server-Sent Events are separated by double newlines
          const parts = acc.split('\n\n')
          acc = parts.pop() || ''
          for (const p of parts) {
            const line = p.replace(/^data:\s*/, '').trim()
            if (!line) continue
            // Append to existing assistant message
            useChatStore.getState().updateText(msgId, (prev) => prev + line)
          }
        }
        const tail = acc.replace(/^data:\s*/, '').trim()
        if (tail) {
          useChatStore.getState().updateText(msgId, (prev) => prev + tail)
        }
      }
    } catch (err: any) {
      antdMessage.error(err?.message || 'LLM request failed')
      add({ id: Date.now() + 1, role: 'assistant', text: '[Error] request failed' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card title="Chat">
      <div style={{ marginBottom: 12, minHeight: 240 }} ref={listRef}>
        {msgs.map((m) => (
      <div key={m.id} style={{ display: 'flex', margin: '6px 0', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start' }}>
            <div
              style={{
                maxWidth: '70%',
                padding: '8px 12px',
                borderRadius: 12,
                background: m.role === 'user' ? '#1677ff' : '#f5f5f5',
                color: m.role === 'user' ? '#fff' : '#000',
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
              }}
            >
              {m.text}
            </div>
          </div>
        ))}
      </div>
      <Input.TextArea value={input} rows={3} onChange={(e) => setInput(e.target.value)} />
  <Button type="primary" onClick={send} style={{ marginTop: 8 }} loading={loading}>
        Send
      </Button>
    </Card>
  )
}
