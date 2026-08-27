const IS_PRODUCTION = import.meta.env.PROD;
const IS_DEVELOPMENT = import.meta.env.DEV;
class Logger {
  static log(...args) {
    if (IS_DEVELOPMENT) {
      console.log(...args);
    }
  }
  static debug(...args) {
    if (IS_DEVELOPMENT) {
      console.debug('[DEBUG]', ...args);
    }
  }
  static info(...args) {
    if (IS_DEVELOPMENT) {
      console.info('[INFO]', ...args);
    }
  }
  static warn(...args) {
    const sanitizedArgs = IS_PRODUCTION ? this._sanitize(args) : args;
    console.warn('[WARN]', ...sanitizedArgs);
  }
  static error(...args) {
    const sanitizedArgs = IS_PRODUCTION ? this._sanitize(args) : args;
    console.error('[ERROR]', ...sanitizedArgs);
  }
  static _sanitize(args) {
    return args.map(arg => {
      if (typeof arg === 'string') {
        return arg.replace(/Bearer\s+[^\s]+/gi, 'Bearer [REDACTED]')
          .replace(/token[=:]\s*[^\s&]+/gi, 'token=[REDACTED]')
          .replace(/api[_-]?key[=:]\s*[^\s&]+/gi, 'api_key=[REDACTED]');
      }
      if (typeof arg === 'object' && arg !== null) {
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
  static time(label) {
    if (IS_DEVELOPMENT) {
      console.time(label);
    }
  }
  static timeEnd(label) {
    if (IS_DEVELOPMENT) {
      console.timeEnd(label);
    }
  }
  static table(data) {
    if (IS_DEVELOPMENT) {
      console.table(data);
    }
  }
}
const overrideGlobalConsole = () => {
  if (IS_PRODUCTION) {
    window.console = {
      ...window.console,
      log: () => { },
      debug: () => { },
      info: () => { },
      warn: Logger.warn.bind(Logger),
      error: Logger.error.bind(Logger),
    };
  }
};
export { overrideGlobalConsole };
export default Logger;
