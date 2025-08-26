#!/usr/bin/env python3
"""
Redis 安裝和配置腳本 for Windows

這個腳本會：
1. 檢查 Redis 是否已安裝
2. 提供 Redis 安裝指南
3. 嘗試啟動 Redis 服務器
4. 測試 Redis 連接
"""

import subprocess
import sys
import time
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_redis_installed():
    """檢查 Redis 是否已安裝"""
    try:
        result = subprocess.run(['redis-server', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            logger.info(f"✅ Redis 已安裝: {result.stdout.strip()}")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        logger.info("❌ Redis 未安裝")
        return False

def check_redis_running():
    """檢查 Redis 是否正在運行"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        logger.info("✅ Redis 服務器正在運行")
        return True
    except Exception as e:
        logger.info(f"❌ Redis 服務器未運行: {e}")
        return False

def install_redis_guide():
    """提供 Redis 安裝指南"""
    logger.info("=" * 60)
    logger.info("📋 Windows Redis 安裝指南")
    logger.info("=" * 60)
    print("""
方法1: 使用 Windows Subsystem for Linux (WSL) - 推薦
1. 安裝 WSL2: 
   wsl --install
2. 在 WSL 中安裝 Redis:
   sudo apt update
   sudo apt install redis-server
3. 啟動 Redis:
   sudo service redis-server start

方法2: 使用 Docker - 簡單快速
1. 安裝 Docker Desktop for Windows
2. 運行 Redis 容器:
   docker run -d -p 6379:6379 --name redis redis:latest

方法3: 使用預編譯的 Windows 版本
1. 下載: https://github.com/tporadowski/redis/releases
2. 解壓並運行 redis-server.exe

方法4: 使用 Chocolatey
1. 安裝 Chocolatey (如果還沒有)
2. 運行: choco install redis-64

推薦使用 Docker 方法，最簡單且可靠。
""")

def start_redis_docker():
    """使用 Docker 啟動 Redis"""
    logger.info("嘗試使用 Docker 啟動 Redis...")
    
    try:
        # 檢查 Docker 是否可用
        result = subprocess.run(['docker', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            logger.error("Docker 未安裝或不可用")
            return False
        
        logger.info(f"Docker 可用: {result.stdout.strip()}")
        
        # 停止並移除現有的 Redis 容器（如果存在）
        subprocess.run(['docker', 'stop', 'redis'], 
                      capture_output=True, timeout=10)
        subprocess.run(['docker', 'rm', 'redis'], 
                      capture_output=True, timeout=10)
        
        # 啟動新的 Redis 容器
        logger.info("啟動 Redis Docker 容器...")
        result = subprocess.run([
            'docker', 'run', '-d', 
            '-p', '6379:6379', 
            '--name', 'redis', 
            'redis:latest'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            logger.info("✅ Redis Docker 容器已啟動")
            
            # 等待 Redis 啟動
            logger.info("等待 Redis 服務啟動...")
            for i in range(10):
                time.sleep(1)
                if check_redis_running():
                    return True
                logger.info(f"等待中... ({i+1}/10)")
            
            logger.error("Redis 啟動超時")
            return False
        else:
            logger.error(f"Docker 啟動失敗: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Docker 啟動 Redis 失敗: {e}")
        return False

def test_redis_connection():
    """測試 Redis 連接並顯示基本信息"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        
        # 測試基本操作
        r.set('test_key', 'test_value')
        value = r.get('test_key')
        r.delete('test_key')
        
        # 獲取 Redis 信息
        info = r.info()
        
        logger.info("✅ Redis 連接測試成功")
        logger.info(f"Redis 版本: {info.get('redis_version', 'unknown')}")
        logger.info(f"使用記憶體: {info.get('used_memory_human', 'unknown')}")
        logger.info(f"連接數: {info.get('connected_clients', 'unknown')}")
        
        return True
    except Exception as e:
        logger.error(f"Redis 連接測試失敗: {e}")
        return False

def main():
    """主函數"""
    logger.info("🔍 檢查 Redis 狀態...")
    
    # 檢查 Redis 是否正在運行
    if check_redis_running():
        logger.info("🎉 Redis 已經在運行中！")
        test_redis_connection()
        return True
    
    # 檢查 Redis 是否已安裝
    if not check_redis_installed():
        install_redis_guide()
        logger.info("\n請按照上述指南安裝 Redis，然後重新運行此腳本。")
        return False
    
    # 嘗試使用 Docker 啟動 Redis
    logger.info("嘗試啟動 Redis...")
    if start_redis_docker():
        logger.info("✅ Redis 已成功啟動！")
        test_redis_connection()
        
        print("\n" + "=" * 60)
        print("🎉 Redis 設置完成！")
        print("=" * 60)
        print("現在可以啟動 Celery worker:")
        print("celery -A app.celery_app worker --loglevel=info --pool=solo")
        print("=" * 60)
        
        return True
    else:
        logger.error("❌ Redis 啟動失敗")
        install_redis_guide()
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("用戶中斷")
        sys.exit(1)
    except Exception as e:
        logger.error(f"意外錯誤: {e}")
        sys.exit(1)
