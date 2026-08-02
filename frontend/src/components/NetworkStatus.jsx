import { useState, useEffect } from 'react';
import { Snackbar, Alert } from '@mui/material';
import networkMonitor from '../utils/networkMonitor';
import offlineCache from '../utils/offlineCache';
const NetworkStatus = () => {
  const [showOfflineAlert, setShowOfflineAlert] = useState(false);
  const [showOnlineAlert, setShowOnlineAlert] = useState(false);
  const [pendingRequestsCount, setPendingRequestsCount] = useState(0);
  useEffect(() => {
    const handleNetworkChange = async (status) => {
      const online = status === 'online';
      if (online) {
        setShowOnlineAlert(true);
        setShowOfflineAlert(false);
        const count = await offlineCache.getCount();
        setPendingRequestsCount(count);
        if (count > 0) {
          console.log(`[NetworkStatus] 檢測到 ${count} 個離線請求，準備同步...`);
        }
      } else {
        setShowOfflineAlert(true);
        setShowOnlineAlert(false);
      }
    };
    networkMonitor.addListener(handleNetworkChange);
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
      { }
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
      { }
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