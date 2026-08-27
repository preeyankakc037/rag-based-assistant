import { useState, useRef, useEffect, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import './App.css'
import logoSrc from './assets/logo.png'

const API_BASE = 'http://127.0.0.1:8000'

// ── Helpers ──────────────────────────────────────────────────────────────────

function genId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
}

function formatDate(isoStr) {
  const d = new Date(isoStr)
  const now = new Date()
  const diff = now - d
  if (diff < 60_000) return 'Just now'
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`
  if (d.toDateString() === now.toDateString()) return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  return d.toLocaleDateString([], { month: 'short', day: 'numeric' })
}

function titleFromMessage(text) {
  const clean = text.replace(/\s+/g, ' ').trim()
  return clean.length > 42 ? clean.slice(0, 42) + '…' : clean
}

function fileName(fullPath) {
  const parts = (fullPath || '').replace(/\\/g, '/').split('/')
  return parts[parts.length - 1] || fullPath
}

// ── CitationBadges ────────────────────────────────────────────────────────────

function CitationBadges({ sources }) {
  if (!sources || sources.length === 0) return null
  const seen = new Set()
  const unique = sources.filter(src => {
    const key = `${src.source}|${src.page}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
  return (
    <div className="citations">
      <span className="citations-label">Sources:</span>
      {unique.map((src, i) => (
        <span key={i} className="citation-badge" title={src.content}>
          📄 {fileName(src.source)} · p.{src.page + 1}
        </span>
      ))}
    </div>
  )
}

// ── Main App ──────────────────────────────────────────────────────────────────

