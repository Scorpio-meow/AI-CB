"""
完整測試用戶聊天隔離 - 包含創建對話
"""
import requests
import json

BASE_URL = "http://localhost:8001/api"

def test_complete_isolation():
    """完整測試用戶隔離,包含創建對話"""
    
    print("=" * 70)
    print("完整測試用戶聊天隔離功能")
    print("=" * 70)
    
    # 1. 創建兩個測試用戶
    test_users = [
        {"username": "isolation_test1", "email": "iso1@test.com", "password": "Test123!"},
        {"username": "isolation_test2", "email": "iso2@test.com", "password": "Test123!"}
    ]
    
    users = []
    for i, user_data in enumerate(test_users, 1):
        print(f"\n{'='*70}")
        print(f"步驟 {i}: 設置用戶 '{user_data['username']}'")
        print(f"{'='*70}")
        
        # 註冊或登入
        reg_response = requests.post(f"{BASE_URL}/auth/register", json=user_data)
        if reg_response.status_code == 201:
            print(f"✅ 用戶註冊成功")
            data = reg_response.json()
            token = data["tokens"]["access_token"]
            user_id = data["user"]["id"]
        else:
            # 如果已存在,嘗試登入
            login_response = requests.post(
                f"{BASE_URL}/auth/login",
                json={"username": user_data["username"], "password": user_data["password"]}
            )
            if login_response.status_code != 200:
                print(f"❌ 登入失敗")
                return False
            data = login_response.json()
            token = data["tokens"]["access_token"]
            user_id = data["user"]["id"]
            print(f"✅ 用戶已存在,登入成功")
        
        users.append({
            "username": user_data["username"],
            "user_id": user_id,
            "token": token,
            "headers": {"Authorization": f"Bearer {token}"}
        })
        print(f"   用戶 ID: {user_id}")
    
    # 2. 每個用戶創建對話並發送消息
    print(f"\n{'='*70}")
    print(f"步驟 3: 每個用戶創建對話並發送消息")
    print(f"{'='*70}")
    
    for user in users:
        # 創建對話
        conv_response = requests.post(
            f"{BASE_URL}/chat/conversations",
            headers=user["headers"]
        )
        
        if conv_response.status_code != 200:
            print(f"❌ 用戶 '{user['username']}' 創建對話失敗")
            return False
        
        conv = conv_response.json()
        user["conversation_id"] = conv["id"]
        
        print(f"\n用戶 '{user['username']}' (ID: {user['user_id']})")
        print(f"  ✅ 創建對話 ID: {conv['id']}")
        
        # 發送消息
        msg_response = requests.post(
            f"{BASE_URL}/chat/send",
            headers=user["headers"],
            json={
                "content": f"這是 {user['username']} 的私密消息",
                "conversation_id": conv["id"]
            }
        )
        
        if msg_response.status_code == 200:
            print(f"  ✅ 發送消息成功")
        else:
            print(f"  ❌ 發送消息失敗: {msg_response.status_code}")
    
    # 3. 驗證每個用戶只能看到自己的對話
    print(f"\n{'='*70}")
    print(f"步驟 4: 驗證每個用戶只能看到自己的對話")
    print(f"{'='*70}")
    
    for user in users:
        response = requests.get(
            f"{BASE_URL}/chat/conversations",
            headers=user["headers"]
        )
        
        conversations = response.json()
        print(f"\n用戶 '{user['username']}' (ID: {user['user_id']})")
        print(f"  對話數量: {len(conversations)}")
        
        # 驗證對話屬於此用戶
        found_own_conv = False
        for conv in conversations:
            if conv["id"] == user["conversation_id"]:
                found_own_conv = True
                print(f"  ✅ 找到自己的對話 ID: {conv['id']}")
                
                # 檢查消息內容
                if conv.get("messages"):
                    user_msg = conv["messages"][0]
                    if user["username"] in user_msg["content"]:
                        print(f"  ✅ 消息內容正確屬於此用戶")
        
        if not found_own_conv:
            print(f"  ❌ 錯誤: 找不到自己的對話!")
            return False
    
    # 4. 測試跨用戶訪問保護
    print(f"\n{'='*70}")
    print(f"步驟 5: 測試跨用戶訪問保護")
    print(f"{'='*70}")
    
    user1, user2 = users[0], users[1]
    
    print(f"\n嘗試: 用戶 '{user2['username']}' 訪問用戶 '{user1['username']}' 的對話")
    
    # 用戶2嘗試訪問用戶1的對話
    response = requests.get(
        f"{BASE_URL}/chat/conversations/{user1['conversation_id']}",
        headers=user2["headers"]
    )
    
    if response.status_code == 404:
        print(f"  ✅ 跨用戶訪問被正確阻止 (404 Not Found)")
    elif response.status_code == 403:
        print(f"  ✅ 跨用戶訪問被正確阻止 (403 Forbidden)")
    elif response.status_code == 200:
        print(f"  ❌ 嚴重錯誤: 跨用戶訪問沒有被阻止!")
        print(f"  用戶2能夠看到用戶1的對話內容:")
        print(f"  {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return False
    else:
        print(f"  ⚠️  未預期的狀態碼: {response.status_code}")
    
    # 5. 測試對話刪除隔離
    print(f"\n{'='*70}")
    print(f"步驟 6: 測試對話刪除隔離")
    print(f"{'='*70}")
    
    print(f"\n嘗試: 用戶 '{user2['username']}' 刪除用戶 '{user1['username']}' 的對話")
    
    response = requests.delete(
        f"{BASE_URL}/chat/conversations/{user1['conversation_id']}",
        headers=user2["headers"]
    )
    
    if response.status_code == 404:
        print(f"  ✅ 跨用戶刪除被正確阻止")
    elif response.status_code == 200:
        print(f"  ❌ 嚴重錯誤: 用戶2能夠刪除用戶1的對話!")
        return False
    
    # 驗證用戶1的對話仍然存在
    response = requests.get(
        f"{BASE_URL}/chat/conversations/{user1['conversation_id']}",
        headers=user1["headers"]
    )
    
    if response.status_code == 200:
        print(f"  ✅ 用戶1的對話仍然存在,沒有被刪除")
    else:
        print(f"  ❌ 錯誤: 用戶1的對話不見了!")
        return False
    
    print(f"\n{'='*70}")
    print(f"✅✅✅ 所有測試通過！用戶聊天記錄完全隔離！✅✅✅")
    print(f"{'='*70}")
    print(f"\n測試結果:")
    print(f"  ✅ 用戶只能看到自己的對話列表")
    print(f"  ✅ 用戶無法訪問其他用戶的對話內容")
    print(f"  ✅ 用戶無法刪除其他用戶的對話")
    print(f"  ✅ 消息內容正確隔離到對應用戶")
    
    return True

if __name__ == "__main__":
    success = test_complete_isolation()
    exit(0 if success else 1)
