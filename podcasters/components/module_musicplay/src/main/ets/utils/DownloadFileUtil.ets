import fs from '@ohos.file.fs';

import { Logger } from './Logger';


/**
 * 文件工具类
 */
export class DownloadFileUtil{
  /**
   * 根据downPath判断歌曲在沙箱内是否存在
   */
  static async isFileExist(downPath: string, context: Context): Promise<boolean> {
    let cachepath: string = AppStorage.get('cache_path') as string
    if (!cachepath || cachepath === '') {
      cachepath = '/music'
      AppStorage.setOrCreate('cache_path', cachepath)
    }
    let files = `${context.filesDir}${cachepath}`;
    try {
      if (!fs.accessSync(files)) {
        fs.mkdirSync(files);
      }
    } catch (err) {
      Logger.error('DownloadFileUtil 文件夹创建失败：', err.message);
    }
    let fileName = DownloadFileUtil.geteFileNameAndType(downPath)
    let filePath = files + '/' + fileName
    return fs.accessSync(filePath)
  }

  // 解析URL中的文件名和文件类型
  static geteFileNameAndType(value: string): string {
    // 解码URL并提取路径部分
    const url = decodeURIComponent(value);
    // 提取文件名（最后一个斜杠后的内容，问号前的部分）
    const pathParts = url.split('/');
    const fileNameWithQuery = pathParts[pathParts.length - 1];
    const fileName = fileNameWithQuery.split('?')[0];
    return fileName;
  }
}
