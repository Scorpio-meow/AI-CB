#!/usr/bin/env python3
"""
配置文件驗證腳本
檢查 .env 配置的有效性和優化建議
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# 添加專案根目錄到 Python 路徑
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv

# 載入環境變數
env_path = backend_dir / ".env"
load_dotenv(env_path)


class ConfigValidator:
    """配置驗證器"""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.suggestions: List[str] = []
        
    def validate_all(self) -> Tuple[bool, List[str], List[str], List[str]]:
        """執行所有驗證"""
        print("🔍 開始驗證配置文件...\n")
        
        self.validate_llm_config()
        self.validate_security_config()
        self.validate_database_config()
        self.validate_rag_config()
        self.validate_cache_config()
        self.validate_performance_config()
        
        return (
            len(self.errors) == 0,
            self.errors,
            self.warnings,
            self.suggestions
        )
    
    def validate_llm_config(self):
        """驗證 LLM 配置"""
        print("📡 驗證 LLM 配置...")
        
        model_name = os.getenv("MODEL_NAME")
        llm_api_base = os.getenv("LLM_API_BASE")
        llm_timeout = int(os.getenv("LLM_TIMEOUT", 120))
        max_context = int(os.getenv("MAX_CONTEXT_LENGTH", 4000))
        
        if not model_name:
            self.errors.append("MODEL_NAME 未設定")
        
        if not llm_api_base:
            self.errors.append("LLM_API_BASE 未設定")
        elif not llm_api_base.startswith("http"):
            self.errors.append("LLM_API_BASE 必須是有效的 HTTP/HTTPS URL")
        
        if llm_timeout < 30:
            self.warnings.append(f"LLM_TIMEOUT ({llm_timeout}s) 過短，建議至少 60s")
        elif llm_timeout > 180:
            self.warnings.append(f"LLM_TIMEOUT ({llm_timeout}s) 過長，建議不超過 120s")
        
        if max_context > 8000:
            self.warnings.append(f"MAX_CONTEXT_LENGTH ({max_context}) 過大，可能影響 LLM 效能")
        
        print(f"  ✓ MODEL_NAME: {model_name}")
        print(f"  ✓ LLM_TIMEOUT: {llm_timeout}s")
        print(f"  ✓ MAX_CONTEXT_LENGTH: {max_context}\n")
    
    def validate_security_config(self):
        """驗證安全配置"""
        print("🔐 驗證安全配置...")
        
        admin_api_key = os.getenv("ADMIN_API_KEY")
        jwt_secret = os.getenv("JWT_SECRET_KEY")
        jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        
        if not admin_api_key:
            self.errors.append("ADMIN_API_KEY 未設定")
        elif len(admin_api_key) < 32:
            self.warnings.append(f"ADMIN_API_KEY 長度 ({len(admin_api_key)}) 不足 32 字符")
        
        if not jwt_secret:
            self.errors.append("JWT_SECRET_KEY 未設定")
        elif len(jwt_secret) < 64:
            self.warnings.append(f"JWT_SECRET_KEY 長度 ({len(jwt_secret)}) 不足 64 字符")
        
        if jwt_algorithm not in ["HS256", "HS384", "HS512"]:
            self.warnings.append(f"JWT_ALGORITHM ({jwt_algorithm}) 不常見，建議使用 HS256")
        
        print(f"  ✓ ADMIN_API_KEY: {'*' * 10} (長度: {len(admin_api_key) if admin_api_key else 0})")
        print(f"  ✓ JWT_SECRET_KEY: {'*' * 10} (長度: {len(jwt_secret) if jwt_secret else 0})")
        print(f"  ✓ JWT_ALGORITHM: {jwt_algorithm}\n")
    
    def validate_database_config(self):
        """驗證資料庫配置"""
        print("🗄️  驗證資料庫配置...")
        
        db_url = os.getenv("DATABASE_URL")
        pool_size = int(os.getenv("DB_POOL_SIZE", 5))
        max_overflow = int(os.getenv("DB_MAX_OVERFLOW", 10))
        pool_recycle = int(os.getenv("DB_POOL_RECYCLE", 3600))
        
        if not db_url:
            self.errors.append("DATABASE_URL 未設定")
        
        # 連接池配置建議
        if pool_size > 50:
            self.warnings.append(f"DB_POOL_SIZE ({pool_size}) 過大，可能浪費資源")
        elif pool_size < 5:
            self.warnings.append(f"DB_POOL_SIZE ({pool_size}) 過小，可能導致連接等待")
        
        if max_overflow > pool_size * 3:
            self.warnings.append(f"DB_MAX_OVERFLOW ({max_overflow}) 過大，建議為 pool_size 的 1-2 倍")
        
        if pool_recycle < 600:
            self.warnings.append(f"DB_POOL_RECYCLE ({pool_recycle}s) 過短，可能頻繁重建連接")
        
        # SQLite 特殊檢查
        if db_url and db_url.startswith("sqlite"):
            if pool_size > 10:
                self.suggestions.append("SQLite 並發能力有限，生產環境建議使用 PostgreSQL")
        
        print(f"  ✓ DB_POOL_SIZE: {pool_size}")
        print(f"  ✓ DB_MAX_OVERFLOW: {max_overflow}")
        print(f"  ✓ DB_POOL_RECYCLE: {pool_recycle}s\n")
    
    def validate_rag_config(self):
        """驗證 RAG 配置"""
        print("🧠 驗證 RAG 配置...")
        
        top_k = int(os.getenv("TOP_K", 50))
        rerank_top_k = int(os.getenv("RERANK_TOP_K", 80))
        final_k = int(os.getenv("FINAL_K", 10))
        similarity_threshold = float(os.getenv("SIMILARITY_THRESHOLD", 0.25))
        chunk_size = int(os.getenv("CHUNK_SIZE", 300))
        chunk_overlap = int(os.getenv("CHUNK_OVERLAP", 100))
        
        # 邏輯檢查
        if rerank_top_k < top_k:
            self.errors.append(f"RERANK_TOP_K ({rerank_top_k}) 應該 >= TOP_K ({top_k})")
        
        if final_k > rerank_top_k:
            self.errors.append(f"FINAL_K ({final_k}) 應該 <= RERANK_TOP_K ({rerank_top_k})")
        
        # 效能建議
        if top_k > 50:
            self.suggestions.append(f"TOP_K ({top_k}) 較大，降低可提升檢索速度")
        
        if final_k > 15:
            self.suggestions.append(f"FINAL_K ({final_k}) 較大，可能影響 LLM 效能")
        
        if similarity_threshold < 0.2:
            self.warnings.append(f"SIMILARITY_THRESHOLD ({similarity_threshold}) 過低，可能引入噪音")
        elif similarity_threshold > 0.5:
            self.warnings.append(f"SIMILARITY_THRESHOLD ({similarity_threshold}) 過高，可能過濾有用資訊")
        
        if chunk_overlap >= chunk_size:
            self.errors.append(f"CHUNK_OVERLAP ({chunk_overlap}) 應該 < CHUNK_SIZE ({chunk_size})")
        
        print(f"  ✓ TOP_K: {top_k}")
        print(f"  ✓ RERANK_TOP_K: {rerank_top_k}")
        print(f"  ✓ FINAL_K: {final_k}")
        print(f"  ✓ SIMILARITY_THRESHOLD: {similarity_threshold}")
        print(f"  ✓ CHUNK_SIZE: {chunk_size}")
        print(f"  ✓ CHUNK_OVERLAP: {chunk_overlap}\n")
    
    def validate_cache_config(self):
        """驗證快取配置"""
        print("💾 驗證快取配置...")
        
        cache_enabled = os.getenv("CACHE_ENABLED", "true").lower() == "true"
        cache_default_ttl = int(os.getenv("CACHE_DEFAULT_TTL", 300))
        cache_max_size = int(os.getenv("CACHE_MAX_SIZE", 1000))
        
        if not cache_enabled:
            self.warnings.append("CACHE_ENABLED 未啟用，可能影響效能")
        
        if cache_default_ttl < 60:
            self.suggestions.append(f"CACHE_DEFAULT_TTL ({cache_default_ttl}s) 較短，快取效果有限")
        elif cache_default_ttl > 1800:
            self.warnings.append(f"CACHE_DEFAULT_TTL ({cache_default_ttl}s) 過長，可能返回過時資料")
        
        if cache_max_size < 100:
            self.suggestions.append(f"CACHE_MAX_SIZE ({cache_max_size}) 較小，快取容量有限")
        elif cache_max_size > 5000:
            self.warnings.append(f"CACHE_MAX_SIZE ({cache_max_size}) 過大，可能佔用過多記憶體")
        
        print(f"  ✓ CACHE_ENABLED: {cache_enabled}")
        print(f"  ✓ CACHE_DEFAULT_TTL: {cache_default_ttl}s")
        print(f"  ✓ CACHE_MAX_SIZE: {cache_max_size}\n")
    
    def validate_performance_config(self):
        """驗證效能配置"""
        print("⚡ 驗證效能配置...")
        
        uvicorn_workers = int(os.getenv("UVICORN_WORKERS", 4))
        rate_limit_enabled = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
        rate_limit_per_min = int(os.getenv("RATE_LIMIT_PER_MINUTE", 100))
        
        # Workers 數量建議
        import multiprocessing
        cpu_count = multiprocessing.cpu_count()
        
        if uvicorn_workers > cpu_count * 2:
            self.warnings.append(
                f"UVICORN_WORKERS ({uvicorn_workers}) > CPU核心數*2 ({cpu_count*2})，"
                f"可能過度佔用資源"
            )
        elif uvicorn_workers < 2 and cpu_count >= 2:
            self.suggestions.append(f"UVICORN_WORKERS ({uvicorn_workers}) 較少，可增加至 {cpu_count}")
        
        if not rate_limit_enabled:
            self.warnings.append("RATE_LIMIT_ENABLED 未啟用，無法防止 API 濫用")
        
        print(f"  ✓ CPU 核心數: {cpu_count}")
        print(f"  ✓ UVICORN_WORKERS: {uvicorn_workers}")
        print(f"  ✓ RATE_LIMIT_ENABLED: {rate_limit_enabled}")
        print(f"  ✓ RATE_LIMIT_PER_MINUTE: {rate_limit_per_min}\n")


def print_results(is_valid: bool, errors: List[str], warnings: List[str], suggestions: List[str]):
    """列印驗證結果"""
    print("=" * 80)
    print("📊 驗證結果摘要")
    print("=" * 80)
    
    if is_valid and not warnings and not suggestions:
        print("✅ 配置文件完全正確，無任何問題！\n")
        return
    
    if errors:
        print(f"\n❌ 錯誤 ({len(errors)} 項) - 必須修復:")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")
    
    if warnings:
        print(f"\n⚠️  警告 ({len(warnings)} 項) - 建議修復:")
        for i, warning in enumerate(warnings, 1):
            print(f"  {i}. {warning}")
    
    if suggestions:
        print(f"\n💡 建議 ({len(suggestions)} 項) - 可選優化:")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {i}. {suggestion}")
    
    print("\n" + "=" * 80)
    
    if is_valid:
        print("✅ 配置文件有效，但有一些建議可改進")
    else:
        print("❌ 配置文件有錯誤，請修復後再啟動服務")
    
    print("=" * 80 + "\n")


def main():
    """主函數"""
    validator = ConfigValidator()
    is_valid, errors, warnings, suggestions = validator.validate_all()
    print_results(is_valid, errors, warnings, suggestions)
    
    # 返回狀態碼
    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()
