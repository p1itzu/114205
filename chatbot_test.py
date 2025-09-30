#!/usr/bin/env python3
"""
訂單收集 Chatbot 測試工具
單頁聊天介面，用於測試訂單資訊收集功能
"""

from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
import openai
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List
from pathlib import Path

# 導入現有的驗證功能
from voice_to_order_v2 import validate_for_database

app = FastAPI(title="訂單收集 Chatbot 測試")
templates = Jinja2Templates(directory="templates")

# 載入配置
def load_openai_config():
    """載入 OpenAI API Key"""
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        env_file = Path('.env')
        if env_file.exists():
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('OPENAI_API_KEY='):
                        api_key = line.strip().split('=', 1)[1].strip('"\'')
                        break
    
    return api_key

# 全域變數存儲對話狀態
conversation_state = {
    "messages": [],
    "collected_data": {
        "step1_data": {},
        "step2_data": {"dishes": []}
    }
}

@app.get("/", response_class=HTMLResponse)
async def chatbot_page(request: Request):
    """顯示 chatbot 測試頁面"""
    return templates.TemplateResponse("chatbot_test.html", {"request": request})

@app.post("/chat")
async def chat_endpoint(user_message: str = Form(...)):
    """處理使用者訊息並回應"""
    try:
        # 載入 API Key
        api_key = load_openai_config()
        if not api_key:
            return JSONResponse({
                "success": False,
                "error": "未設定 OPENAI_API_KEY"
            })
        
        # 記錄使用者訊息
        conversation_state["messages"].append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        })
        
        # 使用 AI 解析使用者輸入
        parsed_info = await parse_user_input_with_ai(user_message, api_key)
        
        # 更新收集的資料
        update_collected_data(parsed_info)
        
        # 驗證資料完整性
        validation_result = validate_for_database(conversation_state["collected_data"])
        
        # 生成回應訊息
        response_message = generate_response_message(validation_result, conversation_state["collected_data"])
        
        # 記錄機器人回應
        conversation_state["messages"].append({
            "role": "assistant", 
            "content": response_message,
            "timestamp": datetime.now().isoformat()
        })
        
        return JSONResponse({
            "success": True,
            "response": response_message,
            "collected_data": format_collected_data_display(conversation_state["collected_data"]),
            "validation": validation_result,
            "conversation_history": conversation_state["messages"][-6:]  # 最近3輪對話
        })
        
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": f"處理失敗：{str(e)}"
        })

async def parse_user_input_with_ai(user_input: str, api_key: str) -> dict:
    """使用 AI 解析使用者輸入"""
    today = datetime.now()
    tomorrow = today + timedelta(days=1)
    day_after_tomorrow = today + timedelta(days=2)
    
    # 構建提示詞，包含當前已收集的資料
    current_data = conversation_state["collected_data"]
    
    prompt = f"""你是一個專業的訂餐助手，負責從客戶的文字訊息中提取訂單資訊。

當前時間資訊：
- 當前日期：{today.strftime('%Y-%m-%d %A')}
- 明天：{tomorrow.strftime('%Y-%m-%d %A')}
- 後天：{day_after_tomorrow.strftime('%Y-%m-%d %A')}

目前已收集的訂單資訊：
{json.dumps(current_data, ensure_ascii=False, indent=2)}

客戶新訊息：「{user_input}」

請分析客戶訊息，提取或更新以下訂單資訊：

=== STEP 1: 預訂基本資訊 ===
1. order_date: 預約日期 (YYYY-MM-DD)
2. order_time: 預約時間 (HH:MM, 24小時制)
3. pickup_method: 取餐方式 ("自取"或"外送")
4. address: 外送地址 (僅外送需要)
5. customer_notes: 客戶備註

=== STEP 2: 菜品詳細資訊 ===
對每道菜品：
1. dish_name: 菜品名稱
2. quantity: 數量 (預設1)
3. salt_level: 鹹度 ("light"/"normal"/"heavy")
4. spice_level: 辣度 ("none"/"mild"/"medium"/"spicy")
5. seasoning_preferences: 辛香料偏好
6. ingredients: 特定食材要求
7. special_instructions: 特殊烹飪方法
8. custom_notes: 客製化備註

解析規則：
- 只提取或更新此次訊息中明確提到的資訊
- 保留之前已確認的資訊
- 如果客戶修正之前的資訊，使用新的資訊
- 對於「今天」「明天」「後天」等相對日期，計算具體日期
- 時間轉換為24小時制，但如果客戶只說「早上」「中午」「下午」「晚上」而沒有具體時間，不要自動推測具體時間
- 調味偏好只有在客戶明確提到時才設定，否則保持null

請以JSON格式回傳，只包含此次提取到的新資訊或更新資訊：

{{
  "step1_data": {{
    "order_date": "YYYY-MM-DD或null",
    "order_time": "HH:MM或null", 
    "pickup_method": "自取或外送或null",
    "address": "地址或null",
    "customer_notes": "備註或null"
  }},
  "step2_data": {{
    "dishes": [
      {{
        "dish_name": "菜名或null",
        "quantity": 數字或null,
        "salt_level": "調味或null",
        "spice_level": "辣度或null",
        "seasoning_preferences": {{
          "include_onion": true/false/null,
          "include_ginger": true/false/null,
          "include_garlic": true/false/null,
          "include_cilantro": true/false/null
        }},
        "ingredients": "食材或null",
        "special_instructions": "作法或null",
        "custom_notes": "備註或null"
      }}
    ]
  }}
}}

重要：
- 如果客戶沒有提到某項資訊，該欄位設為null
- 如果客戶提到新的菜品，添加到dishes陣列
- 如果客戶修正現有菜品，更新對應資訊
"""

    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        
        ai_response = response.choices[0].message.content.strip()
        
        # 提取JSON部分
        json_start = ai_response.find('{')
        json_end = ai_response.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_content = ai_response[json_start:json_end]
            parsed_data = json.loads(json_content)
            return parsed_data
        else:
            return {}
            
    except Exception as e:
        print(f"AI 解析失敗：{e}")
        return {}

