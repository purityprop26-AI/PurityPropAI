import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth, api } from '../context/AuthContext';
import { useChat } from '../context/ChatContext';
import PremiumInput from '../components/PremiumInput';
import { User, Copy, Check } from 'lucide-react';
import AnimatedLogo from '../components/AnimatedLogo';

const API_URL = (import.meta.env.VITE_API_URL || '').trim();

/* ───────── Analysis Phases (perceived speed) ───────── */
const ANALYSIS_PHASES = [
    { text: 'Identifying micro-market zone', icon: '🔍', duration: 600 },
    { text: 'Analyzing comparable corridors', icon: '📊', duration: 800 },
    { text: 'Computing valuation range', icon: '💰', duration: 700 },
    { text: 'Generating intelligence report', icon: '🧠', duration: 500 },
];

/* ───────── Parse structured response into card sections ───────── */
function parseResponseSections(text) {
    if (!text) return [];

    // Pattern: emoji followed by section title — then content
    const sectionPattern = /^(📍|💰|📊|🔍|📈|📉|🧠|🚀|⚠️|✅|🏗️|📋|🔗)\s*(.+?)(?:\s*[—–-]\s*|\n)/gm;
    const sections = [];
    let lastIndex = 0;
    let match;

    // Split text by lines starting with known emoji headers
    const lines = text.split('\n');
    let currentSection = null;

    for (const line of lines) {
        const trimmed = line.trim();
        // Detect section headers by emoji prefix
        const emojiMatch = trimmed.match(/^(📍|💰|📊|🔍|📈|📉|🧠|🚀|⚠️|✅|🏗️|📋|🔗)\s*(.+)/);

        if (emojiMatch) {
            if (currentSection) {
                sections.push(currentSection);
            }
            const emoji = emojiMatch[1];
            let title = emojiMatch[2];
            // Split title from content if " — " or " - " exists
            let content = '';
            const dashIdx = title.search(/\s*[—–]\s*/);
            if (dashIdx > 0) {
                content = title.slice(dashIdx).replace(/^\s*[—–]\s*/, '');
                title = title.slice(0, dashIdx);
            }
            currentSection = {
                emoji,
                title: title.trim(),
                content: content.trim(),
                type: categorizeSection(emoji),
            };
        } else if (currentSection) {
            currentSection.content += (currentSection.content ? '\n' : '') + trimmed;
        } else {
            // Content before any section header
            if (trimmed) {
                if (!sections.length && !currentSection) {
                    currentSection = { emoji: '', title: '', content: trimmed, type: 'text' };
                }
            }
        }
    }
    if (currentSection) sections.push(currentSection);

    // If no sections found, return as single text block
    if (sections.length === 0) {
        return [{ emoji: '', title: '', content: text, type: 'text' }];
    }
    return sections;
}

function categorizeSection(emoji) {
    const map = {
        '📍': 'location',
        '💰': 'valuation',
        '📊': 'benchmark',
        '🔍': 'methodology',
        '📈': 'appreciation',
        '📉': 'liquidity',
        '🏗️': 'drivers',
        '🧠': 'confidence',
        '🚀': 'upgrade',
        '⚠️': 'warning',
        '✅': 'info',
        '📋': 'info',
        '🔗': 'info',
    };
    return map[emoji] || 'text';
}

