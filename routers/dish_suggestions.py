from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import openai
import json
import os
from pathlib import Path
# from utils.dependencies import get_current_user
# from models.user import User

router = APIRouter(prefix="/api/dish-suggestions", tags=["dish-suggestions"])

# Pydantic 模型
class DishSuggestionRequest(BaseModel):
    message: str
    current_dish: Optional[Dict[str, Any]] = None

class DishSuggestionResponse(BaseModel):
    success: bool
    response: str
    suggestions: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

def load_openai_config():
    """載入 OpenAI API Key"""
    try:
        from config import settings
        return settings.OPENAI_API_KEY
    except (ImportError, AttributeError):
        # 備用方案：直接從環境變數讀取
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

def format_dish_response(suggestions: Dict[str, Any]) -> str:
    """
    格式化菜品建議回應，讓內容更精簡易讀
    """
    if not suggestions:
        return "抱歉，我無法為您提供具體建議，請提供更多詳細資訊。"
    
    # 檢查是否為預設訊息（沒有具體建議）
    ingredients = suggestions.get('ingredients', '')
    if ingredients.startswith("請提供"):
        return "🤔 **請告訴我具體菜品名稱**\n\n例如：「蛋炒飯」、「宮保雞丁」、「紅燒肉」等\n\n我會為您提供詳細的食材和做法建議！"
    
    # 獲取菜品名稱
    dish_name = suggestions.get('dish_name', '這道菜')
    if dish_name == "建議菜品":
        dish_name = "您的菜品"
    
    # 檢查是否為針對性建議（根據現有資訊補充）
    is_targeted_suggestion = (
        "建議根據" in ingredients or 
        "建議補充" in ingredients or
        "建議確認" in suggestions.get('special_notes', '') or
        "（建議：" in dish_name or
        "根據現有資訊" in dish_name
    )
    
    # 檢測是否為多輪對話
    is_multi_dish_conversation = any([
        "新菜品" in dish_name,
        "下一道" in dish_name,
        dish_name.startswith("接下來"),
        dish_name.startswith("再來"),
    ])
    
    # 構建回應
    if is_targeted_suggestion:
        if "（建議：" in dish_name:
            # 處理推測菜品的情況
            parts = dish_name.split("（建議：")
            if len(parts) == 2:
                current_info = parts[0]
                suggested_dish = parts[1].replace("）", "")
                response_parts = [f"👨‍🍳 **我分析了您的{current_info}資訊**\n\n🤔 **建議菜品：{suggested_dish}**"]
            else:
                response_parts = [f"👨‍🍳 **根據您提供的資訊，我來協助完善菜品內容**"]
        else:
            response_parts = [f"👨‍🍳 **我看到您正在編輯「{dish_name}」，我來協助補充缺少的資訊！**"]
    elif is_multi_dish_conversation:
        response_parts = [f"🍽️ **太好了！讓我們來規劃{dish_name}**"]
    else:
        response_parts = [f"🍽️ **{dish_name}**"]
    
    # 食材清單
    if suggestions.get('ingredients'):
        ingredients = suggestions['ingredients']
        # 如果不是預設訊息才顯示
        if not ingredients.startswith("請提供"):
            if is_targeted_suggestion and ("建議根據" in ingredients or "建議補充" in ingredients):
                response_parts.append(f"🥘 **建議食材**: {ingredients.replace('建議根據菜名選擇新鮮食材', '請根據菜品選擇合適食材').replace('建議補充主要食材', '請補充主要食材')}")
            else:
                response_parts.append(f"🥘 **食材**: {ingredients}")
    
    # 料理方式
    if suggestions.get('cooking_methods'):
        cooking_methods = suggestions['cooking_methods']
        # 如果不是預設訊息才顯示
        if not cooking_methods.startswith("請告訴我"):
            if is_targeted_suggestion and ("建議根據" in cooking_methods or "建議補充" in cooking_methods):
                response_parts.append(f"👨‍🍳 **建議做法**: {cooking_methods.replace('建議根據菜品特性選擇適當烹飪方法', '請根據菜品選擇適當料理方式').replace('建議補充料理方式', '請補充具體料理步驟')}")
            else:
                response_parts.append(f"👨‍🍳 **做法**: {cooking_methods}")
    
    # 調味建議
    seasoning = suggestions.get('seasoning', {})
    if seasoning:
        salt_level = seasoning.get('salt_level')
        spice_level = seasoning.get('spice_level')
        
        seasoning_info = []
        if salt_level and salt_level != "標準":
            seasoning_info.append(f"鹹度{salt_level}")
        if spice_level and spice_level != "不辣":
            seasoning_info.append(f"{spice_level}")
        
        if seasoning_info:
            response_parts.append(f"🌶️ **調味**: {' | '.join(seasoning_info)}")
    
    # 小提醒
    if suggestions.get('special_notes'):
        special_notes = suggestions['special_notes']
        # 如果不是預設訊息才顯示
        if not special_notes.startswith("請提供"):
            if is_targeted_suggestion and "建議" in special_notes:
                response_parts.append(f"💡 **建議**: {special_notes}")
            else:
                response_parts.append(f"💡 **小提醒**: {special_notes}")
    
    return "\n\n".join(response_parts)

