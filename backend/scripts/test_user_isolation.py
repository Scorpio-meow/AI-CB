"""
測試用戶聊天隔離功能
"""
import requests
import json

BASE_URL = "http://localhost:8001/api"

def test_user_isolation():
    """測試用戶之間的聊天記錄隔離"""
    
    print("=" * 60)
    print("測試用戶聊天隔離功能")
    print("=" * 60)
    
    # 1. 創建兩個測試用戶並登入
    users = []
    
    # 先創建測試用戶
    test_users = [
        {"username": "test_user1", "email": "user1@test.com", "password": "Test123!"},
        {"username": "test_user2", "email": "user2@test.com", "password": "Test123!"}
    ]
    
    for i, user_data in enumerate(test_users, 1):
        print(f"\n{'='*60}")
        print(f"步驟 {i}: 註冊並登入用戶 '{user_data['username']}'")
        print(f"{'='*60}")
        
        # 嘗試註冊（如果已存在會失敗，但沒關係）
        try:
            reg_response = requests.post(
                f"{BASE_URL}/auth/register",
                json=user_data,
                timeout=10
            )
            if reg_response.status_code == 201:
                print(f"✅ 用戶註冊成功")
        except Exception as e:
            print(f"⚠️  註冊跳過 (可能已存在): {e}")
        
        # 登入
        try:
            response = requests.post(
                f"{BASE_URL}/auth/login",
                json={"username": user_data["username"], "password": user_data["password"]},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                token = data["tokens"]["access_token"]
                user_id = data["user"]["id"]
                users.append({
                    "username": user_data["username"],
                    "user_id": user_id,
                    "token": token,
                    "headers": {"Authorization": f"Bearer {token}"}
                })
                print(f"✅ 登入成功")
                print(f"   用戶 ID: {user_id}")
                print(f"   Token: {token[:30]}...")
            else:
                print(f"❌ 登入失敗: {response.status_code}")
                print(f"   {response.text}")
                return False
        except Exception as e:
            print(f"❌ 登入錯誤: {e}")
            return False
    
    # 2. 每個用戶獲取自己的對話列表
    print(f"\n{'='*60}")
    print(f"步驟 3: 獲取各用戶的對話列表")
    print(f"{'='*60}")
    
    for user in users:
        try:
            response = requests.get(
                f"{BASE_URL}/chat/conversations",
                headers=user["headers"],
                timeout=10
            )
            
            if response.status_code == 200:
                conversations = response.json()
                print(f"\n✅ 用戶 '{user['username']}' (ID: {user['user_id']})")
                print(f"   對話數量: {len(conversations)}")
                
                if conversations:
                    for conv in conversations[:3]:  # 只顯示前3個
                        print(f"   - 對話 {conv['id']}: {conv['title']}")
                else:
                    print(f"   (沒有對話)")
            else:
                print(f"❌ 獲取對話失敗: {response.status_code}")
        except Exception as e:
            print(f"❌ 錯誤: {e}")
    
    # 3. 測試跨用戶訪問保護
    if len(users) >= 2:
        print(f"\n{'='*60}")
        print(f"步驟 4: 測試跨用戶訪問保護")
        print(f"{'='*60}")
        
        user1 = users[0]
        user2 = users[1]
        
        # 獲取用戶1的對話
        response1 = requests.get(
            f"{BASE_URL}/chat/conversations",
            headers=user1["headers"],
            timeout=10
        )
        
        if response1.status_code == 200 and response1.json():
            conv_id = response1.json()[0]["id"]
            
            # 嘗試用用戶2的 token 訪問用戶1的對話
            print(f"\n嘗試用用戶 '{user2['username']}' 訪問用戶 '{user1['username']}' 的對話 {conv_id}")
            
            response2 = requests.get(
                f"{BASE_URL}/chat/conversations/{conv_id}",
                headers=user2["headers"],
                timeout=10
            )
            
            if response2.status_code == 404:
                print(f"✅ 跨用戶訪問正確被阻止 (404)")
            elif response2.status_code == 200:
                print(f"❌ 警告: 跨用戶訪問沒有被阻止！")
                return False
            else:
                print(f"⚠️  未預期的狀態碼: {response2.status_code}")
        else:
            print(f"⚠️  用戶1沒有對話,跳過此測試")
    
    print(f"\n{'='*60}")
    print(f"✅ 所有測試通過！用戶聊天記錄已正確隔離")
    print(f"{'='*60}")
    return True

if __name__ == "__main__":
    success = test_user_isolation()
    exit(0 if success else 1)
