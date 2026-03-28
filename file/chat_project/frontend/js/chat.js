// ========== Chat Functions ==========
async function openChat(id, name) {
    if (window.innerWidth <= 768) {
        closeSidebar();
        const menuToggle = document.getElementById('menu-toggle');
        const backButton = document.getElementById('back-to-chats-btn');
        if (menuToggle) menuToggle.style.display = 'none';
        if (backButton) backButton.style.display = 'flex';
    }

    if (chatWithId === id && ws && ws.readyState === WebSocket.OPEN) return;
    closeWebSocket();
    chatWithId = id;
    chatWithName = name;
    lastAddedDate = null;
    if (unreadMessagesCount[id]) {
        delete unreadMessagesCount[id];
        updateUnreadBadge(id, 0);
    }

    document.getElementById('no-chat-selected').style.display = 'none';
    document.getElementById('chat-container').style.display = 'flex';
    document.getElementById('chat-with').innerHTML = name;
    loadUsers();
    document.getElementById('messages').innerHTML = '';

    try {
        const authToken = getToken();
        let res = await fetch(`/messages/${userId}/${chatWithId}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        let data = await res.json();

        if (data.messages && data.messages.length > 0) {
            data.messages.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
            data.messages.forEach(msg => {
                if (msg.content_type === 'image') {
                    addImageMsg(msg.sender, msg.media_path || msg.message, msg.created_at, msg.id);
                } else if (msg.content_type === 'audio') {
                    addAudioMessage(msg.sender, msg.media_path || msg.message, msg.duration || 0, msg.created_at, msg.id);
                } else if (msg.content_type === 'video') {
                    addVideoMessage(msg.sender, msg.media_path || msg.message, msg.duration || 0, msg.created_at, msg.id);
                } else {
                    addMsg(msg.sender, msg.message, msg.created_at, null, msg.id);
                }
            });
        }
        scrollToBottom();
        connectWebSocket();
    } catch (e) {
        console.error(e);
    }
}

function closeChat() {
    closeWebSocket();

    if (typeof cancelImagePreview === 'function') cancelImagePreview();
    if (typeof cancelVideoPreview === 'function') cancelVideoPreview();

    chatWithId = null;
    chatWithName = null;

    const noChatSelected = document.getElementById('no-chat-selected');
    const chatContainer = document.getElementById('chat-container');
    const messagesDiv = document.getElementById('messages');

    if (noChatSelected) noChatSelected.style.display = 'flex';
    if (chatContainer) chatContainer.style.display = 'none';
    if (messagesDiv) messagesDiv.innerHTML = '';

    loadUsers();

    if (window.innerWidth <= 768) {
        const menuToggle = document.getElementById('menu-toggle');
        const backButton = document.getElementById('back-to-chats-btn');
        if (menuToggle) menuToggle.style.display = 'flex';
        if (backButton) backButton.style.display = 'none';
    }
}

function sendMessage() {
    let inp = document.getElementById('message-input'),
        msg = inp.value.trim();
    if (!msg) return;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        alert('Connecting...');
        return;
    }
    let tempId = Date.now();
    pendingMessageIds.add(tempId);
    addMsgLocal(userId, msg, tempId);
    scrollToBottom();
    ws.send(JSON.stringify({
        type: 'text',
        message: msg,
        tempId: tempId
    }));
    inp.value = '';
}

function handleTyping() {
    if (ws && ws.readyState === WebSocket.OPEN && chatWithId) {
        ws.send(JSON.stringify({
            type: 'typing',
            isTyping: true
        }));
        clearTimeout(window.typingTimeout);
        window.typingTimeout = setTimeout(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'typing',
                    isTyping: false
                }));
            }
        }, 2000);
    }
}