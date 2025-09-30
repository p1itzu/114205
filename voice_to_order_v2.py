#!/usr/bin/env python3
"""
語音轉訂單資訊工具 v2
專為新增訂單 Step1-2 設計，提供完整的資訊提取和缺失提醒功能
用法: python voice_to_order_v2.py <音頻文件路徑>
例如: python voice_to_order_v2.py demo.mp3
"""

import sys
import os
import json
import argparse
from datetime import datetime, timedelta
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
        print("❌ 錯誤：未找到 OPENAI_API_KEY")
        print("請設定環境變數或在 .env 文件中添加：")
        print("OPENAI_API_KEY=your-api-key-here")
        sys.exit(1)
    
    return api_key

def transcribe_audio(audio_path, model_size='base'):
    """使用 Whisper 將音頻轉換為文字"""
    print(f"🎤 載入 Whisper 模型 ({model_size})...")
    
    try:
        model = whisper.load_model(model_size)
        print(f"📝 開始轉錄音頻文件: {audio_path}")
        
        result = model.transcribe(audio_path, language='zh')
        transcript = result["text"].strip()
        
        if not transcript:
            print("⚠️  警告：無法從音頻中識別任何文字")
            return None
            
        print(f"✅ 語音轉文字完成")
        print(f"📄 識別內容：{transcript}")
        return transcript
        
    except Exception as e:
        print(f"❌ 語音轉文字失敗：{e}")
        return None

