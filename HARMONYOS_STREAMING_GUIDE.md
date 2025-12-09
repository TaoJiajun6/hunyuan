# 鸿蒙前端流式播客生成适配指南

## 概述

由于鸿蒙的 `http` 模块不支持 Server-Sent Events (SSE) 流式读取，我们需要使用变通方法实现流式播客生成和播放。

## 实现方案

### 方案一：使用 requestInStream() 方法（已实现，推荐）

使用 `http.requestInStream()` 方法实现真正的流式读取，这是鸿蒙官方推荐的流式HTTP响应处理方法。

**优势：**
- 真正的流式读取，数据到达即处理
- 支持边生成边播放，延迟最低
- 使用官方API，稳定可靠

### 方案二：使用轮询方式（备选）

定期请求获取最新生成的音频片段（需要后端支持）。

## 实现步骤

### 1. 在 PodcastService 中添加流式生成方法（已实现）

已在 `podcasters/components/lib_api/src/main/ets/services/PodcastService.ets` 中实现，使用 `requestInStream()` 方法：

**已实现的流式方法：**
- ✅ `generateDeepPodcastStreaming()` - 主题深度播客流式生成
- ✅ `generateMultiRolePodcastStreaming()` - 多角色互动播客流式生成
- ✅ `generateCharacterPodcastStreaming()` - 自定义角色播客流式生成

所有方法都使用 `requestInStream()` 实现真正的流式读取：

**关键实现：**
- 使用 `http.requestInStream()` 发起流式请求
- 订阅 `dataReceive` 事件实时接收数据块
- 使用 `TextDecoder` 将 `ArrayBuffer` 转换为字符串
- 实时解析 SSE 格式数据并触发回调

**代码位置：** `generateDeepPodcastStreaming()` 方法（约第1143行）

**原始实现示例（已更新为使用 requestInStream）：**

