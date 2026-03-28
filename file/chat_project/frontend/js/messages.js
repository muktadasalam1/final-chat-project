// ========== Message Functions ==========
function addMsg(sender, message, ts = null, tempId = null, msgId = null) {
    if (tempId && pendingMessageIds.has(tempId)) {
        pendingMessageIds.delete(tempId);
        let tempMsg = document.querySelector(`[data-temp-id="${tempId}"]`);
        if (tempMsg) tempMsg.remove();
    }
    let div = document.getElementById('messages');
    if (msgId) {
        let existingMsg = document.querySelector(`[data-message-id="${msgId}"]`);
        if (existingMsg) return;
    }
    let msgDiv = document.createElement('div');
    msgCounter++;
    let mid = msgId ? `msg_${msgId}` : `msg_${Date.now()}_${msgCounter}`;
    msgDiv.setAttribute('data-mid', mid);
    if (msgId) msgDiv.setAttribute('data-message-id', msgId);
    if (tempId) msgDiv.setAttribute('data-temp-id', tempId);
    let isSent = sender === userId;
    msgDiv.className = `message ${isSent ? 'sent' : 'received'}`;
    let time;
    if (ts) {
        let d = new Date(ts);
        time = d.toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' });
        addDateSeparatorIfNeeded(d, div);
    } else {
        time = new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' });
    }
    let senderName = isSent ? 'You' : chatWithName;
    msgDiv.innerHTML = `<div class="message-bubble"><div class="message-text">${escapeHtml(message)}</div><div class="message-meta">${senderName} • ${time}</div></div>`;
    div.appendChild(msgDiv);
    scrollToBottom();
    return mid;
}

function addMsgLocal(sender, message, tempId) {
    let div = document.getElementById('messages');
    let msgDiv = document.createElement('div');
    msgCounter++;
    let mid = `temp_${tempId}`;
    msgDiv.setAttribute('data-mid', mid);
    msgDiv.setAttribute('data-temp-id', tempId);
    let isSent = sender === userId;
    msgDiv.className = `message ${isSent ? 'sent' : 'received'}`;
    let time = new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' });
    let senderName = isSent ? 'You' : chatWithName;
    msgDiv.innerHTML = `<div class="message-bubble"><div class="message-text">${escapeHtml(message)}</div><div class="message-meta">${senderName} • ${time}</div></div>`;
    div.appendChild(msgDiv);
}

function addDateSeparatorIfNeeded(date, container) {
    let today = new Date(),
        yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    let dateKey = date.toDateString();
    if (lastAddedDate !== dateKey) {
        lastAddedDate = dateKey;
        let displayDate = dateKey === today.toDateString() ? 'Today' : (dateKey === yesterday.toDateString() ? 'Yesterday' : date.toLocaleDateString('ar-EG', {
            day: 'numeric',
            month: 'long'
        }));
        let sep = document.createElement('div');
        sep.className = 'date-separator';
        sep.innerHTML = `<div class="date-separator-line"></div><div class="date-separator-text">${displayDate}</div><div class="date-separator-line"></div>`;
        container.appendChild(sep);
    }
}

function updateUnreadBadge(userId, count) {
    const userItems = document.querySelectorAll('.user-item');
    for (let item of userItems) {
        if (item.getAttribute('data-user-id') == userId) {
            let badge = item.querySelector('.unread-badge');
            if (count > 0) {
                if (!badge) {
                    badge = document.createElement('span');
                    badge.className = 'unread-badge';
                    item.appendChild(badge);
                }
                badge.textContent = count > 99 ? '99+' : count;
            } else {
                if (badge) badge.remove();
            }
            break;
        }
    }
}