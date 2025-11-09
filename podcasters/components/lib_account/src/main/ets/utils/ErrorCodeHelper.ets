import { ERROR_MSG_MAP } from '../constants/ErrorCode';

/**
 * 根据错误码获取提示信息
 */
export const getAccountErrorMsg = (code: number, defaultMsg?: string): string => {
  const msg = ERROR_MSG_MAP[code];
  if (msg) {
    return msg;
  }
  if (defaultMsg) {
    return defaultMsg;
  }
  return '未知错误';
};