// ========== UI Functions ==========
function showToast(msg, isError = false) {
    let t = document.createElement('div');
    t.className = 'toast';
    t.textContent = msg;
    if (isError) t.style.borderColor = '#ff5e5e';
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 2000);
}

function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById(screenId).classList.add('active');

    const menuToggle = document.getElementById('menu-toggle');
    if (menuToggle) {
        if (screenId === 'chat-screen') {
            menuToggle.style.display = 'flex';
        } else {
            menuToggle.style.display = 'none';
        }
    }
}

function scrollToBottom() {
    let m = document.getElementById('messages');
    if (m) m.scrollTop = m.scrollHeight;
}

function requestNotificationPermission() {
    if ('Notification' in window) Notification.requestPermission();
}

// ========== Mobile Functions ==========
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    if (sidebar.classList.contains('open')) {
        sidebar.classList.remove('open');
        if (overlay) overlay.classList.remove('active');
    } else {
        sidebar.classList.add('open');
        if (overlay) overlay.classList.add('active');
    }
}

function toggleSidebarDesktop() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar.classList.contains('open-desktop')) {
        sidebar.classList.remove('open-desktop');
    } else {
        sidebar.classList.add('open-desktop');
    }
}

function closeSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    if (sidebar) sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('active');
}

function ensureSidebarOverlay() {
    if (!document.getElementById('sidebar-overlay')) {
        const overlay = document.createElement('div');
        overlay.id = 'sidebar-overlay';
        overlay.className = 'sidebar-overlay';
        overlay.onclick = closeSidebar;
        document.body.appendChild(overlay);
    }
}

function initMobileInterface() {
    const isMobile = window.innerWidth <= 768;
    const backButton = document.getElementById('back-to-chats-btn');
    const menuToggle = document.getElementById('menu-toggle');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');

    if (isMobile) {
        if (menuToggle) menuToggle.style.display = 'flex';

        const chatContainer = document.getElementById('chat-container');
        const observer = new MutationObserver(() => {
            if (chatContainer && chatContainer.style.display === 'flex') {
                if (menuToggle) menuToggle.style.display = 'none';
                if (backButton) backButton.style.display = 'flex';
                closeSidebar();
            } else {
                if (menuToggle) menuToggle.style.display = 'flex';
                if (backButton) backButton.style.display = 'none';
            }
        });
        observer.observe(chatContainer, { attributes: true });
    } else {
        if (menuToggle) menuToggle.style.display = 'none';
        if (backButton) backButton.style.display = 'none';
        if (sidebar) sidebar.classList.remove('open');
        if (overlay) overlay.classList.remove('active');
    }
}

function closeChatAndShowSidebar() {
    closeChat();
    if (window.innerWidth <= 768) {
        const menuToggle = document.getElementById('menu-toggle');
        if (menuToggle) menuToggle.style.display = 'flex';
        toggleSidebar();
    }
}