```typescript
/**
 * 流式生成主题深度播客（边生成边播放）
 * @param request 播客生成请求
 * @param onProgress 进度回调
 * @param onAudioSegment 音频片段回调
 * @param onScript 脚本回调
 * @returns Promise<void>
 */
async generateDeepPodcastStreaming(
  request: DeepPodcastRequest,
  onProgress?: (progress: ProgressStatus) => void,
  onAudioSegment?: (segment: AudioSegment) => void,
  onScript?: (script: string) => void
): Promise<ApiResponse<void>> {
  return new Promise<ApiResponse<void>>((resolve) => {
    try {
      // 验证请求参数
      if (!request.topic || request.topic.trim().length === 0) {
        resolve({
          success: false,
          message: '播客主题不能为空',
          error: '主题为空',
        });
        return;
      }

      const numCharacters = request.num_characters || 2;
      const depthLevel = request.depth_level || '深度';

      if (!['深度', '中等', '浅层'].includes(depthLevel)) {
        resolve({
          success: false,
          message: '深度级别必须是：深度、中等或浅层',
          error: '深度级别无效',
        });
        return;
      }

      // 验证音色数据
      const roleVoiceUrls = request.role_voice_urls;
      const roleNames = ['角色A', '角色B', '角色C'].slice(0, numCharacters);
      
      if (!roleVoiceUrls || Object.keys(roleVoiceUrls).length !== numCharacters) {
        resolve({
          success: false,
          message: `角色音色URL数量必须与角色数量(${numCharacters})一致`,
          error: '角色音色URL数量不匹配',
        });
        return;
      }

      for (const roleName of roleNames) {
        if (!roleVoiceUrls[roleName]) {
          resolve({
            success: false,
            message: `缺少角色 ${roleName} 的音色文件URL`,
            error: '角色音色URL缺失',
          });
          return;
        }
      }

      const requestBody = new DeepPodcastRequestBody(
        request.topic,
        undefined,
        roleVoiceUrls,
        numCharacters,
        depthLevel,
        request.silence_interval || 300
      );

      Logger.info(TAG, `开始流式生成主题深度播客: 主题=${request.topic}`);

      const httpRequest = http.createHttp();
      const requestData = JSON.stringify(requestBody);
      const options: http.HttpRequestOptions = {
        method: http.RequestMethod.POST,
        header: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream', // 请求SSE格式
        },
        extraData: requestData,
        connectTimeout: PodcastConfig.API_TIMEOUT,
        readTimeout: PodcastConfig.API_TIMEOUT,
      };

      const apiUrl = PodcastConfig.USE_CLOUD_FUNCTION
        ? this.baseUrl
        : this.buildApiUrl('/api/v1/podcast/deep/stream');

      Logger.info(TAG, `流式请求URL: ${apiUrl}`);

      // 用于累积接收到的数据
      let buffer = '';
      let isCompleted = false;

      httpRequest.request(
        apiUrl,
        options,
        (err: BusinessError, data: http.HttpResponse) => {
          if (err) {
            Logger.error(TAG, `流式请求失败: ${JSON.stringify(err)}`);
            httpRequest.destroy();
            resolve({
              success: false,
              message: '流式生成失败',
              error: err.message || String(err),
            });
            return;
          }

          if (!data) {
            Logger.error(TAG, '流式响应数据为空');
            httpRequest.destroy();
            resolve({
              success: false,
              message: '流式生成失败',
              error: '响应数据为空',
            });
            return;
          }

          // 处理流式数据
          // 注意：鸿蒙的http模块可能不支持真正的流式读取
          // 如果data.result是字符串，直接处理
          // 如果支持流式，需要逐块读取

          try {
            // 尝试解析响应
            if (typeof data.result === 'string') {
              this.processSSEData(data.result, onProgress, onAudioSegment, onScript);
            } else {
              Logger.warn(TAG, '响应数据不是字符串格式，尝试转换');
              const resultStr = JSON.stringify(data.result);
              this.processSSEData(resultStr, onProgress, onAudioSegment, onScript);
            }

            httpRequest.destroy();
            resolve({
              success: true,
              message: '流式生成完成',
            });
          } catch (error) {
            Logger.error(TAG, `处理流式数据失败: ${JSON.stringify(error)}`);
            httpRequest.destroy();
            resolve({
              success: false,
              message: '处理流式数据失败',
              error: error instanceof Error ? error.message : String(error),
            });
          }
        }
      );

      // 注意：如果鸿蒙不支持真正的流式读取，可能需要使用轮询方式
      // 或者等待完整响应后再解析

    } catch (error) {
      Logger.error(TAG, `流式生成异常: ${JSON.stringify(error)}`);
      resolve({
        success: false,
        message: '播客生成失败',
        error: error instanceof Error ? error.message : String(error),
      });
    }
  });
}

/**
 * 处理SSE格式的数据
 */
private processSSEData(
  data: string,
  onProgress?: (progress: ProgressStatus) => void,
  onAudioSegment?: (segment: AudioSegment) => void,
  onScript?: (script: string) => void
): void {
  const lines = data.split('\n');
  let buffer = '';

  for (const line of lines) {
    if (line.startsWith('data: ')) {
      try {
        const jsonStr = line.slice(6); // 移除 'data: ' 前缀
        const eventData = JSON.parse(jsonStr);

        switch (eventData.type) {
          case 'progress':
            if (onProgress) {
              onProgress({
                percent: eventData.percent || 0,
                message: eventData.message || '',
                done: eventData.status === 'completed' || eventData.status === 'failed',
                error: eventData.status === 'failed' ? eventData.message : undefined,
              });
            }
            break;

          case 'audio_segment':
            if (onAudioSegment) {
              onAudioSegment({
                segmentIndex: eventData.segment_index || 0,
                roleName: eventData.role_name || null,
                audioBase64: eventData.audio_base64 || '',
                isFinal: eventData.is_final || false,
                sampleRate: eventData.sample_rate || 22050,
              });
            }
            break;

          case 'script':
            if (onScript) {
              onScript(eventData.script || '');
            }
            break;

          case 'done':
            Logger.info(TAG, `流式生成完成，共 ${eventData.total_segments || 0} 个片段`);
            break;

          case 'error':
            Logger.error(TAG, `流式生成错误: ${eventData.message || '未知错误'}`);
            break;
        }
      } catch (e) {
        Logger.warn(TAG, `解析SSE数据失败: ${line}, 错误: ${JSON.stringify(e)}`);
      }
    }
  }
}
```

### 2. 定义音频片段接口

在 `PodcastService.ets` 文件顶部添加：

```typescript
/**
 * 音频片段
 */
export interface AudioSegment {
  segmentIndex: number;
  roleName: string | null;
  audioBase64: string;
  isFinal: boolean;
  sampleRate: number;
}
```

### 3. 修改 PodcastDeepPage 支持流式播放

在 `podcasters/products/phone/src/main/ets/pages/podcast/PodcastDeepPage.ets` 中修改 `generatePodcast` 方法：

