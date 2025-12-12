/**
 * 生產環境日誌管理器
 * 在生產環境中過濾掉敏感的調試日誌
 */

const isDevelopment = import.meta.env.DEV;

/**
 * 安全的 console.log 包裝器
 * 僅在開發環境輸出日誌
 */
export const devLog = (...args) => {
  if (isDevelopment) {
    console.log(...args);
  }
};

/**
 * 安全的 console.warn 包裝器
 * 所有環境都輸出警告
 */
export const devWarn = (...args) => {
  console.warn(...args);
};

/**
 * 安全的 console.error 包裝器
 * 所有環境都輸出錯誤
 */
export const devError = (...args) => {
  console.error(...args);
};

/**
 * 安全的 console.info 包裝器
 * 僅在開發環境輸出信息
 */
export const devInfo = (...args) => {
  if (isDevelopment) {
    console.info(...args);
  }
};

/**
 * 移除敏感資訊的日誌輸出
 * 用於記錄可能包含敏感資訊的對象
 */
export const secureLog = (label, data) => {
  if (!isDevelopment) {
    return; // 生產環境完全不輸出
  }

  // 深度複製以避免修改原始數據
  const sanitized = JSON.parse(JSON.stringify(data));

  // 移除敏感欄位
  const sensitiveKeys = ['password', 'token', 'access_token', 'refresh_token', 'apiKey', 'secret'];
  
  const removeSensitive = (obj) => {
    if (!obj || typeof obj !== 'object') return obj;
    
    Object.keys(obj).forEach(key => {
      if (sensitiveKeys.some(sensitive => key.toLowerCase().includes(sensitive))) {
        obj[key] = '[REDACTED]';
      } else if (typeof obj[key] === 'object') {
        removeSensitive(obj[key]);
      }
    });
    
    return obj;
  };

  console.log(label, removeSensitive(sanitized));
};

// 在生產環境禁用原生 console
if (!isDevelopment) {
  // 保留錯誤和警告
  const originalError = console.error;
  const originalWarn = console.warn;
  
  // 覆寫 console 方法
  console.log = () => {};
  console.info = () => {};
  console.debug = () => {};
  
  // 恢復錯誤和警告
  console.error = originalError;
  console.warn = originalWarn;
  
  console.warn('🔒 生產環境模式：調試日誌已禁用');
}

const secureLogger = {
  log: devLog,
  warn: devWarn,
  error: devError,
  info: devInfo,
  secure: secureLog,
};

export default secureLogger;
