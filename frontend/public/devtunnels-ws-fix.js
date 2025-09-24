// 全域 WebSocket 修復腳本
// 修復所有無效的 WebSocket URL，包括 HMR WebSocket

(function() {
    console.log('載入 WebSocket 修復腳本...');
    
    // 儲存原始的 WebSocket 構造函數
    const OriginalWebSocket = window.WebSocket;
    
    // 創建新的 WebSocket 構造函數
    function FixedWebSocket(url, protocols) {
        console.log('WebSocket 建立請求:', url);
        
        let fixedUrl = url;
        
        // 檢查並修復各種無效的 URL 格式
        if (typeof url === 'string') {
            // 修復包含 NaN 的 URL
            if (url.includes(':NaN') || url.includes('auto:') || url.match(/ws:\/\/auto:/)) {
                console.log('檢測到無效的 WebSocket URL (包含 NaN)');
                
                // 生成正確的 HMR WebSocket URL
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const host = window.location.host;
                fixedUrl = `${protocol}//${host}/ws`;
                
                console.log('修正為:', fixedUrl);
            }
            // 修復其他格式問題
            else if (url.includes('/ws') && !url.includes('/api/workflow/ws')) {
                // 這是 HMR WebSocket，將其正規化為當前頁面的來源，避免 DevTunnels 上的 :3000 等無效埠導致握手失敗
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const host = window.location.host; // 例如: pttqhds6-3000.asse.devtunnels.ms (無需額外 :3000)
                const normalized = `${protocol}//${host}/ws`;
                if (url !== normalized) {
                    console.log('HMR WebSocket URL 正規化為:', normalized);
                } else {
                    console.log('HMR WebSocket URL 有效:', url);
                }
                fixedUrl = normalized;
            }
        }
        
        // 使用修正後的 URL 創建 WebSocket
        try {
            return new OriginalWebSocket(fixedUrl, protocols);
        } catch (error) {
            console.error('WebSocket 創建失敗:', error);
            console.log('嘗試使用後備 URL...');
            
            // 後備方案：使用簡單的本地 WebSocket URL
            const fallbackUrl = 'ws://localhost:3000/ws';
            console.log('使用後備 URL:', fallbackUrl);
            return new OriginalWebSocket(fallbackUrl, protocols);
        }
    }
    
    // 複製原始構造函數的所有屬性和方法
    FixedWebSocket.prototype = OriginalWebSocket.prototype;
    FixedWebSocket.CONNECTING = OriginalWebSocket.CONNECTING;
    FixedWebSocket.OPEN = OriginalWebSocket.OPEN;
    FixedWebSocket.CLOSING = OriginalWebSocket.CLOSING;
    FixedWebSocket.CLOSED = OriginalWebSocket.CLOSED;
    
    // 替換全域 WebSocket 構造函數
    window.WebSocket = FixedWebSocket;
    
    console.log('WebSocket 修復腳本已啟用');
})();