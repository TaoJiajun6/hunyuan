import { cloudStorage } from '@kit.CloudFoundationKit';
import { BusinessError, request } from '@kit.BasicServicesKit';
import { Logger } from 'lib_common';
import { SongItem } from 'module_musicplay';
import { GlobalContext } from './GlobalContext';
import { common } from '@kit.AbilityKit';
import fs from '@ohos.file.fs';

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
   * 根据云存储路径生成稳定的本地文件路径
   * @param cloudPath 云存储路径
   * @param context 应用上下文
   * @returns 本地文件路径
   */
  private static getLocalFilePath(cloudPath: string, context: common.UIAbilityContext): string {
    // 使用云存储路径生成稳定的本地路径（将路径中的斜杠替换为下划线）
    const safePath = cloudPath.replace(/\//g, '_').replace(/\\/g, '_');
    // 保存到 filesDir/podcasts/ 目录，这是一个持久化目录
    const podcastsDir = `${context.filesDir}/podcasts`;
    // 确保目录存在
    try {
      if (!fs.accessSync(podcastsDir)) {
        fs.mkdirSync(podcastsDir, true);
      }
    } catch (err) {
      Logger.warn(TAG, `创建目录失败，尝试继续: ${err}`);
    }
    return `${podcastsDir}/${safePath}`;
  }

  /**
   * 检查本地文件是否存在
   * @param filePath 文件路径
   * @returns 文件是否存在
   */
  private static isLocalFileExists(filePath: string): boolean {
    try {
      return fs.accessSync(filePath);
    } catch {
      return false;
    }
  }

  /**
   * 将云存储音频文件转换为 SongItem
   * @param audioFile 云存储音频文件信息
   * @returns Promise<SongItem> SongItem 对象
   */
  static async convertToSongItem(audioFile: CloudAudioFile): Promise<SongItem> {
    const songItem = new SongItem();
    
    // 生成唯一ID（基于云存储路径，确保相同文件有相同ID）
    const pathHash = audioFile.filePath.replace(/\//g, '_').replace(/\\/g, '_');
    songItem.id = `cloud_${pathHash}`;
    
    // 从文件名提取标题（去掉扩展名）
    const fileNameWithoutExt = audioFile.fileName.replace(/\.[^/.]+$/, '');
    songItem.title = fileNameWithoutExt;
    songItem.singer = '云存储音频';
    
    // 获取上下文
    let context = GlobalContext.getContext();
    if (!context) {
      const storedContext = AppStorage.get('context') as common.UIAbilityContext | undefined;
      if (storedContext) {
        GlobalContext.initContext(storedContext);
        context = storedContext;
      }
    }
    
    if (!context) {
      Logger.error(TAG, '无法获取上下文，无法下载文件');
      songItem.src = '';
      return songItem;
    }
    
    // 生成本地文件路径
    const localFilePath = CloudStorageMusicUtils.getLocalFilePath(audioFile.filePath, context);
    
    // 检查文件是否已存在
    if (CloudStorageMusicUtils.isLocalFileExists(localFilePath)) {
      Logger.info(TAG, `文件已存在，跳过下载: ${localFilePath}`);
      songItem.src = localFilePath;
      songItem.isLocal = true;
    } else {
      // 文件不存在，需要下载
      try {
        Logger.info(TAG, `开始下载文件到本地: ${audioFile.filePath}`);
        // 使用文件名作为下载路径，但保存到持久化目录
        const downloadedPath = await CloudStorageMusicUtils.downloadFileToPersistent(
          audioFile.filePath,
          localFilePath,
          false // 不覆盖已存在的文件
        );
        songItem.src = downloadedPath;
        songItem.isLocal = true;
        Logger.info(TAG, `文件已下载到本地: ${downloadedPath}`);
      } catch (downloadError) {
        Logger.error(TAG, `下载文件失败: ${downloadError}`);
        // 如果下载失败，设置为空字符串，后续播放时会跳过
        songItem.src = '';
      }
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
   * 下载云侧文件至持久化目录
   * @param cloudPath 云侧文件路径
   * @param targetPath 目标文件完整路径（绝对路径）
   * @param overwrite 是否覆盖已存在的文件，默认为 false
   * @param onProgress 下载进度回调函数
   * @returns Promise<string> 下载完成后的本地文件路径
   */
  static async downloadFileToPersistent(
    cloudPath: string,
    targetPath: string,
    overwrite: boolean = false,
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

      // 检查文件是否已存在
      if (!overwrite && CloudStorageMusicUtils.isLocalFileExists(targetPath)) {
        Logger.info(TAG, `文件已存在，跳过下载: ${targetPath}`);
        resolve(targetPath);
        return;
      }

      // 确保目标目录存在
      const targetDir = targetPath.substring(0, targetPath.lastIndexOf('/'));
      try {
        if (!fs.accessSync(targetDir)) {
          fs.mkdirSync(targetDir, true);
        }
      } catch (err) {
        Logger.warn(TAG, `创建目录失败: ${err}`);
      }

      const uiContext: common.UIAbilityContext = context;
      // 提取文件名（相对路径，用于bucket.downloadFile的localPath参数）
      const fileName = targetPath.split('/').pop() || cloudPath.split('/').pop() || `file_${Date.now()}`;
      const tempFileName = `temp_${Date.now()}_${fileName}`;

      const bucket = CloudStorageMusicUtils.getStorageBucket();
      // 先下载到临时位置（cacheDir），然后移动到目标位置（filesDir）
      // localPath 应该是相对路径，文件会保存在 context.cacheDir/localPath
      bucket.downloadFile(uiContext, {
        localPath: tempFileName, // 相对路径，文件会保存在 context.cacheDir/tempFileName
        cloudPath: cloudPath,
        overwrite: true
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
          // bucket.downloadFile 会将文件保存到 context.cacheDir/localPath
          const tempFilePath = `${uiContext.cacheDir}/${tempFileName}`;
          
          // 将文件从临时位置移动到目标位置
          try {
            if (fs.accessSync(tempFilePath)) {
              // 如果目标文件已存在，先删除
              if (CloudStorageMusicUtils.isLocalFileExists(targetPath)) {
                fs.unlinkSync(targetPath);
              }
              // 复制文件到目标位置
              fs.copyFileSync(tempFilePath, targetPath);
              // 删除临时文件
              fs.unlinkSync(tempFilePath);
              Logger.info(TAG, `文件已移动到持久化目录: ${targetPath}`);
              resolve(targetPath);
            } else {
              reject(new Error('下载的文件不存在'));
            }
          } catch (moveError) {
            Logger.error(TAG, `移动文件失败: ${moveError}`);
            // 如果移动失败，尝试使用临时文件路径
            if (fs.accessSync(tempFilePath)) {
              Logger.warn(TAG, `使用临时文件路径: ${tempFilePath}`);
              resolve(tempFilePath);
            } else {
              reject(new Error(`移动文件失败: ${moveError}`));
            }
          }
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
   * 下载云侧文件至本地（兼容旧方法，保存到cacheDir）
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

