// 通知數據
let notifications = [
    {
        type: 'accept',
        content: 'XXX廚師接受您的訂單！',
        time: '5分鐘前',
        unread: true
    },
    {
        type: 'reject',
        content: 'OOO廚師拒絕您的訂單！',
        time: '10分鐘前',
        unread: true
    },
    {
        type: 'update',
        content: '20250322訂單狀態更新：已完成',
        time: '30分鐘前',
        unread: false
    },
    {
        type: 'create',
        content: '20250322訂單已成立',
        time: '1小時前',
        unread: false
    }
];

// 切換通知中心顯示狀態
function toggleNotification() {
    const notificationCenter = document.getElementById('notificationCenter');
    notificationCenter.style.display = notificationCenter.style.display === 'none' ? 'block' : 'none';
    updateNotifications();
}

// 更新通知列表
function updateNotifications() {
    const notificationList = document.getElementById('notificationList');
    const notificationLink = document.querySelector('a[onclick*="toggleNotification"]');
    
    // 檢查是否有未讀通知
    const hasUnread = notifications.some(notification => notification.unread);
    if (hasUnread) {
        notificationLink.classList.add('has-unread');
    } else {
        notificationLink.classList.remove('has-unread');
    }
    
    // 清空現有通知列表
    notificationList.innerHTML = '';
    
    // 添加所有通知
    notifications.forEach((notification, index) => {
        const li = document.createElement('li');
        li.className = `notification-item ${notification.unread ? 'unread' : ''}`;
        
        // 根據通知類型設置圖標
        const typeIcon = {
            'accept': '✓',
            'reject': '✕',
            'update': '↻',
            'create': '+'
        };
        
        li.innerHTML = `
            <div class="notification-type type-${notification.type}">
                ${typeIcon[notification.type]}
            </div>
            <div class="notification-content">
                ${notification.content}
                <div class="notification-time">${notification.time}</div>
            </div>
        `;
        
        // 點擊通知時標記為已讀
        li.addEventListener('click', () => {
            notifications[index].unread = false;
            updateNotifications();
        });
        
        notificationList.appendChild(li);
    });
}

// 清空所有通知
function clearAllNotifications() {
    notifications = [];
    updateNotifications();
    document.getElementById('notificationCenter').style.display = 'none';
}

// 初始化通知
document.addEventListener('DOMContentLoaded', () => {
    updateNotifications();
    
    // 點擊其他地方關閉通知中心
    document.addEventListener('click', (e) => {
        const notificationCenter = document.getElementById('notificationCenter');
        const notificationLink = document.querySelector('a[onclick*="toggleNotification"]');
        
        if (!notificationCenter.contains(e.target) && !notificationLink.contains(e.target)) {
            notificationCenter.style.display = 'none';
        }
    });
}); 