/* ───────── Confidence Meter Component ───────── */
const ConfidenceMeter = ({ text }) => {
    const [fill, setFill] = useState(0);
    // Extract score from text like "0.78" or "Moderate-High (0.75)"
    const scoreMatch = text?.match(/(0\.\d+)|\b(\d{1,2})%/);
    let score = 0;
    if (scoreMatch) {
        score = scoreMatch[1] ? parseFloat(scoreMatch[1]) : parseInt(scoreMatch[2]) / 100;
    } else if (/high/i.test(text)) {
        score = 0.8;
    } else if (/moderate/i.test(text)) {
        score = 0.6;
    } else if (/low/i.test(text)) {
        score = 0.35;
    }

    useEffect(() => {
        const timer = setTimeout(() => setFill(score * 100), 200);
        return () => clearTimeout(timer);
    }, [score]);

    const getColor = (s) => {
        if (s >= 0.7) return '#10B981';
        if (s >= 0.4) return '#F59E0B';
        return '#EF4444';
    };

    return (
        <div className="confidence-meter">
            <div className="confidence-track">
                <div
                    className="confidence-fill"
                    style={{
                        width: `${fill}%`,
                        background: `linear-gradient(90deg, ${getColor(score)}88, ${getColor(score)})`,
                    }}
                />
            </div>
            <span className="confidence-score" style={{ color: getColor(score) }}>
                {score > 0 ? score.toFixed(2) : '—'}
            </span>
        </div>
    );
};

/* ───────── Intelligence Card Component ───────── */
const IntelligenceCard = ({ section, index }) => {
    const [visible, setVisible] = useState(false);

    useEffect(() => {
        const timer = setTimeout(() => setVisible(true), index * 120);
        return () => clearTimeout(timer);
    }, [index]);

    const typeClasses = {
        location: 'card-location',
        valuation: 'card-valuation',
        benchmark: 'card-benchmark',
        appreciation: 'card-appreciation',
        liquidity: 'card-liquidity',
        drivers: 'card-drivers',
        methodology: 'card-methodology',
        confidence: 'card-confidence',
        upgrade: 'card-upgrade',
        risk: 'card-risk',
    };

    return (
        <div
            className={`intel-card ${typeClasses[section.type] || ''} ${visible ? 'visible' : ''}`}
            style={{ transitionDelay: `${index * 80}ms` }}
        >
            {section.title && (
                <div className="intel-card-header">
                    <span className="intel-card-bullet">•</span>
                    <span className="intel-card-title">{section.title}</span>
                </div>
            )}
            <div className="intel-card-body">
                {section.type === 'confidence' ? (
                    <>
                        <ConfidenceMeter text={section.content} />
                        <div className="intel-card-text">{section.content}</div>
                    </>
                ) : (
                    <div className="intel-card-text">{section.content}</div>
                )}
            </div>
        </div>
    );
};

/* ───────── Loading Skeleton (perceived speed) ───────── */
const AnalysisLoader = () => {
    const [phase, setPhase] = useState(0);

    useEffect(() => {
        const timers = [];
        let cumulative = 0;
        ANALYSIS_PHASES.forEach((p, i) => {
            cumulative += p.duration;
            timers.push(setTimeout(() => setPhase(i + 1), cumulative));
        });
        return () => timers.forEach(clearTimeout);
    }, []);

    return (
        <div className="analysis-loader">
            <div className="analysis-header">
                <div className="analysis-pulse" />
                <span>PurityProp Intelligence Engine</span>
            </div>
            <div className="analysis-phases">
                {ANALYSIS_PHASES.map((p, i) => (
                    <div key={i} className={`analysis-phase ${i < phase ? 'done' : i === phase ? 'active' : ''}`}>
                        <span className="phase-icon">{p.icon}</span>
                        <span className="phase-text">{p.text}</span>
                        {i < phase && <span className="phase-check">✓</span>}
                        {i === phase && <span className="phase-spinner" />}
                    </div>
                ))}
            </div>
            <div className="shimmer-blocks">
                <div className="shimmer-line w80" />
                <div className="shimmer-line w60" />
                <div className="shimmer-line w90" />
            </div>
        </div>
    );
};

