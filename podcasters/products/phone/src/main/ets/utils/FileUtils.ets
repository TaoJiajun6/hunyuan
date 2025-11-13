import { picker } from '@kit.CoreFileKit';
import { BusinessError, request } from '@kit.BasicServicesKit';
import { promptAction } from '@kit.ArkUI';
import { util } from '@kit.ArkTS';
import { common } from '@kit.AbilityKit';
import { cloudStorage } from '@kit.CloudFoundationKit';
import fs from '@ohos.file.fs';
import { GlobalContext } from '../common/GlobalContext';
import { Logger } from 'lib_common';

const TAG = '[FileUtils]';

/**
 * 音频文件信息
 */
export interface AudioFileInfo {
  /** 文件数据（Uint8Array），使用云存储时为空数组 */
  data: Uint8Array;
  /** Base64编码的音频数据，使用云存储时为空字符串 */
  base64: string;
  /** 文件URI */
  uri: string;
  /** 文件名 */
  fileName: string;
  /** 文件大小（字节） */
  fileSize: number;
  /** 云存储路径（如果已上传） */
  cloudPath?: string;
  /** 云存储下载URL（如果已上传） */
  cloudUrl?: string;
}

/**
 * 文本文件信息
 */
export interface TextFileInfo {
  /** 文件URI */
  uri: string;
  /** 文件名 */
  fileName: string;
  /** 文件大小（字节） */
  fileSize: number;
  /** 文件内容（如果读取了） */
  content?: string;
  /** 云存储路径（如果已上传） */
  cloudPath?: string;
  /** 云存储下载URL（如果已上传） */
  cloudUrl?: string;
}

/**
 * 云存储上传结果
 */
interface CloudStorageInfo {
  /** 云存储路径 */
  cloudPath: string;
  /** 云存储下载URL */
  cloudUrl: string;
}

/**
 * 云存储上传进度信息
 */
interface UploadProgressInfo {
  /** 上传状态（32=上传中，65=失败） */
  state?: number;
  /** 任务索引 */
  index?: number;
  /** 已处理的字节数 */
  processed?: number;
  /** 文件大小数组 */
  sizes?: number[];
  /** 额外信息 */
  extras?: Record<string, string | number | boolean | null>;
}

/**
 * 云存储上传响应信息
 */
interface UploadResponseInfo {
  /** HTTP状态码 */
  statusCode?: number;
  /** 响应头 */
  headers?: Record<string, string>;
  /** 响应体 */
  body?: string | Record<string, string | number | boolean | null>;
}

/**
 * 文件工具类
 */
export class FileUtils {
  // 云存储实例
  private static storageBucket: cloudStorage.StorageBucket | null = null;

  /**
   * 获取云存储实例
   */
  private static getStorageBucket(): cloudStorage.StorageBucket {
    if (!FileUtils.storageBucket) {
      Logger.info(TAG, `初始化云存储实例...`);
      FileUtils.storageBucket = cloudStorage.bucket();
      Logger.info(TAG, `云存储实例初始化完成`);
    }
    return FileUtils.storageBucket;
  }

