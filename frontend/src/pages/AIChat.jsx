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

    // Emoji sets that mark section headers
    const sectionEmojis = '📍|💰|📊|🔍|📈|📉|🧠|🚀|⚠️|✅|🏗️|📋|🔗';
    // Numbered emojis used in registry reports (1️⃣ through 🔟)
    const numberedEmojis = '1️⃣|2️⃣|3️⃣|4️⃣|5️⃣|6️⃣|7️⃣|8️⃣|9️⃣|🔟|🔒';
    const allEmojis = `${sectionEmojis}|${numberedEmojis}`;
    const emojiRegex = new RegExp(`^(${allEmojis})\\s*(.+)`);

    // ── PRE-PROCESS: inject newlines before emoji section markers ──
    // This handles streaming responses where chunks concatenate without \n
    const emojiInjectRegex = new RegExp(`(${allEmojis})`, 'g');
    let preprocessed = text.replace(emojiInjectRegex, '\n$1');

    // Also inject newlines before common structured headers
    preprocessed = preprocessed
        .replace(/REGISTRY-BACKED\s*VALUATION\s*REPORT/gi, '\nREGISTRY-BACKED VALUATION REPORT')
        .replace(/Verified\s*Source:/gi, '\nVerified Source:');

    const sections = [];
    const lines = preprocessed.split('\n');
    let currentSection = null;

    for (const line of lines) {
        const trimmed = line.trim();

        // Skip separator lines (━━━, ═══, ───) and empty
        if (!trimmed || /^[━═─—]{3,}/.test(trimmed)) {
            if (currentSection && currentSection.content) {
                currentSection.content += '\n';
            }
            continue;
        }

        // Skip standalone header lines (they become the card's overall header)
        if (/^REGISTRY-BACKED\s*VALUATION\s*REPORT$/i.test(trimmed)) continue;
        if (/^Verified\s*Source:/i.test(trimmed)) continue;

        // Detect section headers by emoji prefix
        const emojiMatch = trimmed.match(emojiRegex);

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
            // Add non-empty lines to current section content
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
        // Numbered emojis used in registry reports
        '🔒': 'info',
        '1️⃣': 'location',
        '2️⃣': 'valuation',
        '3️⃣': 'benchmark',
        '4️⃣': 'confidence',
        '5️⃣': 'valuation',
        '6️⃣': 'info',
        '7️⃣': 'info',
        '8️⃣': 'info',
        '9️⃣': 'info',
        '🔟': 'info',
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

/* ───────── Inline Markdown → HTML (for card text) ───────── */
function renderMarkdown(text) {
    if (!text) return '';

    // ── PRE-PROCESS: inject newlines before structural markers ──
    // Streaming chunks often arrive concatenated without \n
    let processed = text
        // Newline before bullet markers (• or · not at start)
        .replace(/([^\n])([•·])/g, '$1\n$2')
        // Newline before table rows (| at start of a row pattern)
        .replace(/([^\n|])\|(?=[A-Za-z0-9₹])/g, '$1\n|')
        // Newline before markdown table separator rows
        .replace(/([^\n])\|---/g, '$1\n|---')
        // Ensure space after :** in bold labels (e.g., **Name:**Value → **Name:** Value)
        .replace(/\*\*([^*]+?):\*\*(?=\S)/g, '**$1:** ')
        // Ensure space after : in bullet items without bold
        .replace(/:(?=[A-Z₹])/g, ': ');

    // Split into lines to detect tables
    const lines = processed.split('\n');
    const htmlLines = [];
    let inTable = false;
    let tableRows = [];

    const processInline = (line) => {
        return line
            // Bold: **text** or __text__
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/__(.+?)__/g, '<strong>$1</strong>')
            // Italic: *text* (but not inside bold)
            .replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>')
            // Bullet points: • at start of line → indented bullet
            .replace(/^[•·]\s*/gm, '<span class="bullet-item">•&nbsp;</span>');
    };

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();

        // Detect table rows (start and end with |)
        if (line.startsWith('|') && line.endsWith('|')) {
            // Skip separator rows (|---|---|)
            if (/^\|[\s\-:]+\|/.test(line) && !line.replace(/[\s|\-:]/g, '')) {
                continue;
            }
            if (!inTable) {
                inTable = true;
                tableRows = [];
            }
            const cells = line.split('|').filter(c => c.trim() !== '');
            tableRows.push(cells.map(c => processInline(c.trim())));
        } else {
            // End table if we were in one
            if (inTable) {
                htmlLines.push(buildTable(tableRows));
                inTable = false;
                tableRows = [];
            }

            if (line === '') {
                // Skip multiple blanks
                if (htmlLines.length > 0 && htmlLines[htmlLines.length - 1] !== '<br/>') {
                    htmlLines.push('<br/>');
                }
            } else {
                htmlLines.push(processInline(line));
            }
        }
    }

    // Close any pending table
    if (inTable && tableRows.length > 0) {
        htmlLines.push(buildTable(tableRows));
    }

    return htmlLines.join('<br/>');
}

