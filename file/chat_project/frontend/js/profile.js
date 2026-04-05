

// ========== Profile Functions ==========
window.openProfile = function () {
    console.log("Profile clicked");
    showScreen("profile-screen");
    loadProfile();
};
async function loadProfile() {
    try {
        const res = await fetch(`/profile/${userId}`, {
            headers: {
                "Authorization": `Bearer ${getToken()}`
            }
        });

        const result = await res.json();

        if (result.status === "success") {
            const data = result.data;

            document.getElementById("profile-username-display").textContent = data.username || "-";
            document.getElementById("profile-fullname-display").textContent = data.full_name || "-";
            document.getElementById("profile-bio-display").textContent = data.bio || "No bio";
            //document.getElementById("profile-phone-display").textContent = data.phone_number || "-";            
            document.getElementById("profile-phone-display").textContent = data.phone_number || "-";
            document.getElementById("profile-email-display").textContent = data.email || "-";
            document.getElementById("profile-lastseen").textContent = formatDate(data.last_seen || "-");
            document.getElementById("profile-joined").textContent = formatDate(data.joined_date || "-");
            if (data.stats) {
                document.getElementById("stat-messages").textContent = data.stats.messages || 0;
                document.getElementById("stat-chats").textContent    = data.stats.chats    || 0;
                document.getElementById("stat-media").textContent    = data.stats.media    || 0;
            }
            if (data.settings) {
                document.getElementById("notifications-toggle").checked = data.settings.notifications_enabled ?? true;
                document.getElementById("sound-toggle").checked         = data.settings.sound_enabled ?? true;
                document.getElementById("preview-toggle").checked       = data.settings.message_preview_enabled ?? true;
                document.getElementById("theme-select").value           = data.settings.theme_preference || "dark";
                document.getElementById("language-select").value        = data.settings.language || "ar";
            }
        applyTheme(data.settings.theme_preference || "dark");

        } else {
            showToast("Failed to load profile", true);
        }

    } catch (err) {
        console.error(err);
        showToast("Error loading profile", true);
    }
}

function editField(field, event) {
    const displayEl = document.getElementById(`profile-${field}-display`);
    const inputEl = document.getElementById(`profile-${field}-input`);
    const editBtn = event?.target?.closest('.edit-field-btn');


    if (currentEditingField === field) {
        const newValue = inputEl.value.trim();

        if (newValue && newValue !== displayEl.textContent) {
            if (field ==  "phone") {
                field = "phone_number"
            }

            console.log(field)
            updateProfileField(field, newValue);
        }
        
        displayEl.style.display = 'block';
        inputEl.style.display = 'none';

        if (editBtn) editBtn.innerHTML = 'Edit';

        currentEditingField = null;
        return;
    }

    //  If another field is being edited → reset it
    if (currentEditingField && currentEditingField !== field) {
        const prevDisplay = document.getElementById(`profile-${currentEditingField}-display`);
        const prevInput = document.getElementById(`profile-${currentEditingField}-input`);
        const prevBtn = document.querySelector(`[data-field="${currentEditingField}"] .edit-field-btn`);

        if (prevDisplay) prevDisplay.style.display = 'block';
        if (prevInput) prevInput.style.display = 'none';
        if (prevBtn) prevBtn.innerHTML = 'Edit';
    }

    
    displayEl.style.display = 'none';
    inputEl.style.display = 'block';
    inputEl.focus();

    if (editBtn) editBtn.innerHTML = 'Save';

    currentEditingField = field;
}


async function updateProfileField(field, value) {
    try {
        const data = {};

        //  Map frontend fields → backend fields
        const fieldMap = {
            username: "username",
            fullname: "full_name",
            bio: "bio"
        };
        const apiField = fieldMap[field] || field;
        data[apiField] = value;

        const authToken = getToken();

        const response = await fetch(`/profile/update/${userId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (result.status === 'success') {
            showToast('Profile updated');

            const displayEl = document.getElementById(`profile-${field}-display`);
            if (displayEl) {
                displayEl.textContent =
                    value || (field === 'bio' ? 'No bio' : 'Not added');
            }

            if (field === 'username') {
                document.getElementById('current-username').textContent =
                    value || currentUsername;
            }
        } else {
            showToast('Update failed', true);
        }

    } catch (error) {
        console.error('Error updating profile:', error);
        showToast('Update error', true);
    }
}


// =============================
// UPDATE SETTINGS (FIXED)
// =============================
async function updateSetting(setting, value) {
    try {
        const authToken = getToken();

        const response = await fetch(`/settings/update/${userId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                [setting]: value
            })
        });

        const result = await response.json();

        if (result.status === 'success') {
            showToast('Settings updated');

            if (setting === 'theme_preference') {
                applyTheme(value);
            }
        } else {
            showToast('Update failed', true);
        }

    } catch (error) {
        console.error('Error updating setting:', error);
        showToast('Update error', true);
    }
}

function applyTheme(theme) {
    const isDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;

    if (theme === 'dark') {
        document.body.classList.remove('light-mode');
    }

    else if (theme === 'light') {
        document.body.classList.add('light-mode');
    }

    else if (theme === 'auto') {
        if (isDarkMode) {
            document.body.classList.remove('light-mode');
        } else {
            document.body.classList.add('light-mode');
        }
    }
}
function formatDate(isoString) {
    if (!isoString) return "-";
    const date = new Date(isoString);
    return date.toLocaleDateString('ar-IQ', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}