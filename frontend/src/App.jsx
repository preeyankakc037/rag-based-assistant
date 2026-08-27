import { useState, useRef, useEffect } from 'react'
import './App.css'

function App() {
  const [file, setFile] = useState(null)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState(null)
  const [messages, setMessages] = useState([])
  const [inputValue, setInputValue] = useState('')
  const [isChatting, setIsChatting] = useState(false)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
      setUploadStatus(null)
    }
  }

  const handleUpload = async () => {
    if (!file) return

    setIsUploading(true)
    setUploadStatus(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch('http://127.0.0.1:8000/upload', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error('Upload failed')
      }

      setUploadStatus({ type: 'success', message: 'PDF processed successfully! You can now chat.' })
    } catch (error) {
      setUploadStatus({ type: 'error', message: 'Failed to upload and process PDF.' })
    } finally {
      setIsUploading(false)
    }
  }

  const handleSendMessage = async (e) => {
    e.preventDefault()
    if (!inputValue.trim() || isChatting) return

    const userMessage = { role: 'user', content: inputValue }
    setMessages((prev) => [...prev, userMessage])
    setInputValue('')
    setIsChatting(true)

    try {
      const response = await fetch('http://127.0.0.1:8000/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question: userMessage.content }),
      })

      if (!response.ok) {
        throw new Error('Chat request failed')
      }

      const data = await response.json()
      
      setMessages((prev) => [
        ...prev,
        { role: 'bot', content: data.answer, sources: data.sources },
      ])
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { role: 'bot', content: 'Sorry, I encountered an error while trying to answer.' },
      ])
    } finally {
      setIsChatting(false)
    }
  }

  return (
    <div className="app-container">
      {/* Sidebar for Upload */}
      <div className="sidebar">
        <h2 className="sidebar-title">Documents</h2>
        
        <div className={`upload-box ${file ? 'has-file' : ''}`}>
          <label className="upload-label">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="17 8 12 3 7 8"></polyline>
              <line x1="12" y1="3" x2="12" y2="15"></line>
            </svg>
            <span>{file ? file.name : 'Choose a PDF to upload'}</span>
            <input 
              type="file" 
              accept=".pdf" 
              className="upload-input" 
              onChange={handleFileChange}
            />
          </label>
        </div>

        <button 
          className="btn-primary" 
          onClick={handleUpload} 
          disabled={!file || isUploading}
        >
          {isUploading ? 'Processing...' : 'Upload & Process'}
        </button>

        {uploadStatus && (
          <div className={`status-message ${uploadStatus.type}`}>
            {uploadStatus.message}
          </div>
        )}
      </div>

      {/* Main Chat Area */}
      <div className="chat-container">
        <div className="chat-header">
          <h2>RAG Assistant</h2>
        </div>

        <div className="chat-messages">
          {messages.length === 0 ? (
            <div className="empty-state">
              Upload a document and ask me anything about it!
            </div>
          ) : (
            messages.map((msg, idx) => (
              <div key={idx} className={`message ${msg.role}`}>
                <div className="message-bubble">
                  {msg.content}
                </div>
                {msg.role === 'bot' && msg.sources && msg.sources.length > 0 && (
                  <div className="citations">
                    {msg.sources.map((src, sIdx) => (
                      <span key={sIdx} className="citation-badge">
                        📄 Page {src.page}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
          
          {isChatting && (
            <div className="message bot">
              <div className="message-bubble">
                <div className="loading-dots">
                  <span></span><span></span><span></span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="chat-input-container">
          <form className="chat-form" onSubmit={handleSendMessage}>
            <input 
              type="text" 
              className="chat-input" 
              placeholder="Ask a question..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              disabled={isChatting}
            />
            <button 
              type="submit" 
              className="btn-send"
              disabled={!inputValue.trim() || isChatting}
            >
              Send
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}

export default App