function buildTable(tableRows) {
    if (!tableRows.length) return '';
    let html = '<table class="report-table"><thead><tr>';
    tableRows[0].forEach(h => { html += `<th>${h}</th>`; });
    html += '</tr></thead><tbody>';
    for (let r = 1; r < tableRows.length; r++) {
        html += '<tr>';
        tableRows[r].forEach(c => { html += `<td>${c}</td>`; });
        html += '</tr>';
    }
    html += '</tbody></table>';
    return html;
}

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

    const renderedContent = renderMarkdown(section.content);

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
                        <div className="intel-card-text" dangerouslySetInnerHTML={{ __html: renderedContent }} />
                    </>
                ) : (
                    <div className="intel-card-text" dangerouslySetInnerHTML={{ __html: renderedContent }} />
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
    const { token } = useAuth();
    const [loading, setLoading] = useState(false);
    const [copiedIndex, setCopiedIndex] = useState(null);

    const messagesEndRef = useRef(null);
    const location = useLocation();
    const chatInitialized = useRef(false);

    // Create a chat if none exists
    useEffect(() => {
        if (!currentChatId && !chatInitialized.current) {
            chatInitialized.current = true;
            createNewChat();
        }
    }, [currentChatId]);

    // Show welcome message for empty chats
    useEffect(() => {
        if (currentChatId && messages.length === 0) {
            addMessage(currentChatId, {
                id: crypto.randomUUID(),
                role: 'assistant',
                content: '📍 PurityProp Intelligence Engine — Ready\n\nReal estate valuation, registration data, stamp duty computation, and market intelligence for Tamil Nadu.\n\n🔍 Query any location for instant valuation.\n📊 Get structured pricing with confidence scores.\n🧠 Powered by official TN government data sources.'
            });
        }
    }, [currentChatId]);

    const initialMessageSent = useRef(false);

    useEffect(() => {
        if (location.state?.initialMessage && currentChatId && !initialMessageSent.current) {
            initialMessageSent.current = true;
            sendMessage(location.state.initialMessage);
            window.history.replaceState({}, document.title);
        }
    }, [location.state, currentChatId]);

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    const sendMessage = async (messageText) => {
        if (!currentChatId) return;

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
            const headers = { 'Content-Type': 'application/json' };
            if (token) headers['Authorization'] = `Bearer ${token}`;

            const response = await fetch(`${baseUrl}/api/chat/stream`, {
                method: 'POST',
                headers,
                body: JSON.stringify({
                    session_id: currentChatId,
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
                    session_id: currentChatId,
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
                    disabled={loading || !currentChatId}
                    placeholder="Enter location for valuation — e.g. 'Porur land price'"
                />
            </div>
        </div>
    );
};

export default AIChat;
