import { useState, useEffect } from 'react';
import { Snackbar, Alert } from '@mui/material';
import networkMonitor from '../utils/networkMonitor';
import offlineCache from '../utils/offlineCache';

/**
 * 網絡狀態監聽組件
 * 顯示在線/離線提示
 */
const NetworkStatus = () => {
  const [showOfflineAlert, setShowOfflineAlert] = useState(false);
  const [showOnlineAlert, setShowOnlineAlert] = useState(false);
  const [pendingRequestsCount, setPendingRequestsCount] = useState(0);

  useEffect(() => {
    // 監聽網絡狀態
    const handleNetworkChange = async (status) => {
      const online = status === 'online';

      if (online) {
        // 上線時
        setShowOnlineAlert(true);
        setShowOfflineAlert(false);

        // 檢查是否有待處理的請求
        const count = await offlineCache.getCount();
        setPendingRequestsCount(count);

        // 自動同步離線數據
        if (count > 0) {
          console.log(`[NetworkStatus] 檢測到 ${count} 個離線請求，準備同步...`);
          // 這裡可以觸發自動同步邏輯
          // await syncOfflineData();
        }
      } else {
        // 離線時
        setShowOfflineAlert(true);
        setShowOnlineAlert(false);
      }
    };

    networkMonitor.addListener(handleNetworkChange);

    // 清理
    return () => {
      networkMonitor.removeListener(handleNetworkChange);
    };
  }, []);

  const handleCloseOfflineAlert = () => {
    setShowOfflineAlert(false);
  };

  const handleCloseOnlineAlert = () => {
    setShowOnlineAlert(false);
  };

  return (
    <>
      {/* 離線提示 */}
      <Snackbar
        open={showOfflineAlert}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
        onClose={handleCloseOfflineAlert}
      >
        <Alert
          onClose={handleCloseOfflineAlert}
          severity="warning"
          sx={{ width: '100%' }}
        >
          您目前處於離線狀態，某些功能可能不可用
        </Alert>
      </Snackbar>

      {/* 上線提示 */}
      <Snackbar
        open={showOnlineAlert}
        autoHideDuration={3000}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
        onClose={handleCloseOnlineAlert}
      >
        <Alert
          onClose={handleCloseOnlineAlert}
          severity="success"
          sx={{ width: '100%' }}
        >
          {pendingRequestsCount > 0
            ? `網絡已恢復！檢測到 ${pendingRequestsCount} 個離線請求`
            : '網絡已恢復'}
        </Alert>
      </Snackbar>
    </>
  );
};

export default NetworkStatus;