/**
 * ChatContext — Per-User Database-Backed Chat Management
 *
 * Sessions are stored in the database, linked to authenticated users via owner_id.
 * Each user sees only their own chats. Chats persist across devices.
 *
 * API endpoints used:
 *   GET    /api/sessions              — list user's sessions
 *   POST   /api/sessions              — create new session
 *   PATCH  /api/sessions/{id}         — rename session
 *   DELETE /api/sessions/{id}         — delete session
 *   DELETE /api/sessions              — clear all sessions
 *   GET    /api/sessions/{id}/messages — load messages for a session
 */

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from './AuthContext';
import axios from 'axios';

const ChatContext = createContext(null);

const API_URL = (import.meta.env.VITE_API_URL || '').trim();

// Axios instance that auto-attaches auth token
function useApi() {
    const { token } = useAuth();
    const instance = useRef(
        axios.create({ baseURL: API_URL, timeout: 15000 })
    );

    useEffect(() => {
        const id = instance.current.interceptors.request.use((config) => {
            if (token) {
                config.headers.Authorization = `Bearer ${token}`;
            }
            return config;
        });
        return () => instance.current.interceptors.request.eject(id);
    }, [token]);

    return instance.current;
}

export function ChatProvider({ children }) {
    const { user, token, loading: authLoading } = useAuth();
    const api = useApi();

    const [chats, setChats] = useState([]);       // [{session_id, title, created_at, updated_at, message_count}]
    const [currentChatId, setCurrentChatId] = useState(null);
    const [messages, setMessages] = useState([]);
    const [loadingChats, setLoadingChats] = useState(true);

    const fetchedRef = useRef(false);

    // ── Load sessions from backend when user logs in ──────────────────
    useEffect(() => {
        if (authLoading) return;  // wait for auth to settle

        if (user && token && !fetchedRef.current) {
            fetchedRef.current = true;
            loadSessionsFromBackend();
        }

        if (!user) {
            // Logged out — clear everything
            fetchedRef.current = false;
            setChats([]);
            setCurrentChatId(null);
            setMessages([]);
            setLoadingChats(false);
        }
    }, [user, token, authLoading]);

    const loadSessionsFromBackend = async () => {
        setLoadingChats(true);
        try {
            const res = await api.get('/api/sessions');
            const sessions = (res.data.sessions || []).map(s => ({
                id: s.session_id,
                title: s.title || 'New Chat',
                createdAt: s.created_at,
                updatedAt: s.updated_at,
                messageCount: s.message_count || 0,
                messages: null,  // lazy-loaded on select
            }));
            setChats(sessions);

            // Restore last active chat if still exists
            const lastChatId = localStorage.getItem('currentChatId');
            if (lastChatId && sessions.find(s => s.id === lastChatId)) {
                setCurrentChatId(lastChatId);
            }
        } catch (err) {
            console.error('Failed to load sessions:', err?.response?.data || err.message);
        } finally {
            setLoadingChats(false);
        }
    };

    // ── Load messages when switching chats ────────────────────────────
    useEffect(() => {
        if (!currentChatId) {
            setMessages([]);
            localStorage.removeItem('currentChatId');
            return;
        }

        localStorage.setItem('currentChatId', currentChatId);

        // Check if messages are already cached in the chat object
        const chat = chats.find(c => c.id === currentChatId);
        if (chat?.messages) {
            setMessages(chat.messages);
            return;
        }

        // Fetch from backend
        loadMessagesFromBackend(currentChatId);
    }, [currentChatId]);

    const loadMessagesFromBackend = async (chatId) => {
        try {
            const res = await api.get(`/api/sessions/${chatId}/messages`);
            const msgs = (res.data.messages || []).map((m, idx) => ({
                id: `${chatId}-msg-${idx}`,
                role: m.role,
                content: m.content,
                language: m.language,
                timestamp: m.timestamp,
            }));
            setMessages(msgs);

            // Cache in the chat object
            setChats(prev => prev.map(c =>
                c.id === chatId ? { ...c, messages: msgs } : c
            ));
        } catch (err) {
            console.error('Failed to load messages:', err?.response?.data || err.message);
            setMessages([]);
        }
    };

    // ── Create new chat (calls backend) ──────────────────────────────
    const createNewChat = useCallback(async () => {
        try {
            const res = await api.post('/api/sessions', { title: 'New Chat' });
            const newChat = {
                id: res.data.session_id,
                title: res.data.title || 'New Chat',
                createdAt: res.data.created_at,
                updatedAt: res.data.created_at,
                messageCount: 0,
                messages: [],
            };
            setChats(prev => [newChat, ...prev]);
            setCurrentChatId(newChat.id);
            setMessages([]);
            return newChat.id;
        } catch (err) {
            console.error('Failed to create session:', err?.response?.data || err.message);
            // Fallback: create local-only session
            const fallbackId = crypto.randomUUID();
            const fallback = {
                id: fallbackId,
                title: 'New Chat',
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString(),
                messageCount: 0,
                messages: [],
            };
            setChats(prev => [fallback, ...prev]);
            setCurrentChatId(fallbackId);
            setMessages([]);
            return fallbackId;
        }
    }, [api]);

    // ── Add message (local state + backend saves it via /chat) ───────
    const addMessage = useCallback((chatId, message) => {
        const msgWithId = {
            ...message,
            id: message.id || crypto.randomUUID(),
        };

        setMessages(prev => [...prev, msgWithId]);

        setChats(prev => prev.map(chat => {
            if (chat.id !== chatId) return chat;

            const updatedMessages = [...(chat.messages || []), msgWithId];
            const title = chat.title === 'New Chat' && message.role === 'user'
                ? message.content.slice(0, 60)
                : chat.title;

            return { ...chat, messages: updatedMessages, title };
        }));
    }, []);

    // ── Update message (for streaming) ───────────────────────────────
    const updateMessage = useCallback((chatId, messageId, updates) => {
        setMessages(prev => prev.map(msg =>
            msg.id === messageId ? { ...msg, ...updates } : msg
        ));

        setChats(prev => prev.map(chat => {
            if (chat.id !== chatId) return chat;
            const updatedMessages = (chat.messages || []).map(msg =>
                msg.id === messageId ? { ...msg, ...updates } : msg
            );
            return { ...chat, messages: updatedMessages };
        }));
    }, []);

    // ── Delete chat (calls backend) ──────────────────────────────────
    const deleteChat = useCallback(async (chatId) => {
        setChats(prev => prev.filter(c => c.id !== chatId));
        if (currentChatId === chatId) {
            setCurrentChatId(null);
            setMessages([]);
        }

        try {
            await api.delete(`/api/sessions/${chatId}`);
        } catch (err) {
            console.error('Failed to delete session:', err?.response?.data || err.message);
        }
    }, [currentChatId, api]);

    // ── Rename chat (calls backend) ──────────────────────────────────
    const renameChat = useCallback(async (chatId, newTitle) => {
        const trimmed = newTitle.slice(0, 120);
        setChats(prev => prev.map(c =>
            c.id === chatId ? { ...c, title: trimmed } : c
        ));

        try {
            await api.patch(`/api/sessions/${chatId}`, { title: trimmed });
        } catch (err) {
            console.error('Failed to rename session:', err?.response?.data || err.message);
        }
    }, [api]);

    // ── Clear all chats (calls backend) ──────────────────────────────
    const clearAllChats = useCallback(async () => {
        setChats([]);
        setCurrentChatId(null);
        setMessages([]);
        localStorage.removeItem('currentChatId');

        try {
            await api.delete('/api/sessions');
        } catch (err) {
            console.error('Failed to clear sessions:', err?.response?.data || err.message);
        }
    }, [api]);

    // ── Load existing chat ───────────────────────────────────────────
    const loadChat = useCallback((chatId) => {
        setCurrentChatId(chatId);
    }, []);

    const value = {
        chats,
        currentChatId,
        messages,
        loadingChats,
        createNewChat,
        loadChat,
        addMessage,
        updateMessage,
        deleteChat,
        renameChat,
        clearAllChats,
        setCurrentChatId,
    };

    return (
        <ChatContext.Provider value={value}>
            {children}
        </ChatContext.Provider>
    );
}

export function useChat() {
    const ctx = useContext(ChatContext);
    if (!ctx) throw new Error('useChat must be used inside <ChatProvider>');
    return ctx;
}

export default ChatContext;
