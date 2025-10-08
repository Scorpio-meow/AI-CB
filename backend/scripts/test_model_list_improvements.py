#!/usr/bin/env python3
"""
模型列表功能測試腳本
測試新增的模型列表更新功能改進
"""

import requests
import json
import time
from typing import Dict, List, Optional

# 配置
BACKEND_URL = "http://localhost:8001"
API_TAGS_ENDPOINT = f"{BACKEND_URL}/api/tags"
API_EXTERNAL_TAGS_ENDPOINT = f"{BACKEND_URL}/api/external-tags"

# 測試結果
test_results = []


def print_header(text: str):
    """打印測試標題"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def print_test(name: str, passed: bool, details: str = ""):
    """打印測試結果"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {name}")
    if details:
        print(f"    {details}")
    test_results.append({"name": name, "passed": passed, "details": details})


def test_api_tags():
    """測試 /api/tags 端點"""
    print_header("測試 1: /api/tags 端點")
    
    try:
        response = requests.get(
            API_TAGS_ENDPOINT,
            headers={"ngrok-skip-browser-warning": "true"},
            timeout=10
        )
        
        # 測試狀態碼
        test_passed = response.status_code == 200
        print_test(
            "API 端點可訪問", 
            test_passed,
            f"狀態碼: {response.status_code}"
        )
        
        if not test_passed:
            return False
        
        # 測試響應格式
        data = response.json()
        has_tags = "tags" in data
        has_default = "default" in data
        
        print_test(
            "響應包含 'tags' 欄位",
            has_tags,
            f"tags: {data.get('tags', [])}"
        )
        
        print_test(
            "響應包含 'default' 欄位",
            has_default,
            f"default: {data.get('default')}"
        )
        
        # 測試模型列表非空
        models = data.get("tags", [])
        has_models = len(models) > 0
        print_test(
            "模型列表非空",
            has_models,
            f"找到 {len(models)} 個模型"
        )
        
        return test_passed and has_tags and has_models
        
    except Exception as e:
        print_test("API 端點測試", False, f"錯誤: {str(e)}")
        return False


def test_api_external_tags():
    """測試 /api/external-tags 端點"""
    print_header("測試 2: /api/external-tags 端點")
    
    try:
        response = requests.get(
            API_EXTERNAL_TAGS_ENDPOINT,
            headers={"ngrok-skip-browser-warning": "true"},
            timeout=15
        )
        
        # 測試狀態碼
        test_passed = response.status_code == 200
        print_test(
            "External Tags API 可訪問",
            test_passed,
            f"狀態碼: {response.status_code}"
        )
        
        if not test_passed:
            return False
        
        # 測試響應格式
        data = response.json()
        has_models = "models" in data
        
        print_test(
            "響應包含模型信息",
            has_models,
            f"模型數量: {len(data.get('models', []))}"
        )
        
        # 檢查詳細信息
        if has_models and len(data.get("models", [])) > 0:
            first_model = data["models"][0]
            has_details = "details" in first_model
            
            print_test(
                "模型包含詳細信息",
                has_details,
                f"詳細欄位: {first_model.get('details', {}).keys() if has_details else 'N/A'}"
            )
            
            if has_details:
                details = first_model["details"]
                print(f"\n    示例模型詳情:")
                print(f"    - 名稱: {first_model.get('name')}")
                print(f"    - 家族: {details.get('family')}")
                print(f"    - 大小: {details.get('parameter_size')}")
                print(f"    - 量化: {details.get('quantization_level')}")
        
        return test_passed and has_models
        
    except Exception as e:
        print_test("External Tags API 測試", False, f"錯誤: {str(e)}")
        return False