```typescript
// 添加音频片段队列
private audioSegmentQueue: AudioSegment[] = [];
private isPlayingStreaming: boolean = false;
private currentStreamingAudio?: media.AVPlayer;

async generatePodcast(): Promise<void> {
  if (!this.topic.trim()) {
    promptAction.showToast({
      message: '请输入播客主题',
      duration: 2000
    });
    return;
  }

  const currentRoleNames = this.roleNames.slice(0, this.numCharacters);
  const hasAllVoices = currentRoleNames.every(role => this.roleVoiceUrls[role]);
  if (!hasAllVoices) {
    promptAction.showToast({
      message: `请为所有${this.numCharacters}个角色选择音色文件`,
      duration: 2000
    });
    return;
  }

  this.isLoading = true;
  this.jobId = `${Date.now()}_${Math.floor(Math.random() * 1000000)}`;
  this.progressPercent = 1;
  this.progressMessage = '任务已提交';
  
  // 清空音频队列
  this.audioSegmentQueue = [];
  this.isPlayingStreaming = false;

  // 进度回调
  const onProgress = (progress: ProgressStatus) => {
    this.targetProgress = progress.percent || 0;
    this.progressMessage = progress.message || '';
    this.startProgressAnimation();
    
    if (progress.done && progress.error) {
      this.isLoading = false;
      promptAction.showToast({
        message: progress.error || '生成失败',
        duration: 3000
      });
    }
  };

  // 音频片段回调
  const onAudioSegment = async (segment: AudioSegment) => {
    // 将音频片段加入队列
    this.audioSegmentQueue.push(segment);
    
    // 如果还没有开始播放，开始播放第一个片段
    if (!this.isPlayingStreaming && this.audioSegmentQueue.length > 0) {
      this.isPlayingStreaming = true;
      this.isLoading = false; // 开始播放后，隐藏加载状态
      await this.playNextAudioSegment();
    }
  };

  // 脚本回调
  const onScript = (script: string) => {
    this.savedScript = script;
  };

  try {
    let request: DeepPodcastRequest = {
      topic: this.topic,
      role_voice_urls: this.roleVoiceUrls,
      num_characters: this.numCharacters,
      depth_level: this.depthLevel,
      silence_interval: 300,
      background_volume: 0.3,
      job_id: this.jobId
    };

    if (this.category.trim().length > 0) {
      request.category = this.category;
    }

    // 使用流式生成
    const response = await podcastService.generateDeepPodcastStreaming(
      request,
      onProgress,
      onAudioSegment,
      onScript
    );

    if (!response.success) {
      this.isLoading = false;
      promptAction.showToast({
        message: response.error || response.message || '生成失败',
        duration: 3000
      });
    }
  } catch (error) {
    this.isLoading = false;
    promptAction.showToast({
      message: `生成异常: ${error}`,
      duration: 3000
    });
  }
}

/**
 * 播放下一个音频片段
 */
private async playNextAudioSegment(): Promise<void> {
  if (this.audioSegmentQueue.length === 0) {
    // 队列为空，等待更多片段
    // 如果最后一个片段已经播放完成，停止播放
    if (this.currentStreamingAudio) {
      this.isPlayingStreaming = false;
    }
    return;
  }

  const segment = this.audioSegmentQueue.shift()!;
  
  try {
    // 将base64转换为临时文件
    const tempFilePath = await this.saveBase64ToTempFile(segment.audioBase64);
    
    // 创建新的AVPlayer播放片段
    const avPlayer = await media.createAVPlayer();
    
    avPlayer.url = tempFilePath;
    
    // 监听播放完成事件
    avPlayer.on('stateChange', async (state: media.AVPlayerState) => {
      if (state === media.AVPlayerState.IDLE || state === media.AVPlayerState.RELEASED) {
        // 播放完成，播放下一段
        avPlayer.release();
        await this.playNextAudioSegment();
      }
    });

    // 监听播放结束
    avPlayer.on('endOfStream', async () => {
      avPlayer.release();
      await this.playNextAudioSegment();
    });

    // 开始播放
    await avPlayer.prepare();
    await avPlayer.play();
    
    this.currentStreamingAudio = avPlayer;
    
  } catch (error) {
    Logger.error('PodcastDeepPage', `播放音频片段失败: ${error}`);
    // 继续播放下一段
    await this.playNextAudioSegment();
  }
}

/**
 * 将base64音频保存为临时文件
 */
private async saveBase64ToTempFile(base64: string): Promise<string> {
  const context = getContext(this) as common.UIAbilityContext;
  const tempDir = context.filesDir;
  const fileName = `audio_segment_${Date.now()}.wav`;
  const filePath = `${tempDir}/${fileName}`;
  
  // Base64解码
  const binaryString = atob(base64);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  
  // 写入文件
  const file = await fs.open(filePath, fs.OpenMode.CREATE | fs.OpenMode.WRITE_ONLY);
  await file.write(bytes.buffer);
  await file.close();
  
  return filePath;
}
```

### 4. 添加必要的导入

在 `PodcastDeepPage.ets` 文件顶部添加：

```typescript
import { media } from '@kit.MediaKit';
import { fs } from '@kit.CoreFileKit';
import { common } from '@kit.AbilityKit';
import { getContext } from '@kit.ArkUI';
import { AudioSegment } from 'lib_api';
```

## 注意事项

1. **流式读取限制**：鸿蒙的 `http` 模块可能不支持真正的流式读取，可能需要等待完整响应后再解析
2. **内存管理**：及时释放已播放的音频片段，避免内存泄漏
3. **错误处理**：添加完善的错误处理机制，确保播放流畅
4. **网络稳定性**：确保网络连接稳定，避免播放中断

## 备选方案：轮询方式

如果流式读取不可行，可以使用轮询方式：

1. 后端提供 `/api/v1/podcast/deep/stream/segments?job_id=xxx&segment_index=0` 接口
2. 前端定期请求获取新的音频片段
3. 收到片段后立即播放

## 测试建议

1. 先测试小段音频的流式播放
2. 验证音频片段队列管理
3. 测试网络中断恢复
4. 验证内存使用情况

