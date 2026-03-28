// ========== Helper Functions ==========
function escapeHtml(t) {
    let d = document.createElement('div');
    d.textContent = t;
    return d.innerHTML;
}

function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}

function copyText(id) {
    const text = document.getElementById(id).textContent;
    navigator.clipboard.writeText(text);
    showToast('Text copied');
}

// ========== User Management ==========
async function loadUsers() {
    if (!userId) return;
    try {
        const authToken = getToken();
        let res = await fetch(`/users/${userId}?search=${encodeURIComponent(document.getElementById('search-user').value)}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        let data = await res.json();
        let list = document.getElementById('users-list');
        list.innerHTML = '';
        if (!data.users || data.users.length === 0) {
            list.innerHTML = '<div class="empty-list">No users found</div>';
            return;
        }
        data.users.forEach(u => {
            let div = document.createElement('div');
            div.className = `user-item ${chatWithId === u.id ? 'active' : ''}`;
            div.setAttribute('data-user-id', u.id);
            div.innerHTML = `
                <div class="user-avatar">${u.username.charAt(0).toUpperCase()}</div>
                <div class="user-name">${u.username}</div>
            `;
            div.onclick = () => openChat(u.id, u.username);
            list.appendChild(div);
        });
    } catch (e) {
        console.error(e);
    }
}

// ========== Video Functions ==========
async function sendVideo() {
    if (!selectedVideoFile) {
        showToast('No video to send', true);
        return;
    }

    if (!ws || ws.readyState !== WebSocket.OPEN) {
        showToast('Connecting to server...', true);
        if (chatWithId) {
            connectWebSocket();
            await new Promise(r => setTimeout(r, 1000));
            if (!ws || ws.readyState !== WebSocket.OPEN) {
                showToast('Connection failed', true);
                return;
            }
        } else {
            showToast('Not connected to server', true);
            return;
        }
    }

    showToast('Uploading video...');
    try {
        let fd = new FormData();
        fd.append('file', selectedVideoFile);
        let res = await fetch('/upload-video', { method: 'POST', body: fd });
        let result = await res.json();
        if (result.status === 'success') {
            ws.send(JSON.stringify({
                type: 'video',
                media_path: result.media_path,
                duration: result.duration || 0
            }));
            addVideoMessage(userId, result.media_path, result.duration || 0);
            showToast('Video sent');
            document.getElementById('video-preview').style.display = 'none';
            document.getElementById('media-input').value = '';
            selectedVideoFile = null;
        } else {
            showToast('Failed to upload video: ' + (result.detail || 'Error'), true);
        }
    } catch (e) {
        console.error('Error sending video:', e);
        showToast('Error sending video', true);
    }
}

function cancelVideoPreview() {
    const videoPreview = document.getElementById('video-preview');
    const mediaInput = document.getElementById('media-input');
    if (videoPreview) videoPreview.style.display = 'none';
    if (mediaInput) mediaInput.value = '';
    selectedVideoFile = null;
}

function addVideoMessage(sender, videoPath, duration = 0, timestamp = null, msgId = null) {
    let div = document.getElementById('messages');
    let msgDiv = document.createElement('div');
    msgCounter++;
    let mid = msgId ? `video_${msgId}` : `video_${Date.now()}_${msgCounter}`;
    msgDiv.setAttribute('data-mid', mid);
    if (msgId) msgDiv.setAttribute('data-message-id', msgId);

    let isSent = sender === userId;
    msgDiv.className = `message ${isSent ? 'sent' : 'received'}`;

    let time;
    if (timestamp) {
        let d = new Date(timestamp);
        time = d.toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' });
        addDateSeparatorIfNeeded(d, div);
    } else {
        time = new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' });
    }

    let fullPath = videoPath;
    if (!fullPath.startsWith('/')) {
        fullPath = '/' + fullPath;
    }

    let minutes = Math.floor(duration / 60);
    let seconds = duration % 60;
    let durationText = duration > 0 ? ` • ${minutes}:${seconds.toString().padStart(2, '0')}` : '';

    let senderName = isSent ? 'You' : chatWithName;

    msgDiv.innerHTML = `
        <div class="message-bubble">
            <video class="message-video" controls preload="metadata" style="max-width: 250px; max-height: 250px; border-radius: 12px;">
                <source src="${fullPath}" type="video/mp4">
                Your browser doesn't support video playback
            </video>
            <div class="message-meta">${senderName} • ${time}${durationText}</div>
        </div>
    `;
    div.appendChild(msgDiv);
    scrollToBottom();
    return mid;
}

// ========== Image Modal ==========
function showImageModal(path) {
    currentImagePath = path;
    const modal = document.getElementById('image-modal');
    const modalImg = document.getElementById('modal-image');
    const caption = document.getElementById('modal-caption');

    modalImg.src = path;

    const fileName = path.split('/').pop();
    caption.textContent = fileName;

    modal.classList.add('active');
    isZoomed = false;
    document.body.style.overflow = 'hidden';
}

function closeImageModal() {
    const modal = document.getElementById('image-modal');
    modal.classList.remove('active');
    document.body.style.overflow = '';
    isZoomed = false;
    const modalImg = document.getElementById('modal-image');
    modalImg.classList.remove('zoomed');
}

function zoomImage() {
    const modalImg = document.getElementById('modal-image');
    const zoomBtn = document.getElementById('zoom-btn');

    if (!isZoomed) {
        modalImg.classList.add('zoomed');
        zoomBtn.innerHTML = 'Zoom Out';
        isZoomed = true;
    } else {
        modalImg.classList.remove('zoomed');
        zoomBtn.innerHTML = 'Zoom In';
        isZoomed = false;
    }
}

function downloadImage() {
    if (currentImagePath) {
        const link = document.createElement('a');
        link.href = currentImagePath;
        link.download = currentImagePath.split('/').pop();
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        showToast('Downloading image...');
    }
}

function formatDateTime(date) {
    return date.toLocaleString('ar-EG');
}