  /**
   * 选择音频文件并返回文件信息
   * 使用DocumentViewPicker从文件系统中选择音频文件
   * @param context UIAbility上下文，如果未提供则使用GlobalContext获取
   * @param uploadToCloud 是否上传到云存储，默认false
   *                      - true: 上传到云存储，不读取文件内容，不计算base64，返回cloudUrl
   *                      - false: 读取文件内容并转换为base64，不上传到云存储
   * @returns 音频文件信息，包括数据、base64、URI等（使用云存储时base64为空字符串，data为空数组）
   */
  static async pickAudioFile(
    context?: common.UIAbilityContext,
    uploadToCloud: boolean = false
  ): Promise<AudioFileInfo | null> {
    try {
      // 获取上下文
      let uiContext: common.UIAbilityContext | null = null;
      if (context) {
        uiContext = context;
      } else {
        // 使用GlobalContext获取上下文
        uiContext = GlobalContext.getContext();
        if (!uiContext) {
          throw new Error('无法获取上下文，请传入context参数或确保GlobalContext已初始化');
        }
      }

      // 使用DocumentViewPicker选择文件（需要传入context）
      const documentViewPicker = new picker.DocumentViewPicker(uiContext);
      const documentSelectOptions = new picker.DocumentSelectOptions();

      // 设置文件类型过滤器，只显示音频文件（使用文件扩展名）
      documentSelectOptions.fileSuffixFilters = ['.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac', '.wma', '.amr', '.mp4', '.3gp'];
      documentSelectOptions.maxSelectNumber = 1;

      const documentSelectResult = await documentViewPicker.select(documentSelectOptions);
      // DocumentViewPicker返回的是字符串数组（URI数组）
      if (documentSelectResult && documentSelectResult.length > 0) {
        const fileUri = documentSelectResult[0];

        // 提取文件名
        const fileName = fileUri.split('/').pop() || `audio_${Date.now()}.wav`;

        // 获取文件大小（不读取文件内容）
        let file: fs.File | null = null;
        let fileSize = 0;
        try {
          file = fs.openSync(fileUri, fs.OpenMode.READ_ONLY);
          const stat = fs.statSync(file.fd);
          fileSize = stat.size;
          fs.closeSync(file);
          file = null;
        } catch (error) {
          if (file) {
            fs.closeSync(file);
          }
          // ArkTS要求throw Error类型，需要转换
          const err = error as BusinessError;
          throw new Error(err.message || String(error));
        }

        const fileSizeMB = fileSize / (1024 * 1024);

        // 如果使用云存储，直接上传，不读取文件内容
        if (uploadToCloud) {
          const cloudInfo = await FileUtils.uploadAudioToCloud(uiContext, fileUri, fileName);
          if (!cloudInfo) {
            promptAction.showToast({
              message: '文件上传到云存储失败',
              duration: 2000
            });
            return null;
          }

          // 构建文件信息（不包含文件数据和base64）
          const fileInfo: AudioFileInfo = {
            data: new Uint8Array(0), // 使用云存储时不需要文件数据
            base64: '', // 使用云存储时不需要base64
            uri: fileUri,
            fileName: fileName,
            fileSize: fileSize,
            cloudPath: cloudInfo.cloudPath,
            cloudUrl: cloudInfo.cloudUrl
          };

          promptAction.showToast({
            message: `文件选择成功 (${fileSizeMB.toFixed(2)}MB)，已上传到云存储`,
            duration: 2000
          });

          return fileInfo;
        } else {
          // 不使用云存储，读取文件内容并转换为base64
          let file: fs.File | null = null;
          try {
            file = fs.openSync(fileUri, fs.OpenMode.READ_ONLY);
            const buffer = new ArrayBuffer(fileSize);
            fs.readSync(file.fd, buffer);
            fs.closeSync(file);
            file = null;

            const audioData = new Uint8Array(buffer);
            const base64 = FileUtils.uint8ArrayToBase64(audioData);

            // 构建文件信息
            const fileInfo: AudioFileInfo = {
              data: audioData,
              base64: base64,
              uri: fileUri,
              fileName: fileName,
              fileSize: fileSize
            };

            promptAction.showToast({
              message: `文件选择成功 (${fileSizeMB.toFixed(2)}MB)`,
              duration: 2000
            });

            return fileInfo;
          } finally {
            if (file) {
              fs.closeSync(file);
            }
          }
        }
      }
      return null;
    } catch (error) {
      const err = error as BusinessError;
      const errorMessage = err.message || String(error);
      Logger.error(TAG, `选择文件失败: ${errorMessage}`);
      promptAction.showToast({
        message: `选择文件失败: ${errorMessage}`,
        duration: 2000
      });
      return null;
    }
  }

  /**
   * 上传音频文件到云存储
   * 请确认已通过AuthProvider获取用户凭据。未配置用户凭据的情况下，服务端会返回"403 Forbidden"错误。
   * @param context UIAbility上下文
   * @param fileUri 文件URI
   * @param fileName 文件名
   * @returns 云存储路径和下载URL
   */
  static async uploadAudioToCloud(
    context: common.UIAbilityContext,
    fileUri: string,
    fileName: string
  ): Promise<CloudStorageInfo | null> {
    // 复用通用上传方法
    return await FileUtils.uploadFileToCloud(context, fileUri, fileName);
  }

