import { audio } from '@kit.AudioKit';
import { BusinessError } from '@kit.BasicServicesKit';
import { fileIo as fs } from '@kit.CoreFileKit';
import { common } from '@kit.AbilityKit';
import { promptAction } from '@kit.ArkUI';
import { abilityAccessCtrl, Permissions } from '@kit.AbilityKit';
import { Logger } from 'lib_common';
import { FileUtils } from './FileUtils';
import { GlobalContext } from '../common/GlobalContext';

const TAG = 'AudioRecorderUtils';

/**
 * 文件写入选项
 */
interface WriteOptions {
  offset?: number;
  length?: number;
}

/**
 * 停止回调函数类型
 */
type StopCallback = () => Promise<void>;

/**
 * 录制选项
 */
export interface RecordOptions {
  /** 采样率，默认 48000 */
  samplingRate?: audio.AudioSamplingRate;
  /** 通道数，默认 2（立体声） */
  channels?: audio.AudioChannel;
  /** 采样格式，默认 SAMPLE_FORMAT_S16LE */
  sampleFormat?: audio.AudioSampleFormat;
  /** 编码格式，默认 ENCODING_TYPE_RAW */
  encodingType?: audio.AudioEncodingType;
  /** 音源类型，默认 SOURCE_TYPE_MIC */
  sourceType?: audio.SourceType;
}

/**
 * 录制结果
 */
export interface RecordResult {
  /** 录制的文件路径 */
  filePath: string;
  /** 文件大小（字节） */
  fileSize: number;
  /** 录制时长（毫秒） */
  duration: number;
  /** 云存储路径（如果已上传） */
  cloudPath?: string;
  /** 云存储下载URL（如果已上传） */
  cloudUrl?: string;
}

/**
 * 录制进度回调
 */
export interface RecordProgressCallback {
  /** 已录制的字节数 */
  bytesRecorded: number;
  /** 录制时长（毫秒） */
  duration: number;
}

/**
 * 音频录制工具类
 * 使用 AudioCapturer 录制 PCM 音频数据
 */
export class AudioRecorderUtils {
  private static audioCapturer: audio.AudioCapturer | undefined = undefined;
  private static context: common.UIAbilityContext | undefined = undefined;
  private static file: fs.File | null = null;
  private static filePath: string = '';
  private static bufferSize: number = 0;
  private static startTime: number = 0;
  private static isRecording: boolean = false;
  private static progressCallback: ((progress: RecordProgressCallback) => void) | undefined = undefined;
  private static stopCallback: StopCallback | undefined = undefined;

  /**
   * 初始化录制参数
   */
  private static getDefaultOptions(): RecordOptions {
    return {
      samplingRate: audio.AudioSamplingRate.SAMPLE_RATE_48000,
      channels: audio.AudioChannel.CHANNEL_2,
      sampleFormat: audio.AudioSampleFormat.SAMPLE_FORMAT_S16LE,
      encodingType: audio.AudioEncodingType.ENCODING_TYPE_RAW,
      sourceType: audio.SourceType.SOURCE_TYPE_MIC
    };
  }

  /**
   * 检查并申请麦克风权限
   * @param context UIAbility上下文
   * @returns Promise<boolean> 是否有权限
   */
  private static async checkMicrophonePermission(context: common.UIAbilityContext): Promise<boolean> {
    try {
      const atManager = abilityAccessCtrl.createAtManager();
      const tokenId: number = context.applicationInfo.accessTokenId;
      const permission: Permissions = 'ohos.permission.MICROPHONE';

      // 检查权限状态
      const grantStatus = await atManager.checkAccessToken(tokenId, permission);
      if (grantStatus === abilityAccessCtrl.GrantStatus.PERMISSION_GRANTED) {
        Logger.info(TAG, '麦克风权限已授予');
        return true;
      }

      Logger.info(TAG, '麦克风权限未授予，开始申请权限');
      
      // 申请权限
      const requestResult = await atManager.requestPermissionsFromUser(context, [permission]);
      const grantResult = requestResult.authResults[0];
      
      if (grantResult === abilityAccessCtrl.GrantStatus.PERMISSION_GRANTED) {
        Logger.info(TAG, '麦克风权限申请成功');
        return true;
      } else {
        Logger.error(TAG, '麦克风权限申请被拒绝');
        promptAction.showToast({
          message: '需要麦克风权限才能录制音频，请在设置中授予权限',
          duration: 3000
        });
        return false;
      }
    } catch (error) {
      Logger.error(TAG, `检查麦克风权限异常: ${error}`);
      promptAction.showToast({
        message: `权限检查失败: ${error}`,
        duration: 2000
      });
      return false;
    }
  }