export default function App() {
  // Persist sessions to localStorage
  const [sessions, setSessions] = useState(() => {
    try { return JSON.parse(localStorage.getItem('rag-sessions') || '[]') } catch { return [] }
  })
  const [activeId, setActiveId] = useState(() => {
    const saved = JSON.parse(localStorage.getItem('rag-sessions') || '[]')
    return saved.length > 0 ? saved[0].id : null
  })

  // Upload state — tracks what's loaded in the backend right now
  const [loadedDoc, setLoadedDoc] = useState(null)
  const [file, setFile] = useState(null)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState(null)

  // Chat state
  const [inputValue, setInputValue] = useState('')
  const [isChatting, setIsChatting] = useState(false)

  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  // Persist sessions on change
  useEffect(() => {
    localStorage.setItem('rag-sessions', JSON.stringify(sessions))
  }, [sessions])

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [sessions, activeId])

  // Focus input on session switch
  useEffect(() => {
    inputRef.current?.focus()
  }, [activeId])

  // ── Session helpers ─────────────────────────────────────────────────────────

  const activeSession = sessions.find(s => s.id === activeId) || null

  // Activate a session's document on the backend (no re-upload needed)
  const activateDocument = async (docName) => {
    if (!docName) return false
    try {
      const res = await fetch(`${API_BASE}/activate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ document_name: docName }),
      })
      if (res.ok) {
        setLoadedDoc(docName)
        return true
      }
      return false
    } catch {
      return false
    }
  }

  const createNewChat = () => {
    const id = genId()
    const newSession = { id, title: 'New Chat', messages: [], documentName: null, createdAt: new Date().toISOString() }
    setSessions(prev => [newSession, ...prev])
    setActiveId(id)
    setInputValue('')
    setUploadStatus(null)
    setFile(null)
  }

  const deleteSession = (e, id) => {
    e.stopPropagation()
    setSessions(prev => prev.filter(s => s.id !== id))
    if (activeId === id) {
      const remaining = sessions.filter(s => s.id !== id)
      setActiveId(remaining.length > 0 ? remaining[0].id : null)
    }
  }

  const switchSession = async (id) => {
    setActiveId(id)
    setUploadStatus(null)
    setInputValue('')
    const session = sessions.find(s => s.id === id)
    if (session?.documentName) {
      await activateDocument(session.documentName)
    }
  }

  const updateSession = useCallback((id, updater) => {
    setSessions(prev => prev.map(s => s.id === id ? { ...s, ...updater(s) } : s))
  }, [])

  // ── Upload ──────────────────────────────────────────────────────────────────

  const handleFileChange = e => {
    if (e.target.files?.[0]) { setFile(e.target.files[0]); setUploadStatus(null) }
  }

  const handleUpload = async () => {
    if (!file) return

    // Auto-create a session if none exists
    let sessionId = activeId
    if (!sessionId) {
      const id = genId()
      const newSession = { id, title: 'New Chat', messages: [], documentName: null, createdAt: new Date().toISOString() }
      setSessions(prev => [newSession, ...prev])
      setActiveId(id)
      sessionId = id
    }

    setIsUploading(true)
    setUploadStatus(null)
    const formData = new FormData()
    formData.append('file', file)
    try {
      const res = await fetch(`${API_BASE}/upload`, { method: 'POST', body: formData })
      if (!res.ok) throw new Error()
      setLoadedDoc(file.name)
      setUploadStatus({ type: 'success', message: `✓ ${file.name} ready` })
      updateSession(sessionId, s => ({ documentName: file.name }))
    } catch {
      setUploadStatus({ type: 'error', message: 'Upload failed. Try again.' })
    } finally {
      setIsUploading(false)
    }
  }

  // ── Send message (streaming) ────────────────────────────────────────────────

  const handleSend = async e => {
    e.preventDefault()
    const question = inputValue.trim()
    if (!question || isChatting || !activeId) return

    const history = (activeSession?.messages || []).map(m => ({ role: m.role, content: m.content }))
    const userMsg = { id: genId(), role: 'user', content: question }
    const botMsg = { id: genId(), role: 'bot', content: '', sources: [], streaming: true }

    // If this is the first message, set session title
    const isFirst = !activeSession?.messages?.length
    updateSession(activeId, s => ({
      title: isFirst ? titleFromMessage(question) : s.title,
      messages: [...s.messages, userMsg, botMsg],
    }))

    setInputValue('')
    setIsChatting(true)
    const botMsgId = botMsg.id

    try {
      const res = await fetch(`${API_BASE}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, history }),
      })
      if (!res.ok) throw new Error()

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const raw = line.slice(6).trim()
          if (!raw) continue
          try {
            const event = JSON.parse(raw)
            if (event.type === 'token') {
              updateSession(activeId, s => ({
                messages: s.messages.map(m => m.id === botMsgId ? { ...m, content: m.content + event.content } : m)
              }))
            } else if (event.type === 'done') {
              updateSession(activeId, s => ({
                messages: s.messages.map(m => m.id === botMsgId ? { ...m, sources: event.sources || [], streaming: false } : m)
              }))
            }
          } catch { /* ignore */ }
        }
      }
    } catch {
      updateSession(activeId, s => ({
        messages: s.messages.map(m => m.id === botMsgId ? { ...m, content: 'Sorry, I encountered an error.', streaming: false } : m)
      }))
    } finally {
      setIsChatting(false)
    }
  }

  // ── Handle Enter key (send) / Shift+Enter (newline) ────────────────────────
  const handleKeyDown = e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(e) }
  }

  // ── Doc needed? ─────────────────────────────────────────────────────────────
  const docNeeded = !loadedDoc || (activeSession?.documentName && activeSession.documentName !== loadedDoc)

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="layout">

      {/* ── Left Sidebar ── */}
      <div className="sidebar">

        {/* Brand */}
        <div className="sidebar-brand">
          <div className="brand-icon">
            <img src={logoSrc} alt="Logo" className="brand-logo" />
          </div>
          RAG Assistant
        </div>

        {/* New Chat */}
        <button className="btn-new-chat" onClick={createNewChat}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          New Chat
        </button>

        {/* Session List */}
        {sessions.length > 0 && (
          <div className="sidebar-section-label">Recent</div>
        )}

        <div className="sessions-list">
          {sessions.length === 0 ? (
            <div className="empty-sessions">
              No chats yet.<br />Click <strong>New Chat</strong> to begin.
            </div>
          ) : (
            sessions.map(session => (
              <div
                key={session.id}
                className={`session-item ${session.id === activeId ? 'active' : ''}`}
                onClick={() => switchSession(session.id)}
              >
                <div className="session-info">
                  <div className="session-title">{session.title}</div>
                  <div className="session-meta">
                    {session.documentName ? `📄 ${session.documentName}` : 'No document'} · {formatDate(session.createdAt)}
                  </div>
                </div>
                <button className="btn-delete-session" onClick={e => deleteSession(e, session.id)} title="Delete chat">
                  ✕
                </button>
              </div>
            ))
          )}
        </div>

        {/* Document Upload Panel */}
        <div className="doc-panel">
          <div className="doc-panel-label">Document</div>

          <div className={`doc-upload-area ${file ? 'has-file' : ''}`}>
            <label className="doc-upload-label">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="17 8 12 3 7 8"></polyline>
                <line x1="12" y1="3" x2="12" y2="15"></line>
              </svg>
              <span>{file ? file.name : 'Choose PDF'}</span>
              <input type="file" accept=".pdf" className="doc-upload-input" onChange={handleFileChange} />
            </label>
          </div>

          <button
            className="btn-upload"
            onClick={handleUpload}
            disabled={!file || isUploading}
          >
            {isUploading ? 'Processing…' : 'Upload & Process'}
          </button>

          {uploadStatus && (
            <div className={`upload-status ${uploadStatus.type}`}>
              {uploadStatus.message}
            </div>
          )}
        </div>
      </div>

      {/* ── Main Chat ── */}
      <div className="chat-main">

        {/* Header */}
        <div className="chat-header">
          <div className="chat-header-title">
            {activeSession ? activeSession.title : 'RAG Assistant'}
          </div>
          {loadedDoc && (
            <div className="chat-header-doc">
              <span>📄</span>
              {loadedDoc}
            </div>
          )}
        </div>

        {/* Messages */}
        <div className="chat-messages">
          {!activeSession || activeSession.messages.length === 0 ? (
            <div className="empty-chat">
              <div className="empty-chat-icon">💬</div>
              <h3>Start a conversation</h3>
              <p>Upload a PDF in the sidebar and ask me anything about it.</p>
            </div>
          ) : (
            activeSession.messages.map(msg => (
              <div key={msg.id} className={`message ${msg.role}`}>
                <div className="message-bubble">
                  {msg.role === 'bot' ? (
                    <div className="markdown-body">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                      {msg.streaming && <span className="cursor-blink">▍</span>}
                    </div>
                  ) : (
                    msg.content
                  )}
                </div>
                {msg.role === 'bot' && !msg.streaming && (
                  <CitationBadges sources={msg.sources} />
                )}
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="chat-input-wrapper">
          {/* Doc needed: only show if session has a doc but it's not loaded in backend */}
          {activeSession && activeSession.documentName && activeSession.documentName !== loadedDoc && activeSession.messages.length > 0 && (
            <div className="doc-needed-banner">
              ⚠️ <strong>{activeSession.documentName}</strong> needs to be re-uploaded (backend was restarted).
            </div>
          )}
          <form className="chat-form" onSubmit={handleSend}>
            <textarea
              ref={inputRef}
              className="chat-input"
              placeholder={activeId ? 'Ask a question… (Shift+Enter for new line)' : 'Create a new chat to begin'}
              value={inputValue}
              onChange={e => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isChatting || !activeId}
              rows={1}
            />
            <button
              type="submit"
              className="btn-send"
              disabled={!inputValue.trim() || isChatting || !activeId}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
              </svg>
              Send
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