def update_collected_data(parsed_info: dict):
    """更新收集的資料"""
    if not parsed_info:
        return
    
    # 更新 Step 1 資料
    step1_new = parsed_info.get("step1_data", {})
    for key, value in step1_new.items():
        if value is not None:
            conversation_state["collected_data"]["step1_data"][key] = value
    
    # 更新 Step 2 資料
    step2_new = parsed_info.get("step2_data", {})
    new_dishes = step2_new.get("dishes", [])
    
    if new_dishes:
        current_dishes = conversation_state["collected_data"]["step2_data"]["dishes"]
        
        for new_dish in new_dishes:
            # 檢查是否是新菜品還是更新現有菜品
            dish_name = new_dish.get("dish_name")
            if dish_name:
                # 尋找現有同名菜品
                existing_dish_index = None
                for i, existing_dish in enumerate(current_dishes):
                    if existing_dish.get("dish_name") == dish_name:
                        existing_dish_index = i
                        break
                
                if existing_dish_index is not None:
                    # 更新現有菜品
                    for key, value in new_dish.items():
                        if value is not None:
                            current_dishes[existing_dish_index][key] = value
                else:
                    # 添加新菜品，只設置明確提供的值
                    dish_data = {
                        "dish_name": dish_name,
                        "quantity": new_dish.get("quantity", 1)
                    }
                    
                    # 只有當AI明確提取到調味資訊時才設置
                    if new_dish.get("salt_level") is not None:
                        dish_data["salt_level"] = new_dish["salt_level"]
                    if new_dish.get("spice_level") is not None:
                        dish_data["spice_level"] = new_dish["spice_level"]
                    
                    # 更新seasoning_preferences - 只在有明確設定時才添加
                    if new_dish.get("seasoning_preferences"):
                        dish_data["seasoning_preferences"] = {}
                        for pref_key, pref_value in new_dish["seasoning_preferences"].items():
                            if pref_value is not None:
                                dish_data["seasoning_preferences"][pref_key] = pref_value
                    
                    # 設置其他欄位
                    for field in ["ingredients", "special_instructions", "custom_notes"]:
                        if new_dish.get(field):
                            dish_data[field] = new_dish[field]
                    
                    current_dishes.append(dish_data)