@router.post("/")
async def get_dish_suggestions(request: DishSuggestionRequest) -> JSONResponse:
    """
    獲取菜單建議 - 使用OpenAI AI助手
    
    根據用戶輸入的菜品資訊，使用 AI 提供食材和料理方式建議
    """
    try:
        # 載入 OpenAI API Key
        api_key = load_openai_config()
        if not api_key:
            # 如果沒有API Key，使用簡化版本
            return await get_simple_suggestions(request)
        
        # 構建提示詞和分析現有資訊
        current_dish_info = ""
        missing_fields = []
        has_dish_info = False
        
        if request.current_dish:
            dish_parts = []
            has_dish_info = True
            
            # 分析已填寫的欄位
            if request.current_dish.get('name'):
                dish_parts.append(f"菜品名稱: {request.current_dish['name']}")
            else:
                missing_fields.append("菜品名稱")
                
            if request.current_dish.get('ingredients'):
                dish_parts.append(f"現有食材: {request.current_dish['ingredients']}")
            else:
                missing_fields.append("食材清單")
                
            if request.current_dish.get('special'):
                dish_parts.append(f"現有作法: {request.current_dish['special']}")
            else:
                missing_fields.append("料理方式")
            
            if dish_parts:
                current_dish_info = f"\n\n目前用戶正在編輯的菜品資訊:\n" + "\n".join(dish_parts)
                if missing_fields:
                    current_dish_info += f"\n\n缺少的欄位: {', '.join(missing_fields)}"

        # 檢測是否為多輪菜品規劃對話
        is_multi_dish_session = any([
            "下一道" in request.message,
            "還想" in request.message and ("菜" in request.message or "做" in request.message),
            "繼續" in request.message and "菜" in request.message,
            "再來" in request.message,
            "另外" in request.message and "菜" in request.message,
            "接下來" in request.message
        ])

        # 根據情況調整prompt
        if has_dish_info and missing_fields:
            # 如果有部分資訊且有缺少的欄位，提供針對性建議
            prompt = f"""你是一位專業的廚師，專門協助用戶完善菜品資訊。

用戶訊息: 「{request.message}」{current_dish_info}

請根據已有的資訊，針對缺少的欄位提供專業建議。重點補充以下內容：
{f"- 推薦適合的食材" if "食材清單" in missing_fields else ""}
{f"- 建議料理方式" if "料理方式" in missing_fields else ""}
{f"- 確認菜品名稱" if "菜品名稱" in missing_fields else ""}

請提供簡潔實用的建議：
{{
  "dish_name": "{'根據現有資訊推測的菜品名稱' if '菜品名稱' in missing_fields else '確認的菜品名稱'}",
  "ingredients": "{'針對此菜品推薦的主要食材' if '食材清單' in missing_fields else '現有食材的補充建議'}",
  "cooking_methods": "{'推薦的料理步驟' if '料理方式' in missing_fields else '現有做法的改進建議'}", 
  "seasoning": {{
    "salt_level": "清淡/標準/濃郁",
    "spice_level": "不辣/微辣/中辣/重辣"
  }},
  "special_notes": "針對此菜品最重要的提醒"
}}

用 [JSON_START] 和 [JSON_END] 標記包圍JSON回應。"""
        elif is_multi_dish_session:
            # 多輪菜品規劃對話的prompt
            prompt = f"""你是一位專業的廚師，正在協助用戶規劃多道菜品的菜單。

用戶訊息: 「{request.message}」{current_dish_info}

這是一個多菜品規劃的會話，用戶想要新增多道菜色。請以親切、鼓勵的語氣回應，並提供新菜品的建議。

請提供簡潔實用的建議：
{{
  "dish_name": "新菜品的具體名稱",
  "ingredients": "主要食材清單（簡潔版）",
  "cooking_methods": "核心料理步驟（一句話）", 
  "seasoning": {{
    "salt_level": "清淡/標準/濃郁",
    "spice_level": "不辣/微辣/中辣/重辣"
  }},
  "special_notes": "最重要的一個提醒"
}}

用 [JSON_START] 和 [JSON_END] 標記包圍JSON回應。"""
        else:
            # 一般情況的prompt
            prompt = f"""你是一位專業的廚師，專門協助用戶規劃菜單。

用戶需求: 「{request.message}」{current_dish_info}

請提供簡潔實用的建議，包含：
1. 主要食材（簡化版，不超過10個詞）
2. 核心做法（一句話概括）
3. 調味建議
4. 關鍵小提醒

請直接提供JSON格式的建議：
{{
  "dish_name": "具體菜品名稱",
  "ingredients": "主要食材清單（簡潔版）",
  "cooking_methods": "核心料理步驟（一句話）", 
  "seasoning": {{
    "salt_level": "清淡/標準/濃郁",
    "spice_level": "不辣/微辣/中辣/重辣"
  }},
  "special_notes": "最重要的一個提醒"
}}

只需提供JSON格式的回應，用 [JSON_START] 和 [JSON_END] 標記包圍。"""

        try:
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[
                    {
                        "role": "system", 
                        "content": "你是一位專業的廚師，擅長提供實用的烹飪建議和食材搭配建議。請用繁體中文回應。"
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # 分離自然語言回應和JSON建議
            json_start = ai_response.find('[JSON_START]')
            json_end = ai_response.find('[JSON_END]')
            
            natural_response = ai_response
            suggestions = None
            
            if json_start >= 0 and json_end >= 0:
                # 提取自然語言部分
                natural_response = ai_response[:json_start].strip()
                
                # 提取並解析JSON部分
                json_content = ai_response[json_start + 12:json_end].strip()
                try:
                    # 尋找JSON物件
                    json_obj_start = json_content.find('{')
                    json_obj_end = json_content.rfind('}') + 1
                    
                    if json_obj_start >= 0 and json_obj_end > json_obj_start:
                        json_str = json_content[json_obj_start:json_obj_end]
                        suggestions = json.loads(json_str)
                except json.JSONDecodeError as e:
                    print(f"JSON 解析失敗: {e}")
                    print(f"JSON 內容: {json_content}")
            
            # 如果沒有找到標記的JSON，嘗試尋找最後一個JSON物件
            if not suggestions:
                json_start = ai_response.rfind('{')
                json_end = ai_response.rfind('}') + 1
                
                if json_start >= 0 and json_end > json_start:
                    try:
                        json_str = ai_response[json_start:json_end]
                        suggestions = json.loads(json_str)
                        # 移除natural_response中的JSON部分
                        natural_response = ai_response[:json_start].strip()
                    except json.JSONDecodeError:
                        pass
            
            # 格式化回應
            if suggestions:
                formatted_response = format_dish_response(suggestions)
            else:
                formatted_response = natural_response or "我已經為您準備了菜品建議，請查看右側預覽區域！"
            
            return JSONResponse({
                "success": True,
                "response": formatted_response,
                "suggestions": suggestions
            })
            
        except openai.OpenAIError as e:
            print(f"OpenAI API 錯誤: {e}")
            # 如果OpenAI出錯，回退到簡化版本
            return await get_simple_suggestions(request)
            
    except Exception as e:
        print(f"菜單建議 API 錯誤: {e}")
        return JSONResponse({
            "success": False,
            "response": "系統發生錯誤，請稍後再試。",
            "error": str(e)
        })

async def get_simple_suggestions(request: DishSuggestionRequest) -> JSONResponse:
    """
    簡化版建議功能 - 備用方案
    """
    try:
        message = request.message.lower()
        
        # 分析現有菜品資訊
        current_dish = request.current_dish or {}
        dish_name = current_dish.get('name', '')
        existing_ingredients = current_dish.get('ingredients', '')
        existing_methods = current_dish.get('special', '')
        
        # 檢測是否為多輪菜品規劃對話
        is_multi_dish_session = any([
            "下一道" in message,
            "還想" in message and ("菜" in message or "做" in message),
            "繼續" in message and "菜" in message,
            "再來" in message,
            "另外" in message and "菜" in message,
            "接下來" in message
        ])
        
        # 簡單的菜品建議邏輯
        suggestions = {}
        
        # 優先處理多輪菜品規劃會話
        if is_multi_dish_session:
            # 為多輪會話提供新的菜品建議
            multi_dish_suggestions = [
                {
                    "dish_name": "青椒炒肉絲",
                    "ingredients": "豬肉絲、青椒、蔥薑蒜",
                    "cooking_methods": "肉絲醃製後炒青椒，調味炒勻",
                    "seasoning": {"salt_level": "標準", "spice_level": "不辣"},
                    "special_notes": "青椒要保持脆嫩"
                },
                {
                    "dish_name": "番茄雞蛋",
                    "ingredients": "雞蛋、番茄、蔥花、糖",
                    "cooking_methods": "先炒雞蛋，再炒番茄，最後混合",
                    "seasoning": {"salt_level": "標準", "spice_level": "不辣"},
                    "special_notes": "番茄要炒出汁水"
                },
                {
                    "dish_name": "紅燒茄子",
                    "ingredients": "茄子、蒜泥、生抽、糖",
                    "cooking_methods": "茄子過油後燒製入味",
                    "seasoning": {"salt_level": "濃郁", "spice_level": "不辣"},
                    "special_notes": "茄子要先過油防止變黑"
                },
                {
                    "dish_name": "酸辣土豆絲",
                    "ingredients": "土豆、辣椒、醋、蔥",
                    "cooking_methods": "土豆絲大火爆炒，調酸辣味",
                    "seasoning": {"salt_level": "標準", "spice_level": "微辣"},
                    "special_notes": "土豆絲要先泡水去澱粉"
                }
            ]
            
            # 隨機選擇一個建議（或根據關鍵詞匹配）
            import random
            suggestions = random.choice(multi_dish_suggestions)
            
        # 智能分析並提供建議
        elif dish_name:
            # 如果已有菜品名稱，根據菜名提供建議
            if '雞' in dish_name or '宮保' in dish_name:
                base_suggestions = {
                    "dish_name": dish_name,
                    "ingredients": "雞胸肉、花生米、乾辣椒、蔥薑蒜",
                    "cooking_methods": "雞肉醃製後爆炒，配菜調料快速翻炒",
                    "seasoning": {"salt_level": "標準", "spice_level": "中辣"},
                    "special_notes": "大火快炒保持雞肉嫩滑"
                }
            elif '蛋炒飯' in dish_name or '炒飯' in dish_name:
                base_suggestions = {
                    "dish_name": dish_name,
                    "ingredients": "隔夜米飯、雞蛋、蔥花",
                    "cooking_methods": "先炒蛋盛起，再炒飯，最後混合炒勻",
                    "seasoning": {"salt_level": "標準", "spice_level": "不辣"},
                    "special_notes": "隔夜飯效果最佳"
                }
            elif '豆腐' in dish_name:
                base_suggestions = {
                    "dish_name": dish_name,
                    "ingredients": "嫩豆腐、豬絞肉、豆瓣醬、花椒",
                    "cooking_methods": "炒絞肉加豆瓣醬，放豆腐燉煮勾芡",
                    "seasoning": {"salt_level": "濃郁", "spice_level": "中辣"},
                    "special_notes": "豆腐先用鹽水燙過"
                }
            else:
                base_suggestions = {
                    "dish_name": dish_name,
                    "ingredients": "建議根據菜名選擇新鮮食材",
                    "cooking_methods": "建議根據菜品特性選擇適當烹飪方法",
                    "seasoning": {"salt_level": "標準", "spice_level": "不辣"},
                    "special_notes": "注意火候控制，保持食材新鮮"
                }
            
            # 如果已有部分資訊，則補充缺少的部分
            suggestions = {
                "dish_name": dish_name,
                "ingredients": existing_ingredients or base_suggestions["ingredients"],
                "cooking_methods": existing_methods or base_suggestions["cooking_methods"],
                "seasoning": base_suggestions["seasoning"],
                "special_notes": base_suggestions["special_notes"]
            }
            
        elif existing_ingredients or existing_methods:
            # 如果沒有菜名但有食材或做法，嘗試推測
            combined_text = f"{existing_ingredients} {existing_methods}".lower()
            
            if '雞' in combined_text or '雞肉' in combined_text:
                suggestions = {
                    "dish_name": "雞肉料理（建議：宮保雞丁）",
                    "ingredients": existing_ingredients or "雞胸肉、配菜、調料",
                    "cooking_methods": existing_methods or "爆炒",
                    "seasoning": {"salt_level": "標準", "spice_level": "微辣"},
                    "special_notes": "建議確認具體菜品名稱"
                }
            elif '蛋' in combined_text and ('飯' in combined_text or '米' in combined_text):
                suggestions = {
                    "dish_name": "蛋炒飯",
                    "ingredients": existing_ingredients or "米飯、雞蛋、蔥花",
                    "cooking_methods": existing_methods or "先炒蛋再炒飯",
                    "seasoning": {"salt_level": "標準", "spice_level": "不辣"},
                    "special_notes": "用隔夜飯效果更好"
                }
            else:
                suggestions = {
                    "dish_name": "根據現有資訊的料理",
                    "ingredients": existing_ingredients or "建議補充主要食材",
                    "cooking_methods": existing_methods or "建議補充料理方式",
                    "seasoning": {"salt_level": "標準", "spice_level": "不辣"},
                    "special_notes": "建議提供菜品名稱以獲得更精確建議"
                }
        else:
            # 根據用戶訊息關鍵詞提供建議
            if '雞' in message or '雞肉' in message or '宮保雞丁' in message:
                suggestions = {
                    "dish_name": "宮保雞丁",
                    "ingredients": "雞胸肉、花生米、乾辣椒、蔥薑蒜",
                    "cooking_methods": "雞肉醃製後爆炒，配菜調料快速翻炒",
                    "seasoning": {"salt_level": "標準", "spice_level": "中辣"},
                    "special_notes": "大火快炒保持雞肉嫩滑"
                }
            elif '蛋炒飯' in message or '炒飯' in message:
                suggestions = {
                    "dish_name": "蛋炒飯",
                    "ingredients": "隔夜米飯、雞蛋、蔥花",
                    "cooking_methods": "先炒蛋盛起，再炒飯，最後混合炒勻",
                    "seasoning": {"salt_level": "標準", "spice_level": "不辣"},
                    "special_notes": "隔夜飯效果最佳"
                }
            elif '麻婆豆腐' in message or '豆腐' in message:
                suggestions = {
                    "dish_name": "麻婆豆腐",
                    "ingredients": "嫩豆腐、豬絞肉、豆瓣醬、花椒",
                    "cooking_methods": "炒絞肉加豆瓣醬，放豆腐燉煮勾芡",
                    "seasoning": {"salt_level": "濃郁", "spice_level": "中辣"},
                    "special_notes": "豆腐先用鹽水燙過"
                }
            else:
                # 默認建議
                suggestions = {
                    "dish_name": "您想做的菜",
                    "ingredients": "請提供更具體的菜品名稱，我將為您推薦合適的食材",
                    "cooking_methods": "請告訴我具體菜名，我會提供詳細做法",
                    "seasoning": {"salt_level": "標準", "spice_level": "不辣"},
                    "special_notes": "請提供菜品名稱獲得更精準的建議"
                }
        
        # 使用統一的格式化函數
        formatted_response = format_dish_response(suggestions)
        
        return JSONResponse({
            "success": True,
            "response": formatted_response,
            "suggestions": suggestions
        })
        
    except Exception as e:
        print(f"簡化建議 API 錯誤: {e}")
        return JSONResponse({
            "success": False,
            "response": "抱歉，系統暫時無法處理您的請求，請稍後再試。",
            "error": str(e)
        })

# 測試用端點
@router.get("/test")
async def test_api():
    """測試 API 是否正常運作"""
    return JSONResponse({
        "success": True,
        "message": "菜單建議 API 運作正常",
        "version": "1.0.0"
    })

@router.get("/dish-suggestions/test") 
async def test_dish_suggestions():
    """測試菜單建議 API 是否正常運作"""
    return JSONResponse({
        "success": True,
        "message": "菜單建議 API 運作正常",
        "version": "1.0.0"
    })

