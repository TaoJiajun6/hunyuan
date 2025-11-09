import { GlobalKey } from '../constants/GlobalKey';
import { Logger } from './Logger';

const TAG = '[GlobalUtils]';

/**
 * 全局变量管理，不支持UI动态观测变化
 */
export class GlobalUtils {
  static globalThis: Map<string, Object> = new Map();

  static set(storageKey: GlobalKey, objectClass: Object) {
    Logger.info(TAG, `Create key of ${storageKey}`);
    GlobalUtils.globalThis.set(storageKey, objectClass);
  }

  static get(storageKey: GlobalKey): Object | undefined {
    return GlobalUtils.globalThis.get(storageKey);
  }
}