def generate_response_message(validation_result: dict, collected_data: dict) -> str:
    """生成機器人回應訊息"""
    if validation_result["ready_for_db"]:
        return "太棒了！您的訂單資訊已經完整，我已經幫您整理好所有詳細資料。這份訂單可以直接送給廚師處理了！如果還想調整什麼內容，隨時告訴我。"
    
    # 資料不完整時的回應
    response_parts = []
    
    # 確認已收集的資訊
    step1 = collected_data.get("step1_data", {})
    step2 = collected_data.get("step2_data", {})
    
    collected_info = []
    if step1.get("order_date"):
        collected_info.append(f"預約日期：{step1['order_date']}")
    if step1.get("order_time"):
        collected_info.append(f"用餐時間：{step1['order_time']}")
    if step1.get("pickup_method"):
        collected_info.append(f"取餐方式：{step1['pickup_method']}")
    if step1.get("address"):
        collected_info.append(f"外送地址：{step1['address']}")
    
    dishes = step2.get("dishes", [])
    if dishes:
        dish_info = []
        for i, dish in enumerate(dishes, 1):
            dish_desc = f"{dish.get('dish_name', '未命名菜品')} × {dish.get('quantity', 1)}份"
            
            # 只顯示明確設定的調味資訊
            spice_level = dish.get('spice_level')
            if spice_level and spice_level != 'none':
                dish_desc += f" ({spice_level}辣)"
            
            salt_level = dish.get('salt_level')
            if salt_level and salt_level != 'normal':
                dish_desc += f" ({salt_level}鹹度)"
            
            dish_info.append(dish_desc)
        collected_info.append(f"菜品：{', '.join(dish_info)}")
    
    if collected_info:
        response_parts.append(f"好的！我已經記錄了：{' | '.join(collected_info)}")
    
    # 詢問缺少的資訊
    if validation_result["oral_questions"]:
        if len(validation_result["oral_questions"]) == 1:
            response_parts.append(f"還需要確認一下：{validation_result['oral_questions'][0]}")
        else:
            response_parts.append("還需要確認幾個資訊：")
            for i, question in enumerate(validation_result["oral_questions"], 1):
                response_parts.append(f"{i}. {question}")
    
    return "\n\n".join(response_parts)

def format_collected_data_display(collected_data: dict) -> dict:
    """格式化顯示收集的資料"""
    step1 = collected_data.get("step1_data", {})
    step2 = collected_data.get("step2_data", {})
    
    formatted = {
        "預訂資訊": {},
        "菜品資訊": []
    }
    
    # Step 1 資料
    if step1.get("order_date"):
        formatted["預訂資訊"]["預約日期"] = step1["order_date"]
    if step1.get("order_time"):
        formatted["預訂資訊"]["用餐時間"] = step1["order_time"]
    if step1.get("pickup_method"):
        formatted["預訂資訊"]["取餐方式"] = step1["pickup_method"]
    if step1.get("address"):
        formatted["預訂資訊"]["外送地址"] = step1["address"]
    if step1.get("customer_notes"):
        formatted["預訂資訊"]["客戶備註"] = step1["customer_notes"]
    
    # Step 2 資料
    dishes = step2.get("dishes", [])
    for i, dish in enumerate(dishes, 1):
        dish_formatted = {
            "菜品名稱": dish.get("dish_name", "未命名"),
            "數量": f"{dish.get('quantity', 1)}份",
        }
        
        # 調味資訊
        seasoning = []
        if dish.get("salt_level", "normal") != "normal":
            seasoning.append(f"{dish['salt_level']}鹹度")
        if dish.get("spice_level", "none") != "none":
            seasoning.append(f"{dish['spice_level']}辣")
        if seasoning:
            dish_formatted["調味"] = " | ".join(seasoning)
        
        # 辛香料偏好
        prefs = dish.get("seasoning_preferences", {})
        excluded_seasonings = []
        if not prefs.get("include_onion", True):
            excluded_seasonings.append("不加蔥")
        if not prefs.get("include_ginger", True):
            excluded_seasonings.append("不加薑")
        if not prefs.get("include_garlic", True):
            excluded_seasonings.append("不加蒜")
        if not prefs.get("include_cilantro", True):
            excluded_seasonings.append("不加香菜")
        if excluded_seasonings:
            dish_formatted["辛香料"] = " | ".join(excluded_seasonings)
        
        # 其他要求
        if dish.get("ingredients"):
            dish_formatted["食材要求"] = dish["ingredients"]
        if dish.get("special_instructions"):
            dish_formatted["特殊作法"] = dish["special_instructions"]
        if dish.get("custom_notes"):
            dish_formatted["客製備註"] = dish["custom_notes"]
        
        formatted["菜品資訊"].append(dish_formatted)
    
    return formatted

@app.post("/reset")
async def reset_conversation():
    """重置對話狀態"""
    global conversation_state
    conversation_state = {
        "messages": [],
        "collected_data": {
            "step1_data": {},
            "step2_data": {"dishes": []}
        }
    }
    return JSONResponse({"success": True, "message": "對話已重置"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