  /**
   * 上传背景音乐文件到云存储的music目录
   * @param context UIAbility上下文
   * @param fileUri 文件URI
   * @param fileName 文件名（可选，如果不提供则从fileUri提取）
   * @returns 云存储路径和下载URL
   */
  static async uploadBackgroundMusicToCloud(
    context: common.UIAbilityContext,
    fileUri: string,
    fileName?: string
  ): Promise<CloudStorageInfo | null> {
    // 如果没有提供文件名，从URI中提取
    if (!fileName) {
      const uriParts = fileUri.split('/');
      fileName = uriParts[uriParts.length - 1];
    }
    
    // 生成云存储路径（上传到music目录）
    const cloudPath = `music/${fileName}`;
    const cacheFile = context.cacheDir + '/' + fileName;
    
    Logger.info(TAG, `开始上传背景音乐到云存储: ${cloudPath}`);
    
    // 将文件复制到cache目录
    let srcFile: fs.File | null = null;
    let dstFile: fs.File | null = null;
    try {
      srcFile = fs.openSync(fileUri, fs.OpenMode.READ_ONLY);
      dstFile = fs.openSync(cacheFile, fs.OpenMode.READ_WRITE | fs.OpenMode.CREATE);
      fs.copyFileSync(srcFile.fd, dstFile.fd);
      fs.closeSync(srcFile);
      fs.closeSync(dstFile);
      srcFile = null;
      dstFile = null;
    } catch (copyError) {
      Logger.error(TAG, `复制文件失败: ${JSON.stringify(copyError)}`);
      if (srcFile) fs.closeSync(srcFile);
      if (dstFile) fs.closeSync(dstFile);
      return null;
    }
    
    // 检查文件是否存在
    try {
      const fileStat = fs.statSync(cacheFile);
      const fileSizeMB = fileStat.size / (1024 * 1024);
      Logger.info(TAG, `准备上传背景音乐: ${cacheFile}, 大小: ${fileSizeMB.toFixed(2)}MB`);
    } catch (statError) {
      Logger.error(TAG, `文件不存在或无法访问: ${cacheFile}`);
      return null;
    }
    
    // 上传到云存储
    const bucket = FileUtils.getStorageBucket();
    Logger.info(TAG, `开始创建上传任务: localPath=${cacheFile}, cloudPath=${cloudPath}`);
    
    return new Promise<CloudStorageInfo | null>((resolve) => {
      bucket.uploadFile(context, {
        localPath: cacheFile,
        cloudPath: cloudPath
      }).then((task: request.agent.Task) => {
        Logger.info(TAG, `背景音乐上传任务创建成功`);
        
        task.on('progress', (progress: Object) => {
          const progressInfo = progress as UploadProgressInfo;
          const state = progressInfo.state;
          const processed = progressInfo.processed || 0;
          const sizes = progressInfo.sizes || [0];
          const fileSize = sizes[0] || 0;
          const fileSizeMB = fileSize / (1024 * 1024);
          const processedMB = processed / (1024 * 1024);
          const progressPercent = fileSize > 0 ? ((processed / fileSize) * 100).toFixed(2) : '0';
          
          Logger.info(TAG, `背景音乐上传进度: ${processedMB.toFixed(2)}MB/${fileSizeMB.toFixed(2)}MB (${progressPercent}%)`);
        });
        
        task.on('completed', async (progress: Object) => {
          const progressInfo = progress as UploadProgressInfo;
          Logger.info(TAG, `背景音乐上传完成: ${JSON.stringify(progress)}`);
          
          try {
            // 获取下载URL
            Logger.info(TAG, `开始获取背景音乐下载URL: ${cloudPath}`);
            const downloadUrl = await bucket.getDownloadURL(cloudPath);
            Logger.info(TAG, `获取背景音乐下载URL成功: ${downloadUrl}`);
            
            // 删除临时文件
            fs.unlink(cacheFile).catch((err: BusinessError) => {
              Logger.warn(TAG, `删除临时文件失败: ${err.message}`);
            });
            
            resolve({
              cloudPath: cloudPath,
              cloudUrl: downloadUrl
            });
          } catch (error) {
            const err = error as BusinessError;
            Logger.error(TAG, `获取背景音乐下载URL失败: ${err.message || String(error)}`);
            resolve(null);
          }
        });
        
        task.on('failed', (progress: Object) => {
          Logger.error(TAG, `背景音乐上传失败: ${JSON.stringify(progress)}`);
          resolve(null);
        });
        
        // 启动上传任务
        task.start((err: BusinessError) => {
          if (err) {
            Logger.error(TAG, `启动背景音乐上传任务失败: ${err.message || String(err)}`);
            resolve(null);
          }
        });
      }).catch((err: BusinessError) => {
        Logger.error(TAG, `创建背景音乐上传任务失败: ${err.message || String(err)}`);
        resolve(null);
      });
    });
  }

