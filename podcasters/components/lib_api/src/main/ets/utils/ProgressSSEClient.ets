import { http } from '@kit.NetworkKit';
import { BusinessError } from '@kit.BasicServicesKit';
import { Logger } from 'lib_common';
import { PodcastConfig } from '../services/PodcastService';
import { ProgressStatus } from '../services/PodcastService';

const TAG = '[ProgressSSEClient]';

/**
 * SSE进度推送客户端
 * 用于实时接收播客生成进度，避免轮询
 */
export class ProgressSSEClient {
  private requestTask: http.HttpRequest | null = null;
  private jobId: string;
  private onProgress: (progress: ProgressStatus) => void;
  private onError: (error: Error) => void;
  private baseUrl: string;
  private isConnected: boolean = false;
  private buffer: string = '';

  constructor(
    jobId: string,
    onProgress: (progress: ProgressStatus) => void,
    onError: (error: Error) => void
  ) {
    this.jobId = jobId;
    this.onProgress = onProgress;
    this.onError = onError;
    // 规范化base URL（移除末尾斜杠）
    this.baseUrl = PodcastConfig.API_BASE_URL.replace(/\/+$/, '');
  }

  /**
   * 构建完整的API URL
   */
  private buildApiUrl(path: string): string {
    if (PodcastConfig.USE_CLOUD_FUNCTION) {
      // 云函数模式：直接使用base URL
      return this.baseUrl;
    } else {
      // 直接API模式：拼接路径
      const cleanPath = path.startsWith('/') ? path : `/${path}`;
      return `${this.baseUrl}${cleanPath}`;
    }
  }

  /**
   * 连接SSE流
   */
  connect(): void {
    if (this.isConnected) {
      Logger.warn(TAG, 'SSE连接已存在，先关闭旧连接');
      this.close();
    }

    const url = this.buildApiUrl(`/api/v1/podcast/progress/${this.jobId}/stream`);
    Logger.info(TAG, `开始连接SSE: ${url}`);

    try {
      this.requestTask = http.createHttp();
      const options: http.HttpRequestOptions = {
        method: http.RequestMethod.GET,
        header: {
          'Accept': 'text/event-stream',
          'Cache-Control': 'no-cache',
        },
        // 注意：HarmonyOS的http模块不支持真正的流式读取
        // 响应会在连接建立后一次性返回，而不是持续推送
        // 因此使用较短的超时时间，避免长时间等待
        // 如果SSE连接失败，会自动回退到轮询方式
        readTimeout: 60000, // 60秒读取超时（足够接收初始数据）
        connectTimeout: 30000, // 30秒连接超时（足够建立连接）
      };

      this.requestTask.request(url, options, (err: BusinessError, data: http.HttpResponse) => {
        if (err) {
          // 检查错误类型
          const errorCode = err.code || 0;
          const errorMessage = err.message || '';
          
          // CURL错误码23：Failed writing received data to disk/application
          // 这通常表示HarmonyOS的http模块不支持流式读取，导致数据写入失败
          const isWriteError = errorCode === 2300023 || errorMessage.includes('Failed writing') || errorMessage.includes('writing received data');
          
          // 超时错误（错误码2300028）
          const isTimeout = errorCode === 2300028 || errorMessage.includes('Timeout') || errorMessage.includes('timeout');
          
          if (isWriteError) {
            // HarmonyOS的http模块不支持流式读取，这是已知限制
            Logger.warn(TAG, `SSE连接失败（流式读取不支持）: ${JSON.stringify(err)}，将回退到轮询方式`);
            // 创建一个特殊的错误，标识这是流式读取不支持的情况
            const sseError = new Error('SSE流式读取不支持，请使用轮询方式');
            (sseError as any).isSSENotSupported = true;
            (sseError as any).originalError = err;
            this.isConnected = false;
            this.onError(sseError);
            return;
          } else if (isTimeout) {
            Logger.warn(TAG, `SSE连接超时: ${JSON.stringify(err)}，将回退到轮询方式`);
            // 超时也回退到轮询
            const timeoutError = new Error('SSE连接超时，请使用轮询方式');
            (timeoutError as any).isTimeout = true;
            (timeoutError as any).originalError = err;
            this.isConnected = false;
            this.onError(timeoutError);
            return;
          } else {
            Logger.error(TAG, `SSE连接失败: ${JSON.stringify(err)}`);
            this.isConnected = false;
            this.onError(new Error(err.message || 'SSE连接失败'));
            return;
          }
        }

        if (data && data.responseCode === 200) {
          this.isConnected = true;
          Logger.info(TAG, 'SSE连接成功');
          
          // 处理SSE数据流
          // 注意：HarmonyOS的http模块可能不支持真正的流式读取
          // 如果响应是一次性返回的，这里会处理完整的数据
          const streamData = data.result?.toString() || '';
          if (streamData) {
            this.processSSEStream(streamData);
          } else {
            Logger.warn(TAG, 'SSE响应数据为空');
          }
        } else {
          Logger.error(TAG, `SSE连接返回非200状态码: ${data?.responseCode}`);
          this.isConnected = false;
          this.onError(new Error(`HTTP ${data?.responseCode || 'Unknown'}`));
        }
      });

      // 监听数据流（如果支持）
      // 注意：HarmonyOS的http模块可能不支持流式读取，需要根据实际情况调整
      // 如果http模块不支持流式读取，可能需要使用轮询作为fallback
      
    } catch (error) {
      Logger.error(TAG, `SSE连接异常: ${JSON.stringify(error)}`);
      this.isConnected = false;
      this.onError(new Error(`连接异常: ${error instanceof Error ? error.message : String(error)}`));
    }
  }