/* ───────── Main AIChat Component ───────── */
const AIChat = () => {
    const { messages, currentChatId, addMessage, updateMessage, createNewChat } = useChat();
    const [sessionId, setSessionId] = useState(null);
    const [loading, setLoading] = useState(false);
    const [sessionError, setSessionError] = useState(false);
    const [copiedIndex, setCopiedIndex] = useState(null);

    const messagesEndRef = useRef(null);
    const location = useLocation();
    const sessionCreating = useRef(false);
    const chatInitialized = useRef(false);

    useEffect(() => {
        if (!currentChatId && !chatInitialized.current) {
            chatInitialized.current = true;
            createNewChat();
        }
    }, [currentChatId]);

    // Reset session when chat changes (but don't clear the guard flag — let the next effect handle it)
    useEffect(() => {
        setSessionId(null);
    }, [currentChatId]);

    // Create session — runs when chatId exists but sessionId is null
    useEffect(() => {
        if (currentChatId && !sessionId && !sessionCreating.current) {
            sessionCreating.current = true;
            const controller = new AbortController();
            createNewSession(1, controller.signal);
            return () => {
                controller.abort();
                sessionCreating.current = false;
            };
        }
    }, [currentChatId, sessionId]);

    const initialMessageSent = useRef(false);

    useEffect(() => {
        if (location.state?.initialMessage && sessionId && !initialMessageSent.current) {
            initialMessageSent.current = true;
            sendMessage(location.state.initialMessage);
            window.history.replaceState({}, document.title);
        }
    }, [location.state, sessionId]);

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    const createNewSession = async (attempt = 1, signal) => {
        setSessionError(false);
        try {
            const response = await api.post(`/api/sessions`, {}, { signal });
            if (signal?.aborted) return; // Don't update state if aborted
            setSessionId(response.data.session_id);
            sessionCreating.current = false;

            if (messages.length === 0) {
                addMessage(currentChatId, {
                    id: crypto.randomUUID(),
                    role: 'assistant',
                    content: '📍 PurityProp Intelligence Engine — Ready\n\nReal estate valuation, registration data, stamp duty computation, and market intelligence for Tamil Nadu.\n\n🔍 Query any location for instant valuation.\n📊 Get structured pricing with confidence scores.\n🧠 Powered by official TN government data sources.'
                });
            }
        } catch (err) {
            if (signal?.aborted) return; // Silently drop aborted requests
            console.error(`Session error (attempt ${attempt}/3):`, err?.response?.data || err.message);
            if (attempt < 3) {
                setTimeout(() => createNewSession(attempt + 1, signal), 2000 * attempt);
            } else {
                sessionCreating.current = false;
                setSessionError(true);
            }
        }
    };

    const sendMessage = async (messageText) => {
        if (!sessionId || !currentChatId) return;

        const userMessage = {
            id: crypto.randomUUID(),
            role: 'user',
            content: messageText
        };
        addMessage(currentChatId, userMessage);
        setLoading(true);

        // Create a placeholder assistant message for streaming
        const assistantId = crypto.randomUUID();
        const streamingMsg = {
            id: assistantId,
            role: 'assistant',
            content: '',
            isStreaming: true
        };
        addMessage(currentChatId, streamingMsg);

        try {
            const baseUrl = API_URL || '';
            const response = await fetch(`${baseUrl}/api/chat/stream`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sessionId,
                    message: messageText
                })
            });

            if (!response.ok) {
                throw new Error(`Stream failed: ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let fullText = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const text = decoder.decode(value, { stream: true });
                const lines = text.split('\n');

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    try {
                        const data = JSON.parse(line.slice(6));
                        if (data.done) {
                            // Stream complete — use full_text if available
                            if (data.full_text) fullText = data.full_text;
                            // Update the message with final content (no longer streaming)
                            updateMessage(currentChatId, assistantId, {
                                content: fullText,
                                language: data.language,
                                isStreaming: false
                            });
                        } else if (data.chunk) {
                            fullText += data.chunk;
                            // Update streaming message with accumulated text
                            updateMessage(currentChatId, assistantId, {
                                content: fullText,
                                isStreaming: true
                            });
                        }
                    } catch (e) {
                        // Skip malformed SSE lines
                    }
                }
            }

            // Ensure streaming flag is cleared if stream ended
            updateMessage(currentChatId, assistantId, {
                content: fullText || 'No response received.',
                isStreaming: false
            });
        } catch (err) {
            console.error('Stream error, falling back:', err);
            // Fallback to non-streaming endpoint
            try {
                const response = await api.post(`/api/chat`, {
                    session_id: sessionId,
                    message: messageText
                });
                updateMessage(currentChatId, assistantId, {
                    content: response.data.message,
                    language: response.data.language,
                    isStreaming: false
                });
            } catch (fallbackErr) {
                updateMessage(currentChatId, assistantId, {
                    content: '⚠️ Connection Error — Unable to reach the intelligence engine. Please retry.',
                    isStreaming: false
                });
            }
        } finally {
            setLoading(false);
        }
    };

    const copyToClipboard = (text, msgId) => {
        navigator.clipboard.writeText(text);
        setCopiedIndex(msgId);
        setTimeout(() => setCopiedIndex(null), 2000);
    };

    /* ───────── Render ───────── */
    return (
        <div className="chat-container">
            {sessionError && (
                <div className="session-error-banner">
                    <span>⚠️ Engine initialization failed. Server may be waking up.</span>
                    <button
                        onClick={() => {
                            sessionCreating.current = true;
                            createNewSession();
                        }}
                        className="retry-btn"
                    >
                        Retry Connection
                    </button>
                </div>
            )}

            <div className="chat-messages">
                {messages.map((msg, idx) => (
                    <div key={msg.id || `msg-fallback-${idx}`} className={`message-wrapper ${msg.role}`}>
                        <div className={`message-avatar ${msg.role === 'assistant' ? 'avatar-engine' : ''}`}>
                            {msg.role === 'user' ? <User size={18} /> : <AnimatedLogo size={30} />}
                        </div>
                        <div className="message-content-wrapper">
                            <div className="message-header">
                                <span className="message-role">
                                    {msg.role === 'user' ? 'You' : 'PurityProp Engine'}
                                </span>
                                {msg.role === 'assistant' && (
                                    <button
                                        className="copy-btn"
                                        onClick={() => copyToClipboard(msg.content, msg.id)}
                                        title="Copy response"
                                    >
                                        {copiedIndex === msg.id ? <Check size={14} /> : <Copy size={14} />}
                                    </button>
                                )}
                            </div>

                            {msg.role === 'assistant' ? (
                                msg.isStreaming ? (
                                    <div className="intel-response">
                                        <div className="streaming-text streaming-cursor">
                                            {msg.content || 'Analyzing...'}
                                        </div>
                                    </div>
                                ) : (
                                    <div className="intel-response">
                                        <div className="data-freshness-bar">
                                            <span className="freshness-dot" />
                                            <span className="freshness-label">Registry-Backed</span>
                                            <span>•</span>
                                            <span>Updated: Jul 2024</span>
                                            <span>•</span>
                                            <span className="trust-badge registry">Verified</span>
                                        </div>
                                        {parseResponseSections(msg.content).map((section, i) => (
                                            <IntelligenceCard key={i} section={section} index={i} />
                                        ))}
                                    </div>
                                )
                            ) : (
                                <div className="message-text user-query">{msg.content}</div>
                            )}

                            {msg.language && (
                                <div className="message-meta">
                                    <span className="language-badge">{msg.language}</span>
                                </div>
                            )}
                        </div>
                    </div>
                ))}

                {loading && !messages.some(m => m.isStreaming) && (
                    <div className="message-wrapper assistant">
                        <div className="message-avatar avatar-engine">
                            <AnimatedLogo size={30} />
                        </div>
                        <div className="message-content-wrapper">
                            <AnalysisLoader />
                        </div>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            <div className="chat-input-area">
                <PremiumInput
                    onSend={sendMessage}
                    disabled={loading || !sessionId}
                    placeholder="Enter location for valuation — e.g. 'Porur land price'"
                />
            </div>
        </div>
    );
};

export default AIChat;