  /**
   * 通用文件上传到云存储（供音频和文本文件共用）
   * @param context UIAbility上下文
   * @param fileUri 文件URI
   * @param fileName 文件名
   * @returns 云存储路径和下载URL
   */
  private static async uploadFileToCloud(
    context: common.UIAbilityContext,
    fileUri: string,
    fileName: string
  ): Promise<CloudStorageInfo | null> {
    return new Promise<CloudStorageInfo | null>(async (resolve) => {
      try {
        //生成云存储路径
        const cloudPath = `hunyuan/${fileName}`;
        const cacheFile = context.cacheDir + '/' + fileName;
        
        Logger.info(TAG, `开始上传文件到云存储: ${cloudPath}`);
        
        // 将文件复制到cache目录
        let srcFile: fs.File | null = null;
        let dstFile: fs.File | null = null;
        try {
          srcFile = fs.openSync(fileUri, fs.OpenMode.READ_ONLY);
          dstFile = fs.openSync(cacheFile, fs.OpenMode.READ_WRITE | fs.OpenMode.CREATE);
          fs.copyFileSync(srcFile.fd, dstFile.fd);
          fs.closeSync(srcFile);
          fs.closeSync(dstFile);
          srcFile = null;
          dstFile = null;
        } catch (copyError) {
          Logger.error(TAG, `复制文件失败: ${JSON.stringify(copyError)}`);
          if (srcFile) fs.closeSync(srcFile);
          if (dstFile) fs.closeSync(dstFile);
          resolve(null);
          return;
        }
        
        // 检查文件是否存在
        try {
          const fileStat = fs.statSync(cacheFile);
          const fileSizeMB = fileStat.size / (1024 * 1024);
          Logger.info(TAG, `准备上传文件: ${cacheFile}, 大小: ${fileSizeMB.toFixed(2)}MB`);
        } catch (statError) {
          Logger.error(TAG, `文件不存在或无法访问: ${cacheFile}`);
          resolve(null);
          return;
        }
        
        // 上传到云存储
        const bucket = FileUtils.getStorageBucket();
        Logger.info(TAG, `开始创建上传任务: localPath=${cacheFile}, cloudPath=${cloudPath}`);
        
        bucket.uploadFile(context, {
          localPath: cacheFile,
          cloudPath: cloudPath
        }).then((task: request.agent.Task) => {
          Logger.info(TAG, `上传任务创建成功`);
          
          // 监听response事件，获取更详细的错误信息
          task.on('response', (response: Object) => {
            Logger.info(TAG, `上传响应: ${JSON.stringify(response)}`);
            // 检查响应中的错误信息
            if (response && typeof response === 'object') {
              const resp = response as UploadResponseInfo;
              if (resp.statusCode && resp.statusCode !== 200) {
                Logger.error(TAG, `HTTP状态码: ${resp.statusCode}`);
              }
              if (resp.headers) {
                Logger.info(TAG, `响应头: ${JSON.stringify(resp.headers)}`);
              }
              if (resp.body) {
                Logger.info(TAG, `响应体: ${JSON.stringify(resp.body)}`);
              }
            }
          });
          
          task.on('progress', (progress: Object) => {
            // 解析进度信息
            const progressInfo = progress as UploadProgressInfo;
            const state = progressInfo.state;
            const processed = progressInfo.processed || 0;
            const sizes = progressInfo.sizes || [0];
            const fileSize = sizes[0] || 0;
            const fileSizeMB = fileSize / (1024 * 1024);
            const processedMB = processed / (1024 * 1024);
            const progressPercent = fileSize > 0 ? ((processed / fileSize) * 100).toFixed(2) : '0';
            
            Logger.info(TAG, `上传进度: state=${state}, 已上传=${processedMB.toFixed(2)}MB/${fileSizeMB.toFixed(2)}MB (${progressPercent}%)`);
            
            // state=32 表示上传中
            if (state === 32) {
              Logger.info(TAG, `文件上传中...`);
            }
          });
          
          task.on('completed', async (progress: Object) => {
            const progressInfo = progress as UploadProgressInfo;
            Logger.info(TAG, `上传完成: state=${progressInfo.state}, ${JSON.stringify(progress)}`);
            
            try {
              // 获取下载URL
              Logger.info(TAG, `开始获取下载URL: ${cloudPath}`);
              const downloadUrl = await bucket.getDownloadURL(cloudPath);
              Logger.info(TAG, `获取下载URL成功: ${downloadUrl}`);
              
              // 删除临时文件
              fs.unlink(cacheFile).catch((err: BusinessError) => {
                Logger.warn(TAG, `删除临时文件失败: ${err.message}`);
              });
              
              resolve({
                cloudPath: cloudPath,
                cloudUrl: downloadUrl
              });
            } catch (urlError) {
              const urlErr = urlError as BusinessError;
              Logger.error(TAG, `获取下载URL失败: code=${urlErr.code}, message=${urlErr.message}`);
              // 即使获取URL失败，也返回云存储路径
              resolve({
                cloudPath: cloudPath,
                cloudUrl: ''
              });
            }
          });
          
          task.on('failed', (progress: Object) => {
            const progressInfo = progress as UploadProgressInfo;
            const state = progressInfo.state;
            const processed = progressInfo.processed || 0;
            const sizes = progressInfo.sizes || [0];
            const extras = progressInfo.extras || {};
            const fileSize = sizes[0] || 0;
            const fileSizeMB = fileSize / (1024 * 1024);
            const processedMB = processed / (1024 * 1024);
            
            Logger.error(TAG, `========== 上传失败 ==========`);
            Logger.error(TAG, `状态: state=${state} (32=上传中, 65=失败)`);
            Logger.error(TAG, `文件信息: 大小=${fileSizeMB.toFixed(2)}MB, 已上传=${processedMB.toFixed(2)}MB`);
            Logger.error(TAG, `云存储路径: ${cloudPath}`);
            Logger.error(TAG, `本地文件路径: ${cacheFile}`);
            Logger.error(TAG, `错误详情: ${JSON.stringify(extras)}`);
            Logger.error(TAG, `完整进度信息: ${JSON.stringify(progress)}`);
            
            // 分析失败原因
            if (state === 65) {
              Logger.error(TAG, `失败原因分析:`);
              
              // 检查extras是否为空
              const hasExtras = extras && Object.keys(extras).length > 0;
              if (hasExtras) {
                Logger.error(TAG, `错误详情 (extras): ${JSON.stringify(extras)}`);
                // 尝试提取具体的错误信息
                const extraKeys = Object.keys(extras);
                for (let i = 0; i < extraKeys.length; i++) {
                  const key = extraKeys[i];
                  const value = extras[key];
                  if (value !== null && value !== undefined) {
                    if (typeof value === 'string' && value.length > 0) {
                      Logger.error(TAG, `  ${key}: ${value}`);
                    } else {
                      Logger.error(TAG, `  ${key}: ${String(value)}`);
                    }
                  }
                }
              } else {
                Logger.error(TAG, `⚠️ 注意: extras为空，可能是云存储服务端配置问题`);
                Logger.error(TAG, `可能的原因:`);
                Logger.error(TAG, `  1. 云存储服务未正确初始化或配置`);
                Logger.error(TAG, `  2. AppGallery Connect中云存储服务未开通`);
                Logger.error(TAG, `  3. 云存储权限配置不正确（需要读写权限）`);
                Logger.error(TAG, `  4. 云存储实例未创建或配置错误`);
                Logger.error(TAG, `  5. 应用未正确关联到AppGallery Connect项目`);
                Logger.error(TAG, `  6. client_id配置错误（检查module.json5中的metadata）`);
              }
              
              Logger.error(TAG, `排查步骤:`);
              Logger.error(TAG, `  1. 登录 AppGallery Connect: https://developer.huawei.com/consumer/cn/service/josp/agc/index.html`);
              Logger.error(TAG, `  2. 选择项目，进入"云存储"服务`);
              Logger.error(TAG, `  3. 检查云存储服务是否已开通`);
              Logger.error(TAG, `  4. 检查存储实例是否已创建（默认实例或自定义实例）`);
              Logger.error(TAG, `  5. 检查云存储权限配置（安全 > 权限设置）`);
              Logger.error(TAG, `  6. 检查应用配置中的client_id是否正确`);
              Logger.error(TAG, `  7. 检查网络连接和防火墙设置`);
              Logger.error(TAG, `  8. 查看AppGallery Connect的错误日志`);
              
              Logger.error(TAG, `文件信息:`);
              Logger.error(TAG, `  文件名: ${fileName}`);
              Logger.error(TAG, `  文件大小: ${fileSizeMB.toFixed(2)}MB`);
              Logger.error(TAG, `  云存储路径: ${cloudPath}`);
              Logger.error(TAG, `  支持的文件格式: WAV, MP3, M4A, AAC, OGG, FLAC等`);
            }
            Logger.error(TAG, `============================`);
            
            // 删除临时文件
            fs.unlink(cacheFile).catch((err: BusinessError) => {
              Logger.warn(TAG, `删除临时文件失败: ${err.message}`);
            });
            
            resolve(null);
          });
          
          // 启动上传任务
          Logger.info(TAG, `启动上传任务...`);
          task.start((err: BusinessError) => {
            if (err) {
              Logger.error(TAG, `启动上传任务失败: code=${err.code}, message=${err.message}`);
              // 删除临时文件
              fs.unlink(cacheFile).catch((unlinkErr: BusinessError) => {
                Logger.warn(TAG, `删除临时文件失败: ${unlinkErr.message}`);
              });
              resolve(null);
            } else {
              Logger.info(TAG, `上传任务已启动: ${cloudPath}`);
            }
          });
        }).catch((err: BusinessError) => {
          Logger.error(TAG, `创建上传任务失败: code=${err.code}, message=${err.message}`);
          Logger.error(TAG, `可能原因:`);
          Logger.error(TAG, `1. 云存储未正确配置`);
          Logger.error(TAG, `2. 文件路径错误: ${cacheFile}`);
          Logger.error(TAG, `3. 云存储服务不可用`);
          // 删除临时文件
          fs.unlink(cacheFile).catch((unlinkErr: BusinessError) => {
            Logger.warn(TAG, `删除临时文件失败: ${unlinkErr.message}`);
          });
          resolve(null);
        });
      } catch (error) {
        Logger.error(TAG, `上传到云存储异常: ${JSON.stringify(error)}`);
        resolve(null);
      }
    });
  }

