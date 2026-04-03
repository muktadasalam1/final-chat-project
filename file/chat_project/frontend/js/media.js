// ========== Media Functions ==========
document.addEventListener('DOMContentLoaded', () => {
    const mediaInput = document.getElementById('media-input');
    if (mediaInput) {
        mediaInput.addEventListener('change', async (e) => {
            const files = e.target.files;
            if (!files || files.length === 0) return;

            if (files.length === 1) {
                const file = files[0];
                if (file.type.startsWith('image/')) {
                    selectedImageFile = file;
                    selectedVideoFile = null;
                    let reader = new FileReader();
                    reader.onload = (ev) => {
                        selectedImageData = ev.target.result;
                        document.getElementById('preview-img').src = selectedImageData;
                        document.getElementById('image-preview').style.display = 'block';
                        document.getElementById('video-preview').style.display = 'none';
                    };
                    reader.readAsDataURL(file);
                } else if (file.type.startsWith('video/')) {
                    selectedVideoFile = file;
                    selectedImageFile = null;
                    let reader = new FileReader();
                    reader.onload = (ev) => {
                        selectedVideoData = ev.target.result;
                        const videoPreview = document.getElementById('video-preview');
                        const videoElement = document.getElementById('preview-video');
                        videoElement.src = selectedVideoData;
                        videoPreview.style.display = 'block';
                        document.getElementById('image-preview').style.display = 'none';
                    };
                    reader.readAsDataURL(file);
                }
            } else {
                showToast(`Uploading ${files.length} files...`);

                for (let i = 0; i < files.length; i++) {
                    const file = files[i];

                    if (file.type.startsWith('image/')) {
                        await uploadAndSendImage(file);
                    } else if (file.type.startsWith('video/')) {
                        await uploadAndSendVideo(file);
                    }

                    if (i < files.length - 1) {
                        await new Promise(r => setTimeout(r, 500));
                    }
                }

                e.target.value = '';
                showToast('All files sent');
            }
        });
    }
});

async function uploadAndSendImage(file) {
    try {
        let fd = new FormData();
        fd.append('file', file);
        let res = await fetch('/upload-image', { method: 'POST', body: fd });
        let result = await res.json();

        if (result.status === 'success') {
            ws.send(JSON.stringify({
                type: 'image',
                media_path: result.media_path
            }));
            addImageMsg(userId, result.media_path);
        } else {
            showToast(`Failed to upload image: ${file.name}`, true);
        }
    } catch (e) {
        console.error('Error uploading image:', e);
        showToast(`Error uploading image: ${file.name}`, true);
    }
}

async function uploadAndSendVideo(file) {
    try {
        let fd = new FormData();
        fd.append('file', file);

        let duration = 0;
        const videoElement = document.createElement('video');
        videoElement.preload = 'metadata';
        videoElement.onloadedmetadata = function () {
            duration = Math.floor(videoElement.duration);
        };
        videoElement.src = URL.createObjectURL(file);
        await new Promise(r => setTimeout(r, 500));
        duration = Math.floor(videoElement.duration) || 0;

        fd.append('duration', duration);

        let res = await fetch('/upload-video', { method: 'POST', body: fd });
        let result = await res.json();

        if (result.status === 'success') {
            ws.send(JSON.stringify({
                type: 'video',
                media_path: result.media_path,
                duration: duration
            }));
            addVideoMessage(userId, result.media_path, duration);
        } else {
            showToast(`Failed to upload video: ${file.name}`, true);
        }
    } catch (e) {
        console.error('Error uploading video:', e);
        showToast(`Error uploading video: ${file.name}`, true);
    }
}

async function sendImage() {
    if (!selectedImageFile) {
        showToast('No image to send', true);
        return;
    }
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        showToast('Not connected to server', true);
        return;
    }
    showToast('Uploading image...');
    try {
        let fd = new FormData();
        fd.append('file', selectedImageFile);
        let res = await fetch('/upload-image', { method: 'POST', body: fd });
        let result = await res.json();
        if (result.status === 'success') {
            ws.send(JSON.stringify({
                type: 'image',
                media_path: result.media_path
            }));
            showToast('Image sent');
            document.getElementById('image-preview').style.display = 'none';
            document.getElementById('media-input').value = '';
            selectedImageFile = null;
        } else {
            showToast('Failed to upload image', true);
        }
    } catch (e) {
        console.error('Error sending image:', e);
        showToast('Error sending image', true);
    }
}

function cancelImagePreview() {
    const imagePreview = document.getElementById('image-preview');
    const mediaInput = document.getElementById('media-input');
    if (imagePreview) imagePreview.style.display = 'none';
    if (mediaInput) mediaInput.value = '';
    selectedImageFile = null;
}

function addImageMsg(sender, imagePath, timestamp = null, msgId = null) {
    let div = document.getElementById('messages');
    let msgDiv = document.createElement('div');
    msgCounter++;
    let mid = msgId ? `img_${msgId}` : `img_${Date.now()}_${msgCounter}`;
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

    let fullPath = imagePath;
    if (!fullPath.startsWith('/')) {
        fullPath = '/' + fullPath;
    }

    let senderName = isSent ? 'You' : chatWithName;

    msgDiv.innerHTML = `
        <div class="message-bubble">
            <img class="message-image" src="${fullPath}" 
                 onclick="showImageModal('${fullPath}')" 
                 style="max-width: 250px; max-height: 250px; border-radius: 12px; cursor: pointer;"
                 onerror="console.error('Image load failed:', '${fullPath}')">
            <div class="message-meta">${senderName} • ${time}</div>
        </div>
    `;
    div.appendChild(msgDiv);
    scrollToBottom();
    return mid;
}