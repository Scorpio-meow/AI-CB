"""
測試腳本：驗證只有創建者可以修改 is_public 狀態

測試場景：
1. 創建者可以修改 is_public
2. 管理員不能修改其他人的 is_public
3. 管理員可以修改其他欄位（name, role 等）
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import json
from typing import Optional

# 配置
BASE_URL = "http://localhost:8001/api"

# 測試用戶憑證
CREATOR_USER = {
    "username": "testuser1",
    "password": "password123"
}

ADMIN_USER = {
    "username": "admin",
    "password": "admin123"
}

class TestClient:
    def __init__(self):
        self.creator_token: Optional[str] = None
        self.admin_token: Optional[str] = None
        self.test_agent_id: Optional[int] = None
    
    def login(self, username: str, password: str) -> str:
        """登入並返回 JWT token"""
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"username": username, "password": password}
        )
        if response.status_code == 200:
            token = response.json()["access_token"]
            print(f"✅ {username} 登入成功")
            return token
        else:
            print(f"❌ {username} 登入失敗: {response.text}")
            return None
    
    def create_agent(self, token: str, agent_data: dict) -> Optional[int]:
        """創建 Agent"""
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(
            f"{BASE_URL}/custom_agents/",
            headers=headers,
            json=agent_data
        )
        if response.status_code == 200:
            agent = response.json()
            print(f"✅ Agent 創建成功 (ID: {agent['id']}, is_public: {agent['is_public']})")
            return agent['id']
        else:
            print(f"❌ Agent 創建失敗: {response.text}")
            return None
    
    def update_agent(self, token: str, agent_id: int, update_data: dict) -> bool:
        """更新 Agent"""
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.put(
            f"{BASE_URL}/custom_agents/{agent_id}",
            headers=headers,
            json=update_data
        )
        
        if response.status_code == 200:
            agent = response.json()
            print(f"✅ Agent 更新成功")
            return True
        else:
            print(f"❌ Agent 更新失敗 (狀態碼: {response.status_code})")
            print(f"   錯誤訊息: {response.json().get('detail', 'Unknown error')}")
            return False
    
    def get_agent(self, token: str, agent_id: int) -> Optional[dict]:
        """獲取 Agent 詳情"""
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{BASE_URL}/custom_agents/{agent_id}",
            headers=headers
        )
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ 獲取 Agent 失敗: {response.text}")
            return None
    
    def delete_agent(self, token: str, agent_id: int) -> bool:
        """刪除 Agent"""
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.delete(
            f"{BASE_URL}/custom_agents/{agent_id}",
            headers=headers
        )
        if response.status_code == 200:
            print(f"✅ Agent 刪除成功")
            return True
        else:
            print(f"❌ Agent 刪除失敗: {response.text}")
            return False

def run_tests():
    """運行所有測試"""
    client = TestClient()
    
    print("=" * 60)
    print("測試：is_public 修改權限")
    print("=" * 60)
    
    # 步驟 1: 登入用戶
    print("\n[步驟 1] 登入測試用戶")
    print("-" * 60)
    client.creator_token = client.login(CREATOR_USER["username"], CREATOR_USER["password"])
    client.admin_token = client.login(ADMIN_USER["username"], ADMIN_USER["password"])
    
    if not client.creator_token or not client.admin_token:
        print("\n❌ 登入失敗，無法繼續測試")
        return
    
    # 步驟 2: 創建者創建一個公開 Agent
    print("\n[步驟 2] 創建者創建公開 Agent")
    print("-" * 60)
    agent_data = {
        "name": "測試Agent",
        "role": "測試角色",
        "system_prompt": "這是測試用的系統提示詞",
        "is_public": True
    }
    client.test_agent_id = client.create_agent(client.creator_token, agent_data)
    
    if not client.test_agent_id:
        print("\n❌ 創建 Agent 失敗，無法繼續測試")
        return
    
    # 步驟 3: 創建者修改 is_public (應該成功)
    print("\n[步驟 3] 測試：創建者修改 is_public 為 False")
    print("-" * 60)
    success = client.update_agent(
        client.creator_token,
        client.test_agent_id,
        {"is_public": False}
    )
    
    if success:
        agent = client.get_agent(client.creator_token, client.test_agent_id)
        if agent and agent["is_public"] == False:
            print("✅ 測試通過：創建者可以修改 is_public")
        else:
            print("❌ 測試失敗：is_public 未正確更新")
    else:
        print("❌ 測試失敗：創建者應該可以修改 is_public")
    
    # 步驟 4: 管理員嘗試修改 is_public (應該失敗)
    print("\n[步驟 4] 測試：管理員修改其他人的 is_public")
    print("-" * 60)
    success = client.update_agent(
        client.admin_token,
        client.test_agent_id,
        {"is_public": True}
    )
    
    if not success:
        agent = client.get_agent(client.admin_token, client.test_agent_id)
        if agent and agent["is_public"] == False:
            print("✅ 測試通過：管理員無法修改他人的 is_public")
        else:
            print("❌ 測試失敗：is_public 不應該被修改")
    else:
        print("❌ 測試失敗：管理員不應該能修改他人的 is_public")
    
    # 步驟 5: 管理員修改其他欄位 (應該成功)
    print("\n[步驟 5] 測試：管理員修改其他欄位（name）")
    print("-" * 60)
    success = client.update_agent(
        client.admin_token,
        client.test_agent_id,
        {"name": "管理員修改後的名稱"}
    )
    
    if success:
        agent = client.get_agent(client.admin_token, client.test_agent_id)
        if agent and agent["name"] == "管理員修改後的名稱":
            print("✅ 測試通過：管理員可以修改其他欄位")
        else:
            print("❌ 測試失敗：名稱未正確更新")
    else:
        print("❌ 測試失敗：管理員應該可以修改其他欄位")
    
    # 步驟 6: 創建者再次修改 is_public (應該成功)
    print("\n[步驟 6] 測試：創建者再次修改 is_public 為 True")
    print("-" * 60)
    success = client.update_agent(
        client.creator_token,
        client.test_agent_id,
        {"is_public": True}
    )
    
    if success:
        agent = client.get_agent(client.creator_token, client.test_agent_id)
        if agent and agent["is_public"] == True:
            print("✅ 測試通過：創建者可以再次修改 is_public")
        else:
            print("❌ 測試失敗：is_public 未正確更新")
    else:
        print("❌ 測試失敗：創建者應該可以修改 is_public")
    
    # 清理: 刪除測試 Agent
    print("\n[清理] 刪除測試 Agent")
    print("-" * 60)
    client.delete_agent(client.admin_token, client.test_agent_id)
    
    print("\n" + "=" * 60)
    print("測試完成！")
    print("=" * 60)

if __name__ == "__main__":
    try:
        run_tests()
    except Exception as e:
        print(f"\n❌ 測試過程中發生錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
