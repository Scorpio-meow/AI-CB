
const isDevelopment = import.meta.env.DEV;
export const devLog = (...args) => {
  if (isDevelopment) {
    console.log(...args);
  }
};
export const devWarn = (...args) => {
  console.warn(...args);
};
export const devError = (...args) => {
  console.error(...args);
};
export const devInfo = (...args) => {
  if (isDevelopment) {
    console.info(...args);
  }
};
export const secureLog = (label, data) => {
  if (!isDevelopment) {
    return;
  }
  const sanitized = JSON.parse(JSON.stringify(data));
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
if (!isDevelopment) {
  const originalError = console.error;
  const originalWarn = console.warn;
  console.log = () => { };
  console.info = () => { };
  console.debug = () => { };
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