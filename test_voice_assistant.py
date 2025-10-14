#!/usr/bin/env python3
"""
語音AI助手功能測試腳本
"""

import os
import sys
import asyncio
import tempfile
from pathlib import Path

# 添加項目根目錄到Python路徑
sys.path.append(str(Path(__file__).parent))

def test_dependencies():
    """測試必要的依賴項是否已安裝"""
    print("🔍 檢查依賴項...")
    
    try:
        import openai
        print("✅ OpenAI 已安裝")
    except ImportError:
        print("❌ OpenAI 未安裝，請運行: pip install openai")
        return False
    
    try:
        import whisper
        print("✅ Whisper 已安裝")
    except ImportError:
        print("❌ Whisper 未安裝，請運行: pip install openai-whisper")
        return False
    
    try:
        from fastapi import FastAPI
        print("✅ FastAPI 已安裝")
    except ImportError:
        print("❌ FastAPI 未安裝")
        return False
    
    return True

def test_environment_variables():
    """測試環境變數設定"""
    print("\n🔧 檢查環境變數...")
    
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        print("✅ OPENAI_API_KEY 已設定")
        return True
    else:
        print("❌ OPENAI_API_KEY 未設定")
        print("請在 .env 文件中設定 OPENAI_API_KEY=your_api_key_here")
        return False

def test_openai_connection():
    """測試OpenAI API連線"""
    print("\n🌐 測試OpenAI API連線...")
    
    try:
        import openai
        openai.api_key = os.getenv("OPENAI_API_KEY")
        
        # 簡單的API測試
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10
        )
        
        print("✅ OpenAI API 連線成功")
        return True
        
    except Exception as e:
        print(f"❌ OpenAI API 連線失敗: {e}")
        return False

def test_whisper_model():
    """測試Whisper模型載入"""
    print("\n🎤 測試Whisper模型...")
    
    try:
        import whisper
        # 載入base模型（較小，適合測試）
        model = whisper.load_model("base")
        print("✅ Whisper 模型載入成功")
        return True
        
    except Exception as e:
        print(f"❌ Whisper 模型載入失敗: {e}")
        return False

def test_database_models():
    """測試資料庫模型"""
    print("\n🗄️ 檢查資料庫模型...")
    
    try:
        from models.order import Order, OrderDish, DeliveryMethod, SpiceLevel, SaltLevel
        from models.user import User
        print("✅ 資料庫模型載入成功")
        return True
        
    except Exception as e:
        print(f"❌ 資料庫模型載入失敗: {e}")
        return False

def test_api_routes():
    """測試API路由"""
    print("\n🛣️ 檢查API路由...")
    
    try:
        from routers.customer import router
        print("✅ 客戶路由載入成功")
        return True
        
    except Exception as e:
        print(f"❌ 客戶路由載入失敗: {e}")
        return False

def main():
    """主測試函數"""
    print("🚀 語音AI助手功能測試")
    print("=" * 50)
    
    tests = [
        test_dependencies,
        test_environment_variables,
        test_database_models,
        test_api_routes,
        test_openai_connection,
        test_whisper_model,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ 測試失敗: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 測試結果: {passed}/{total} 通過")
    
    if passed == total:
        print("🎉 所有測試通過！語音AI助手功能已準備就緒。")
        print("\n📝 使用說明:")
        print("1. 啟動應用程式: uvicorn main:app --reload")
        print("2. 訪問: http://localhost:8000")
        print("3. 登入後選擇廚師，然後選擇'語音AI助手'")
        print("4. 開始使用語音創建訂單！")
    else:
        print("⚠️ 部分測試失敗，請檢查上述錯誤並修復。")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