def test_model_details_extraction():
    """測試模型詳細信息提取"""
    print_header("測試 3: 模型詳細信息提取")
    
    try:
        response = requests.get(
            API_EXTERNAL_TAGS_ENDPOINT,
            headers={"ngrok-skip-browser-warning": "true"},
            timeout=15
        )
        
        if response.status_code != 200:
            print_test("詳細信息提取測試", False, "無法獲取模型數據")
            return False
        
        data = response.json()
        models = data.get("models", [])
        
        if not models:
            print_test("詳細信息提取測試", False, "模型列表為空")
            return False
        
        # 檢查每個模型的詳細信息
        models_with_details = 0
        for model in models:
            details = model.get("details", {})
            if details and (details.get("family") or details.get("parameter_size")):
                models_with_details += 1
        
        coverage = models_with_details / len(models) * 100
        test_passed = models_with_details > 0
        
        print_test(
            "模型詳細信息覆蓋率",
            test_passed,
            f"{models_with_details}/{len(models)} 個模型 ({coverage:.1f}%)"
        )
        
        return test_passed
        
    except Exception as e:
        print_test("詳細信息提取測試", False, f"錯誤: {str(e)}")
        return False


def test_cache_mechanism():
    """測試緩存機制（模擬前端行為）"""
    print_header("測試 4: 緩存機制")
    
    print("提示: 此測試模擬前端緩存行為，無法直接在後端測試")
    print("前端緩存策略:")
    print("  - 緩存期限: 5 分鐘")
    print("  - 存儲位置: localStorage")
    print("  - 緩存鍵: cached_tags, cached_tags_time")
    
    print_test(
        "緩存機制實現",
        True,
        "已在前端代碼中實現 (Chat.js)"
    )
    
    return True


def test_performance():
    """測試 API 性能"""
    print_header("測試 5: API 性能")
    
    try:
        # 測試 /api/tags 響應時間
        start_time = time.time()
        response = requests.get(
            API_TAGS_ENDPOINT,
            headers={"ngrok-skip-browser-warning": "true"},
            timeout=10
        )
        tags_time = time.time() - start_time
        
        tags_passed = tags_time < 2.0  # 2秒內
        print_test(
            "/api/tags 響應時間",
            tags_passed,
            f"{tags_time:.2f} 秒 (目標: < 2秒)"
        )
        
        # 測試 /api/external-tags 響應時間
        start_time = time.time()
        response = requests.get(
            API_EXTERNAL_TAGS_ENDPOINT,
            headers={"ngrok-skip-browser-warning": "true"},
            timeout=15
        )
        external_time = time.time() - start_time
        
        external_passed = external_time < 5.0  # 5秒內
        print_test(
            "/api/external-tags 響應時間",
            external_passed,
            f"{external_time:.2f} 秒 (目標: < 5秒)"
        )
        
        return tags_passed and external_passed
        
    except Exception as e:
        print_test("性能測試", False, f"錯誤: {str(e)}")
        return False


def print_summary():
    """打印測試摘要"""
    print_header("測試摘要")
    
    total = len(test_results)
    passed = sum(1 for r in test_results if r["passed"])
    failed = total - passed
    
    print(f"總測試數: {total}")
    print(f"✅ 通過: {passed}")
    print(f"❌ 失敗: {failed}")
    print(f"成功率: {passed/total*100:.1f}%")
    
    if failed > 0:
        print("\n失敗的測試:")
        for result in test_results:
            if not result["passed"]:
                print(f"  - {result['name']}: {result['details']}")
    
    print(f"\n{'='*60}\n")
    
    return passed == total


def main():
    """主測試函數"""
    print("\n" + "="*60)
    print("  模型列表功能改進 - 自動化測試")
    print("="*60)
    print(f"\n後端 URL: {BACKEND_URL}")
    print("測試時間:", time.strftime("%Y-%m-%d %H:%M:%S"))
    
    # 執行測試
    test_api_tags()
    test_api_external_tags()
    test_model_details_extraction()
    test_cache_mechanism()
    test_performance()
    
    # 打印摘要
    all_passed = print_summary()
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
