// ========== Audio Recording ==========
async function requestMicrophonePermission() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        console.log('Microphone not supported in this context (HTTP)');
        return false;
    }
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        stream.getTracks().forEach(track => track.stop());
        console.log('Microphone permission granted');
        return true;
    } catch (err) {
        console.error('Microphone permission denied:', err);
        if (err.name === 'NotAllowedError') {
            showToast('Microphone access denied', true);
        } else if (err.name === 'NotFoundError') {
            showToast('No microphone detected', true);
        }
        return false;
    }
}

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = async () => {
            recordedAudioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            audioDuration = Math.round((Date.now() - startTime) / 1000);
            showRecordingControls();
            stream.getTracks().forEach(track => track.stop());
        };

        mediaRecorder.start();
        isRecording = true;
        startTime = Date.now();
        const voiceBtn = document.getElementById('voice-btn');
        voiceBtn.classList.add('recording');
        voiceBtn.innerHTML = '⏹️';
        showToast('Recording... Press Stop to finish');
        voiceBtn.onclick = stopRecording;
    } catch (err) {
        console.error('Recording error:', err);
        showToast('Cannot access microphone', true);
    }
}

function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        const voiceBtn = document.getElementById('voice-btn');
        voiceBtn.classList.remove('recording');
        voiceBtn.innerHTML = '🎤';
        voiceBtn.onclick = () => {
            if (recordedAudioBlob) {
                showToast('Please send or cancel existing recording first');
                return;
            }
            startRecording();
        };
    }
}

function showRecordingControls() {
    let controlBar = document.getElementById('recording-controls');
    if (!controlBar) {
        controlBar = document.createElement('div');
        controlBar.id = 'recording-controls';
        controlBar.style.cssText = `position:fixed;bottom:100px;left:50%;transform:translateX(-50%);background:#1e2b36;border-radius:32px;padding:12px 20px;display:flex;gap:16px;z-index:2000;border:1px solid #2b5278;`;
        document.body.appendChild(controlBar);
    }
    const minutes = Math.floor(audioDuration / 60);
    const seconds = audioDuration % 60;
    const durationText = `${minutes}:${seconds.toString().padStart(2, '0')}`;
    controlBar.innerHTML = `
        <div style="display:flex;align-items:center;gap:12px;">
            <span style="color:#ff5e5e;">🎙️ Recording: ${durationText}</span>
            <button onclick="cancelRecording()" style="background:#ff5e5e;border:none;color:white;padding:8px 20px;border-radius:24px;cursor:pointer;">❌ Cancel</button>
            <button onclick="sendRecordedAudio()" style="background:linear-gradient(135deg,#2b5278,#1e3a5f);border:none;color:white;padding:8px 20px;border-radius:24px;cursor:pointer;">📤 Send</button>
        </div>
    `;
}

function cancelRecording() {
    recordedAudioBlob = null;
    audioChunks = [];
    audioDuration = 0;
    const controlBar = document.getElementById('recording-controls');
    if (controlBar) controlBar.remove();
    showToast('Recording cancelled');
}

async function sendRecordedAudio() {
    if (!recordedAudioBlob) {
        showToast('No recording to send', true);
        return;
    }
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        showToast('Not connected to server', true);
        return;
    }
    const controlBar = document.getElementById('recording-controls');
    if (controlBar) controlBar.remove();
    await sendAudioToServer(recordedAudioBlob);
    recordedAudioBlob = null;
    audioChunks = [];
    audioDuration = 0;
}

async function sendAudioToServer(audioBlob) {
    const formData = new FormData();
    formData.append('file', audioBlob, 'audio.webm');
    formData.append('duration', audioDuration);
    showToast('Uploading audio...');
    try {
        const response = await fetch('/upload-audio', { method: 'POST', body: formData });
        const result = await response.json();
        if (result.status === 'success') {
            ws.send(JSON.stringify({
                type: 'audio',
                media_path: result.media_path,
                duration: result.duration
            }));
            showToast('Audio sent');
        } else {
            showToast('Failed to upload audio', true);
        }
    } catch (err) {
        console.error('Error sending audio:', err);
        showToast('Error sending audio', true);
    }
}

function addAudioMessage(sender, audioPath, duration, timestamp = null, msgId = null) {
    let div = document.getElementById('messages');
    let msgDiv = document.createElement('div');
    msgCounter++;
    let mid = msgId ? `audio_${msgId}` : `audio_${Date.now()}_${msgCounter}`;
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

    let minutes = Math.floor(duration / 60);
    let seconds = duration % 60;
    let durationText = `${minutes}:${seconds.toString().padStart(2, '0')}`;

    let fullPath = audioPath;
    if (!fullPath.startsWith('/')) {
        fullPath = '/' + fullPath;
    }

    let senderName = isSent ? 'You' : chatWithName;

    msgDiv.innerHTML = `
        <div class="message-bubble">
            <div class="audio-player">
                <button class="audio-play-btn" onclick="playAudio(this)">Play</button>
                <span class="audio-duration">${durationText}</span>
                <audio src="${fullPath}" style="display: none;" preload="none"></audio>
            </div>
            <div class="message-meta">${senderName} • ${time}</div>
        </div>
    `;
    div.appendChild(msgDiv);
    scrollToBottom();
    return mid;
}

function playAudio(btn) {
    let audio = btn.parentElement.querySelector('audio');
    if (audio.paused) {
        audio.play().catch(e => console.error('Play error:', e));
        btn.innerHTML = 'Pause';
        audio.onended = () => {
            btn.innerHTML = 'Play';
        };
    } else {
        audio.pause();
        btn.innerHTML = 'Play';
    }
}

function checkMicrophoneSupport() {
    if (/Android|webOS|iPhone|iPad|iPod/i.test(navigator.userAgent)) {
        console.log('Mobile device detected, skipping HTTPS check');
        return true;
    }

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        showToast('Browser does not support microphone', true);
        return false;
    }
    return true;
}

async function initVoiceButton() {
    const voiceBtn = document.getElementById('voice-btn');
    if (voiceBtn) {
        voiceBtn.onclick = async () => {
            if (!checkMicrophoneSupport()) return;

            if (recordedAudioBlob) {
                showToast('Please send or cancel existing recording first');
                return;
            }

            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                stream.getTracks().forEach(track => track.stop());
                showToast('Microphone access granted');
                startRecording();
            } catch (err) {
                console.error('Microphone error:', err);

                if (err.name === 'NotAllowedError') {
                    showToast('Microphone access denied', true);
                    if (confirm('Would you like to open microphone settings?')) {
                        if (location.protocol === 'http:') {
                            alert('Site is running on HTTP. For microphone access, please use HTTPS or Firefox');
                        } else {
                            window.open('chrome://settings/content/microphone', '_blank');
                        }
                    }
                } else if (err.name === 'NotFoundError') {
                    showToast('No microphone detected', true);
                } else {
                    showToast('Cannot access microphone: ' + err.message, true);
                }
            }
        };
    }
}