  /**
   * 处理SSE数据流
   * 注意：HarmonyOS的http模块可能不支持真正的流式读取
   * 如果响应是一次性返回的，这里会处理完整的数据
   * 如果支持流式读取，需要调整实现方式
   */
  private processSSEStream(stream: string): void {
    if (!stream || stream.length === 0) {
      Logger.warn(TAG, 'SSE数据流为空');
      return;
    }

    // 将新数据添加到缓冲区
    this.buffer += stream;

    // 按行分割处理
    const lines = this.buffer.split('\n');
    // 保留最后一行（可能不完整）
    this.buffer = lines.pop() || '';

    let currentData = '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        // 提取data字段
        currentData = line.substring(6); // 移除 "data: " 前缀
      } else if (line.startsWith(': ')) {
        // 注释行（心跳），忽略
        continue;
      } else if (line === '' && currentData) {
        // 空行表示一个完整的事件
        this.handleProgressEvent(currentData);
        currentData = '';
      }
    }

    // 如果缓冲区中还有未处理的数据，继续处理
    if (this.buffer.includes('\n')) {
      const remainingLines = this.buffer.split('\n');
      this.buffer = remainingLines.pop() || '';
      for (const line of remainingLines) {
        if (line.startsWith('data: ')) {
          currentData = line.substring(6);
        } else if (line === '' && currentData) {
          this.handleProgressEvent(currentData);
          currentData = '';
        }
      }
    }
  }

  /**
   * 处理进度事件
   */
  private handleProgressEvent(data: string): void {
    if (!data || data.trim().length === 0) {
      return;
    }

    try {
      const progress = JSON.parse(data) as ProgressStatus;
      Logger.info(TAG, `收到进度更新: phase=${progress.phase}, percent=${progress.percent}, message=${progress.message}`);
      
      this.onProgress(progress);

      // 如果任务完成或失败，关闭连接
      if (progress.done) {
        Logger.info(TAG, '任务完成，关闭SSE连接');
        this.close();
      }
    } catch (e) {
      Logger.error(TAG, `解析进度数据失败: ${JSON.stringify(e)}, data: ${data}`);
    }
  }

  /**
   * 关闭SSE连接
   */
  close(): void {
    if (this.requestTask) {
      try {
        this.requestTask.destroy();
        Logger.info(TAG, 'SSE连接已关闭');
      } catch (error) {
        Logger.error(TAG, `关闭SSE连接异常: ${JSON.stringify(error)}`);
      }
      this.requestTask = null;
    }
    this.isConnected = false;
    this.buffer = '';
  }

  /**
   * 检查连接状态
   */
  isActive(): boolean {
    return this.isConnected && this.requestTask !== null;
  }
}

