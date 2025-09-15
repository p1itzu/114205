/**
 * 通知中心功能 - 真實API版本
 * 
 * 功能：
 * 1. 後端 API 整合 - 獲取真實通知數據 ✅
 * 2. 數據庫存儲 - 通知記錄持久化 ✅
 * 3. 用戶特定通知 - 根據登入用戶顯示 ✅
 * 4. 通知狀態管理 - 已讀/未讀狀態同步 ✅
 * 5. 即時更新 - 定期輪詢 (可選)
 * 
 * 各頁面使用內聯 JavaScript 來避免外部文件載入問題
 * 此文件作為統一的通知功能模組
 */

// 測試 JavaScript 文件是否載入
console.log('notification.js 文件已載入 (真實API版本)');

// 通知數據 (從API獲取)
let notifications = [];
let unreadCount = 0;

// 從API載入通知
async function loadNotifications() {
    try {
        const response = await fetch('/api/notifications');
        const result = await response.json();
        
        if (result.success) {
            notifications = result.data.notifications;
            unreadCount = result.data.unread_count;
            console.log('通知載入成功:', notifications.length, '條通知，', unreadCount, '條未讀');
        } else {
            console.error('載入通知失敗:', result.message);
            notifications = [];
            unreadCount = 0;
        }
    } catch (error) {
        console.error('載入通知時發生錯誤:', error);
        notifications = [];
        unreadCount = 0;
    }
}

// 標記通知為已讀
async function markNotificationAsRead(notificationId) {
    try {
        const response = await fetch(`/api/notifications/${notificationId}/mark_read`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.json();
        if (result.success) {
            // 更新本地通知狀態
            const notification = notifications.find(n => n.id === notificationId);
            if (notification && !notification.is_read) {
                notification.is_read = true;
                unreadCount = Math.max(0, unreadCount - 1);
                updateNotificationStatus();
            }
        }
    } catch (error) {
        console.error('標記已讀失敗:', error);
    }
}

// 清空所有通知
async function clearAllNotifications() {
    try {
        const response = await fetch('/api/notifications/clear', {
            method: 'DELETE'
        });
        
        const result = await response.json();
        if (result.success) {
            notifications = [];
            unreadCount = 0;
            updateNotifications();
            updateNotificationStatus();
            
            // 隱藏通知中心
            const notificationCenter = document.getElementById('notificationCenter');
            if (notificationCenter) {
                notificationCenter.style.display = 'none';
            }
        } else {
            alert('清空通知失敗：' + result.message);
        }
    } catch (error) {
        console.error('清空通知失敗:', error);
        alert('清空通知失敗，請稍後再試');
    }
}

// 切換通知中心顯示狀態
async function toggleNotification() {
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
        
        // 載入最新通知
        await loadNotifications();
        updateNotifications();
    }
}

// 只更新通知連結的狀態（未讀提示）
function updateNotificationStatus() {
    const notificationLink = document.querySelector('a[onclick*="toggleNotification"]');
    if (!notificationLink) return;
    
    // 檢查是否有未讀通知
    if (unreadCount > 0) {
        notificationLink.classList.add('has-unread');
        
        // 如果有未讀數量顯示元素，更新數字
        const badge = notificationLink.querySelector('.notification-badge');
        if (badge) {
            badge.textContent = unreadCount;
            badge.style.display = 'inline';
        }
    } else {
        notificationLink.classList.remove('has-unread');
        
        // 隱藏未讀數量顯示
        const badge = notificationLink.querySelector('.notification-badge');
        if (badge) {
            badge.style.display = 'none';
        }
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
    
    // 如果沒有通知，顯示空狀態
    if (notifications.length === 0) {
        const emptyLi = document.createElement('li');
        emptyLi.className = 'notification-item';
        emptyLi.style.textAlign = 'center';
        emptyLi.style.color = '#999';
        emptyLi.innerHTML = '<div class="notification-content">暫無通知</div>';
        notificationList.appendChild(emptyLi);
        return;
    }
    
    // 添加所有通知
    notifications.forEach((notification, index) => {
        const li = document.createElement('li');
        li.className = `notification-item ${!notification.is_read ? 'unread' : ''}`;
        
        // 根據通知類型設置圖標
        const typeIcon = {
            'order_accepted': '✓',
            'order_rejected': '✕',
            'order_status_update': '↻',
            'order_ready': '🍽️',
            'order_completed': '✅',
            'new_order': '📋',
            'new_review': '⭐',
            'review_reply': '💬',
            'order_negotiation': '💰',
            'negotiation_response': '💬'
        };
        
        const icon = typeIcon[notification.type] || '📢';
        
        // 判斷是否為訂單類通知，如果是則顯示訂單編號
        const orderTypes = ['order_accepted', 'order_rejected', 'order_status_update', 'order_ready', 'order_completed', 'new_order', 'order_negotiation', 'negotiation_response'];
        const isOrderNotification = orderTypes.includes(notification.type);
        const orderInfo = isOrderNotification && notification.order_id ? `<span style="color: #007bff; font-size: 12px;">#${notification.order_id}</span> ` : '';
        
        li.innerHTML = `
            <div class="notification-type type-${notification.type.replace('_', '-')}">
                ${icon}
            </div>
            <div class="notification-content">
                <div style="font-weight: ${!notification.is_read ? 'bold' : 'normal'};">
                    ${orderInfo}${notification.title}
                </div>
                <div style="margin-top: 4px; font-size: 14px; color: #666;">
                    ${notification.content}
                </div>
                <div class="notification-time">${notification.time_ago}</div>
            </div>
        `;
        
        // 點擊通知時標記為已讀
        li.addEventListener('click', async () => {
            if (!notification.is_read) {
                await markNotificationAsRead(notification.id);
            }
            
            // 如果通知有相關訂單，可以跳轉到訂單詳情
            if (notification.order_id) {
                // 根據用戶角色跳轉到不同頁面
                // 這裡可以根據實際需求調整跳轉邏輯
                window.location.href = `/customer/order/${notification.order_id}`;
            }
        });
        
        notificationList.appendChild(li);
    });
}

// 獲取未讀通知數量
async function getUnreadCount() {
    try {
        const response = await fetch('/api/notifications/unread_count');
        const result = await response.json();
        
        if (result.success) {
            unreadCount = result.unread_count;
            updateNotificationStatus();
        }
    } catch (error) {
        console.error('獲取未讀數量失敗:', error);
    }
}

// 初始化通知
document.addEventListener('DOMContentLoaded', async () => {
    // 確保通知中心初始為隱藏狀態（明確設定，確保 JavaScript 和 CSS 同步）
    const notificationCenter = document.getElementById('notificationCenter');
    if (notificationCenter) {
        // 明確設定為 none，這樣第一次點擊時 style.display 就不是 'block'
        notificationCenter.style.display = 'none';
        console.log('通知中心初始化完成，設定為隱藏狀態');
    }
    
    // 載入未讀通知數量
    await getUnreadCount();
    
    // 點擊其他地方關閉通知中心
    document.addEventListener('click', (e) => {
        const notificationCenter = document.getElementById('notificationCenter');
        const notificationLink = document.querySelector('a[onclick*="toggleNotification"]');
        
        if (notificationCenter && notificationLink && 
            !notificationCenter.contains(e.target) && !notificationLink.contains(e.target)) {
            notificationCenter.style.display = 'none';
        }
    });
    
    // 定期更新未讀通知數量（可選，每30秒檢查一次）
    setInterval(async () => {
        await getUnreadCount();
    }, 30000);
}); 