  /**
   * 初始化录制器
   * @param context UIAbility上下文
   * @param options 录制选项
   * @returns Promise<boolean> 是否初始化成功
   */
  static async initRecorder(
    context: common.UIAbilityContext,
    options?: RecordOptions
  ): Promise<boolean> {
    try {
      // 检查并申请麦克风权限
      const hasPermission = await AudioRecorderUtils.checkMicrophonePermission(context);
      if (!hasPermission) {
        return false;
      }

      AudioRecorderUtils.context = context;
      const opts = options || AudioRecorderUtils.getDefaultOptions();

      // 配置音频流信息
      const audioStreamInfo: audio.AudioStreamInfo = {
        samplingRate: opts.samplingRate || audio.AudioSamplingRate.SAMPLE_RATE_48000,
        channels: opts.channels || audio.AudioChannel.CHANNEL_2,
        sampleFormat: opts.sampleFormat || audio.AudioSampleFormat.SAMPLE_FORMAT_S16LE,
        encodingType: opts.encodingType || audio.AudioEncodingType.ENCODING_TYPE_RAW
      };

      // 配置音频采集器信息
      const audioCapturerInfo: audio.AudioCapturerInfo = {
        source: opts.sourceType || audio.SourceType.SOURCE_TYPE_MIC,
        capturerFlags: 0
      };

      // 配置音频采集器选项
      const audioCapturerOptions: audio.AudioCapturerOptions = {
        streamInfo: audioStreamInfo,
        capturerInfo: audioCapturerInfo
      };

      // 创建 AudioCapturer 实例
      return new Promise<boolean>((resolve) => {
        audio.createAudioCapturer(audioCapturerOptions, (err: BusinessError, capturer: audio.AudioCapturer) => {
          if (err) {
            Logger.error(TAG, `创建AudioCapturer失败: code=${err.code}, message=${err.message}`);
            
            // 根据错误代码提供更详细的错误信息
            let errorMessage = '初始化录制器失败';
            if (err.code === 6800301) {
              errorMessage = '系统错误，可能是麦克风权限未授予或设备不支持。请检查权限设置';
            } else if (err.code === 6800101) {
              errorMessage = '参数错误，请检查音频采集器配置';
            } else if (err.code === 6800103) {
              errorMessage = '音频服务不可用，请稍后重试';
            } else {
              errorMessage = `${err.message || '未知错误'} (code: ${err.code})`;
            }
            
            promptAction.showToast({
              message: errorMessage,
              duration: 3000
            });
            resolve(false);
            return;
          }

          AudioRecorderUtils.audioCapturer = capturer;
          Logger.info(TAG, 'AudioCapturer创建成功');
          resolve(true);
        });
      });
    } catch (error) {
      Logger.error(TAG, `初始化录制器异常: ${error}`);
      promptAction.showToast({
        message: `初始化录制器失败: ${error}`,
        duration: 2000
      });
      return false;
    }
  }