  /**
   * 将Uint8Array转换为base64字符串
   */
  static uint8ArrayToBase64(uint8Array: Uint8Array): string {
    try {
      const base64Helper = new util.Base64Helper();
      // 使用util.Type.MIME进行base64编码
      return base64Helper.encodeToStringSync(uint8Array, util.Type.MIME);
    } catch (error) {
      const err = error as BusinessError;
      promptAction.showToast({
        message: `Base64编码失败: ${err.message || String(err)}`,
        duration: 2000
      });
      return '';
    }
  }

  /**
   * 选择文本文件并上传到云存储
   * 支持.txt、Word文件（.doc, .docx）和PDF文件（.pdf）
   * @param context UIAbility上下文，如果未提供则使用GlobalContext获取
   * @param uploadToCloud 是否上传到云存储，默认true
   * @returns 文本文件信息，包括URI、文件名、云存储URL等
   */
  static async pickTextFile(
    context?: common.UIAbilityContext,
    uploadToCloud: boolean = true
  ): Promise<TextFileInfo | null> {
    try {
      // 获取上下文
      let uiContext: common.UIAbilityContext | null = null;
      if (context) {
        uiContext = context;
      } else {
        uiContext = GlobalContext.getContext();
        if (!uiContext) {
          throw new Error('无法获取上下文，请传入context参数或确保GlobalContext已初始化');
        }
      }

      // 使用DocumentViewPicker选择文件
      const documentViewPicker = new picker.DocumentViewPicker(uiContext);
      const documentSelectOptions = new picker.DocumentSelectOptions();
      
      // 设置文件类型过滤器（支持文本文件、Word文件和PDF文件）
      documentSelectOptions.fileSuffixFilters = ['.txt', '.doc', '.docx', '.pdf'];
      documentSelectOptions.maxSelectNumber = 1;
      
      const documentSelectResult = await documentViewPicker.select(documentSelectOptions);
      
      if (!documentSelectResult || documentSelectResult.length === 0) {
        Logger.info(TAG, '用户取消选择文件');
        return null;
      }

      const fileUri = documentSelectResult[0];
      Logger.info(TAG, `选择的文件URI: ${fileUri}`);

      // 获取文件信息（需要先打开文件才能获取文件描述符）
      let tempFile: fs.File | null = null;
      let fileSize = 0;
      try {
        tempFile = fs.openSync(fileUri, fs.OpenMode.READ_ONLY);
        const fileStat = fs.statSync(tempFile.fd);
        fileSize = fileStat.size;
        fs.closeSync(tempFile);
        tempFile = null;
      } catch (error) {
        if (tempFile) {
          fs.closeSync(tempFile);
        }
        const err = error as BusinessError;
        Logger.error(TAG, `获取文件信息失败: code=${err.code}, message=${err.message}`);
        promptAction.showToast({
          message: `无法访问文件: ${err.message || '文件不存在或无法访问'}`,
          duration: 2000
        });
        return null;
      }

      const fileSizeMB = fileSize / (1024 * 1024);

      // 检查文件大小（限制50MB，因为PDF文件可能较大）
      if (fileSize > 50 * 1024 * 1024) {
        promptAction.showToast({
          message: `文件过大: ${fileSizeMB.toFixed(2)}MB (限制: 50MB)`,
          duration: 2000
        });
        return null;
      }

      // 提取文件名（从URI中提取，可能需要URL解码）
      let fileName = fileUri.split('/').pop() || `text_${Date.now()}.txt`;
      // 尝试URL解码文件名（处理中文文件名）
      try {
        fileName = decodeURIComponent(fileName);
      } catch {
        // 如果解码失败，使用原始文件名
      }

      // 检测文件类型（根据文件扩展名）
      const fileExtension = fileName.toLowerCase().split('.').pop() || '';
      const supportedExtensions = ['txt', 'doc', 'docx', 'pdf'];
      const isSupportedFile = supportedExtensions.includes(fileExtension);

      if (!isSupportedFile) {
        promptAction.showToast({
          message: `不支持的文件格式: .${fileExtension}，支持格式: .txt, .doc, .docx, .pdf`,
          duration: 3000
        });
        return null;
      }

      // 如果启用云存储上传（PDF和Word文件必须上传到云存储）
      const requiresCloudUpload = fileExtension === 'pdf' || fileExtension === 'doc' || fileExtension === 'docx';
      
      if (requiresCloudUpload && !uploadToCloud) {
        // PDF和Word文件必须上传到云存储
        promptAction.showToast({
          message: `${fileExtension.toUpperCase()}文件必须上传到云存储，请启用云存储上传`,
          duration: 2000
        });
        return null;
      }

      if (uploadToCloud || requiresCloudUpload) {
        const cloudInfo = await FileUtils.uploadFileToCloud(uiContext, fileUri, fileName);
        if (cloudInfo) {
          const fileInfo: TextFileInfo = {
            uri: fileUri,
            fileName: fileName,
            fileSize: fileSize,
            cloudPath: cloudInfo.cloudPath,
            cloudUrl: cloudInfo.cloudUrl
          };

          // 根据文件类型显示不同的提示信息
          const fileTypeName = fileExtension === 'pdf' ? 'PDF' : 
                               fileExtension === 'docx' || fileExtension === 'doc' ? 'Word' : 
                               '文本';
          
          promptAction.showToast({
            message: `${fileTypeName}文件选择成功 (${fileSizeMB.toFixed(2)}MB)，已上传到云存储`,
            duration: 2000
          });

          Logger.info(TAG, `文件上传成功: ${fileName} (${fileSizeMB.toFixed(2)}MB) -> ${cloudInfo.cloudUrl}`);
          return fileInfo;
        } else {
          // 上传失败
          if (requiresCloudUpload) {
            // PDF和Word文件上传失败，无法继续
            Logger.error(TAG, `${fileExtension.toUpperCase()}文件上传到云存储失败`);
            promptAction.showToast({
              message: `${fileExtension.toUpperCase()}文件上传失败，请重试`,
              duration: 3000
            });
            return null;
          } else {
            // 文本文件上传失败，回退到本地处理模式
            Logger.warn(TAG, '文件上传到云存储失败，回退到本地处理模式');
            promptAction.showToast({
              message: `文件上传失败，将尝试本地处理`,
              duration: 2000
            });
            // 继续执行本地处理逻辑
          }
        }
      }

      // 不使用云存储，读取文件内容（仅支持.txt文件）
      // PDF和Word文件必须上传到云存储，由后端处理
      if (fileExtension === 'txt') {
        let file: fs.File | null = null;
        try {
          file = fs.openSync(fileUri, fs.OpenMode.READ_ONLY);
          const buffer = new ArrayBuffer(fileSize);
          fs.readSync(file.fd, buffer);
          fs.closeSync(file);
          file = null;

          // 转换为文本（尝试UTF-8编码）
          const uint8Array = new Uint8Array(buffer);
          let content = '';
          try {
            // 尝试UTF-8解码
            content = new util.TextDecoder('utf-8').decodeWithStream(uint8Array);
          } catch (decodeError) {
            // 如果UTF-8失败，尝试GBK（中文常用编码）
            try {
              content = new util.TextDecoder('gbk').decodeWithStream(uint8Array);
            } catch {
              // 如果都失败，使用循环逐个转换字符（避免使用Function.apply）
              const charArray: string[] = [];
              for (let i = 0; i < uint8Array.length; i++) {
                charArray.push(String.fromCharCode(uint8Array[i]));
              }
              content = charArray.join('');
            }
          }

          const fileInfo: TextFileInfo = {
            uri: fileUri,
            fileName: fileName,
            fileSize: fileSize,
            content: content
          };

          promptAction.showToast({
            message: `文本文件选择成功 (${fileSizeMB.toFixed(2)}MB)`,
            duration: 2000
          });

          Logger.info(TAG, `文本文件读取成功: ${fileName} (${fileSizeMB.toFixed(2)}MB), 内容长度: ${content.length} 字符`);
          return fileInfo;
        } finally {
          if (file) {
            fs.closeSync(file);
          }
        }
      } else {
        // Word和PDF文件需要上传到云存储，由后端处理
        // 这不应该到达这里，因为前面已经检查了requiresCloudUpload
        Logger.error(TAG, `${fileExtension.toUpperCase()}文件必须上传到云存储，但uploadToCloud为false`);
        promptAction.showToast({
          message: `${fileExtension.toUpperCase()}文件需要上传到云存储，请启用云存储上传`,
          duration: 2000
        });
        return null;
      }
    } catch (error) {
      const err = error as BusinessError;
      const errorMessage = err.message || String(error);
      Logger.error(TAG, `选择文本文件失败: ${errorMessage}`);
      promptAction.showToast({
        message: `选择文件失败: ${errorMessage}`,
        duration: 2000
      });
      return null;
    }
  }

  /**
   * 将base64字符串转换为Uint8Array
   */
  static base64ToUint8Array(base64: string): Uint8Array {
    try {
      // 移除可能的数据URI前缀（如 data:audio/wav;base64,）
      let base64Data = base64;
      if (base64.includes(',')) {
        base64Data = base64.split(',')[1];
      }
      
      const base64Helper = new util.Base64Helper();
      return base64Helper.decodeSync(base64Data);
    } catch (error) {
      const err = error as BusinessError;
      promptAction.showToast({
        message: `Base64解码失败: ${err.message || String(err)}`,
        duration: 2000
      });
      return new Uint8Array(0);
    }
  }
}