def parse_complete_order_info(transcript, api_key):
    """使用 OpenAI API 解析完整的訂單資訊"""
    print("🤖 使用 AI 解析完整訂單資訊...")
    
    try:
        # 獲取當前日期用於日期解析
        today = datetime.now()
        tomorrow = today + timedelta(days=1)
        day_after_tomorrow = today + timedelta(days=2)
        
        # 構建詳細的提示詞，避免 f-string 嵌套過深
        json_template = '''{
  "analysis_summary": {
    "provided_info": ["已提取到的資訊清單"],
    "missing_info": ["缺少的必要資訊清單"],
    "assumptions_made": ["基於常理做出的假設清單"]
  },
  "step1_data": {
    "order_date": "YYYY-MM-DD或null",
    "order_time": "HH:MM或null",
    "pickup_method": "自取或外送或null",
    "address": "完整地址或null",
    "customer_notes": "備註或null"
  },
  "step2_data": {
    "dishes": [
      {
        "dish_name": "菜名",
        "quantity": 1,
        "salt_level": "normal",
        "spice_level": "none",
        "seasoning_preferences": {
          "include_onion": true,
          "include_ginger": true,
          "include_garlic": true,
          "include_cilantro": true
        },
        "ingredients": "特定食材或null",
        "special_instructions": "特殊作法或null",
        "custom_notes": "客製備註或null"
      }
    ]
  }
}'''

        prompt = f"""你是一個專業的訂餐助手，需要從語音識別文字中提取完整的訂單資訊。

當前時間資訊：
- 當前日期：{today.strftime('%Y-%m-%d %A')}
- 明天：{tomorrow.strftime('%Y-%m-%d %A')}
- 後天：{day_after_tomorrow.strftime('%Y-%m-%d %A')}
- 當前時間：{today.strftime('%H:%M')}

語音內容：「{transcript}」

請分析語音內容並提取以下兩個部分的資訊：

=== STEP 1: 預訂基本資訊 ===
1. order_date: 預約日期 (YYYY-MM-DD)
2. order_time: 預約時間 (HH:MM, 24小時制)
3. pickup_method: 取餐方式 ("自取"或"外送")
4. address: 外送地址 (僅外送需要)
5. customer_notes: 客戶備註

=== STEP 2: 菜品詳細資訊 ===
針對每道菜品，提取：
1. dish_name: 菜品名稱
2. quantity: 數量 (預設1)
3. salt_level: 鹹度 ("light"輕淡/"normal"標準/"heavy"重鹹)
4. spice_level: 辣度 ("none"不辣/"mild"小辣/"medium"中辣/"spicy"大辣)
5. seasoning_preferences: 辛香料偏好
   - include_onion: 是否加蔥 (true/false)
   - include_ginger: 是否加薑 (true/false) 
   - include_garlic: 是否加蒜 (true/false)
   - include_cilantro: 是否加香菜 (true/false)
6. ingredients: 特定食材要求
7. special_instructions: 特殊烹飪方法
8. custom_notes: 客製化備註

解析規則：
- 日期：「今天」→當前日期，「明天」→明天，「後天」→後天，「週X/星期X」→計算日期
  * 對於「X月Y號」格式：如果該日期已過，推測為明年同月日期
  * 對於具體日期：優先選擇未來最近的日期
- 時間：「早上/上午X點」→AM，「下午/晚上X點」→PM，單獨「X點」且<12→假設下午
- 取餐：「外送/送到/配送」→外送，「自取/自己拿/去拿」→自取
- 調味：如未明確說明，使用預設值（標準鹹度、不辣）
- 辛香料：如未明確排除，預設為true

請以JSON格式回傳，包含三個部分：

{json_template}

請確保：
1. 所有已明確提及的資訊都要準確提取
2. 缺少的必要資訊要在missing_info中列出
3. 基於常理的假設要在assumptions_made中說明
4. 日期不能早於今天
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
        print(f"🤖 AI 原始響應：")
        print(ai_response)
        print()
        
        # 提取JSON部分
        json_start = ai_response.find('{')
        json_end = ai_response.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_content = ai_response[json_start:json_end]
            try:
                parsed_data = json.loads(json_content)
                return validate_and_clean_data(parsed_data, today)
            except json.JSONDecodeError as e:
                print(f"❌ JSON 解析失敗：{e}")
                print(f"JSON 內容：{json_content}")
                return {}
        else:
            print("❌ 無法找到有效的 JSON 格式")
            return {}
            
    except Exception as e:
        print(f"❌ OpenAI API 調用失敗：{e}")
        return {}

def validate_and_clean_data(data, today):
    """驗證和清理解析的數據"""
    cleaned_data = {
        "analysis_summary": data.get("analysis_summary", {}),
        "step1_data": {},
        "step2_data": {"dishes": []}
    }
    
    # 驗證 Step1 數據
    step1 = data.get("step1_data", {})
    
    # 驗證日期
    if step1.get('order_date'):
        try:
            parsed_date = datetime.strptime(step1['order_date'], '%Y-%m-%d')
            order_date = parsed_date.date()
            
            if order_date >= today.date():
                # 日期在今天或未來，直接使用
                cleaned_data['step1_data']['order_date'] = step1['order_date']
            else:
                # 日期已過，嘗試智能調整到明年同日期
                try:
                    next_year_date = order_date.replace(year=today.year + 1)
                    adjusted_date_str = next_year_date.strftime('%Y-%m-%d')
                    cleaned_data['step1_data']['order_date'] = adjusted_date_str
                    print(f"💡 智能調整：日期 {step1['order_date']} 已過，調整為明年 {adjusted_date_str}")
                except ValueError:
                    # 如果明年調整失敗（如2月29日閏年問題），忽略日期
                    print(f"⚠️  日期 {step1['order_date']} 已過且無法調整，請重新指定")
                    
        except ValueError:
            print(f"⚠️  無效日期格式：{step1['order_date']}")
    
    # 驗證時間
    if step1.get('order_time'):
        try:
            datetime.strptime(step1['order_time'], '%H:%M')
            cleaned_data['step1_data']['order_time'] = step1['order_time']
        except ValueError:
            print(f"⚠️  無效時間格式：{step1['order_time']}")
    
    # 驗證取餐方式
    if step1.get('pickup_method') in ['自取', '外送']:
        cleaned_data['step1_data']['pickup_method'] = step1['pickup_method']
    
    # 驗證地址
    if step1.get('address') and cleaned_data['step1_data'].get('pickup_method') == '外送':
        cleaned_data['step1_data']['address'] = step1['address'].strip()
    
    # 保留備註
    if step1.get('customer_notes'):
        cleaned_data['step1_data']['customer_notes'] = step1['customer_notes'].strip()
    
    # 驗證 Step2 數據
    step2 = data.get("step2_data", {})
    if step2.get("dishes"):
        for dish in step2["dishes"]:
            cleaned_dish = {}
            
            # 必填欄位
            if dish.get('dish_name'):
                cleaned_dish['dish_name'] = dish['dish_name'].strip()
            
            # 數量（預設1）
            cleaned_dish['quantity'] = max(1, dish.get('quantity', 1))
            
            # 調味等級驗證
            salt_levels = ['light', 'normal', 'heavy']
            spice_levels = ['none', 'mild', 'medium', 'spicy']
            
            cleaned_dish['salt_level'] = dish.get('salt_level', 'normal')
            if cleaned_dish['salt_level'] not in salt_levels:
                cleaned_dish['salt_level'] = 'normal'
                
            cleaned_dish['spice_level'] = dish.get('spice_level', 'none')
            if cleaned_dish['spice_level'] not in spice_levels:
                cleaned_dish['spice_level'] = 'none'
            
            # 辛香料偏好
            seasoning = dish.get('seasoning_preferences', {})
            cleaned_dish['seasoning_preferences'] = {
                'include_onion': seasoning.get('include_onion', True),
                'include_ginger': seasoning.get('include_ginger', True),
                'include_garlic': seasoning.get('include_garlic', True),
                'include_cilantro': seasoning.get('include_cilantro', True)
            }
            
            # 可選欄位
            for field in ['ingredients', 'special_instructions', 'custom_notes']:
                if dish.get(field):
                    cleaned_dish[field] = dish[field].strip()
            
            if cleaned_dish.get('dish_name'):  # 只保留有菜名的菜品
                cleaned_data['step2_data']['dishes'].append(cleaned_dish)
    
    return cleaned_data

def display_comprehensive_results(transcript, parsed_data):
    """顯示完整的處理結果"""
    print("\n" + "="*80)
    print("🍽️  語音轉訂單資訊完整分析結果")
    print("="*80)
    
    print(f"\n📝 原始語音內容：")
    print(f"   {transcript}")
    
    if not parsed_data:
        print("\n❌ 無法解析出有效的訂單資訊")
        return
    
    # 顯示分析摘要
    analysis = parsed_data.get('analysis_summary', {})
    if analysis:
        print(f"\n📊 分析摘要：")
        
        if analysis.get('provided_info'):
            print(f"   ✅ 已提取資訊：")
            for info in analysis['provided_info']:
                print(f"      • {info}")
        
        if analysis.get('missing_info'):
            print(f"   ⚠️  缺少資訊：")
            for info in analysis['missing_info']:
                print(f"      • {info}")
        
        if analysis.get('assumptions_made'):
            print(f"   💭 智能推測：")
            for assumption in analysis['assumptions_made']:
                print(f"      • {assumption}")
    
    # 顯示 Step 1 資料
    step1 = parsed_data.get('step1_data', {})
    if step1:
        print(f"\n📅 Step 1 - 預訂基本資訊：")
        if step1.get('order_date'):
            print(f"   📅 預約日期：{step1['order_date']}")
        if step1.get('order_time'):
            print(f"   ⏰ 預約時間：{step1['order_time']}")
        if step1.get('pickup_method'):
            print(f"   🚚 取餐方式：{step1['pickup_method']}")
        if step1.get('address'):
            print(f"   📍 外送地址：{step1['address']}")
        if step1.get('customer_notes'):
            print(f"   📝 客戶備註：{step1['customer_notes']}")
    
    # 顯示 Step 2 資料
    step2 = parsed_data.get('step2_data', {})
    if step2 and step2.get('dishes'):
        print(f"\n🍽️  Step 2 - 菜品詳細資訊：")
        for i, dish in enumerate(step2['dishes'], 1):
            print(f"   【第 {i} 道菜】")
            print(f"     🥘 菜品：{dish.get('dish_name', 'N/A')} × {dish.get('quantity', 1)} 份")
            print(f"     🧂 調味：鹹度 {dish.get('salt_level', 'normal')} | 辣度 {dish.get('spice_level', 'none')}")
            
            # 辛香料
            seasoning = dish.get('seasoning_preferences', {})
            seasonings = []
            if seasoning.get('include_onion'): seasonings.append('蔥')
            if seasoning.get('include_ginger'): seasonings.append('薑')
            if seasoning.get('include_garlic'): seasonings.append('蒜')
            if seasoning.get('include_cilantro'): seasonings.append('香菜')
            if seasonings:
                print(f"     🧄 辛香料：{', '.join(seasonings)}")
            
            if dish.get('ingredients'):
                print(f"     🥕 食材要求：{dish['ingredients']}")
            if dish.get('special_instructions'):
                print(f"     👨‍🍳 特殊作法：{dish['special_instructions']}")
            if dish.get('custom_notes'):
                print(f"     📝 客製備註：{dish['custom_notes']}")
            print()
    
    # 顯示完整性檢查
    print(f"📋 訂單完整性檢查：")
    
    # Step 1 必填項目檢查
    step1_required = ['order_date', 'order_time', 'pickup_method']
    step1_missing = [field for field in step1_required if not step1.get(field)]
    
    if step1.get('pickup_method') == '外送' and not step1.get('address'):
        step1_missing.append('address')
    
    if step1_missing:
        print(f"   ❌ Step 1 缺少：{', '.join(step1_missing)}")
    else:
        print(f"   ✅ Step 1 資訊完整")
    
    # Step 2 必填項目檢查
    if not step2.get('dishes') or len(step2['dishes']) == 0:
        print(f"   ❌ Step 2 缺少：至少需要一道菜品")
    else:
        print(f"   ✅ Step 2 包含 {len(step2['dishes'])} 道菜品")
    
    print(f"\n💾 完整 JSON 格式：")
    print(json.dumps(parsed_data, ensure_ascii=False, indent=2))
    
    print("\n" + "="*80)

def validate_for_database(parsed_data: dict) -> dict:
    """
    驗證解析的訂單資料是否完整，可以存入資料庫
    
    Args:
        parsed_data: 語音解析後的資料
        
    Returns:
        dict: 包含驗證結果、缺少欄位和口語化提醒
    """
    validation_result = {
        "ready_for_db": False,
        "missing_fields": [],
        "oral_questions": [],
        "critical_issues": []
    }
    
    step1_data = parsed_data.get('step1_data', {})
    step2_data = parsed_data.get('step2_data', {})
    
    # Step 1 必要欄位檢查
    step1_issues = []
    
    # 1. 預約日期 - 必填
    if not step1_data.get('order_date'):
        step1_issues.append('order_date')
        validation_result["oral_questions"].append("請問您要訂哪一天的餐呢？比如說明天、後天，或者具體的日期像是1月15號？")
    
    # 2. 預約時間 - 必填
    if not step1_data.get('order_time'):
        step1_issues.append('order_time')
        validation_result["oral_questions"].append("請問您希望什麼時候用餐呢？比如說中午12點、下午6點，或者晚餐時間？")
    
    # 3. 取餐方式 - 必填
    pickup_method = step1_data.get('pickup_method')
    if not pickup_method:
        step1_issues.append('pickup_method')
        validation_result["oral_questions"].append("請問您是要自己來拿，還是需要外送到府呢？")
    elif pickup_method == '外送':
        # 4. 外送地址 - 外送時必填
        if not step1_data.get('address'):
            step1_issues.append('address')
            validation_result["oral_questions"].append("請問您的外送地址是哪裡呢？請提供完整的地址，包含縣市、區域和街道門牌號碼。")
    
    # Step 2 必要欄位檢查
    step2_issues = []
    dishes = step2_data.get('dishes', [])
    
    # 1. 至少需要一道菜
    if not dishes or len(dishes) == 0:
        step2_issues.append('dishes')
        validation_result["oral_questions"].append("請問您想要訂什麼菜呢？可以告訴我菜名和需要幾人份。")
    else:
        # 2. 檢查每道菜的必要資訊
        for i, dish in enumerate(dishes, 1):
            dish_name = dish.get('dish_name', '這道菜')
            
            # 菜品名稱 - 必填
            if not dish.get('dish_name') or not dish.get('dish_name').strip():
                step2_issues.append(f'dish_{i}_name')
                validation_result["oral_questions"].append(f"請問您的第{i}道菜想要點什麼呢？")
            
            # 數量檢查 - 必須是正數
            quantity = dish.get('quantity', 1)
            if not isinstance(quantity, int) or quantity <= 0:
                step2_issues.append(f'dish_{i}_quantity')
                validation_result["oral_questions"].append(f"請問您的{dish_name}需要幾人份呢？")
            
            # 調味偏好檢查 - 只有在資料真的缺失時才詢問
            salt_level = dish.get('salt_level')
            spice_level = dish.get('spice_level')
            
            if salt_level is None:
                step2_issues.append(f'dish_{i}_salt')
                validation_result["oral_questions"].append(f"請問您的{dish_name}鹹度偏好？比如清淡一點、正常，還是重口味？")
            
            if spice_level is None:
                step2_issues.append(f'dish_{i}_spice')
                validation_result["oral_questions"].append(f"請問您的{dish_name}辣度偏好？不辣、微辣、中辣還是很辣？")
    
    # 整合所有問題
    validation_result["missing_fields"] = step1_issues + step2_issues
    validation_result["ready_for_db"] = len(validation_result["missing_fields"]) == 0
    
    # 設定關鍵問題
    if step1_issues:
        validation_result["critical_issues"].append("預訂基本資訊不完整")
    if step2_issues:
        validation_result["critical_issues"].append("菜品資訊不完整")
    
    return validation_result

def display_database_validation(validation_result: dict):
    """顯示資料庫驗證結果"""
    print("\n" + "🔍 " + "="*70)
    print("🗄️  資料庫完整性驗證")
    print("="*72)
    
    if validation_result["ready_for_db"]:
        print("✅ 太棒了！訂單資料完整，可以直接存入資料庫並送給廚師！")
        print("   📝 所有必要資訊都已齊全")
        print("   🚀 可以進行下一步流程")
    else:
        print("❌ 訂單資料還不完整，需要再補充一些資訊才能送出")
        
        if validation_result["critical_issues"]:
            print(f"   ⚠️  主要問題：{' | '.join(validation_result['critical_issues'])}")
        
        print(f"   📊 缺少欄位：{len(validation_result['missing_fields'])} 個")
    
    # 顯示口語化詢問
    if validation_result["oral_questions"]:
        print(f"\n💬 請您補充以下資訊：")
        for i, question in enumerate(validation_result["oral_questions"], 1):
            print(f"   {i}. {question}")
        
        print(f"\n💡 小提示：您可以重新錄音補充這些資訊，或者直接口頭告知這些詳細內容！")
    
    print("="*72)

def generate_completion_suggestions(parsed_data):
    """生成完成訂單的建議"""
    suggestions = []
    
    step1 = parsed_data.get('step1_data', {})
    step2 = parsed_data.get('step2_data', {})
    analysis = parsed_data.get('analysis_summary', {})
    
    # Step 1 必要欄位檢查
    if not step1.get('order_date'):
        suggestions.append("📅 建議補充：預約日期（例如：明天、下週五、1月15號）")
    
    if not step1.get('order_time'):
        suggestions.append("⏰ 建議補充：預約時間（例如：下午6點、18:30、晚餐時間）")
    
    if not step1.get('pickup_method'):
        suggestions.append("🚚 建議補充：取餐方式（自取或外送）")
    elif step1.get('pickup_method') == '外送' and not step1.get('address'):
        suggestions.append("📍 建議補充：外送地址（完整地址資訊）")
    
    # Step 2 必要欄位檢查
    if not step2.get('dishes') or len(step2['dishes']) == 0:
        suggestions.append("🍽️  建議補充：至少需要一道菜品（菜名和份數）")
        return suggestions
    
    # 檢查每道菜的必要資訊
    for i, dish in enumerate(step2['dishes'], 1):
        if not dish.get('dish_name'):
            suggestions.append(f"🥘 第{i}道菜建議補充：菜品名稱")
    
    # 基於分析摘要的智能建議
    missing_info = analysis.get('missing_info', [])
    
    # 過濾掉不必要的建議
    important_missing = []
    for item in missing_info:
        # 跳過自取時的地址要求
        if item == 'address' and step1.get('pickup_method') == '自取':
            continue
        # 跳過已有預設值的調味設定
        if item in ['salt_level', 'spice_level', 'quantity']:
            continue
        # 跳過可選的備註欄位
        if item in ['customer_notes', 'special_instructions', 'custom_notes']:
            continue
        # 跳過辛香料相關（通常有預設值）
        if 'include_' in item:
            continue
        important_missing.append(item)
    
    # 生成針對性的建議
    if 'ingredients' in important_missing and len(step2['dishes']) > 0:
        dishes_without_ingredients = [i+1 for i, dish in enumerate(step2['dishes']) 
                                    if not dish.get('ingredients')]
        if dishes_without_ingredients:
            dish_list = '、'.join([f"第{i}道菜" for i in dishes_without_ingredients])
            suggestions.append(f"🥕 建議補充：{dish_list}的特定食材要求（可選）")
    
    # 提供可選的改善建議
    optional_suggestions = []
    if not step1.get('customer_notes'):
        optional_suggestions.append("📝 可選補充：客戶備註（如：請提前通知、不要太晚）")
    
    # 檢查調味偏好是否明確
    unclear_seasoning_dishes = []
    for i, dish in enumerate(step2['dishes'], 1):
        dish_name = dish.get('dish_name', f'第{i}道菜')
        # 如果語音中沒有明確提到調味偏好，給出提醒
        if ('salt_level' in missing_info or 'spice_level' in missing_info):
            unclear_seasoning_dishes.append(dish_name)
    
    if unclear_seasoning_dishes:
        dish_list = '、'.join(unclear_seasoning_dishes[:2])  # 最多顯示兩道菜
        if len(unclear_seasoning_dishes) > 2:
            dish_list += f" 等{len(unclear_seasoning_dishes)}道菜"
        optional_suggestions.append(f"🌶️ 可選補充：{dish_list}的口味偏好（鹹淡、辣度）")
    
    # 添加可選建議
    if optional_suggestions and len(suggestions) < 3:  # 避免建議過多
        suggestions.extend(optional_suggestions[:2])
    
    return suggestions

def main():
    """主函數"""
    parser = argparse.ArgumentParser(
        description='語音轉訂單資訊工具 v2 - 專為新增訂單 Step1-2 設計',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用範例:
  python voice_to_order_v2.py demo.mp3
  python voice_to_order_v2.py recording.wav  
  python voice_to_order_v2.py --model large audio.m4a
  python voice_to_order_v2.py --help

特色功能:
  • 完整提取 Step 1-2 所有必要資訊
  • 智能識別缺少的必要資訊
  • 提供訂單完成度分析和建議
  • 支援複雜的菜品調味和客製化需求
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
        print(f"❌ 錯誤：音頻文件不存在 - {args.audio_file}")
        sys.exit(1)
    
    print("🎤 語音轉訂單資訊工具 v2")
    print(f"📁 音頻文件：{args.audio_file}")
    print(f"🤖 Whisper 模型：{args.model}")
    print("🎯 專為新增訂單 Step1-2 設計")
    print("-" * 60)
    
    try:
        # 載入配置
        api_key = load_config()
        
        # 步驟1：語音轉文字
        transcript = transcribe_audio(args.audio_file, args.model)
        if not transcript:
            sys.exit(1)
        
        # 步驟2：AI 解析完整訂單資訊
        parsed_data = parse_complete_order_info(transcript, api_key)
        
        # 步驟3：顯示完整結果
        display_comprehensive_results(transcript, parsed_data)
        
        # 步驟4：資料庫完整性驗證
        validation_result = validate_for_database(parsed_data)
        display_database_validation(validation_result)
        
        # 步驟5：生成完成建議（如果資料庫驗證通過，則不顯示建議）
        if not validation_result["ready_for_db"]:
            suggestions = generate_completion_suggestions(parsed_data)
            if suggestions:
                print("\n💡 完成訂單的建議：")
                for suggestion in suggestions:
                    print(f"   {suggestion}")
        else:
            print("\n🎉 恭喜！訂單可以直接送給廚師了！")
        
        # 步驟6：儲存結果
        output_file = f"complete_order_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        result = {
            "timestamp": datetime.now().isoformat(),
            "audio_file": args.audio_file,
            "whisper_model": args.model,
            "transcript": transcript,
            "parsed_data": parsed_data,
            "database_validation": validation_result,
            "completion_suggestions": generate_completion_suggestions(parsed_data) if not validation_result["ready_for_db"] else []
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 完整結果已儲存至：{output_file}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  用戶中斷程序")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 程序執行失敗：{e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
