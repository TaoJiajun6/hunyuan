import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import isToday from 'dayjs/plugin/isToday';
import isYesterday from 'dayjs/plugin/isYesterday';
dayjs.extend(relativeTime);
dayjs.extend(isToday);
dayjs.extend(isYesterday);
export class TimeUtils {
  static formatDate(date: number | string | Date | undefined, format = 'YYYY-MM-DD HH:mm'): string {
    if (!date) {
      return ''
    }
    let targetDate = date instanceof Date ? date : new Date(date);
    const pad = (num: number) => num.toString().padStart(2, '0');

    const month = targetDate.getMonth();

    const formats: Record<string, string | number> = {
      // 年份
      'YYYY': targetDate.getFullYear(),
      'YY': targetDate.getFullYear().toString().slice(-2),
      // 月份
      'MM': pad(month + 1),
      // 日期
      'DD': pad(targetDate.getDate()),

      // 时间
      'HH': pad(targetDate.getHours()),
      'hh': pad(targetDate.getHours() % 12 || 12),
      'mm': pad(targetDate.getMinutes()),
      'ss': pad(targetDate.getSeconds()),
    }
    return format.replace(/\[([^\]]+)]|Y{2,4}|M{1,4}|D{1,2}|H{1,2}|h{1,2}|m{1,2}|s{1,2}/g,
      (match: string, escaped: string): string => escaped || formats[match].toString())
  }

  /**
   * 获取相对时间
   * @param dateTimeStamp
   * @returns
   */
  static getDateDiff(dateTimeStamp: number): string {
    if (!dateTimeStamp || dateTimeStamp <= 0) {
      return '';
    }
    const now = dayjs();
    const target = dayjs(dateTimeStamp);
    if (target.isAfter(now)) {
      return '';
    }
    const diffSeconds = now.diff(target, 'second');
    if (diffSeconds < 60) {
      return '刚刚';
    }
    const diffMinutes = now.diff(target, 'minute');
    if (diffMinutes < 60) {
      return `${diffMinutes}分钟前`;
    }
    const diffHours = now.diff(target, 'hour');
    if (diffHours < 24) {
      return `${diffHours}小时前`;
    }
    if (target.isYesterday()) {
      return '昨天';
    }
    if (target.isSame(now.subtract(2, 'day'), 'day')) {
      return '前天';
    }
    if (target.isAfter(now.subtract(7, 'day'))) {
      const diffDays = now.diff(target, 'day');
      return `${diffDays}天前`;
    }
    return target.format('YYYY-MM-DD');
  }

  /**
   * 获取消息相对时间
   * @param dateTimeStamp
   */
  static handleMsgTimeDiff(dateTimeStamp: number): string {
    if (!dateTimeStamp) {
      return '';
    }

    let timeStamp = dayjs(dateTimeStamp).format('YYYY-MM-DD hh:mm')

    // 时间字符串转时间戳
    const time = new Date(timeStamp);
    const now = new Date();

    const isToday =
      time.getFullYear() === now.getFullYear() &&
        time.getMonth() === now.getMonth() &&
        time.getDate() === now.getDate();

    const isThisYear = time.getFullYear() === now.getFullYear()

    let result: string = '';
    if (isToday) {
      result = dayjs(time).format('HH:mm');
    } else if (isThisYear) {
      result = dayjs(time).format('MM-DD');
    } else {
      result = dayjs(time).format('YYYY-MM-DD');
    }

    return result;
  }

  /**
   * 处理视频时长
   * @param duration
   */
  static handleDuration(duration?: number): string {
    if (!duration) {
      return '';
    }
    let sec = duration / 1000;
    let hour = Math.floor(sec / 60 / 60);
    let min = Math.floor((sec % 3600) / 60);
    sec = Math.floor(sec % 60);
    if (hour) {
      return `${hour.toString().padStart(2, '0')}:${min.toString().padStart(2, '0')}:${sec.toString()
        .padStart(2, '0')}`;
    }
    return `${min.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
  }
}