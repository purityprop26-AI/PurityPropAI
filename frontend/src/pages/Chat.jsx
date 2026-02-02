import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { MessageSquare, RefreshCw, AlertCircle, LogOut } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import ChatMessage from '../components/ChatMessage';
import ChatInput from '../components/ChatInput';

const API_URL = (import.meta.env.VITE_API_URL || '').trim();

function Chat() {
    const [messages, setMessages] = useState([]);
    const [sessionId, setSessionId] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const messagesEndRef = useRef(null);
    const { user, logout, token } = useAuth();

    // Auto-scroll to bottom
    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // Create new session on mount
    useEffect(() => {
        createNewSession();
    }, []);

    const createNewSession = async () => {
        try {
            setLoading(true);
            setError(null);
            const response = await axios.post(`${API_URL}/api/sessions`, {}, {
                headers: { Authorization: `Bearer ${token} ` }
            });
            setSessionId(response.data.session_id);
            setMessages([]);

            // Add welcome message
            setMessages([{
                role: 'assistant',
                content: `வணக்கம் ${user?.name} !Welcome! Vanakkam!\n\nI am your Tamil Nadu Real Estate AI Assistant.I can help you with: \n\n• Property buying and selling(சொத்து வாங்குதல் மற்றும் விற்பனை) \n• Registration process(பதிவு செயல்முறை) \n• Required documents(தேவையான ஆவணங்கள்) \n• Bank loans(வங்கி கடன்) \n• Legal compliance(சட்ட இணக்கம்) \n\nYou can ask questions in Tamil(தமிழ்), Tanglish, or English!`,
                language: 'multilingual',
                timestamp: new Date().toISOString()
            }]);
        } catch (err) {
            setError('Failed to create session. Please refresh the page.');
            console.error('Session creation error:', err);
        } finally {
            setLoading(false);
        }
    };

    const sendMessage = async (messageText) => {
        if (!sessionId) {
            setError('No active session. Please refresh the page.');
            return;
        }

        // Add user message to UI
        const userMessage = {
            role: 'user',
            content: messageText,
            timestamp: new Date().toISOString()
        };
        setMessages(prev => [...prev, userMessage]);
        setLoading(true);
        setError(null);

        try {
            const response = await axios.post(`${API_URL}/api/chat`, {
                session_id: sessionId,
                message: messageText
            }, {
                headers: { Authorization: `Bearer ${token} ` }
            });

            // Add assistant response
            const assistantMessage = {
                role: 'assistant',
                content: response.data.message,
                language: response.data.language,
                timestamp: response.data.timestamp
            };
            setMessages(prev => [...prev, assistantMessage]);
        } catch (err) {
            setError('Failed to get response. Please try again.');
            console.error('Chat error:', err);

            // Remove user message if request failed
            setMessages(prev => prev.slice(0, -1));
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="app">
            {/* Header */}
            <header className="app-header">
                <div className="header-content">
                    <div className="header-title">
                        <MessageSquare size={28} className="header-icon" />
                        <div>
                            <h1>TN Real Estate AI Assistant</h1>
                            <p className="header-subtitle">தமிழ்நாடு ரியல் எஸ்டேட் AI உதவியாளர்</p>
                        </div>
                    </div>
                    <div className="header-actions">
                        <button
                            className="new-chat-button"
                            onClick={createNewSession}
                            disabled={loading}
                            title="Start new conversation"
                        >
                            <RefreshCw size={18} />
                            <span>New Chat</span>
                        </button>
                        <button
                            className="logout-button"
                            onClick={logout}
                            title="Logout"
                        >
                            <LogOut size={18} />
                            <span>Logout</span>
                        </button>
                    </div>
                </div>
            </header>

            {/* Main Chat Area */}
            <main className="chat-container">
                <div className="messages-container">
                    {messages.map((msg, index) => (
                        <ChatMessage
                            key={index}
                            message={msg}
                            isUser={msg.role === 'user'}
                        />
                    ))}
                    {loading && (
                        <div className="typing-indicator">
                            <div className="typing-dot"></div>
                            <div className="typing-dot"></div>
                            <div className="typing-dot"></div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                {/* Error Display */}
                {error && (
                    <div className="error-banner">
                        <AlertCircle size={18} />
                        <span>{error}</span>
                    </div>
                )}

                {/* Input Area */}
                <ChatInput
                    onSend={sendMessage}
                    disabled={loading || !sessionId}
                    loading={loading}
                />
            </main>

            {/* Footer */}
            <footer className="app-footer">
                <p>
                    ⚠️ This is informational guidance only, not legal advice.
                    Consult professionals for specific cases.
                </p>
            </footer>
        </div>
    );
}

export default Chat;
