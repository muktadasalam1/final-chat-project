// ========== WebSocket ==========
function connectWebSocket() {
    if (reconnectTimeout) clearTimeout(reconnectTimeout);
    if (!userId || !chatWithId) {
        console.log('Cannot connect: userId or chatWithId missing');
        return;
    }
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
        console.log('WebSocket already open or connecting');
        return;
    }

    try {
        let protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        let wsUrl = `${protocol}//${location.host}/ws/${userId}/${chatWithId}`;
        console.log('Connecting to WebSocket:', wsUrl);

        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('WebSocket connected');
            const sendButton = document.getElementById('send-button');
            if (sendButton) sendButton.disabled = false;
            reconnectAttempts = 0;
        };

        ws.onmessage = (ev) => {
            try {
                let d = JSON.parse(ev.data);
                if (d.type === 'text') {
                    addMsg(d.sender, d.message, d.timestamp, d.tempId, d.id);
                } else if (d.type === 'image') {
                    addImageMsg(d.sender, d.media_path, d.timestamp, d.id);
                } else if (d.type === 'audio') {
                    addAudioMessage(d.sender, d.media_path, d.duration, d.timestamp, d.id);
                } else if (d.type === 'video') {
                    addVideoMessage(d.sender, d.media_path, d.duration, d.timestamp, d.id);
                }
                scrollToBottom();
            } catch (e) {
                console.error('Error parsing message:', e);
            }
        };

        ws.onclose = (event) => {
            console.log('WebSocket disconnected, code:', event.code);
            const sendButton = document.getElementById('send-button');
            if (sendButton) sendButton.disabled = true;

            if (chatWithId && reconnectAttempts < maxReconnectAttempts && !window.isClosingWebSocket) {
                reconnectAttempts++;
                reconnectTimeout = setTimeout(() => {
                    console.log('Reconnecting... attempt', reconnectAttempts);
                    if (chatWithId) connectWebSocket();
                }, Math.min(1000 * Math.pow(1.5, reconnectAttempts - 1), 10000));
            }
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

    } catch (e) {
        console.error('Error creating WebSocket:', e);
    }
}

function closeWebSocket() {
    window.isClosingWebSocket = true;
    if (reconnectTimeout) clearTimeout(reconnectTimeout);
    if (ws) {
        try {
            ws.close();
        } catch (e) { }
        ws = null;
    }
    reconnectAttempts = 0;
    setTimeout(() => {
        window.isClosingWebSocket = false;
    }, 100);
}

function connectNotificationWebSocket() {
    if (!userId) return;
    if (notificationWs && notificationWs.readyState === WebSocket.OPEN) return;
    let protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    notificationWs = new WebSocket(`${protocol}//${location.host}/ws/notifications/${userId}`);
    notificationWs.onmessage = (event) => {
        try {
            let data = JSON.parse(event.data);
            if (data.type === 'text') {
                if (data.sender !== chatWithId) {
                    showToast(`New message from ${data.sender_name || 'User'}: ${data.message}`);
                    if (!unreadMessagesCount[data.sender]) unreadMessagesCount[data.sender] = 0;
                    unreadMessagesCount[data.sender]++;
                    updateUnreadBadge(data.sender, unreadMessagesCount[data.sender]);
                }
            }
        } catch (e) {
            console.error('Error parsing notification:', e);
        }
    };
}

function connectUsersUpdatesWebSocket() {
    if (!userId) return;
    if (usersUpdateWs && usersUpdateWs.readyState === WebSocket.OPEN) return;
    let protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    usersUpdateWs = new WebSocket(`${protocol}//${location.host}/ws/users-updates`);
    usersUpdateWs.onmessage = (event) => {
        try {
            let data = JSON.parse(event.data);
            if (data.type === 'new_user') {
                showToast(`New user joined: ${data.user.username}`);
                loadUsers();
            }
        } catch (e) {
            console.error('Error parsing users update:', e);
        }
    };
}