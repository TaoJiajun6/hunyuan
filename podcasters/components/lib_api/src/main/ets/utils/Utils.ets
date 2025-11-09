import dayjs from 'dayjs';

/**
 * 通用方法类
 */
export class Utils {
  /**
   * 随机打乱数组
   * @param array
   * @returns
   */
  public static shuffleArray<T>(array: T[]): T[] {
    for (let i = array.length - 1; i > 0; i--) {
      // 生成 0 到 i 之间的随机索引
      const j = Math.floor(Math.random() * (i + 1));

      // 交换当前元素与随机位置的元素
      const temp = array[i];
      array[i] = array[j]
      array[j] = temp;
    }
    return array;
  }

  /**
   * 随机生成推荐id
   * @returns
   */
  public static randomRecommendId() {
    return Math.floor(Math.random() * (12 - 6 + 1)) + 6;
  }

  /**
   * 随机生成文章id
   * @returns
   */
  public static randomArticleId() {
    return Math.floor(Math.random() * (100 - 20 + 1)) + 20;
  }

  /**
   * 获取相对时间
   * @param dateTimeStamp
   * @returns
   */
  public static getDateDiff(dateTimeStamp: number): string {
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
}