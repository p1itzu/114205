// 語音助手 JavaScript - 重新規劃版本

// ==================== 全局變量 ====================
let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];
let orderData = {
    chef_id: null,
    chef_name: '',
    order_date: null,
    order_time: null,
    delivery_method: null,
    delivery_address: null,
    dishes: [],
    customer_notes: ''
};

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', function() {
    console.log('Voice Assistant initialized');
    
    // 從頁面獲取廚師資訊
    const chefIdElement = document.getElementById('chefId');
    const chefNameElement = document.getElementById('chefName');
    
    if (chefIdElement && chefNameElement) {
        orderData.chef_id = parseInt(chefIdElement.value);
        orderData.chef_name = chefNameElement.value;
    }
    
    updateOrderSummary();
    
    // 綁定事件
    const voiceBtn = document.getElementById('voiceBtn');
    const sendBtn = document.getElementById('sendBtn');
    const messageInput = document.getElementById('messageInput');
    
    if (voiceBtn) {
        voiceBtn.addEventListener('click', toggleVoiceRecording);
    }
    
    if (sendBtn) {
        sendBtn.addEventListener('click', sendMessage);
    }
    
    if (messageInput) {
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    }
    
    const submitBtn = document.getElementById('submitOrderBtn');
    if (submitBtn) {
        submitBtn.addEventListener('click', submitOrder);
    }
    
    const backBtn = document.getElementById('backBtn');
    if (backBtn) {
        backBtn.addEventListener('click', returnToChefSelection);
    }
});

// ==================== 語音錄製功能 ====================
async function toggleVoiceRecording() {
    console.log('Toggle voice recording, current state:', isRecording);
    
    if (isRecording) {
        stopRecording();
    } else {
        await startRecording();
    }
}

async function startRecording() {
    console.log('Starting recording...');
    
    try {
        // 檢查瀏覽器支援
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            showError('您的瀏覽器不支援語音錄製功能');
            return;
        }
        
        // 請求麥克風權限
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        console.log('Microphone access granted');
        
        // 創建 MediaRecorder
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };
        
        mediaRecorder.onstop = async () => {
            console.log('Recording stopped, processing audio...');
            
            if (audioChunks.length > 0) {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                await processAudio(audioBlob);
            }
            
            // 停止所有音軌
            stream.getTracks().forEach(track => track.stop());
        };
        
        mediaRecorder.onerror = (event) => {
            console.error('MediaRecorder error:', event);
            showError('錄音過程發生錯誤');
            stream.getTracks().forEach(track => track.stop());
        };
        
        // 開始錄音
        mediaRecorder.start();
        isRecording = true;
        
        // 更新UI
        updateVoiceButton(true);
        addMessage('system', '🎤 正在錄音...請說話');
        
    } catch (error) {
        console.error('Error starting recording:', error);
        
        let errorMsg = '無法訪問麥克風';
        if (error.name === 'NotAllowedError') {
            errorMsg = '麥克風權限被拒絕，請在瀏覽器設定中允許使用麥克風';
        } else if (error.name === 'NotFoundError') {
            errorMsg = '找不到麥克風設備';
        }
        
        showError(errorMsg);
    }
}

function stopRecording() {
    console.log('Stopping recording...');
    
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        
        // 更新UI
        updateVoiceButton(false);
        addMessage('system', '🔄 正在轉換語音...');
    }
}

function updateVoiceButton(recording) {
    const voiceBtn = document.getElementById('voiceBtn');
    if (!voiceBtn) return;
    
    if (recording) {
        voiceBtn.classList.add('recording');
        voiceBtn.innerHTML = '⏹️';
        voiceBtn.title = '停止錄音';
    } else {
        voiceBtn.classList.remove('recording');
        voiceBtn.innerHTML = '🎤';
        voiceBtn.title = '語音輸入';
    }
}

