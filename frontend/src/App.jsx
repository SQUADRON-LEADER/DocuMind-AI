import React, { useState, useEffect, useRef } from 'react';
import { 
  Upload, Trash2, Send, RefreshCw, X, FileText, BookOpen
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import Marquee from 'react-fast-marquee';

export default function App() {
  const [stats, setStats] = useState({ total_chunks: 0, total_documents: 0 });
  const [documents, setDocuments] = useState([]);
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      sender: 'ai',
      text: "DOCUMENT INTELLIGENCE SYSTEM ACTIVE. ASK QUESTIONS BASED ON YOUR INDEXED PDF DOCUMENTS.",
      sources: []
    }
  ]);
  const [inputQuery, setInputQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);
  const chatEndRef = useRef(null);

  useEffect(() => {
    fetchStats();
    fetchDocuments();
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const fetchStats = async () => {
    try {
      const res = await fetch('/api/stats');
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (err) {
      console.error("Failed to fetch stats:", err);
    }
  };

  const fetchDocuments = async () => {
    try {
      const res = await fetch('/api/documents');
      if (res.ok) {
        const data = await res.json();
        setDocuments(data.documents || []);
      }
    } catch (err) {
      console.error("Failed to fetch documents:", err);
    }
  };

  const handleFileUpload = async (files) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }

    try {
      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData
      });
      if (res.ok) {
        await fetchStats();
        await fetchDocuments();
      } else {
        alert("ERROR UPLOADING PDF DOCUMENT.");
      }
    } catch (err) {
      console.error("Upload error:", err);
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteDoc = async (filename) => {
    if (!confirm(`REMOVE ${filename.toUpperCase()} FROM VECTOR STORE?`)) return;
    try {
      const res = await fetch(`/api/documents/${encodeURIComponent(filename)}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        fetchStats();
        fetchDocuments();
      }
    } catch (err) {
      console.error("Failed to delete document:", err);
    }
  };

  const handleSendQuery = async (queryText = inputQuery) => {
    const textToSubmit = queryText.trim();
    if (!textToSubmit || loading) return;

    const userMsg = { id: Date.now().toString(), sender: 'user', text: textToSubmit.toUpperCase() };
    setMessages((prev) => [...prev, userMsg]);
    setInputQuery('');
    setLoading(true);

    try {
      const res = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: textToSubmit, top_k: 4 })
      });

      if (res.ok) {
        const data = await res.json();
        const aiMsg = {
          id: (Date.now() + 1).toString(),
          sender: 'ai',
          text: data.answer || "No answer found in the provided document context.",
          sources: data.sources || []
        };
        setMessages((prev) => [...prev, aiMsg]);
      } else {
        setMessages((prev) => [
          ...prev,
          { id: Date.now().toString(), sender: 'ai', text: "No answer found in the provided document context.", sources: [] }
        ]);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { id: Date.now().toString(), sender: 'ai', text: "No answer found in the provided document context.", sources: [] }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files);
    }
  };

  const sampleQueries = [
    "WHAT IS ENCODER DECODER ARCHITECTURE?",
    "SUMMARIZE THE RESEARCH PAPER",
    "EXPLAIN RAG ROBUSTNESS"
  ];

  return (
    <div className="app-shell">
      {/* Brutalist Sidebar */}
      <aside className="brutal-sidebar">
        <div className="sidebar-header">
          <h1 className="brand-title">DOCUMIND<span>.AI</span></h1>
          <p style={{ fontSize: '11px', color: 'var(--fg-muted)', marginTop: '6px', fontWeight: '700', letterSpacing: '0.1em' }}>
            KINETIC DOCUMENT INTELLIGENCE
          </p>
        </div>

        <div className="sidebar-body">
          {/* Upload Dropzone */}
          <div 
            className={`brutal-dropzone ${dragActive ? 'active' : ''}`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input 
              ref={fileInputRef}
              type="file" 
              accept=".pdf" 
              multiple 
              style={{ display: 'none' }}
              onChange={(e) => handleFileUpload(e.target.files)}
            />
            <Upload size={28} style={{ color: 'var(--accent)', marginBottom: '8px' }} />
            <p style={{ fontSize: '14px', fontWeight: '700' }}>
              {uploading ? 'PROCESSING...' : 'UPLOAD PDF FILES'}
            </p>
            <p style={{ fontSize: '10px', color: 'var(--fg-muted)', marginTop: '4px' }}>
              DRAG & DROP PDF OR CLICK
            </p>
          </div>

          {/* Stats Grid */}
          <div className="brutal-stats">
            <div className="stat-card">
              <div className="stat-num">{stats.total_documents}</div>
              <div className="stat-lbl">DOCUMENTS</div>
            </div>
            <div className="stat-card">
              <div className="stat-num">{stats.total_chunks}</div>
              <div className="stat-lbl">CHUNKS</div>
            </div>
          </div>

          {/* Indexed File List */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
              <span style={{ fontSize: '12px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--fg-muted)' }}>
                INDEXED FILES ({documents.length})
              </span>
              <RefreshCw size={14} style={{ cursor: 'pointer', color: 'var(--fg-muted)' }} onClick={() => { fetchStats(); fetchDocuments(); }} />
            </div>

            {documents.length === 0 ? (
              <p style={{ fontSize: '12px', color: 'var(--fg-muted)', fontStyle: 'italic', padding: '12px 0' }}>
                NO PDF DOCUMENTS INDEXED YET.
              </p>
            ) : (
              documents.map((doc) => (
                <div key={doc.filename} className="brutal-doc-item">
                  <div style={{ overflow: 'hidden', marginRight: '8px' }}>
                    <p style={{ fontSize: '14px', fontWeight: '700', textTransform: 'uppercase', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {doc.filename}
                    </p>
                    <p style={{ fontSize: '11px', color: 'var(--fg-muted)', marginTop: '2px' }}>
                      {doc.total_pages} PAGES • {doc.total_chunks} CHUNKS
                    </p>
                  </div>
                  <Trash2 
                    size={16} 
                    style={{ cursor: 'pointer', flexShrink: 0, color: '#ef4444' }} 
                    onClick={() => handleDeleteDoc(doc.filename)}
                  />
                </div>
              ))
            )}
          </div>
        </div>
      </aside>

      {/* Main Workspace */}
      <main className="brutal-main">
        {/* Infinite Ticker Bar */}
        <div className="ticker-bar">
          <Marquee speed={60} gradient={false}>
            <span>✦ KINETIC VECTOR DB SYSTEM // FULL-TEXT RETRIEVAL ACTIVE // TOP-K SEMANTIC INDEXING // PROCESSED DOCUMENT DATA // NO MATCH PERCENTAGES // DEEP CONTEXT REASONING // ✦ &nbsp;&nbsp;&nbsp;</span>
          </Marquee>
        </div>

        {/* Chat Area */}
        <div className="chat-viewport">
          {messages.map((msg) => (
            <div key={msg.id} className={`msg-row ${msg.sender}`}>
              <div className="msg-avatar">
                {msg.sender === 'ai' ? 'AI' : 'YOU'}
              </div>
              <div className="msg-box">
                <div className="markdown-body">
                  <ReactMarkdown>{msg.text}</ReactMarkdown>
                </div>

                {/* Sources Citation List (NO MATCH PERCENTAGES) */}
                {msg.sources && msg.sources.length > 0 && (
                  <div className="citations-wrapper">
                    <div className="citations-hdr">
                      <BookOpen size={14} style={{ display: 'inline', marginRight: '6px' }} />
                      CITED CONTEXT SOURCES ({msg.sources.length})
                    </div>
                    <div className="citations-grid">
                      {msg.sources.map((src, idx) => (
                        <div 
                          key={idx} 
                          className="brutal-citation-card"
                          onClick={() => setSelectedCitation(src)}
                        >
                          <p style={{ fontSize: '13px', fontWeight: '700', textTransform: 'uppercase', marginBottom: '4px' }}>
                            📄 {src.filename}
                          </p>
                          <p style={{ fontSize: '11px', color: 'var(--fg-muted)' }}>
                            PAGE {src.page} • CHUNK #{src.rank}
                          </p>
                          <p style={{ fontSize: '11px', marginTop: '6px', fontStyle: 'italic', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                            "{src.document}"
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="msg-row ai">
              <div className="msg-avatar">AI</div>
              <div className="msg-box" style={{ background: 'var(--bg-muted)', display: 'flex', alignItems: 'center', gap: '12px' }}>
                <RefreshCw size={18} className="animate-spin" style={{ color: 'var(--accent)' }} />
                <span style={{ fontWeight: '700', textTransform: 'uppercase' }}>SEARCHING VECTOR DB & SYNTHESIZING RESPONSE...</span>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Input Bar & Prompts */}
        <div className="input-section">
          {messages.length <= 2 && (
            <div style={{ maxWidth: '1000px', margin: '0 auto 16px auto', display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
              {sampleQueries.map((q, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSendQuery(q)}
                  style={{
                    background: 'var(--bg-main)',
                    border: '2px solid var(--border-color)',
                    color: 'var(--fg-main)',
                    padding: '8px 16px',
                    fontSize: '12px',
                    fontWeight: '700',
                    textTransform: 'uppercase',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease'
                  }}
                  onMouseEnter={(e) => { e.target.style.borderColor = 'var(--accent)'; e.target.style.background = 'var(--accent)'; e.target.style.color = '#000'; }}
                  onMouseLeave={(e) => { e.target.style.borderColor = 'var(--border-color)'; e.target.style.background = 'var(--bg-main)'; e.target.style.color = 'var(--fg-main)'; }}
                >
                  {q}
                </button>
              ))}
            </div>
          )}

          <div className="input-row">
            <input 
              type="text" 
              className="brutal-input"
              placeholder="ENTER YOUR QUERY ON INDEXED PDFS..."
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSendQuery()}
              disabled={loading}
            />
            <button 
              className="brutal-btn"
              onClick={() => handleSendQuery()}
              disabled={loading || !inputQuery.trim()}
            >
              <span>SEND</span>
              <Send size={18} />
            </button>
          </div>
        </div>
      </main>

      {/* Citation Snippet Modal */}
      {selectedCitation && (
        <div className="modal-overlay">
          <div className="modal-box">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <FileText size={20} style={{ color: 'var(--accent)' }} />
                <h3 style={{ fontSize: '18px', fontWeight: '700', textTransform: 'uppercase' }}>{selectedCitation.filename}</h3>
              </div>
              <X size={24} style={{ cursor: 'pointer', color: 'var(--fg-muted)' }} onClick={() => setSelectedCitation(null)} />
            </div>

            <p style={{ fontSize: '12px', fontWeight: '700', color: 'var(--fg-muted)', textTransform: 'uppercase', marginBottom: '16px' }}>
              PAGE {selectedCitation.page} • CHUNK #{selectedCitation.rank}
            </p>

            <div style={{ 
              background: 'var(--bg-muted)', 
              border: '2px solid var(--border-color)',
              padding: '20px', 
              fontSize: '14px', 
              lineHeight: '1.6', 
              maxHeight: '350px',
              overflowY: 'auto'
            }}>
              {selectedCitation.document}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
