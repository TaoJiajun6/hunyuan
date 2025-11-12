import { cloudStorage } from '@kit.CloudFoundationKit';
import { BusinessError, request } from '@kit.BasicServicesKit';
import { Logger } from 'lib_common';
import { SongItem } from 'module_musicplay';
import { GlobalContext } from './GlobalContext';
import { common } from '@kit.AbilityKit';

const TAG = 'CloudStorageMusicUtils';

/**
 * 云存储音频文件信息
 */
export interface CloudAudioFile {
  fileName: string;
  filePath: string;
  downloadUrl?: string;
}

/**
 * 云存储音频工具类
 * 用于从云存储获取音频文件列表并转换为播放器所需的 SongItem
 */
export class CloudStorageMusicUtils {
  private static storageBucket: cloudStorage.StorageBucket | null = null;

  /**
   * 获取云存储实例
   */
  private static getStorageBucket(): cloudStorage.StorageBucket {
    if (!CloudStorageMusicUtils.storageBucket) {
      CloudStorageMusicUtils.storageBucket = cloudStorage.bucket();
    }
    return CloudStorageMusicUtils.storageBucket;
  }

  /**
   * 从 URL 或路径中提取云侧路径（outputs/... 开头）
   * @param pathOrUrl 云侧路径或下载 URL
   */
  public static extractCloudPath(pathOrUrl: string): string | null {
    if (!pathOrUrl) {
      return null;
    }
    try {
      // 如果本身就是 outputs 开头的相对路径
      if (pathOrUrl.startsWith('outputs/')) {
        return pathOrUrl;
      }
      // URL 中包含 /outputs/ 的情况
      const outputsIndex = pathOrUrl.indexOf('/outputs/');
      if (outputsIndex !== -1) {
        return pathOrUrl.substring(outputsIndex + 1); // 去掉开头的 /
      }
      // 匹配路径中的 outputs 段
      const match = pathOrUrl.match(/outputs\/[\w\d\/\-\.]+\.(wav|mp3|m4a|aac|flac|ogg|wma)/i);
      if (match && match[0]) {
        return match[0];
      }
    } catch (error) {
      Logger.warn(TAG, `extractCloudPath 解析失败: ${error}`);
    }
    return null;
  }

  /**
   * 根据路径获取文件名
   */
  public static getFileName(path: string, defaultPrefix: string = 'audio'): string {
    const normalized = path.replace(/\\/g, '/');
    const name = normalized.split('/').pop();
    if (name && name.length > 0) {
      return name;
    }
    return `${defaultPrefix}_${Date.now()}.wav`;
  }

  /**
   * 规范化路径，确保路径格式正确
   * @param path 路径
   * @returns 规范化后的路径
   */
  private static normalizePath(path: string): string {
    // 移除开头的斜杠，统一使用相对路径
    let normalized = path.replace(/^\/+/, '');
    // 确保路径以斜杠结尾（如果是目录）
    if (!normalized.endsWith('/') && normalized !== '') {
      normalized = normalized + '/';
    }
    return normalized;
  }

  /**
   * 获取云存储中的音频文件列表
   * @param directoryPath 目录路径，默认为 'outputs/podcasts/'（播客音频存储目录）
   * @returns Promise<CloudAudioFile[]> 音频文件列表
   */
  static async getAudioFileList(directoryPath: string = 'outputs/podcasts/'): Promise<CloudAudioFile[]> {
    try {
      // 规范化目录路径
      const normalizedPath = CloudStorageMusicUtils.normalizePath(directoryPath);
      const bucket = CloudStorageMusicUtils.getStorageBucket();
      const result: cloudStorage.ListResults = await bucket.list(normalizedPath);
      
      Logger.info(TAG, `获取文件列表成功，路径: ${normalizedPath}, 结果: ${JSON.stringify(result)}`);
      
      const audioFiles: CloudAudioFile[] = [];
      
      // 处理文件列表
      if (result.files && result.files.length > 0) {
        for (const fileName of result.files) {
          // 处理文件名和完整路径
          const isFullPath = fileName.includes('/');
          const fullPath = isFullPath ? fileName : `${normalizedPath}${fileName}`;
          const displayName = fullPath.split('/').pop() ?? fileName;

          if (CloudStorageMusicUtils.isAudioFile(displayName)) {
            audioFiles.push({
              fileName: displayName,
              filePath: fullPath
            });
          }
        }
      }
      
      // 递归处理子目录
      if (result.directories && result.directories.length > 0) {
        for (const dir of result.directories) {
          // 规范化子目录名，移除可能的前缀
          let subDirName = dir.replace(/^\/+/, ''); // 移除开头的斜杠
          if (!subDirName.endsWith('/')) {
            subDirName = subDirName + '/';
          }
          
          // 检查子目录名是否已经包含完整路径
          // 如果子目录名已经以 outputs/ 开头，说明是完整路径，直接使用
          // 否则拼接当前路径
          let subDirPath: string;
          if (subDirName.startsWith('outputs/')) {
            subDirPath = subDirName;
          } else {
            subDirPath = `${normalizedPath}${subDirName}`;
          }
          
          // 再次规范化，避免重复
          subDirPath = CloudStorageMusicUtils.normalizePath(subDirPath);
          
          try {
            Logger.info(TAG, `处理子目录: ${subDirPath}`);
            const subFiles = await CloudStorageMusicUtils.getAudioFileList(subDirPath);
            audioFiles.push(...subFiles);
          } catch (error) {
            Logger.error(TAG, `获取子目录 ${subDirPath} 文件列表失败: ${error}`);
          }
        }
      }
      
      return audioFiles;
    } catch (error) {
      const err = error as BusinessError;
      Logger.error(TAG, `获取文件列表失败, code: ${err.code}, message: ${err.message}`);
      // 发生错误时返回空数组，而不是抛出异常
      return [];
    }
  }

