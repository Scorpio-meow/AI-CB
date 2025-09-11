#!/usr/bin/env python3
"""
清除預設 Agent 的腳本
這個腳本會刪除資料庫中所有原本的預設 Agent
"""

from app.models.database import SessionLocal, engine
from app.models.custom_agent import CustomAgent

# 預設 Agent 的角色列表
DEFAULT_AGENT_ROLES = [
    "BA", "PM", "ARCHITECT", "PO", "SCRUM_MASTER", "RD", "BD", "DEFAULT"
]

def clear_default_agents():
    """清除資料庫中的預設 Agent"""
    db = SessionLocal()
    try:
        # 查詢所有預設 Agent
        default_agents = db.query(CustomAgent).filter(
            CustomAgent.role.in_(DEFAULT_AGENT_ROLES)
        ).all()
        
        print(f"找到 {len(default_agents)} 個預設 Agent:")
        for agent in default_agents:
            print(f"  - ID: {agent.id}, 名稱: {agent.name}, 角色: {agent.role}")
        
        if default_agents:
            confirm = input("\n確定要刪除這些 Agent 嗎？(y/N): ")
            if confirm.lower() in ['y', 'yes']:
                # 刪除預設 Agent
                for agent in default_agents:
                    db.delete(agent)
                
                db.commit()
                print(f"已成功刪除 {len(default_agents)} 個預設 Agent")
            else:
                print("取消刪除操作")
        else:
            print("沒有找到預設 Agent")
            
    except Exception as e:
        db.rollback()
        print(f"刪除失敗: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    clear_default_agents()
