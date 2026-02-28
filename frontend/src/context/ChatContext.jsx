/**
 * ChatContext — Global Chat State Management
 *
 * Fixes applied:
 *   [HIGH-F3]  localStorage now capped at MAX_CHATS (50) with LRU eviction.
 *              Previously stored ALL chats forever → QuotaExceededError risk.
 *   [MED-F5]   Messages now use stable msg.id as key (set on creation).
 *              Previously used array index → incorrect DOM recycling on insert.
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

const ChatContext = createContext(null);

// FIX [HIGH-F3]: Hard caps prevent localStorage from growing unbounded.
const MAX_CHATS = 50;   // Max chat sessions kept in history
const MAX_MSG_COUNT = 100;  // Max messages kept per chat session

const STORAGE_KEY = 'chatHistory';

/** Load chat history from localStorage, gracefully handling corruption. */
function loadChatHistory() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return [];
        const parsed = JSON.parse(raw);
        if (!Array.isArray(parsed)) return [];

        // Deduplicate chats by id — keep last occurrence (most recent wins)
        // Also migrate old timestamp-based ids to UUIDs for stable React keys
        const seen = new Map();
        for (const chat of parsed) {
            // Migrate timestamp-based chat ids → UUID
            const isTimestampId = /^\d+$/.test(String(chat.id));
            const stableId = isTimestampId ? crypto.randomUUID() : (chat.id || crypto.randomUUID());

            // Ensure every message has a unique id (old messages have no id)
            const migratedMessages = Array.isArray(chat.messages)
                ? chat.messages.map((msg, idx) => ({
                    ...msg,
                    id: msg.id || `${stableId}-msg-${idx}-${crypto.randomUUID()}`,
                }))
                : [];

            seen.set(stableId, { ...chat, id: stableId, messages: migratedMessages });
        }
        return Array.from(seen.values());
    } catch {
        // Corrupted storage — start fresh
        localStorage.removeItem(STORAGE_KEY);
        return [];
    }
}



/**
 * Persist chat history to localStorage with size guard.
 * FIX [HIGH-F3]: Caps array at MAX_CHATS (LRU: drops oldest).
 *               Caps messages per chat at MAX_MSG_COUNT.
 *               Catches QuotaExceededError and silently drops oldest chat.
 */
function saveChatHistory(chats) {
    try {
        // Cap total sessions (keep most recent MAX_CHATS)
        const capped = chats.slice(-MAX_CHATS).map(chat => ({
            ...chat,
            // Cap messages per session to prevent per-chat bloat
            messages: Array.isArray(chat.messages)
                ? chat.messages.slice(-MAX_MSG_COUNT)
                : [],
        }));
        localStorage.setItem(STORAGE_KEY, JSON.stringify(capped));
    } catch (err) {
        // QuotaExceededError — storage full; evict oldest half and retry once
        if (err.name === 'QuotaExceededError' || err.code === 22) {
            try {
                const reduced = chats.slice(Math.ceil(chats.length / 2));
                localStorage.setItem(STORAGE_KEY, JSON.stringify(reduced));
            } catch {
                // If still failing, clear storage entirely to unblock the app
                localStorage.removeItem(STORAGE_KEY);
            }
        }
    }
}

export function ChatProvider({ children }) {
    const [chats, setChats] = useState(loadChatHistory);
    const [currentChatId, setCurrentChatId] = useState(() => {
        // Restore last active chat on mount
        try {
            const saved = localStorage.getItem('currentChatId');
            return saved || null;
        } catch { return null; }
    });
    const [messages, setMessages] = useState([]);

    // FIX [HIGH-F3]: Persist on change, but with cap enforcement
    useEffect(() => {
        if (chats.length > 0) {
            saveChatHistory(chats);
        }
    }, [chats]);

    // Sync messages when changing chat
    useEffect(() => {
        if (currentChatId) {
            const chat = chats.find(c => c.id === currentChatId);
            if (chat) {
                setMessages(chat?.messages || []);
                // Persist active chat ID
                try { localStorage.setItem('currentChatId', currentChatId); } catch { }
            } else {
                // Chat was deleted or doesn't exist — reset
                setCurrentChatId(null);
                setMessages([]);
                try { localStorage.removeItem('currentChatId'); } catch { }
            }
        } else {
            setMessages([]);
            try { localStorage.removeItem('currentChatId'); } catch { }
        }
    }, [currentChatId]);

    const createNewChat = useCallback(() => {
        const id = crypto.randomUUID();
        const newChat = {
            id,
            title: 'New Chat',
            messages: [],
            createdAt: new Date().toISOString(),
        };
        setChats(prev => [...prev, newChat]);
        setCurrentChatId(id);
        setMessages([]);
        return id;
    }, []);

    const addMessage = useCallback((chatId, message) => {
        // FIX [MED-F5]: Ensure every message has a stable unique id.
        // API responses get a uuid; welcome messages already have one set on creation.
        const msgWithId = {
            ...message,
            id: message.id || crypto.randomUUID(),
        };

        setMessages(prev => [...prev, msgWithId]);

        setChats(prev => prev.map(chat => {
            if (chat.id !== chatId) return chat;

            const updatedMessages = [...(chat.messages || []), msgWithId];
            // Auto-title from first user message
            const title = chat.title === 'New Chat' && message.role === 'user'
                ? message.content.slice(0, 40)
                : chat.title;

            return { ...chat, messages: updatedMessages, title };
        }));
    }, []);

    const updateMessage = useCallback((chatId, messageId, updates) => {
        // Update a specific message by id (used for streaming updates)
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

    const deleteChat = useCallback((chatId) => {
        setChats(prev => prev.filter(c => c.id !== chatId));
        if (currentChatId === chatId) {
            setCurrentChatId(null);
            setMessages([]);
        }
    }, [currentChatId]);

    const renameChat = useCallback((chatId, newTitle) => {
        setChats(prev => prev.map(c =>
            c.id === chatId ? { ...c, title: newTitle.slice(0, 60) } : c
        ));
    }, []);

    const clearAllChats = useCallback(() => {
        setChats([]);
        setCurrentChatId(null);
        setMessages([]);
        localStorage.removeItem(STORAGE_KEY);
        localStorage.removeItem('currentChatId');
    }, []);

    /**
     * loadChat — switch to an existing chat session.
     * Sets currentChatId AND immediately syncs the message list.
     * This is what Sidebar calls when a user clicks a recent chat.
     */
    const loadChat = useCallback((chatId) => {
        setCurrentChatId(chatId);
        setChats(prev => {
            const chat = prev.find(c => c.id === chatId);
            setMessages(chat?.messages || []);
            return prev; // no structural change, just side-effect sync
        });
    }, []);

    const value = {
        chats,
        currentChatId,
        messages,
        createNewChat,
        loadChat,        // FIX: was missing — Sidebar.jsx needs this to switch chats
        addMessage,
        updateMessage,   // NEW: for streaming message updates
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
