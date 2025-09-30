import sys
import os
import json
import argparse
from datetime import datetime
import whisper
import openai
from pathlib import Path

def load_config():
    """載入配置，優先使用環境變數，其次是 .env 文件"""
    # 嘗試從環境變數獲取 API Key
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        # 嘗試從 .env 文件載入
        env_file = Path('.env')
        if env_file.exists():
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('OPENAI_API_KEY='):
                        api_key = line.strip().split('=', 1)[1].strip('"\'')
                        break
    
    if not api_key:
        print("沒有 OPENAI_API_KEY")
        sys.exit(1)
    
    return api_key

def transcribe_audio(audio_path, model_size='base'):
    """使用 Whisper 將音頻轉換為文字"""
    print(f"載入 Whisper 模型 ({model_size})...")
    
    try:
        model = whisper.load_model(model_size)
        print(f"開始轉錄音頻文件: {audio_path}")
        
        result = model.transcribe(audio_path, language='zh')
        transcript = result["text"].strip()
        
        if not transcript:
            print("警告：無法從音頻中識別任何文字")
            return None
            
        print(f"語音轉文字完成")
        print(f"識別內容：{transcript}")
        return transcript
        
    except Exception as e:
        print(f"語音轉文字失敗：{e}")
        return None

def parse_order_with_ai(transcript, api_key):
    """使用 OpenAI API 解析訂單資訊"""
    print("使用 AI 解析訂單資訊...")
    
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

5. dishes: 菜品資訊（數組格式）
   - 提取提到的菜品名稱
   - 如果提到數量，一併記錄

6. special_requirements: 特殊要求
   - 提取任何特殊需求或備註

請只返回 JSON 格式，不要包含其他文字：
{{
  "order_date": "YYYY-MM-DD或null",
  "order_time": "HH:MM或null", 
  "pickup_method": "外送或自取或null",
  "address": "地址或null",
  "dishes": ["菜品1", "菜品2"] 或 [],
  "special_requirements": "特殊要求或null"
}}
"""
        
        # 調用 OpenAI API
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.1  # 降低隨機性，提高準確性
        )
        
        # 解析響應
        ai_response = response.choices[0].message.content.strip()
        print(f"AI 原始響應：{ai_response}")
        
        # 嘗試解析 JSON
        try:
            parsed_data = json.loads(ai_response)
            
            # 驗證和清理數據
            cleaned_data = {}
            
            # 驗證日期格式
            if parsed_data.get('order_date'):
                try:
                    datetime.strptime(parsed_data['order_date'], '%Y-%m-%d')
                    # 確保日期不早於今天
                    order_date = datetime.strptime(parsed_data['order_date'], '%Y-%m-%d').date()
                    if order_date >= today.date():
                        cleaned_data['order_date'] = parsed_data['order_date']
                except ValueError:
                    print(f"⚠️  無效日期格式：{parsed_data['order_date']}")
            
            # 驗證時間格式
            if parsed_data.get('order_time'):
                try:
                    datetime.strptime(parsed_data['order_time'], '%H:%M')
                    cleaned_data['order_time'] = parsed_data['order_time']
                except ValueError:
                    print(f"⚠️  無效時間格式：{parsed_data['order_time']}")
            
            # 驗證取餐方式
            if parsed_data.get('pickup_method') in ['外送', '自取']:
                cleaned_data['pickup_method'] = parsed_data['pickup_method']
            
            # 驗證地址
            if parsed_data.get('address') and cleaned_data.get('pickup_method') == '外送':
                cleaned_data['address'] = parsed_data['address'].strip()
            
            # 處理菜品資訊
            if parsed_data.get('dishes') and isinstance(parsed_data['dishes'], list):
                cleaned_data['dishes'] = [dish.strip() for dish in parsed_data['dishes'] if dish.strip()]
            
            # 處理特殊要求
            if parsed_data.get('special_requirements'):
                cleaned_data['special_requirements'] = parsed_data['special_requirements'].strip()
            
            return cleaned_data
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON 解析失敗：{e}")
            print(f"AI 響應內容：{ai_response}")
            return {}
            
    except Exception as e:
        print(f"❌ OpenAI API 調用失敗：{e}")
        return {}

def display_results(transcript, parsed_data):
    """顯示處理結果"""
    print("\n" + "="*60)
    print("語音轉訂單資訊結果")
    print("="*60)
    
    print(f"\n 原始語音內容：")
    print(f"   {transcript}")
    
    print(f"\n 解析結果：")
    
    if not parsed_data:
        print("    無法解析出有效的訂單資訊")
        return
    
    # 顯示解析的訂單資訊
    if parsed_data.get('order_date'):
        print(f"   預約日期：{parsed_data['order_date']}")
    
    if parsed_data.get('order_time'):
        print(f"   預約時間：{parsed_data['order_time']}")
    
    if parsed_data.get('pickup_method'):
        print(f"   取餐方式：{parsed_data['pickup_method']}")
    
    if parsed_data.get('address'):
        print(f"   外送地址：{parsed_data['address']}")
    
    if parsed_data.get('dishes'):
        print(f"    菜品清單：")
        for i, dish in enumerate(parsed_data['dishes'], 1):
            print(f"      {i}. {dish}")
    
    if parsed_data.get('special_requirements'):
        print(f"   特殊要求：{parsed_data['special_requirements']}")
    
    print(f"\nJSON 格式：")
    print(json.dumps(parsed_data, ensure_ascii=False, indent=2))
    
    print("\n" + "="*60)

def main():
    """主函數"""
    parser = argparse.ArgumentParser(
        description='語音轉訂單資訊工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用範例:
  python voice_to_order.py demo.mp3
  python voice_to_order.py recording.wav
  python voice_to_order.py --model large audio.m4a
  python voice_to_order.py --help
        '''
    )
    
    parser.add_argument('audio_file', 
                       help='音頻文件路徑 (支援格式: mp3, wav, m4a, ogg 等)')
    
    parser.add_argument('--model', 
                       choices=['tiny', 'base', 'small', 'medium', 'large'],
                       default='base',
                       help='Whisper 模型大小 (預設: base)')
    
    args = parser.parse_args()
    
    # 檢查音頻文件是否存在
    if not os.path.exists(args.audio_file):
        print(f"錯誤：音頻文件不存在 - {args.audio_file}")
        sys.exit(1)
    
    print("語音轉訂單資訊工具")
    print(f"音頻文件：{args.audio_file}")
    print(f"Whisper 模型：{args.model}")
    print("-" * 40)
    
    try:
        # 載入配置
        api_key = load_config()
        
        # 步驟1：語音轉文字
        transcript = transcribe_audio(args.audio_file, args.model)
        if not transcript:
            sys.exit(1)
        
        # 步驟2：AI 解析訂單資訊
        parsed_data = parse_order_with_ai(transcript, api_key)
        
        # 步驟3：顯示結果
        display_results(transcript, parsed_data)
        
        # 可選：儲存結果到文件
        output_file = f"order_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        result = {
            "timestamp": datetime.now().isoformat(),
            "audio_file": args.audio_file,
            "whisper_model": args.model,
            "transcript": transcript,
            "parsed_data": parsed_data
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"結果已儲存至：{output_file}")
        
    except KeyboardInterrupt:
        print("\n\n用戶中斷程序")
        sys.exit(1)
    except Exception as e:
        print(f"\n程序執行失敗：{e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
