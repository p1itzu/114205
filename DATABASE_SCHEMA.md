# 🍳 味你而煮 - 資料庫結構設計

## 📊 系統概述
本系統是一個連接廚師和顧客的代做菜平台，支持兩種用戶類型和完整的訂單流程。

## 🗄️ 資料表結構

### 1. 用戶管理 (User Management)

#### `users` - 用戶基本資料
```sql
- id: 主鍵
- email: 信箱 (唯一)
- hashed_password: 密碼雜湊 (OAuth用戶可為空)
- oauth_provider: OAuth提供者 ('google' 或 null)
- oauth_id: OAuth用戶ID
- name: 姓名
- phone: 電話
- avatar_url: 頭像URL
- role: 用戶角色 (CUSTOMER/CHEF)
- is_active: 是否啟用
- email_verified: 信箱是否已驗證
- verification_token: 驗證令牌
- verification_sent_at: 驗證郵件發送時間
- created_at: 建立時間
- updated_at: 更新時間
```

#### `chef_profiles` - 廚師詳細資料
```sql
- id: 主鍵
- user_id: 關聯用戶ID (外鍵)
- kitchen_address: 廚房地址
- service_area: 服務範圍
- certificate_name: 證照名稱
- certificate_image_url: 證照圖片URL
- certificate_verified: 證照是否已驗證
- experience_years: 經驗年數
- description: 自我介紹
- average_rating: 平均評分
- total_reviews: 總評價數
- total_orders: 總訂單數
- is_available: 是否接單中
- is_verified: 是否已認證
- created_at: 建立時間
- updated_at: 更新時間
```

#### `chef_specialties` - 廚師專長
```sql
- id: 主鍵
- chef_id: 關聯廚師ID (外鍵)
- specialty: 專長 (例如：川菜、粵菜、義式料理)
- created_at: 建立時間
```

#### `chef_signature_dishes` - 廚師招牌菜
```sql
- id: 主鍵
- chef_id: 關聯廚師ID (外鍵)
- dish_name: 菜名
- description: 描述
- image_url: 圖片URL
- price: 建議價格
- created_at: 建立時間
- updated_at: 更新時間
```

### 2. 訂單管理 (Order Management)

#### `orders` - 訂單主表
```sql
- id: 主鍵
- customer_id: 顧客ID (外鍵)
- chef_id: 廚師ID (外鍵，接單後才有值)
- order_number: 訂單編號 (唯一)
- status: 訂單狀態 (PENDING/ACCEPTED/PREPARING/READY/DELIVERING/COMPLETED/CANCELLED)
- delivery_method: 取餐方式 (PICKUP/DELIVERY)
- delivery_address: 配送地址
- delivery_notes: 配送備註
- preferred_time: 希望完成時間
- accepted_at: 接單時間
- completed_at: 完成時間
- total_amount: 總金額
- delivery_fee: 配送費
- customer_notes: 客戶備註
- chef_notes: 廚師備註
- created_at: 建立時間
- updated_at: 更新時間
```

#### `order_dishes` - 訂單菜品明細
```sql
- id: 主鍵
- order_id: 訂單ID (外鍵)
- dish_name: 菜名
- quantity: 份數
- unit_price: 單價
- salt_level: 鹹度 (LIGHT/NORMAL/HEAVY)
- spice_level: 辣度 (NONE/MILD/MEDIUM/SPICY/VERY_SPICY)
- include_onion: 是否加蔥
- include_ginger: 是否加薑
- include_garlic: 是否加蒜
- include_cilantro: 是否加香菜
- ingredients: 食材需求
- special_instructions: 特殊作法
- custom_notes: 客製備註
- created_at: 建立時間
```

#### `order_status_history` - 訂單狀態歷史
```sql
- id: 主鍵
- order_id: 訂單ID (外鍵)
- old_status: 舊狀態
- new_status: 新狀態
- notes: 備註
- created_at: 變更時間
```

### 3. 評價系統 (Review System)

#### `reviews` - 評價
```sql
- id: 主鍵
- order_id: 訂單ID (外鍵，唯一)
- reviewer_id: 評價者ID (外鍵)
- reviewee_id: 被評價者ID (外鍵)
- rating: 總評分 (1-5星)
- title: 評價標題
- content: 評價內容
- taste_rating: 口味評分
- service_rating: 服務評分
- hygiene_rating: 衛生評分
- delivery_rating: 配送評分
- is_public: 是否公開顯示
- is_verified: 是否已驗證
- created_at: 建立時間
- updated_at: 更新時間
```

### 4. 溝通系統 (Communication System)

#### `messages` - 訊息
```sql
- id: 主鍵
- sender_id: 發送者ID (外鍵)
- receiver_id: 接收者ID (外鍵)
- order_id: 關聯訂單ID (外鍵，可選)
- subject: 主題
- content: 訊息內容
- message_type: 訊息類型 (text/image/system)
- is_read: 是否已讀
- is_system: 是否為系統訊息
- created_at: 建立時間
- read_at: 已讀時間
```

## 🔄 業務流程

### 用戶註冊流程
1. 用戶選擇註冊方式 (傳統註冊/Google OAuth)
2. 傳統註冊需要信箱驗證
3. 首次登入選擇用戶角色 (顧客/廚師)
4. 廚師需要上傳證照並完善資料

### 訂單處理流程
1. **PENDING** - 顧客建立訂單
2. **ACCEPTED** - 廚師接受訂單
3. **PREPARING** - 廚師開始製作
4. **READY** - 製作完成
5. **DELIVERING** - 配送中 (外送訂單)
6. **COMPLETED** - 訂單完成
7. **CANCELLED** - 訂單取消

### 評價系統
- 訂單完成後顧客可評價廚師
- 支援多維度評分 (口味、服務、衛生、配送)
- 自動更新廚師平均評分

## 🔑 關鍵特性

### 用戶管理
- 支援傳統註冊和 Google OAuth
- 角色分離設計 (顧客/廚師)
- 廚師認證系統

### 訂單系統
- 完整的訂單狀態追蹤
- 靈活的菜品客製化選項
- 辛香料個別控制

### 評價系統
- 多維度評分機制
- 自動統計更新
- 公開/私人評價選項

### 溝通系統
- 用戶間訊息溝通
- 訂單相關討論
- 系統通知機制

## 📈 擴展性考慮

### 已預留欄位
- 用戶頭像 URL
- 廚師服務範圍
- 配送費用
- 訊息類型擴展

### 可添加功能
- 廚師專長標籤系統
- 招牌菜展示
- 訂單排程系統
- 付款記錄
- 優惠券系統 