  /**
   * 开始录制
   * @param fileName 文件名（不含扩展名），默认使用时间戳
   * @param onProgress 进度回调（可选）
   * @returns Promise<boolean> 是否开始成功
   */
  static async startRecording(
    fileName?: string,
    onProgress?: (progress: RecordProgressCallback) => void
  ): Promise<boolean> {
    if (!AudioRecorderUtils.audioCapturer || !AudioRecorderUtils.context) {
      Logger.error(TAG, '录制器未初始化');
      promptAction.showToast({
        message: '录制器未初始化，请先初始化',
        duration: 2000
      });
      return false;
    }

    if (AudioRecorderUtils.isRecording) {
      Logger.warn(TAG, '正在录制中，无法重复开始');
      return false;
    }

    try {
      // 检查状态
      const state = AudioRecorderUtils.audioCapturer.state.valueOf();
      const validStates = [
        audio.AudioState.STATE_PREPARED,
        audio.AudioState.STATE_PAUSED,
        audio.AudioState.STATE_STOPPED
      ];

      if (validStates.indexOf(state) === -1) {
        Logger.error(TAG, `录制器状态不正确: ${state}`);
        promptAction.showToast({
          message: `录制器状态不正确: ${state}`,
          duration: 2000
        });
        return false;
      }

      // 创建文件
      const finalFileName = fileName || `voice_${Date.now()}`;
      const path = AudioRecorderUtils.context.cacheDir;
      AudioRecorderUtils.filePath = `${path}/${finalFileName}.pcm`;
      
      Logger.info(TAG, `开始录制，文件路径: ${AudioRecorderUtils.filePath}`);

      // 打开文件
      AudioRecorderUtils.file = fs.openSync(
        AudioRecorderUtils.filePath,
        fs.OpenMode.READ_WRITE | fs.OpenMode.CREATE | fs.OpenMode.TRUNC
      );

      // 重置状态
      AudioRecorderUtils.bufferSize = 0;
      AudioRecorderUtils.startTime = Date.now();
      AudioRecorderUtils.isRecording = true;
      AudioRecorderUtils.progressCallback = onProgress;

      // 设置数据读取回调
      const readDataCallback = (buffer: ArrayBuffer) => {
        if (!AudioRecorderUtils.isRecording || !AudioRecorderUtils.file) {
          return;
        }

        try {
          const options: WriteOptions = {
            offset: AudioRecorderUtils.bufferSize,
            length: buffer.byteLength
          };
          fs.writeSync(AudioRecorderUtils.file!.fd, buffer, options);
          AudioRecorderUtils.bufferSize += buffer.byteLength;

          // 调用进度回调
          if (AudioRecorderUtils.progressCallback) {
            const duration = Date.now() - AudioRecorderUtils.startTime;
            AudioRecorderUtils.progressCallback({
              bytesRecorded: AudioRecorderUtils.bufferSize,
              duration: duration
            });
          }
        } catch (error) {
          Logger.error(TAG, `写入数据失败: ${error}`);
        }
      };

      AudioRecorderUtils.audioCapturer.on('readData', readDataCallback);

      // 监听状态变化
      AudioRecorderUtils.audioCapturer.on('stateChange', (state: audio.AudioState) => {
        Logger.info(TAG, `录制器状态变化: ${state}`);
        if (state === audio.AudioState.STATE_RUNNING) {
          Logger.info(TAG, '录制已开始');
        } else if (state === audio.AudioState.STATE_STOPPED) {
          Logger.info(TAG, '录制已停止');
        } else if (state === audio.AudioState.STATE_PAUSED) {
          Logger.error(TAG, '录制器进入错误状态');
          promptAction.showToast({
            message: '录制错误，请重试',
            duration: 2000
          });
        }
      });

      // 开始录制
      return new Promise<boolean>((resolve) => {
        AudioRecorderUtils.audioCapturer!.start((err: BusinessError) => {
          if (err) {
            Logger.error(TAG, `开始录制失败: code=${err.code}, message=${err.message}`);
            promptAction.showToast({
              message: `开始录制失败: ${err.message}`,
              duration: 2000
            });
            AudioRecorderUtils.isRecording = false;
            if (AudioRecorderUtils.file) {
              fs.closeSync(AudioRecorderUtils.file);
              AudioRecorderUtils.file = null;
            }
            resolve(false);
            return;
          }

          Logger.info(TAG, '录制已开始');
          promptAction.showToast({
            message: '开始录制',
            duration: 1000
          });
          resolve(true);
        });
      });
    } catch (error) {
      Logger.error(TAG, `开始录制异常: ${error}`);
      AudioRecorderUtils.isRecording = false;
      if (AudioRecorderUtils.file) {
        fs.closeSync(AudioRecorderUtils.file);
        AudioRecorderUtils.file = null;
      }
      promptAction.showToast({
        message: `开始录制失败: ${error}`,
        duration: 2000
      });
      return false;
    }
  }

