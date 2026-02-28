import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
    Home,
    Building2,
    Calculator,
    FileText,
    CheckSquare,
    MessageSquare,
    LogOut,
    PanelLeftClose,
    PanelLeft,
    MoreVertical,
    Pencil,
    Trash2,
    Plus,
    Search
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useChat } from '../context/ChatContext';
import AnimatedLogo from './AnimatedLogo';

const Sidebar = () => {
    const location = useLocation();
    const navigate = useNavigate();
    const { user, logout } = useAuth();
    const { chats, currentChatId, loadChat, createNewChat, renameChat, deleteChat } = useChat();
    const [isCollapsed, setIsCollapsed] = useState(false);
    const [activeMenu, setActiveMenu] = useState(null);
    const [searchQuery, setSearchQuery] = useState('');

    const navItems = [
        { path: '/dashboard', icon: Home, label: 'Dashboard' },
        { path: '/properties', icon: Building2, label: 'Properties' },
        { path: '/valuation', icon: Calculator, label: 'Land Valuation' },
        { path: '/documents', icon: FileText, label: 'Documents' },
        { path: '/approvals', icon: CheckSquare, label: 'Approvals' },
        { path: '/chat', icon: MessageSquare, label: 'AI Assistant' },
    ];

    const isActive = (path) => location.pathname === path;

    // Filter chats: exclude empty "New Chat" entries and apply search, newest first
    const filteredChats = chats
        .filter(chat =>
            chat.title.toLowerCase().includes(searchQuery.toLowerCase()) &&
            (chat.title !== 'New Chat' || (chat.messages && chat.messages.length > 1))
        )
        .slice()
        .reverse();

    const handleNewChat = () => {
        createNewChat();
        navigate('/chat');
    };

    const handleChatClick = (chatId) => {
        loadChat(chatId);
        navigate('/chat');
        setActiveMenu(null);
    };

    const handleRenameChat = (chatId) => {
        const chat = chats.find(c => c.id === chatId);
        const newTitle = prompt('Enter new chat name:', chat?.title);
        if (newTitle && newTitle.trim()) {
            renameChat(chatId, newTitle.trim());
        }
        setActiveMenu(null);
    };

    const handleDeleteChat = (chatId) => {
        if (confirm('Are you sure you want to delete this chat?')) {
            deleteChat(chatId);
        }
        setActiveMenu(null);
    };

    return (
        <div className={`sidebar ${isCollapsed ? 'collapsed' : ''}`}>
            {/* Logo Header */}
            <div className="sidebar-header">
                <div className="sidebar-header-content">
                    <div className="sidebar-logo">
                        <AnimatedLogo size={40} />
                    </div>
                    <button
                        className="sidebar-toggle"
                        onClick={() => setIsCollapsed(!isCollapsed)}
                        title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
                    >
                        {isCollapsed ? <PanelLeft size={20} /> : <PanelLeftClose size={20} />}
                    </button>
                </div>
            </div>

            {/* New Chat & Search - ChatGPT Style */}
            {!isCollapsed && (
                <div className="new-chat-section">
                    <div className="new-chat-link" onClick={handleNewChat}>
                        <Plus size={18} />
                        <span>New chat</span>
                    </div>

                    {/* Search Chats */}
                    <div className="search-chat-wrapper">
                        <Search size={16} className="search-icon" />
                        <input
                            type="text"
                            className="search-chat-input"
                            placeholder="Search chats"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                    </div>
                </div>
            )}

            {/* Navigation */}
            <nav className="sidebar-nav">
                <div className="nav-section">
                    {!isCollapsed && <div className="nav-section-title">Main Menu</div>}
                    {navItems.map((item) => (
                        <Link
                            key={item.path}
                            to={item.path}
                            className={`nav-item ${isActive(item.path) ? 'active' : ''}`}
                            title={isCollapsed ? item.label : ''}
                        >
                            <div className="nav-item-icon">
                                <item.icon size={20} />
                            </div>
                            {!isCollapsed && <span className="nav-item-text">{item.label}</span>}
                        </Link>
                    ))}
                </div>

                {/* Chat History Section */}
                {!isCollapsed && filteredChats.length > 0 && (
                    <div className="nav-section">
                        <div className="nav-section-title">Recent Chats</div>
                        <div className="chat-history">
                            {filteredChats.slice(0, 10).map((chat) => (
                                <div
                                    key={chat.id}
                                    className={`chat-history-item-wrapper ${currentChatId === chat.id ? 'active' : ''}`}
                                >
                                    <div
                                        className="chat-history-item"
                                        onClick={() => handleChatClick(chat.id)}
                                    >
                                        {chat.title}
                                    </div>
                                    <div className="chat-menu-wrapper">
                                        <button
                                            className="chat-menu-button"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                setActiveMenu(activeMenu === chat.id ? null : chat.id);
                                            }}
                                        >
                                            <MoreVertical size={16} />
                                        </button>
                                        {activeMenu === chat.id && (
                                            <div className="chat-menu-dropdown">
                                                <button
                                                    className="chat-menu-item"
                                                    onClick={() => handleRenameChat(chat.id)}
                                                >
                                                    <Pencil size={14} />
                                                    Rename
                                                </button>
                                                <button
                                                    className="chat-menu-item delete"
                                                    onClick={() => handleDeleteChat(chat.id)}
                                                >
                                                    <Trash2 size={14} />
                                                    Delete
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </nav>

            {/* User Profile Footer */}
            {!isCollapsed && (
                <div className="sidebar-footer">
                    <div className="user-profile">
                        <div className="user-avatar">
                            {user?.name?.charAt(0).toUpperCase() || 'U'}
                        </div>
                        <div className="user-info">
                            <div className="user-name">{user?.name || 'User'}</div>
                            <div className="user-email">{user?.email || 'user@example.com'}</div>
                        </div>
                    </div>
                    <button
                        onClick={logout}
                        className="nav-item"
                        style={{ marginTop: '0.5rem', width: '100%', border: 'none', background: 'transparent' }}
                    >
                        <div className="nav-item-icon">
                            <LogOut size={20} />
                        </div>
                        <span className="nav-item-text">Logout</span>
                    </button>
                </div>
            )}
        </div>
    );
};

export default Sidebar;