  /**
   * 检查文件是否为音频文件
   * @param fileName 文件名
   * @returns 是否为音频文件
   */
  private static isAudioFile(fileName: string): boolean {
    const audioExtensions = ['.wav', '.mp3', '.m4a', '.aac', '.flac', '.ogg', '.wma'];
    const lowerFileName = fileName.toLowerCase();
    return audioExtensions.some(ext => lowerFileName.endsWith(ext));
  }

  /**
   * 获取云存储文件的下载URL
   * @param filePath 云侧文件路径
   * @returns Promise<string> 下载URL
   */
  static async getDownloadUrl(filePath: string): Promise<string> {
    try {
      const bucket = CloudStorageMusicUtils.getStorageBucket();
      const downloadUrl = await bucket.getDownloadURL(filePath);
      Logger.info(TAG, `获取下载URL成功: ${downloadUrl}`);
      return downloadUrl;
    } catch (error) {
      const err = error as BusinessError;
      Logger.error(TAG, `获取下载URL失败, code: ${err.code}, message: ${err.message}`);
      const errorObj = new Error(`获取下载URL失败: code=${err.code}, message=${err.message}`);
      throw errorObj;
    }
  }

  /**
   * 将云存储音频文件转换为 SongItem
   * @param audioFile 云存储音频文件信息
   * @returns Promise<SongItem> SongItem 对象
   */
  static async convertToSongItem(audioFile: CloudAudioFile): Promise<SongItem> {
    const songItem = new SongItem();
    
    // 生成唯一ID
    songItem.id = `cloud_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    // 从文件名提取标题（去掉扩展名）
    const fileNameWithoutExt = audioFile.fileName.replace(/\.[^/.]+$/, '');
    songItem.title = fileNameWithoutExt;
    songItem.singer = '云存储音频';
    
    // 直接下载文件到本地，不通过URL形式
    try {
      Logger.info(TAG, `开始下载文件到本地: ${audioFile.filePath}`);
      const localPath = await CloudStorageMusicUtils.downloadFile(audioFile.filePath, audioFile.fileName, true);
      // 使用本地文件路径，MediaService 会识别为沙箱文件
      songItem.src = localPath;
      songItem.isLocal = true;
      Logger.info(TAG, `文件已下载到本地: ${localPath}`);
    } catch (downloadError) {
      Logger.error(TAG, `下载文件失败: ${downloadError}`);
      // 如果下载失败，设置为空字符串，后续播放时会跳过
      songItem.src = '';
    }
    
    // 设置其他属性
    songItem.mark = '1';
    songItem.label = $r('app.media.ic_music_icon');
    songItem.lyric = '';
    songItem.isCollected = false;
    songItem.mvUrl = '';
    songItem.isVip = false;
    songItem.collectedCount = 0;
    songItem.playlistCount = 0;
    songItem.downloadCount = 0;
    songItem.shareCount = 0;
    
    return songItem;
  }

  /**
   * 批量将云存储音频文件转换为 SongItem 列表
   * @param audioFiles 云存储音频文件列表
   * @returns Promise<SongItem[]> SongItem 列表（只包含成功转换的项，src 不为空的项）
   */
  static async convertToSongItemList(audioFiles: CloudAudioFile[]): Promise<SongItem[]> {
    const songItems: SongItem[] = [];
    
    for (const audioFile of audioFiles) {
      try {
        const songItem = await CloudStorageMusicUtils.convertToSongItem(audioFile);
        // 只添加成功下载到本地的项（src不为空）
        if (songItem.src && songItem.src !== '') {
          songItems.push(songItem);
        } else {
          Logger.warn(TAG, `跳过文件 ${audioFile.fileName}，下载失败`);
        }
      } catch (error) {
        Logger.error(TAG, `转换文件 ${audioFile.fileName} 失败: ${error}`);
      }
    }
    
    return songItems;
  }

  /**
   * 从云存储导入音频到播放列表
   * @param directoryPath 目录路径，默认为 'outputs/podcasts/'
   * @returns Promise<SongItem[]> 导入的音频列表
   */
  static async importAudioFromCloudStorage(directoryPath: string = 'outputs/podcasts/'): Promise<SongItem[]> {
    try {
      // 获取音频文件列表
      const audioFiles = await CloudStorageMusicUtils.getAudioFileList(directoryPath);
      Logger.info(TAG, `找到 ${audioFiles.length} 个音频文件`);
      
      if (audioFiles.length === 0) {
        return [];
      }
      
      // 转换为 SongItem 列表
      const songItems = await CloudStorageMusicUtils.convertToSongItemList(audioFiles);
      Logger.info(TAG, `成功转换 ${songItems.length} 个音频文件`);
      
      return songItems;
    } catch (error) {
      Logger.error(TAG, `从云存储导入音频失败: ${error}`);
      return [];
    }
  }

  /**
   * 下载云侧文件至本地
   * @param cloudPath 云侧文件路径
   * @param localPath 本地文件路径（相对于 context.cacheDir），文件将会保存在context.cacheDir目录下
   * @param overwrite 是否覆盖已存在的文件，默认为 true
   * @param onProgress 下载进度回调函数
   * @returns Promise<string> 下载完成后的本地文件路径
   */
  static async downloadFile(
    cloudPath: string,
    localPath?: string,
    overwrite: boolean = true,
    onProgress?: (progress: request.agent.Progress) => void
  ): Promise<string> {
    return new Promise<string>((resolve, reject) => {
      let context = GlobalContext.getContext();
      if (!context) {
        const storedContext = AppStorage.get('context') as common.UIAbilityContext | undefined;
        if (storedContext) {
          GlobalContext.initContext(storedContext);
          context = storedContext;
        }
      }

      if (!context) {
        const errorObj = new Error('无法获取上下文，请确保GlobalContext已初始化');
        reject(errorObj);
        return;
      }

      const uiContext: common.UIAbilityContext = context;

      // 如果没有指定本地路径，使用文件名
      const finalLocalPath = localPath || cloudPath.split('/').pop() || `file_${Date.now()}`;

      const bucket = CloudStorageMusicUtils.getStorageBucket();
      // 获取云存储默认实例中文件，保存至本地
      bucket.downloadFile(uiContext, {
        localPath: finalLocalPath, // 文件将会保存在context.cacheDir目录下
        cloudPath: cloudPath, // 云侧文件路径，支持传入"文件目录/文件名"，或仅传入文件名
        overwrite: overwrite
      }).then((task: request.agent.Task) => {
        // 监听下载进度
        task.on('progress', (progress: request.agent.Progress) => {
          Logger.info(TAG, `下载进度: ${JSON.stringify(progress)}`);
          if (onProgress) {
            onProgress(progress);
          }
        });

        // 监听下载完成
        task.on('completed', (progress: request.agent.Progress) => {
          Logger.info(TAG, `下载完成: ${JSON.stringify(progress)}`);
          // 文件已保存在 context.cacheDir 目录下，返回完整路径
          const localFilePath = `${uiContext.cacheDir}/${finalLocalPath}`;
          Logger.info(TAG, `文件下载成功: ${localFilePath}`);
          resolve(localFilePath);
        });

        // 监听下载失败
        task.on('failed', (progress: request.agent.Progress) => {
          Logger.error(TAG, `下载失败: ${JSON.stringify(progress)}`);
          const errorObj = new Error(`文件下载失败: ${JSON.stringify(progress)}`);
          reject(errorObj);
        });

        // 监听响应
        task.on('response', (response) => {
          Logger.info(TAG, `下载响应: ${JSON.stringify(response)}`);
        });

        // 启动下载任务
        task.start((err: BusinessError) => {
          if (err) {
            Logger.error(TAG, `启动下载任务失败, code: ${err.code}, message: ${err.message}`);
            const errorObj = new Error(`启动下载任务失败: code=${err.code}, message=${err.message}`);
            reject(errorObj);
          } else {
            Logger.info(TAG, `下载任务已启动, taskId: ${task.tid}`);
          }
        });
      }).catch((err: BusinessError) => {
        Logger.error(TAG, `创建下载任务失败, code: ${err.code}, message: ${err.message}`);
        const errorObj = new Error(`创建下载任务失败: code=${err.code}, message=${err.message}`);
        reject(errorObj);
      });
    });
  }

  /**
   * 批量下载云侧文件至本地
   * @param cloudPaths 云侧文件路径列表
   * @param overwrite 是否覆盖已存在的文件，默认为 true
   * @param onProgress 单个文件下载进度回调函数
   * @returns Promise<string[]> 下载完成后的本地文件路径列表
   */
  static async downloadFiles(
    cloudPaths: string[],
    overwrite: boolean = true,
    onProgress?: (cloudPath: string, progress: request.agent.Progress) => void
  ): Promise<string[]> {
    const localPaths: string[] = [];
    
    for (const cloudPath of cloudPaths) {
      try {
        const localPath = await CloudStorageMusicUtils.downloadFile(
          cloudPath,
          undefined,
          overwrite,
          onProgress ? (progress) => onProgress(cloudPath, progress) : undefined
        );
        localPaths.push(localPath);
      } catch (error) {
        Logger.error(TAG, `下载文件 ${cloudPath} 失败: ${error}`);
        // 继续下载其他文件，不中断整个流程
      }
    }
    
    return localPaths;
  }
}