  /**
   * 停止录制
   * @returns Promise<RecordResult | null> 录制结果
   */
  static async stopRecording(): Promise<RecordResult | null> {
    if (!AudioRecorderUtils.audioCapturer) {
      Logger.error(TAG, '录制器未初始化');
      return null;
    }

    if (!AudioRecorderUtils.isRecording) {
      Logger.warn(TAG, '未在录制中');
      return null;
    }

    try {
      // 检查状态
      const state = AudioRecorderUtils.audioCapturer.state.valueOf();
      if (state !== audio.AudioState.STATE_RUNNING && state !== audio.AudioState.STATE_PAUSED) {
        Logger.warn(TAG, `录制器状态不正确，无法停止: ${state}`);
        return null;
      }

      // 停止录制
      return new Promise<RecordResult | null>((resolve) => {
        AudioRecorderUtils.audioCapturer!.stop((err: BusinessError) => {
          if (err) {
            Logger.error(TAG, `停止录制失败: code=${err.code}, message=${err.message}`);
            promptAction.showToast({
              message: `停止录制失败: ${err.message}`,
              duration: 2000
            });
            resolve(null);
            return;
          }

          // 关闭文件
          if (AudioRecorderUtils.file) {
            fs.closeSync(AudioRecorderUtils.file);
            AudioRecorderUtils.file = null;
          }

          // 计算录制时长
          const duration = Date.now() - AudioRecorderUtils.startTime;
          const fileSize = AudioRecorderUtils.bufferSize;

          Logger.info(TAG, `录制完成: 文件=${AudioRecorderUtils.filePath}, 大小=${fileSize}字节, 时长=${duration}ms`);

          AudioRecorderUtils.isRecording = false;
          AudioRecorderUtils.progressCallback = undefined;

          const result: RecordResult = {
            filePath: AudioRecorderUtils.filePath,
            fileSize: fileSize,
            duration: duration
          };

          promptAction.showToast({
            message: `录制完成 (${(duration / 1000).toFixed(1)}秒)`,
            duration: 2000
          });

          resolve(result);
        });
      });
    } catch (error) {
      Logger.error(TAG, `停止录制异常: ${error}`);
      AudioRecorderUtils.isRecording = false;
      if (AudioRecorderUtils.file) {
        fs.closeSync(AudioRecorderUtils.file);
        AudioRecorderUtils.file = null;
      }
      return null;
    }
  }

  /**
   * 录制并上传到云存储
   * @param context UIAbility上下文
   * @param fileName 文件名（不含扩展名），默认使用时间戳
   * @param onProgress 进度回调（可选）
   * @returns Promise<RecordResult | null> 录制结果（包含云存储URL）
   */
  static async recordAndUpload(
    context: common.UIAbilityContext,
    fileName?: string,
    onProgress?: (progress: RecordProgressCallback) => void
  ): Promise<RecordResult | null> {
    try {
      // 初始化录制器
      const initSuccess = await AudioRecorderUtils.initRecorder(context);
      if (!initSuccess) {
        return null;
      }

      // 开始录制
      const startSuccess = await AudioRecorderUtils.startRecording(fileName, onProgress);
      if (!startSuccess) {
        await AudioRecorderUtils.release();
        return null;
      }

      // 返回一个 Promise，等待用户停止录制
      return new Promise<RecordResult | null>((resolve) => {
        // 这里需要外部调用 stopRecordingAndUpload 来停止录制
        // 为了简化，我们可以提供一个方法让外部设置停止回调
        AudioRecorderUtils.stopCallback = async () => {
          const result = await AudioRecorderUtils.stopRecording();
          if (!result) {
            await AudioRecorderUtils.release();
            resolve(null);
            return;
          }

          // 上传到云存储
          const fileName = AudioRecorderUtils.getFileNameFromPath(result.filePath);
          const cloudInfo = await FileUtils.uploadAudioToCloud(context, result.filePath, fileName);
          
          if (cloudInfo) {
            result.cloudPath = cloudInfo.cloudPath;
            result.cloudUrl = cloudInfo.cloudUrl;
            Logger.info(TAG, `录制文件已上传到云存储: ${cloudInfo.cloudUrl}`);
          } else {
            Logger.warn(TAG, '录制文件上传到云存储失败');
          }

          await AudioRecorderUtils.release();
          resolve(result);
        };
      });
    } catch (error) {
      Logger.error(TAG, `录制并上传异常: ${error}`);
      await AudioRecorderUtils.release();
      return null;
    }
  }

