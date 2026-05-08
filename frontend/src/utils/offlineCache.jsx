/**
 * 離線緩存管理器
 * 使用 IndexedDB 存儲離線數據
 */

const DB_NAME = 'ChatBotOfflineCache';
const DB_VERSION = 1;
const STORE_NAME = 'pendingRequests';

class OfflineCache {
  constructor() {
    this.db = null;
    this.initDB();
  }

  /**
   * 初始化 IndexedDB
   */
  async initDB() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onerror = () => {
        console.error('[OfflineCache] IndexedDB 初始化失敗:', request.error);
        reject(request.error);
      };

      request.onsuccess = () => {
        this.db = request.result;
        console.log('[OfflineCache] IndexedDB 初始化成功');
        resolve(this.db);
      };

      request.onupgradeneeded = (event) => {
        const db = event.target.result;

        // 創建對象存儲
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          const objectStore = db.createObjectStore(STORE_NAME, {
            keyPath: 'id',
            autoIncrement: true
          });

          objectStore.createIndex('timestamp', 'timestamp', { unique: false });
          objectStore.createIndex('type', 'type', { unique: false });

          console.log('[OfflineCache] 對象存儲已創建');
        }
      };
    });
  }

  /**
   * 確保數據庫已初始化
   */
  async ensureDB() {
    if (!this.db) {
      await this.initDB();
    }
    return this.db;
  }

  /**
   * 添加離線請求到緩存
   * @param {Object} request - 請求對象 { url, method, data, type }
   */
  async addRequest(request) {
    try {
      const db = await this.ensureDB();

      const transaction = db.transaction([STORE_NAME], 'readwrite');
      const store = transaction.objectStore(STORE_NAME);

      const item = {
        ...request,
        timestamp: Date.now(),
      };

      const addRequest = store.add(item);

      return new Promise((resolve, reject) => {
        addRequest.onsuccess = () => {
          console.log('[OfflineCache] 請求已緩存:', item);
          resolve(addRequest.result);
        };

        addRequest.onerror = () => {
          console.error('[OfflineCache] 緩存請求失敗:', addRequest.error);
          reject(addRequest.error);
        };
      });
    } catch (error) {
      console.error('[OfflineCache] 添加請求失敗:', error);
      throw error;
    }
  }

  /**
   * 獲取所有待處理的請求
   */
  async getAllRequests() {
    try {
      const db = await this.ensureDB();

      const transaction = db.transaction([STORE_NAME], 'readonly');
      const store = transaction.objectStore(STORE_NAME);
      const getAllRequest = store.getAll();

      return new Promise((resolve, reject) => {
        getAllRequest.onsuccess = () => {
          resolve(getAllRequest.result);
        };

        getAllRequest.onerror = () => {
          reject(getAllRequest.error);
        };
      });
    } catch (error) {
      console.error('[OfflineCache] 獲取請求失敗:', error);
      return [];
    }
  }

  /**
   * 刪除已處理的請求
   * @param {number} id - 請求 ID
   */
  async removeRequest(id) {
    try {
      const db = await this.ensureDB();

      const transaction = db.transaction([STORE_NAME], 'readwrite');
      const store = transaction.objectStore(STORE_NAME);
      const deleteRequest = store.delete(id);

      return new Promise((resolve, reject) => {
        deleteRequest.onsuccess = () => {
          console.log('[OfflineCache] 請求已刪除:', id);
          resolve();
        };

        deleteRequest.onerror = () => {
          reject(deleteRequest.error);
        };
      });
    } catch (error) {
      console.error('[OfflineCache] 刪除請求失敗:', error);
      throw error;
    }
  }

  /**
   * 清空所有緩存
   */
  async clearAll() {
    try {
      const db = await this.ensureDB();

      const transaction = db.transaction([STORE_NAME], 'readwrite');
      const store = transaction.objectStore(STORE_NAME);
      const clearRequest = store.clear();

      return new Promise((resolve, reject) => {
        clearRequest.onsuccess = () => {
          console.log('[OfflineCache] 緩存已清空');
          resolve();
        };

        clearRequest.onerror = () => {
          reject(clearRequest.error);
        };
      });
    } catch (error) {
      console.error('[OfflineCache] 清空緩存失敗:', error);
      throw error;
    }
  }

  /**
   * 獲取緩存大小
   */
  async getCount() {
    try {
      const db = await this.ensureDB();

      const transaction = db.transaction([STORE_NAME], 'readonly');
      const store = transaction.objectStore(STORE_NAME);
      const countRequest = store.count();

      return new Promise((resolve, reject) => {
        countRequest.onsuccess = () => {
          resolve(countRequest.result);
        };

        countRequest.onerror = () => {
          reject(countRequest.error);
        };
      });
    } catch (error) {
      console.error('[OfflineCache] 獲取計數失敗:', error);
      return 0;
    }
  }
}

// 全局單例
const offlineCache = new OfflineCache();

export default offlineCache;