async function processAudio(audioBlob) {
    console.log('Processing audio, size:', audioBlob.size);
    
    try {
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.webm');
        
        const response = await fetch('/customer/orders/new/voice_assistant/transcribe', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success && result.text) {
            console.log('Transcription successful:', result.text);
            
            // 設置輸入框並發送
            const messageInput = document.getElementById('messageInput');
            if (messageInput) {
                messageInput.value = result.text;
                await sendMessage();
            }
        } else {
            showError(result.message || '語音轉換失敗');
        }
    } catch (error) {
        console.error('Error processing audio:', error);
        showError('語音處理錯誤，請重試');
    }
}

// ==================== 訊息發送功能 ====================
async function sendMessage() {
    const messageInput = document.getElementById('messageInput');
    if (!messageInput) return;
    
    const message = messageInput.value.trim();
    if (!message) return;
    
    console.log('Sending message:', message);
    
    // 添加用戶訊息
    addMessage('user', message);
    messageInput.value = '';
    
    // 顯示處理中
    const processingId = 'processing-' + Date.now();
    addMessage('assistant', '<div class="loading"></div> 正在處理您的訊息...', processingId);
    
    try {
        const response = await fetch('/customer/orders/new/voice_assistant/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                order_data: orderData
            })
        });
        
        const result = await response.json();
        
        // 移除處理中訊息
        removeMessage(processingId);
        
        if (result.success) {
            // 更新訂單數據 - 深度合併，保留已有資料
            if (result.order_data) {
                // 對於簡單欄位，只更新有值的
                for (let key in result.order_data) {
                    if (key === 'dishes') {
                        // 菜色需要特殊處理
                        if (result.order_data.dishes && result.order_data.dishes.length > 0) {
                            orderData.dishes = result.order_data.dishes;
                        }
                    } else if (result.order_data[key] !== null && result.order_data[key] !== undefined && result.order_data[key] !== '') {
                        // 只更新有值的欄位
                        orderData[key] = result.order_data[key];
                    }
                }
                
                console.log('Updated order data:', orderData);
                updateOrderSummary();
            }
            
            // 添加AI回應
            addMessage('assistant', result.response);
            
            // 檢查是否完成
            if (result.is_complete) {
                const submitBtn = document.getElementById('submitOrderBtn');
                if (submitBtn) {
                    submitBtn.disabled = false;
                }
                addMessage('system', '✅ 訂單資訊已收集完成！您可以確認並送出訂單。');
            }
        } else {
            showError(result.message || '處理訊息時發生錯誤');
        }
    } catch (error) {
        console.error('Error sending message:', error);
        removeMessage(processingId);
        showError('網路錯誤，請稍後再試');
    }
}

// ==================== UI 更新功能 ====================
function addMessage(type, content, id = null) {
    const messagesContainer = document.getElementById('chatMessages');
    if (!messagesContainer) return id || Date.now().toString();
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    messageDiv.innerHTML = content;
    
    if (id) {
        messageDiv.id = id;
    }
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    return id || messageDiv.id || Date.now().toString();
}

function removeMessage(id) {
    if (!id) return;
    const message = document.getElementById(id);
    if (message) {
        message.remove();
    }
}

function showError(message) {
    addMessage('error', message);
}

function updateOrderSummary() {
    // 更新基本資訊
    updateSummaryField('orderDate', orderData.order_date || '未設定');
    updateSummaryField('orderTime', orderData.order_time || '未設定');
    updateSummaryField('deliveryMethod', orderData.delivery_method || '未設定');
    updateSummaryField('deliveryAddress', orderData.delivery_address || '未設定');
    
    // 更新菜色
    const dishesContainer = document.getElementById('dishesList');
    if (dishesContainer) {
        if (orderData.dishes && orderData.dishes.length > 0) {
            dishesContainer.innerHTML = orderData.dishes.map(dish => {
                const dishName = dish.dish_name || '未命名菜色';
                const quantity = dish.quantity || 1;
                return `<div class="summary-item"><span class="summary-label">${dishName} x${quantity}</span></div>`;
            }).join('');
        } else {
            dishesContainer.innerHTML = '<div class="summary-item"><span class="summary-label">尚無菜色</span></div>';
        }
    }
    
    // 更新備註
    updateSummaryField('customerNotes', orderData.customer_notes || '無');
    
    // 檢查並顯示缺少的資訊
    checkMissingInfo();
}

