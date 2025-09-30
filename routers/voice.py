"""
語音處理路由 - 負責語音轉文字和AI解析功能
"""
import os
import tempfile
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
import whisper
import openai
from config import get_settings

# 初始化設定
settings = get_settings()
router = APIRouter(prefix="/api/voice", tags=["voice"])

# 載入 Whisper 模型
whisper_model = None

def get_whisper_model():
    """獲取 Whisper 模型（懶加載）"""
    global whisper_model
    if whisper_model is None:
        # 使用較小的模型以提高速度，可根據需要調整
        whisper_model = whisper.load_model("base")
    return whisper_model

# 設定 OpenAI API
openai.api_key = settings.OPENAI_API_KEY

@router.post("/process")
async def process_voice_input(audio: UploadFile = File(...)):
    """
    處理語音輸入：
    1. 將音頻文件轉換為文字（使用 Whisper）
    2. 使用 OpenAI API 解析文字內容
    3. 返回結構化的訂單資訊
    """
    try:
        # 檢查文件格式
        if not audio.content_type.startswith('audio/'):
            raise HTTPException(status_code=400, detail="上傳的文件不是音頻格式")
        
        # 將上傳的音頻保存到臨時文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_audio:
            content = await audio.read()
            temp_audio.write(content)
            temp_audio_path = temp_audio.name
        
        try:
            # 步驟1：使用 Whisper 進行語音轉文字
            model = get_whisper_model()
            result = model.transcribe(temp_audio_path, language='zh')
            transcript = result["text"].strip()
            
            if not transcript:
                return JSONResponse(content={
                    "success": False, 
                    "error": "無法識別音頻內容，請重新錄音"
                })
            
            # 步驟2：使用 OpenAI API 解析文字內容
            parsed_data = await parse_order_info(transcript)
            
            return JSONResponse(content={
                "success": True,
                "transcript": transcript,
                "parsed_data": parsed_data
            })
            
        finally:
            # 清理臨時文件
            if os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)
                
    except Exception as e:
        return JSONResponse(content={
            "success": False,
            "error": f"處理音頻時發生錯誤: {str(e)}"
        })

async def parse_order_info(transcript: str) -> dict:
    """
    使用 OpenAI API 解析訂單資訊
    """
    try:
        # 獲取當前日期用於日期解析
        today = datetime.now()
        
        # 構建提示詞
        prompt = f"""
請從以下中文語音識別文字中提取訂單預約資訊，並以 JSON 格式返回。

當前日期：{today.strftime('%Y-%m-%d')}
當前時間：{today.strftime('%H:%M')}

語音內容：「{transcript}」

請提取以下資訊：
1. order_date: 預約日期（YYYY-MM-DD 格式）
   - 如果提到「今天」，使用當前日期
   - 如果提到「明天」，使用明天的日期  
   - 如果提到「後天」，使用後天的日期
   - 如果提到「週X」或「星期X」，計算對應的日期
   - 如果提到具體日期，轉換為標準格式

2. order_time: 預約時間（HH:MM 格式，24小時制）
   - 如果提到「早上X點」「上午X點」，轉換為24小時制
   - 如果提到「下午X點」「晚上X點」，轉換為24小時制
   - 如果只說「X點」且時間小於12，假設為下午時間

3. pickup_method: 取餐方式
   - 如果提到「外送」「送到」「配送」「送餐」，返回「外送」
   - 如果提到「自取」「自己拿」「去拿」「到店取餐」，返回「自取」

4. address: 外送地址（僅當pickup_method為「外送」時提取）
   - 提取完整的地址資訊

請只返回 JSON 格式，不要包含其他文字：
{{
  "order_date": "YYYY-MM-DD或null",
  "order_time": "HH:MM或null", 
  "pickup_method": "外送或自取或null",
  "address": "地址或null"
}}
"""
        
        # 調用 OpenAI API
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.1  # 降低隨機性，提高準確性
        )
        
        # 解析響應
        ai_response = response.choices[0].message.content.strip()
        
        # 嘗試解析 JSON
        try:
            parsed_data = json.loads(ai_response)
            
            # 驗證和清理數據
            cleaned_data = {}
            
            # 驗證日期格式
            if parsed_data.get('order_date'):
                try:
                    # 驗證日期格式
                    datetime.strptime(parsed_data['order_date'], '%Y-%m-%d')
                    # 確保日期不早於今天
                    order_date = datetime.strptime(parsed_data['order_date'], '%Y-%m-%d').date()
                    if order_date >= today.date():
                        cleaned_data['order_date'] = parsed_data['order_date']
                except ValueError:
                    pass  # 忽略無效日期
            
            # 驗證時間格式
            if parsed_data.get('order_time'):
                try:
                    datetime.strptime(parsed_data['order_time'], '%H:%M')
                    cleaned_data['order_time'] = parsed_data['order_time']
                except ValueError:
                    pass  # 忽略無效時間
            
            # 驗證取餐方式
            if parsed_data.get('pickup_method') in ['外送', '自取']:
                cleaned_data['pickup_method'] = parsed_data['pickup_method']
            
            # 驗證地址
            if parsed_data.get('address') and cleaned_data.get('pickup_method') == '外送':
                cleaned_data['address'] = parsed_data['address'].strip()
            
            return cleaned_data
            
        except json.JSONDecodeError:
            # 如果JSON解析失敗，返回空字典
            return {}
            
    except Exception as e:
        print(f"OpenAI API 調用失敗: {e}")
        return {}
