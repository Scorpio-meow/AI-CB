/**
 * 網絡狀態監聽器
 * 檢測在線/離線狀態
 */

class NetworkMonitor {
  constructor() {
    this.listeners = [];
    this.isOnline = navigator.onLine;

    // 監聽網絡狀態變化
    window.addEventListener('online', this.handleOnline.bind(this));
    window.addEventListener('offline', this.handleOffline.bind(this));
  }

  handleOnline() {
    console.log('[Network] 網絡已連接');
    this.isOnline = true;
    this.notifyListeners('online');
  }

  handleOffline() {
    console.log('[Network] 網絡已斷開');
    this.isOnline = false;
    this.notifyListeners('offline');
  }

  /**
   * 添加狀態監聽器
   * @param {Function} callback - 回調函數 (status) => void
   */
  addListener(callback) {
    this.listeners.push(callback);
    // 立即通知當前狀態
    callback(this.isOnline ? 'online' : 'offline');
  }

  /**
   * 移除狀態監聽器
   */
  removeListener(callback) {
    this.listeners = this.listeners.filter(listener => listener !== callback);
  }

  /**
   * 通知所有監聽器
   */
  notifyListeners(status) {
    this.listeners.forEach(listener => {
      try {
        listener(status);
      } catch (error) {
        console.error('[Network] 監聽器執行錯誤:', error);
      }
    });
  }

  /**
   * 檢查當前是否在線
   */
  checkOnline() {
    return this.isOnline;
  }

  /**
   * 主動檢測網絡連接（通過發送請求）
   * @param {string} url - 測試 URL
   */
  async pingServer(url = '/api/auth/validate-token') {
    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`,
        },
        cache: 'no-cache',
        signal: AbortSignal.timeout(5000), // 5 秒超時
      });

      return response.ok;
    } catch (error) {
      console.error('[Network] 服務器連接測試失敗:', error);
      return false;
    }
  }
}

// 全局單例
const networkMonitor = new NetworkMonitor();

export default networkMonitor;