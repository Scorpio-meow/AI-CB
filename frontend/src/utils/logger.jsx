/**
 * 生產環境安全的日誌工具
 * 在開發環境顯示日誌，生產環境自動過濾敏感日誌
 */

const IS_PRODUCTION = import.meta.env.PROD;
const IS_DEVELOPMENT = import.meta.env.DEV;

class Logger {
  /**
   * 普通日誌（生產環境不輸出）
   */
  static log(...args) {
    if (IS_DEVELOPMENT) {
      console.log(...args);
    }
  }

  /**
   * 調試日誌（僅開發環境）
   */
  static debug(...args) {
    if (IS_DEVELOPMENT) {
      console.debug('[DEBUG]', ...args);
    }
  }

  /**
   * 信息日誌（僅開發環境）
   */
  static info(...args) {
    if (IS_DEVELOPMENT) {
      console.info('[INFO]', ...args);
    }
  }

  /**
   * 警告日誌（生產環境也輸出，但不包含敏感資訊）
   */
  static warn(...args) {
    const sanitizedArgs = IS_PRODUCTION ? this._sanitize(args) : args;
    console.warn('[WARN]', ...sanitizedArgs);
  }

  /**
   * 錯誤日誌（始終輸出，但生產環境過濾敏感資訊）
   */
  static error(...args) {
    const sanitizedArgs = IS_PRODUCTION ? this._sanitize(args) : args;
    console.error('[ERROR]', ...sanitizedArgs);
  }

  /**
   * 清理敏感資訊
   */
  static _sanitize(args) {
    return args.map(arg => {
      if (typeof arg === 'string') {
        // 移除可能的 token 或密鑰
        return arg.replace(/Bearer\s+[^\s]+/gi, 'Bearer [REDACTED]')
                  .replace(/token[=:]\s*[^\s&]+/gi, 'token=[REDACTED]')
                  .replace(/api[_-]?key[=:]\s*[^\s&]+/gi, 'api_key=[REDACTED]');
      }
      if (typeof arg === 'object' && arg !== null) {
        // 清理對象中的敏感字段
        const cleaned = { ...arg };
        const sensitiveKeys = ['password', 'token', 'apiKey', 'api_key', 'secret', 'authorization'];
        
        for (const key of Object.keys(cleaned)) {
          if (sensitiveKeys.some(sk => key.toLowerCase().includes(sk))) {
            cleaned[key] = '[REDACTED]';
          }
        }
        return cleaned;
      }
      return arg;
    });
  }

  /**
   * 性能計時開始
   */
  static time(label) {
    if (IS_DEVELOPMENT) {
      console.time(label);
    }
  }

  /**
   * 性能計時結束
   */
  static timeEnd(label) {
    if (IS_DEVELOPMENT) {
      console.timeEnd(label);
    }
  }

  /**
   * 表格輸出（僅開發環境）
   */
  static table(data) {
    if (IS_DEVELOPMENT) {
      console.table(data);
    }
  }
}

// 覆蓋全局 console（可選，僅在嚴格模式下使用）
export const overrideGlobalConsole = () => {
  if (IS_PRODUCTION) {
    window.console = {
      ...window.console,
      log: () => {},
      debug: () => {},
      info: () => {},
      warn: Logger.warn.bind(Logger),
      error: Logger.error.bind(Logger),
    };
  }
};

export default Logger;