  /**
   * 停止录制并上传到云存储
   * @returns Promise<RecordResult | null> 录制结果（包含云存储URL）
   */
  static async stopRecordingAndUpload(): Promise<RecordResult | null> {
    if (!AudioRecorderUtils.context) {
      Logger.error(TAG, '上下文未设置');
      return null;
    }

    const result = await AudioRecorderUtils.stopRecording();
    if (!result) {
      await AudioRecorderUtils.release();
      return null;
    }

    // 上传到云存储
    const fileName = AudioRecorderUtils.getFileNameFromPath(result.filePath);
    const cloudInfo = await FileUtils.uploadAudioToCloud(AudioRecorderUtils.context, result.filePath, fileName);
    
    if (cloudInfo) {
      result.cloudPath = cloudInfo.cloudPath;
      result.cloudUrl = cloudInfo.cloudUrl;
      Logger.info(TAG, `录制文件已上传到云存储: ${cloudInfo.cloudUrl}`);
      promptAction.showToast({
        message: '录制文件已上传到云存储',
        duration: 2000
      });
    } else {
      Logger.warn(TAG, '录制文件上传到云存储失败');
      promptAction.showToast({
        message: '录制文件上传失败',
        duration: 2000
      });
    }

    await AudioRecorderUtils.release();
    return result;
  }

  /**
   * 释放录制器资源
   */
  static async release(): Promise<void> {
    try {
      // 如果正在录制，先停止
      if (AudioRecorderUtils.isRecording && AudioRecorderUtils.audioCapturer) {
        const state = AudioRecorderUtils.audioCapturer.state.valueOf();
        if (state === audio.AudioState.STATE_RUNNING || state === audio.AudioState.STATE_PAUSED) {
          await new Promise<void>((resolve) => {
            AudioRecorderUtils.audioCapturer!.stop((err: BusinessError) => {
              if (err) {
                Logger.error(TAG, `停止录制失败: ${err.message}`);
              }
              resolve();
            });
          });
        }
      }

      // 关闭文件
      if (AudioRecorderUtils.file) {
        fs.closeSync(AudioRecorderUtils.file);
        AudioRecorderUtils.file = null;
      }

      // 释放录制器
      if (AudioRecorderUtils.audioCapturer) {
        const state = AudioRecorderUtils.audioCapturer.state.valueOf();
        if (state !== audio.AudioState.STATE_RELEASED && state !== audio.AudioState.STATE_NEW) {
          await new Promise<void>((resolve) => {
            AudioRecorderUtils.audioCapturer!.release((err: BusinessError) => {
              if (err) {
                Logger.error(TAG, `释放录制器失败: ${err.message}`);
              } else {
                Logger.info(TAG, '录制器已释放');
              }
              resolve();
            });
          });
        }
        AudioRecorderUtils.audioCapturer = undefined;
      }

      // 重置状态
      AudioRecorderUtils.isRecording = false;
      AudioRecorderUtils.bufferSize = 0;
      AudioRecorderUtils.filePath = '';
      AudioRecorderUtils.progressCallback = undefined;
      AudioRecorderUtils.stopCallback = undefined;
    } catch (error) {
      Logger.error(TAG, `释放录制器异常: ${error}`);
    }
  }

  /**
   * 检查是否正在录制
   */
  static isRecordingNow(): boolean {
    return AudioRecorderUtils.isRecording;
  }

  /**
   * 从文件路径提取文件名
   */
  private static getFileNameFromPath(filePath: string): string {
    const parts = filePath.split('/');
    const fileName = parts[parts.length - 1];
    // 将 .pcm 扩展名改为 .wav
    return fileName.replace(/\.pcm$/, '.wav');
  }
}
