/**
 * 通知中心功能 - 待實作真實功能
 * 
 * 注意：目前此文件包含假資料和基礎架構
 * 未來需要實作：
 * 1. 後端 API 整合 - 獲取真實通知數據
 * 2. 數據庫存儲 - 通知記錄持久化  
 * 3. 即時更新 - WebSocket 或定期輪詢
 * 4. 用戶特定通知 - 根據登入用戶顯示
 * 5. 通知狀態管理 - 已讀/未讀狀態同步
 * 
 * 目前各頁面使用內聯 JavaScript 來避免外部文件載入問題
 * 實作真實功能時可考慮重新使用此外部文件
 */

// 測試 JavaScript 文件是否載入
console.log('notification.js 文件已載入 (目前為假資料版本)');

// 通知數據 (假資料 - 待替換為真實 API 數據)
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
    console.log('toggleNotification 被調用');
    
    const notificationCenter = document.getElementById('notificationCenter');
    if (!notificationCenter) {
        console.error('通知中心元素未找到');
        return;
    }
    
    console.log('當前 style.display:', notificationCenter.style.display);
    console.log('當前 computed display:', window.getComputedStyle(notificationCenter).display);
    
    // 簡單的切換邏輯：如果當前是隱藏的就顯示，如果是顯示的就隱藏
    if (notificationCenter.style.display === 'block') {
        console.log('隱藏通知中心');
        notificationCenter.style.display = 'none';
    } else {
        console.log('顯示通知中心');
        notificationCenter.style.display = 'block';
        updateNotifications();
    }
}

// 只更新通知連結的狀態（未讀提示）
function updateNotificationStatus() {
    const notificationLink = document.querySelector('a[onclick*="toggleNotification"]');
    if (!notificationLink) return;
    
    // 檢查是否有未讀通知
    const hasUnread = notifications.some(notification => notification.unread);
    if (hasUnread) {
        notificationLink.classList.add('has-unread');
    } else {
        notificationLink.classList.remove('has-unread');
    }
}

// 更新通知列表
function updateNotifications() {
    const notificationList = document.getElementById('notificationList');
    if (!notificationList) return;
    
    // 更新通知連結狀態
    updateNotificationStatus();
    
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
    updateNotificationStatus();
    const notificationCenter = document.getElementById('notificationCenter');
    if (notificationCenter) {
        notificationCenter.style.display = 'none';
    }
}

// 初始化通知
document.addEventListener('DOMContentLoaded', () => {
    // 確保通知中心初始為隱藏狀態（明確設定，確保 JavaScript 和 CSS 同步）
    const notificationCenter = document.getElementById('notificationCenter');
    if (notificationCenter) {
        // 明確設定為 none，這樣第一次點擊時 style.display 就不是 'block'
        notificationCenter.style.display = 'none';
        console.log('通知中心初始化完成，設定為隱藏狀態');
    }
    
    // 只更新通知連結的狀態（未讀提示），但不更新通知列表內容
    updateNotificationStatus();
    
    // 點擊其他地方關閉通知中心
    document.addEventListener('click', (e) => {
        const notificationCenter = document.getElementById('notificationCenter');
        const notificationLink = document.querySelector('a[onclick*="toggleNotification"]');
        
        if (notificationCenter && notificationLink && 
            !notificationCenter.contains(e.target) && !notificationLink.contains(e.target)) {
            notificationCenter.style.display = 'none';
        }
    });
}); 