function checkMissingInfo() {
    const missing = [];
    
    if (!orderData.order_date) {
        missing.push('用餐日期');
    }
    if (!orderData.order_time) {
        missing.push('用餐時間');
    }
    if (!orderData.delivery_method) {
        missing.push('取餐方式');
    }
    // 只有外送才需要地址
    if (orderData.delivery_method === '外送' && !orderData.delivery_address) {
        missing.push('外送地址');
    }
    if (!orderData.dishes || orderData.dishes.length === 0) {
        missing.push('菜色');
    } else {
        // 檢查每道菜是否有完整資訊
        const incompleteDishes = orderData.dishes.filter(dish => 
            !dish.salt_level || !dish.spice_level
        );
        if (incompleteDishes.length > 0) {
            missing.push('菜色口味設定');
        }
    }
    
    // 顯示缺少的資訊
    const missingInfoElement = document.getElementById('missingInfo');
    if (missingInfoElement) {
        if (missing.length > 0) {
            missingInfoElement.innerHTML = `<div class="missing-info-alert">⚠️ 還需要：${missing.join('、')}</div>`;
            missingInfoElement.style.display = 'block';
        } else {
            missingInfoElement.style.display = 'none';
        }
    }
}

function updateSummaryField(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = value;
    }
}

// ==================== 訂單提交功能 ====================
async function submitOrder() {
    console.log('Submitting order:', orderData);
    
    // 驗證必要欄位
    if (!orderData.order_date || !orderData.order_time) {
        Swal.fire({
            icon: 'warning',
            title: '資料不完整',
            text: '請提供用餐日期和時間'
        });
        return;
    }
    
    if (!orderData.delivery_method) {
        Swal.fire({
            icon: 'warning',
            title: '資料不完整',
            text: '請選擇取餐方式（外送或自取）'
        });
        return;
    }
    
    if (orderData.delivery_method === '外送' && !orderData.delivery_address) {
        Swal.fire({
            icon: 'warning',
            title: '資料不完整',
            text: '外送需要提供地址'
        });
        return;
    }
    
    if (!orderData.dishes || orderData.dishes.length === 0) {
        Swal.fire({
            icon: 'warning',
            title: '資料不完整',
            text: '至少需要一道菜'
        });
        return;
    }
    
    // 轉換 delivery_method 為後端格式
    const submitData = {
        ...orderData,
        delivery_method: orderData.delivery_method === '外送' ? 'delivery' : 'pickup'
    };
    
    try {
        const response = await fetch('/customer/orders/new/voice_assistant/submit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(submitData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            Swal.fire({
                icon: 'success',
                title: '訂單已送出！',
                text: '請等待廚師回應',
                confirmButtonText: '查看訂單'
            }).then(() => {
                window.location.href = `/customer/order/${result.order_id}`;
            });
        } else {
            Swal.fire({
                icon: 'error',
                title: '送出失敗',
                text: result.message || '請稍後再試'
            });
        }
    } catch (error) {
        console.error('Error submitting order:', error);
        Swal.fire({
            icon: 'error',
            title: '網路錯誤',
            text: '請檢查網路連線後重試'
        });
    }
}

function returnToChefSelection() {
    if (confirm('確定要返回選擇廚師嗎？目前的訂單資訊將會遺失。')) {
        window.location.href = '/customer/orders/new/step0';
    }
}

// 導出函數供HTML使用
window.toggleVoiceRecording = toggleVoiceRecording;
window.sendMessage = sendMessage;
window.submitOrder = submitOrder;
window.returnToChefSelection = returnToChefSelection;
