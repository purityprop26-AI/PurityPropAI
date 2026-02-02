import React, { useState, useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { useChat } from '../context/ChatContext';
import PremiumInput from '../components/PremiumInput';
import { Bot, User, Copy, Check } from 'lucide-react';

const API_URL = (import.meta.env.VITE_API_URL || '').trim();

const AIChat = () => {
    const { messages, currentChatId, addMessage, createNewChat } = useChat();
    const [sessionId, setSessionId] = useState(null);
    const [loading, setLoading] = useState(false);
    const [copiedIndex, setCopiedIndex] = useState(null);
    const [welcomeShown, setWelcomeShown] = useState(false);
    const messagesEndRef = useRef(null);
    const location = useLocation();
    const { token } = useAuth();

    useEffect(() => {
        // Create new chat if no current chat
        if (!currentChatId) {
            createNewChat();
        }
    }, [currentChatId, createNewChat]);

    useEffect(() => {
        // Reset welcome flag when chat changes
        setWelcomeShown(false);
        setSessionId(null);
    }, [currentChatId]);

    useEffect(() => {
        // Create session when we don't have one
        if (currentChatId && !sessionId) {
            createNewSession();
        }
    }, [currentChatId, sessionId]);

    const initialMessageSent = useRef(false);

    useEffect(() => {
        // Handle initial message from dashboard
        if (location.state?.initialMessage && sessionId && !initialMessageSent.current) {
            initialMessageSent.current = true;
            sendMessage(location.state.initialMessage);
            // Clear the state
            window.history.replaceState({}, document.title);
        }
    }, [location.state, sessionId]);

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    const createNewSession = async () => {
        try {
            const response = await axios.post(`${API_URL} /api/sessions`, {}, {
                headers: token ? { Authorization: `Bearer ${token} ` } : {}
            });
            setSessionId(response.data.session_id);

            // Add welcome message only once per chat and only if no messages exist
            if (messages.length === 0 && !welcomeShown) {
                setWelcomeShown(true);
                addMessage({
                    role: 'assistant',
                    content: 'வணக்கம்! Welcome! I\'m your Tamil Nadu Real Estate AI Assistant.\n\nI can help you with:\n• Property registration and documents\n• Stamp duty and fees\n• Land measurements (cents, grounds, acres)\n• Bank loans and eligibility\n• Legal compliance and regulations\n\nAsk me anything about real estate in Tamil Nadu!'
                });
            }
        } catch (err) {
            console.error('Session creation error:', err);
        }
    };

    const sendMessage = async (messageText) => {
        if (!sessionId) return;

        const userMessage = {
            role: 'user',
            content: messageText
        };
        addMessage(userMessage);
        setLoading(true);

        try {
            const response = await axios.post(`${API_URL} /api/chat`, {
                session_id: sessionId,
                message: messageText
            }, {
                headers: token ? { Authorization: `Bearer ${token} ` } : {}
            });

            const assistantMessage = {
                role: 'assistant',
                content: response.data.message,
                language: response.data.language
            };
            addMessage(assistantMessage);
        } catch (err) {
            console.error('Chat error:', err);
        } finally {
            setLoading(false);
        }
    };

    const copyToClipboard = (text, index) => {
        navigator.clipboard.writeText(text);
        setCopiedIndex(index);
        setTimeout(() => setCopiedIndex(null), 2000);
    };

    return (
        <div className="chat-container">
            <div className="chat-messages">
                {messages.map((msg, index) => (
                    <div key={index} className={`message - wrapper ${msg.role} `}>
                        <div className="message-avatar">
                            {msg.role === 'user' ? <User size={20} /> : <Bot size={20} />}
                        </div>
                        <div className="message-content-wrapper">
                            <div className="message-header">
                                <span className="message-role">
                                    {msg.role === 'user' ? 'You' : 'AI Assistant'}
                                </span>
                                {msg.role === 'assistant' && (
                                    <button
                                        className="copy-btn"
                                        onClick={() => copyToClipboard(msg.content, index)}
                                        title="Copy message"
                                    >
                                        {copiedIndex === index ? <Check size={16} /> : <Copy size={16} />}
                                    </button>
                                )}
                            </div>
                            <div className="message-text">{msg.content}</div>
                            {msg.language && (
                                <div className="message-meta">
                                    <span className="language-badge">{msg.language}</span>
                                </div>
                            )}
                        </div>
                    </div>
                ))}

                {loading && (
                    <div className="message-wrapper assistant">
                        <div className="message-avatar">
                            <Bot size={20} />
                        </div>
                        <div className="typing-indicator">
                            <div className="typing-dot"></div>
                            <div className="typing-dot"></div>
                            <div className="typing-dot"></div>
                        </div>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            <div className="chat-input-area">
                <PremiumInput
                    onSend={sendMessage}
                    disabled={loading || !sessionId}
                    placeholder="Ask about property registration, documents, loans..."
                />
            </div>
        </div>
    );
};

export default AIChat;
