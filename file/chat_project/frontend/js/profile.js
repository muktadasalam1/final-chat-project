// ========== Profile Functions ==========
function openProfile() {
    showToast('Profile feature coming soon');
}

function editField(field) {
    const displayEl = document.getElementById(`profile-${field}-display`);
    const inputEl = document.getElementById(`profile-${field}-input`);
    const editBtn = event?.target?.closest('.edit-field-btn');
    if (currentEditingField === field) {
        const newValue = inputEl.value.trim();
        if (newValue !== displayEl.textContent && newValue !== '') {
            updateProfileField(field, newValue);
        }
        displayEl.style.display = 'block';
        inputEl.style.display = 'none';
        if (editBtn) editBtn.innerHTML = 'Edit';
        currentEditingField = null;
    } else {
        if (currentEditingField) {
            const prevDisplay = document.getElementById(`profile-${currentEditingField}-display`);
            const prevInput = document.getElementById(`profile-${currentEditingField}-input`);
            const prevBtn = document.querySelector(`.info-row.editable .edit-field-btn`);
            if (prevDisplay) prevDisplay.style.display = 'block';
            if (prevInput) prevInput.style.display = 'none';
            if (prevBtn) prevBtn.innerHTML = 'Edit';
        }
        displayEl.style.display = 'none';
        inputEl.style.display = 'block';
        if (editBtn) editBtn.innerHTML = 'Save';
        inputEl.focus();
        currentEditingField = field;
    }
}

async function updateProfileField(field, value) {
    try {
        const data = {};
        let apiField = field;
        if (field === 'username') apiField = 'full_name';
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
                displayEl.textContent = value || (field === 'bio' ? 'No bio' : 'Not added');
            }
            if (field === 'fullname') {
                document.getElementById('current-username').textContent = value || currentUsername;
            }
        } else {
            showToast('Update failed', true);
        }
    } catch (error) {
        console.error('Error updating profile:', error);
        showToast('Update error', true);
    }
}

async function updateSetting(setting, value) {
    try {
        const data = {};
        data[setting] = value;
        const authToken = getToken();
        const response = await fetch(`/settings/update/${userId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify(data)
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
    if (theme === 'dark') {
        document.body.classList.remove('light-mode');
    } else if (theme === 'light') {
        document.body.classList.add('light-mode');
    } else if (theme === 'auto') {
        const isDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
        if (isDarkMode) {
            document.body.classList.remove('light-mode');
        } else {
            document.body.classList.add('light-mode');
        }
    }
}