"""
效能基準測試腳本
用於測試和監控系統效能
"""
import asyncio
import time
import statistics
import requests
from typing import List, Dict, Any
import os
from dotenv import load_dotenv

load_dotenv()

# 測試配置
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8001")
TEST_TOKEN = None  # 需要先登入獲取 token

class PerformanceTester:
    """效能測試器"""
    
    def __init__(self, api_base: str, token: str = None):
        self.api_base = api_base
        self.headers = {}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
    
    def test_endpoint(self, endpoint: str, method: str = "GET", 
                     data: dict = None, iterations: int = 10) -> Dict[str, Any]:
        """測試單個端點的效能"""
        times = []
        errors = 0
        
        print(f"\n測試 {method} {endpoint} (執行 {iterations} 次)...")
        
        for i in range(iterations):
            start = time.time()
            try:
                if method == "GET":
                    response = requests.get(
                        f"{self.api_base}{endpoint}",
                        headers=self.headers,
                        timeout=30
                    )
                elif method == "POST":
                    response = requests.post(
                        f"{self.api_base}{endpoint}",
                        json=data,
                        headers=self.headers,
                        timeout=30
                    )
                
                elapsed = time.time() - start
                
                if response.status_code == 200:
                    times.append(elapsed)
                    print(f"  請求 {i+1}: {elapsed:.3f}s ✓")
                else:
                    errors += 1
                    print(f"  請求 {i+1}: 錯誤 {response.status_code} ✗")
                    
            except Exception as e:
                errors += 1
                print(f"  請求 {i+1}: 異常 {str(e)} ✗")
        
        if times:
            return {
                "endpoint": endpoint,
                "method": method,
                "iterations": iterations,
                "success": len(times),
                "errors": errors,
                "min": min(times),
                "max": max(times),
                "mean": statistics.mean(times),
                "median": statistics.median(times),
                "stdev": statistics.stdev(times) if len(times) > 1 else 0
            }
        else:
            return {
                "endpoint": endpoint,
                "errors": errors,
                "success": 0
            }
    
    def print_results(self, results: List[Dict[str, Any]]):
        """打印測試結果"""
        print("\n" + "="*80)
        print("效能測試結果摘要")
        print("="*80)
        
        for result in results:
            if result.get("success", 0) > 0:
                print(f"\n端點: {result['method']} {result['endpoint']}")
                print(f"  成功率: {result['success']}/{result['iterations']} "
                      f"({result['success']/result['iterations']*100:.1f}%)")
                print(f"  最小時間: {result['min']*1000:.0f}ms")
                print(f"  最大時間: {result['max']*1000:.0f}ms")
                print(f"  平均時間: {result['mean']*1000:.0f}ms")
                print(f"  中位數: {result['median']*1000:.0f}ms")
                print(f"  標準差: {result['stdev']*1000:.0f}ms")
                
                # 效能評級
                avg_ms = result['mean'] * 1000
                if avg_ms < 100:
                    grade = "優秀 🌟"
                elif avg_ms < 300:
                    grade = "良好 ✓"
                elif avg_ms < 1000:
                    grade = "普通 ~"
                else:
                    grade = "需改進 ⚠"
                
                print(f"  評級: {grade}")
            else:
                print(f"\n端點: {result['endpoint']} - 所有請求失敗 ✗")

def run_basic_tests():
    """執行基本效能測試"""
    tester = PerformanceTester(API_BASE)
    
    results = []
    
    # 測試健康檢查端點
    results.append(tester.test_endpoint("/health", iterations=20))
    
    # 測試公開端點
    results.append(tester.test_endpoint("/api/chat/models", iterations=15))
    
    # 如果有認證 token，測試需要認證的端點
    # results.append(tester.test_endpoint("/api/admin/statistics", iterations=10))
    
    tester.print_results(results)
    
    return results

def run_load_test(endpoint: str, num_concurrent: int = 10, requests_per_client: int = 5):
    """執行並發負載測試"""
    import concurrent.futures
    
    print(f"\n{'='*80}")
    print(f"負載測試: {num_concurrent} 個並發客戶端，每個發送 {requests_per_client} 個請求")
    print(f"端點: {endpoint}")
    print(f"{'='*80}")
    
    tester = PerformanceTester(API_BASE)
    
    def client_task(client_id: int):
        """單個客戶端任務"""
        times = []
        for i in range(requests_per_client):
            start = time.time()
            try:
                response = requests.get(
                    f"{API_BASE}{endpoint}",
                    timeout=30
                )
                elapsed = time.time() - start
                times.append(elapsed)
            except Exception as e:
                print(f"客戶端 {client_id} 請求 {i+1} 失敗: {e}")
        return times
    
    # 執行並發測試
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
        futures = [executor.submit(client_task, i) for i in range(num_concurrent)]
        all_times = []
        
        for future in concurrent.futures.as_completed(futures):
            try:
                times = future.result()
                all_times.extend(times)
            except Exception as e:
                print(f"客戶端任務失敗: {e}")
    
    total_time = time.time() - start_time
    
    # 計算統計
    if all_times:
        total_requests = len(all_times)
        successful = sum(1 for t in all_times if t > 0)
        
        print(f"\n負載測試結果:")
        print(f"  總請求數: {total_requests}")
        print(f"  成功請求: {successful}")
        print(f"  總時間: {total_time:.2f}s")
        print(f"  吞吐量: {total_requests/total_time:.2f} 請求/秒")
        print(f"  平均響應時間: {statistics.mean(all_times)*1000:.0f}ms")
        print(f"  中位數響應時間: {statistics.median(all_times)*1000:.0f}ms")
        print(f"  95th 百分位: {sorted(all_times)[int(len(all_times)*0.95)]*1000:.0f}ms")
        print(f"  99th 百分位: {sorted(all_times)[int(len(all_times)*0.99)]*1000:.0f}ms")

def run_database_query_test():
    """測試資料庫查詢效能"""
    print(f"\n{'='*80}")
    print("資料庫查詢效能測試")
    print(f"{'='*80}")
    
    # 這裡需要直接連接資料庫進行測試
    # 或通過 API 端點間接測試
    
    tester = PerformanceTester(API_BASE)
    
    # 測試統計端點（包含多個資料庫查詢）
    print("\n測試管理後台統計查詢...")
    # 需要管理員 token
    # result = tester.test_endpoint("/api/admin/statistics", iterations=5)
    
    print("\n測試對話列表查詢...")
    # 需要用戶 token
    # result = tester.test_endpoint("/api/chat/conversations", iterations=10)
    
    print("注意: 需要有效的認證 token 才能執行此測試")

def main():
    """主測試函數"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║          ChatBot 效能基準測試工具                            ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    print(f"測試目標: {API_BASE}")
    print(f"請確保後端服務正在運行\n")
    
    # 基本效能測試
    print("\n[1] 執行基本效能測試...")
    run_basic_tests()
    
    # 負載測試
    print("\n[2] 執行負載測試...")
    run_load_test("/health", num_concurrent=20, requests_per_client=10)
    
    # 資料庫查詢測試
    print("\n[3] 資料庫查詢效能測試...")
    run_database_query_test()
    
    print(f"\n{'='*80}")
    print("測試完成!")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
