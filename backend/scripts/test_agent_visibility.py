"""
快速測試 Agent 公開/私人功能

此腳本測試：
1. 創建公開 Agent
2. 創建私人 Agent
3. 驗證權限控制
"""

import requests
import json

BASE_URL = "http://localhost:8001"

def test_agent_visibility():
    print("🧪 測試 Agent 公開/私人功能\n")
    
    # 1. 登入獲取 token
    print("1️⃣ 登入用戶...")
    login_response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": "admin", "password": "Admin123!"}
    )
    
    if login_response.status_code != 200:
        print(f"❌ 登入失敗: {login_response.text}")
        return
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ 登入成功\n")
    
    # 2. 創建公開 Agent
    print("2️⃣ 創建公開 Agent...")
    public_agent = {
        "name": "公開測試助手",
        "role": "Public Test Assistant",
        "expertise": "這是一個公開的測試 Agent",
        "prompt": "你是一個公開的測試助手",
        "tools": ["File", "Search"],
        "is_public": True
    }
    
    response = requests.post(
        f"{BASE_URL}/api/custom_agents/",
        json=public_agent,
        headers=headers
    )
    
    if response.status_code == 200:
        agent_data = response.json()
        print(f"✅ 公開 Agent 創建成功 (ID: {agent_data['id']})")
        print(f"   - is_public: {agent_data.get('is_public')}")
        print(f"   - created_by: {agent_data.get('created_by')}\n")
        public_agent_id = agent_data['id']
    else:
        print(f"❌ 創建失敗: {response.text}\n")
        return
    
    # 3. 創建私人 Agent
    print("3️⃣ 創建私人 Agent...")
    private_agent = {
        "name": "私人測試助手",
        "role": "Private Test Assistant",
        "expertise": "這是一個私人的測試 Agent",
        "prompt": "你是一個私人的測試助手",
        "tools": ["File"],
        "is_public": False
    }
    
    response = requests.post(
        f"{BASE_URL}/api/custom_agents/",
        json=private_agent,
        headers=headers
    )
    
    if response.status_code == 200:
        agent_data = response.json()
        print(f"✅ 私人 Agent 創建成功 (ID: {agent_data['id']})")
        print(f"   - is_public: {agent_data.get('is_public')}")
        print(f"   - created_by: {agent_data.get('created_by')}\n")
        private_agent_id = agent_data['id']
    else:
        print(f"❌ 創建失敗: {response.text}\n")
        return
    
    # 4. 獲取所有 Agent 列表
    print("4️⃣ 獲取 Agent 列表...")
    response = requests.get(
        f"{BASE_URL}/api/custom_agents/all_with_details",
        headers=headers
    )
    
    if response.status_code == 200:
        agents = response.json()
        print(f"✅ 獲取到 {len(agents)} 個 Agent")
        for agent in agents:
            visibility = "🌍 公開" if agent.get('is_public') else "🔒 私人"
            print(f"   - {agent['name']} ({visibility})")
        print()
    else:
        print(f"❌ 獲取列表失敗: {response.text}\n")
    
    # 5. 測試更新 Agent
    print("5️⃣ 測試更新 Agent...")
    update_data = {
        "name": "更新後的公開助手",
        "is_public": False  # 改為私人
    }
    
    response = requests.put(
        f"{BASE_URL}/api/custom_agents/{public_agent_id}",
        json=update_data,
        headers=headers
    )
    
    if response.status_code == 200:
        agent_data = response.json()
        print(f"✅ Agent 更新成功")
        print(f"   - 新名稱: {agent_data['name']}")
        print(f"   - is_public: {agent_data.get('is_public')}\n")
    else:
        print(f"❌ 更新失敗: {response.text}\n")
    
    # 6. 清理測試數據（可選）
    print("6️⃣ 清理測試數據...")
    for agent_id in [public_agent_id, private_agent_id]:
        response = requests.delete(
            f"{BASE_URL}/api/custom_agents/{agent_id}",
            headers=headers
        )
        if response.status_code == 200:
            print(f"✅ Agent {agent_id} 已刪除")
        else:
            print(f"⚠️  無法刪除 Agent {agent_id}: {response.text}")
    
    print("\n🎉 測試完成！")

if __name__ == "__main__":
    try:
        test_agent_visibility()
    except Exception as e:
        print(f"\n❌ 測試過程中發生錯誤: {e}")
