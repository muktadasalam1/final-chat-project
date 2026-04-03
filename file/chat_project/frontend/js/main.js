// ========== Global Variables ==========
let userId = null;
let currentUsername = null;
let ws = null;
let notificationWs = null;
let usersUpdateWs = null;
let chatWithId = null;
let chatWithName = null;
let token = null;
let reconnectAttempts = 0;
let notificationReconnectAttempts = 0;
let maxReconnectAttempts = 10;
let reconnectTimeout = null;
let selectedImageFile = null;
let selectedImageData = null;
let selectedVideoFile = null;
let selectedVideoData = null;
let lastAddedDate = null;
let activeMessageMenu = null;
let currentMessageDiv = null;
let msgCounter = 0;
let unreadMessagesCount = {};
let pendingMessageIds = new Set();
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let startTime = null;
let audioDuration = 0;
let recordedAudioBlob = null;
let recordingStream = null;
let currentImagePath = '';
let isZoomed = false;
let currentEditingField = null;

window.isClosingWebSocket = false;

// ========== Sidebar Control ==========
let isResizing = false;
let startX = 0;
let startWidth = 0;
const sidebar = document.getElementById('sidebar');
const resizeHandle = document.getElementById('resize-handle');

if (resizeHandle) {
    resizeHandle.addEventListener('mousedown', (e) => {
        isResizing = true;
        startX = e.clientX;
        startWidth = sidebar.offsetWidth;
        document.body.style.cursor = 'col-resize';
        e.preventDefault();
    });
}

document.addEventListener('mousemove', (e) => {
    if (!isResizing) return;
    let newWidth = startWidth + (startX - e.clientX);
    newWidth = Math.min(500, Math.max(200, newWidth));
    sidebar.style.width = newWidth + 'px';
});

document.addEventListener('mouseup', () => {
    isResizing = false;
    document.body.style.cursor = '';
    localStorage.setItem('sidebarWidth', sidebar.style.width);
});

const savedWidth = localStorage.getItem('sidebarWidth');
if (savedWidth && sidebar) {
    sidebar.style.width = savedWidth;
}


document.addEventListener('click', function (e) {
    if (e.target.classList && e.target.classList.contains('message-image')) {
        const imgPath = e.target.src;
        showImageModal(imgPath);
    }
});

document.addEventListener('keydown', function (e) {
    if (document.getElementById('image-modal').classList.contains('active')) {
        if (e.key === 'Escape') {
            closeImageModal();
        } else if (e.key === '+' || e.key === '=') {
            zoomImage();
        } else if (e.key === '-' || e.key === '_') {
            zoomImage();
        }
    }
});