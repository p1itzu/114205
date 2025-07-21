# 🔄 重新選擇廚師功能 - 修改總結

## 📋 功能概述

實現了當廚師拒絕接單或議價失敗時，讓顧客能夠重新選擇廚師的功能，而不是直接取消訂單。

## 🎯 主要修改

### 1. 新增訂單狀態 `RESELECTING_CHEF`

**檔案**: `models/order.py`
- 在 `OrderStatus` 枚舉中新增 `RESELECTING_CHEF = "reselecting_chef"` 狀態
- 用於標示訂單需要重新選擇廚師

### 2. 修改廚師拒絕接單邏輯

**檔案**: `routers/chef.py` - `reject_order` 函數
- 原本：訂單狀態變成 `CANCELLED`
- 修改後：訂單狀態變成 `RESELECTING_CHEF`
- 清除廚師分配 (`order.chef_id = None`)
- 更新狀態歷史記錄

### 3. 修改議價失敗邏輯

**檔案**: `routers/customer.py` - `respond_negotiation` 函數
- 當議價次數 >= 2 時，原本變成 `CANCELLED`
- 修改後：訂單狀態變成 `RESELECTING_CHEF`
- 清除廚師分配讓顧客重新選擇

### 4. 修改廚師拒絕顧客再議價邏輯

**檔案**: `routers/chef.py` - `respond_counter_offer` 函數
- 原本：廚師拒絕時訂單變成 `CANCELLED`
- 修改後：訂單狀態變成 `RESELECTING_CHEF`
- 清除廚師分配讓顧客重新選擇

### 5. 修改顧客拒絕最終定價邏輯

**檔案**: `routers/customer.py` - `respond_final_pricing` 函數
- 原本：顧客拒絕最終定價時訂單變成 `CANCELLED`
- 修改後：訂單狀態變成 `RESELECTING_CHEF`
- 清除廚師分配讓顧客重新選擇

## 🆕 新增功能

### 6. 重新選擇廚師路由

**檔案**: `routers/customer.py`

#### GET `/order/{order_id}/reselect_chef`
- 顯示重新選擇廚師的頁面
- 檢查訂單狀態是否為 `RESELECTING_CHEF`
- 獲取所有可用廚師列表

#### POST `/order/{order_id}/reselect_chef`
- 處理重新選擇廚師的提交
- 更新訂單的廚師分配
- 將訂單狀態改回 `PENDING`
- 重置議價次數

### 7. 重新選擇廚師模板

**檔案**: `templates/reselect_chef.html`
- 基於 `add_order_step0.html` 設計
- 顯示訂單資訊和說明
- 提供廚師篩選功能
- 支援選擇廚師並提交

## 🎨 前端修改

### 8. 訂單列表頁面

**檔案**: `templates/order_list.html`
- 新增 `reselecting_chef` 狀態顯示為「重新選擇廚師」
- 當訂單狀態為 `reselecting_chef` 時顯示「重新選擇廚師」按鈕

### 9. 訂單詳情頁面

**檔案**: `templates/order_detail.html`
- 新增 `reselecting_chef` 狀態的處理邏輯
- 顯示重新選擇廚師的提示訊息和按鈕
- 修改狀態進度條，為特殊狀態 (`reselecting_chef`, `cancelled`) 顯示特殊樣式

## 🔄 流程圖

```
顧客建立訂單 → PENDING
                ↓
            廚師接單/拒絕
                ↓
     接單 → NEGOTIATING (議價)
                ↓
        議價成功 → ACCEPTED
                ↓
            製作流程...
                ↓
            COMPLETED

     拒絕 → RESELECTING_CHEF
                ↓
        顧客重新選擇廚師
                ↓
            回到 PENDING
```

## 📝 關鍵改進

1. **用戶體驗提升**：避免訂單直接取消，給顧客重新選擇的機會
2. **流程優化**：將失敗的議價轉化為重新選擇機會
3. **狀態管理**：清晰的狀態流轉和歷史記錄
4. **UI 改進**：直觀的重新選擇廚師界面

## 🚀 部署注意事項

1. **資料庫更新**：新增的 `RESELECTING_CHEF` 狀態需要資料庫支援
2. **模板路由**：確保 `reselect_chef` 路由名稱正確註冊
3. **前端樣式**：確保新狀態的 CSS 樣式正確載入
4. **測試流程**：測試各種議價失敗和拒絕接單的情況

## 🔍 測試建議

1. 測試廚師拒絕接單流程
2. 測試議價失敗（次數用盡）流程
3. 測試廚師拒絕顾客再議價流程
4. 測試顧客拒絕最終定價流程
5. 測試重新選擇廚師後的正常流程
6. 測試訂單狀態顯示和按鈕功能

## 🎉 完成效果

- ✅ 廚師拒絕接單：顧客可重新選擇廚師
- ✅ 議價失敗：顧客可重新選擇廚師
- ✅ 直觀的重新選擇界面
- ✅ 完整的狀態追蹤和歷史記錄
- ✅ 用戶友好的提示和引導 