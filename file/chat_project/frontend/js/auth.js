// ========== Session Management ==========
function saveSession(newToken, user) {
    token = newToken;
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(user));
}

function getToken() {
    if (token) return token;
    token = localStorage.getItem('token');
    return token;
}

function getStoredUser() {
    const user = localStorage.getItem('user');
    return user ? JSON.parse(user) : null;
}

function clearSession() {
    token = null;
    localStorage.removeItem('token');
    localStorage.removeItem('user');
}

function isLoggedIn() {
    return !!getToken();
}

// ========== Authentication ==========
async function login() {
    let user = document.getElementById('login-username').value.trim(),
        pass = document.getElementById('login-password').value;
    if (!user || !pass) {
        document.getElementById('login-error').innerText = 'Please enter credentials';
        return;
    }
    try {
        let res = await fetch('/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ username: user, password: pass })
        });
        let data = await res.json();
        if (data.status === 'success') {
            userId = data.user_id;
            currentUsername = data.username;
            saveSession(userId, { user_id: userId, username: currentUsername });
            requestNotificationPermission();
            document.getElementById('current-username').innerHTML = currentUsername;
            showScreen('chat-screen');

            const menuToggle = document.getElementById('menu-toggle');
            if (menuToggle) menuToggle.style.display = 'flex';

            setTimeout(() => {
                requestMicrophonePermission();
            }, 500);

            loadUsers();
            connectNotificationWebSocket();
            connectUsersUpdatesWebSocket();
        } else {
            document.getElementById('login-error').innerText = data.detail || 'Invalid credentials';
        }
    } catch (e) {
        console.error(e);
        document.getElementById('login-error').innerText = 'Connection error';
    }
}

async function register() {
    let user = document.getElementById('register-username').value.trim(),
        pass = document.getElementById('register-password').value;
    if (!user || !pass) {
        document.getElementById('register-error').innerText = 'Please enter credentials';
        return;
    }
    if (pass.length < 6) {
        document.getElementById('register-error').innerText = 'Password must be at least 6 characters';
        return;
    }
    try {
        let res = await fetch('/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ username: user, password: pass })
        });
        let data = await res.json();
        if (data.status === 'success') {
            alert('Account created successfully');
            showScreen('login-screen');
            document.getElementById('login-username').value = user;
        } else {
            document.getElementById('register-error').innerText = data.detail || 'Registration failed';
        }
    } catch (e) {
        document.getElementById('register-error').innerText = 'Connection error';
    }
}

function logout() {
    if (notificationWs) notificationWs.close();
    if (usersUpdateWs) usersUpdateWs.close();
    closeWebSocket();
    clearSession();
    userId = null;
    currentUsername = null;
    chatWithId = null;
    chatWithName = null;
    unreadMessagesCount = {};
    showScreen('welcome-screen');

    const menuToggle = document.getElementById('menu-toggle');
    if (menuToggle) menuToggle.style.display = 'none';
}