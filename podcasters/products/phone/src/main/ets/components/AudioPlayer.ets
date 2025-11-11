import { media } from '@kit.MediaKit';
import { fileIo } from '@kit.CoreFileKit';
import { common } from '@kit.AbilityKit';
import { promptAction } from '@kit.ArkUI';
import { util } from '@kit.ArkTS';
import { BusinessError, request } from '@kit.BasicServicesKit';
import { cloudStorage } from '@kit.CloudFoundationKit';

/**
 * 音频播放器组件
 * 支持播放云存储URL或base64编码的音频
 * 功能：播放/暂停、进度条、时间显示、音量控制
 */
@ComponentV2
export struct AudioPlayer {
  @Local isPlaying: boolean = false;
  @Local duration: number = 0;
  @Local currentTime: number = 0;
  @Local volume: number = 1.0;
  @Local isMuted: boolean = false;
  @Local isLoading: boolean = false;
  @Local audioPlayer?: media.AVPlayer;
  @Local tempFilePath: string = '';
  @Local isSeeking: boolean = false;
  @Param audioBase64: string = '';
  // 新增：支持直接播放云存储URL（优先使用此字段）
  @Param audioUrl: string = '';
  @Param onStateChange: (isPlaying: boolean) => void = () => {};

  async aboutToAppear(): Promise<void> {
    if (this.audioUrl || this.audioBase64) {
      await this.initPlayer();
    }
  }

  aboutToDisappear(): void {
    this.releasePlayer();
  }

  /**
   * 从云存储URL中提取云侧文件路径
   * 例如：https://ops-server-drcn.agcstorage.link/v0/podcasters-y0qig/outputs/podcasts/podcast_xxx.wav
   * 提取：outputs/podcasts/podcast_xxx.wav
   */
  private extractCloudPath(url: string): string | null {
    try {
      // 查找 /outputs/ 来确定路径起始位置（这是最可靠的方式）
      const outputsIndex = url.indexOf('/outputs/');
      if (outputsIndex !== -1) {
        // 提取从 /outputs/ 开始到URL结尾的所有内容
        const cloudPath = url.substring(outputsIndex + 1); // +1 去掉开头的 /
        return cloudPath;
      }
      
      // 如果没有找到 /outputs/，尝试其他方式
      // 查找 bucket 名称后的路径（例如：podcasters-y0qig/outputs/podcasts/xxx.wav）
      const bucketMatch = url.match(/\/[^\/]+\/(outputs\/[^\/]+\/.+)$/);
      if (bucketMatch && bucketMatch[1]) {
        return bucketMatch[1];
      }
      
      // 最后尝试：只提取文件名，假设在 outputs/podcasts/ 目录下
      const lastSlashIndex = url.lastIndexOf('/');
      if (lastSlashIndex !== -1) {
        const fileName = url.substring(lastSlashIndex + 1);
        // 如果文件名看起来像音频文件，假设它在 outputs/podcasts/ 目录下
        if (fileName.match(/\.(wav|mp3|m4a|aac)$/i)) {
          return `outputs/podcasts/${fileName}`;
        }
      }
      
      return null;
    } catch (error) {
      return null;
    }
  }

  /**
   * 从云存储下载文件
   */
  private async downloadFromCloudStorage(cloudPath: string): Promise<string> {
    return new Promise<string>((resolve, reject) => {
      try {
        const context = getContext(this) as common.UIAbilityContext;
        const storageBucket = cloudStorage.bucket();
        
        // 生成本地文件名
        const fileName = cloudPath.split('/').pop() || `audio_${Date.now()}.wav`;
        const localPath = fileName;

        storageBucket.downloadFile(context, {
          localPath: localPath,
          cloudPath: cloudPath,
          overwrite: true // 允许覆盖已存在的文件
        }).then((task: request.agent.Task) => {
          // 监听下载进度
          task.on('progress', (progress) => {
            // 可以在这里更新下载进度UI
          });

          // 监听下载完成
          task.on('completed', () => {
            // 文件已下载到 context.cacheDir/localPath
            const localFilePath = `${context.cacheDir}/${localPath}`;
            resolve(localFilePath);
          });

          // 监听下载失败
          task.on('failed', (error: BusinessError) => {
            reject(new Error(`下载失败: ${error.message || String(error)}`));
          });

          // 启动下载任务
          task.start((err: BusinessError) => {
            if (err) {
              reject(new Error(`启动下载任务失败: ${err.message || String(err)}`));
            }
          });
        }).catch((err: BusinessError) => {
          reject(new Error(`下载文件失败: ${err.message || String(err)}`));
        });
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * 初始化播放器
   */
  async initPlayer(): Promise<void> {
    if (!this.audioUrl && !this.audioBase64) {
      return;
    }

    try {
      this.isLoading = true;
      // 创建播放器
      this.audioPlayer = await media.createAVPlayer();
      
      if (this.audioUrl) {
        // 从云存储URL中提取云侧文件路径
        const cloudPath = this.extractCloudPath(this.audioUrl);
        if (cloudPath) {
          // 从云存储下载文件
          try {
            this.tempFilePath = await this.downloadFromCloudStorage(cloudPath);
            this.audioPlayer.url = this.tempFilePath;
          } catch (downloadError) {
            // 下载失败，尝试直接使用URL播放（作为备选）
            promptAction.showToast({
              message: `云存储下载失败，尝试直接播放: ${downloadError}`,
              duration: 2000
            });
            this.audioPlayer.url = this.audioUrl;
          }
        } else {
          // 无法提取云侧路径，直接使用URL播放
          this.audioPlayer.url = this.audioUrl;
        }
      } else {
        // 将base64数据保存为临时文件后播放
        const audioData = this.base64ToUint8Array(this.audioBase64);
        const context = getContext(this) as common.UIAbilityContext;
        const tempDir = context.cacheDir;
        this.tempFilePath = `${tempDir}/temp_audio_${Date.now()}.wav`;
        const file = await fileIo.open(this.tempFilePath, fileIo.OpenMode.CREATE | fileIo.OpenMode.READ_WRITE | fileIo.OpenMode.TRUNC);
        await fileIo.write(file.fd, audioData.buffer);
        await fileIo.close(file.fd);
        this.audioPlayer.url = this.tempFilePath;
      }

      // 设置音量
      this.audioPlayer.volume = this.volume;

      // 监听播放状态
      this.audioPlayer.on('stateChange', (state: string) => {
        if (state === 'playing') {
          this.isPlaying = true;
          this.isLoading = false;
          this.onStateChange?.(true);
        } else if (state === 'paused' || state === 'stopped') {
          this.isPlaying = false;
          this.isLoading = false;
          this.onStateChange?.(false);
        } else if (state === 'prepared' || state === 'idle') {
          this.isLoading = false;
        }
      });

      // 监听时间更新（仅在非拖拽时更新）
      this.audioPlayer.on('timeUpdate', (time: number) => {
        if (!this.isSeeking) {
          this.currentTime = time;
        }
      });

      // 获取时长
      this.audioPlayer.on('durationUpdate', (duration: number) => {
        this.duration = duration;
      });

      // 监听错误
      this.audioPlayer.on('error', (error: BusinessError) => {
        this.isLoading = false;
        promptAction.showToast({
          message: `播放错误: ${error.message || String(error)}`,
          duration: 3000
        });
      });

    } catch (error) {
      this.isLoading = false;
      promptAction.showToast({
        message: `初始化播放器失败: ${error}`,
        duration: 2000
      });
    }
  }

  /**
   * 播放/暂停
   */
  async togglePlay(): Promise<void> {
    if (!this.audioPlayer) {
      await this.initPlayer();
      return;
    }

    try {
      if (this.isPlaying) {
        await this.audioPlayer.pause();
      } else {
        await this.audioPlayer.play();
      }
    } catch (error) {
      promptAction.showToast({
        message: `播放失败: ${error}`,
        duration: 2000
      });
    }
  }

  /**
   * 停止播放
   */
  async stop(): Promise<void> {
    if (this.audioPlayer) {
      try {
        await this.audioPlayer.stop();
        await this.audioPlayer.reset();
      } catch (error) {
        // 忽略错误
      }
    }
  }

  /**
   * 释放播放器
   */
  releasePlayer(): void {
    if (this.audioPlayer) {
      this.audioPlayer.release();
      this.audioPlayer = undefined;
    }
    // 清理临时文件
    if (this.tempFilePath) {
      try {
        fileIo.unlinkSync(this.tempFilePath);
      } catch (error) {
        // 忽略错误
      }
    }
  }

  /**
   * base64转Uint8Array
   */
  private base64ToUint8Array(base64: string): Uint8Array {
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

  /**
   * 跳转到指定时间
   */
  async seekTo(time: number): Promise<void> {
    if (!this.audioPlayer || this.duration === 0) {
      return;
    }
    try {
      this.isSeeking = true;
      await this.audioPlayer.seek(time);
      this.currentTime = time;
      this.isSeeking = false;
    } catch (error) {
      this.isSeeking = false;
      promptAction.showToast({
        message: `跳转失败: ${error}`,
        duration: 2000
      });
    }
  }

  /**
   * 设置音量
   */
  async setVolume(vol: number): Promise<void> {
    if (!this.audioPlayer) {
      return;
    }
    try {
      this.volume = Math.max(0, Math.min(1, vol));
      this.audioPlayer.volume = this.volume;
      if (this.volume === 0) {
        this.isMuted = true;
      } else if (this.isMuted && this.volume > 0) {
        this.isMuted = false;
      }
    } catch (error) {
      // 忽略错误
    }
  }

  /**
   * 切换静音
   */
  async toggleMute(): Promise<void> {
    if (this.isMuted) {
      await this.setVolume(0.5);
    } else {
      await this.setVolume(0);
    }
  }

  /**
   * 格式化时间
   */
  private formatTime(seconds: number): string {
    const totalSeconds = Math.floor(seconds);
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }

  /**
   * 获取进度百分比
   */
  private getProgressPercent(): number {
    if (this.duration === 0) {
      return 0;
    }
    return (this.currentTime / this.duration) * 100;
  }

  build() {
    Column({ space: 12 }) {
      // 播放控制行
      Row({ space: 12 }) {
        // 播放/暂停按钮
        Button() {
          if (this.isLoading) {
            LoadingProgress()
              .width(20)
              .height(20)
              .color($r('sys.color.font_on_primary'))
          } else {
            Text(this.isPlaying ? '⏸️' : '▶️')
              .fontSize(24)
              .fontColor($r('sys.color.font_on_primary'))
          }
        }
        .width(48)
        .height(48)
        .borderRadius(24)
        .backgroundColor($r('sys.color.icon_emphasize'))
        .enabled(!this.isLoading)
        .onClick(() => {
          this.togglePlay();
        })

        // 时间显示和进度条
        Column({ space: 4 }) {
          // 进度条
          Slider({
            value: this.getProgressPercent(),
            min: 0,
            max: 100,
            step: 0.1
          })
            .blockColor($r('sys.color.icon_emphasize'))
            .selectedColor($r('sys.color.icon_emphasize'))
            .trackColor($r('sys.color.comp_background_tertiary'))
            .showSteps(false)
            .showTips(false)
            .enabled(this.duration > 0 && !this.isLoading)
            .onChange((value: number) => {
              if (this.duration > 0) {
                const seekTime = (value / 100) * this.duration;
                this.seekTo(seekTime);
              }
            })

          // 时间显示
          Row() {
            Text(this.formatTime(this.currentTime / 1000))
              .fontSize($r('sys.float.Body_S'))
              .fontColor($r('sys.color.font_secondary'))
            
            Blank()
            
            Text(this.duration > 0 ? this.formatTime(this.duration / 1000) : '--:--')
              .fontSize($r('sys.float.Body_S'))
              .fontColor($r('sys.color.font_secondary'))
          }
          .width('100%')
        }
        .layoutWeight(1)

        // 音量控制按钮
        Button() {
          Text(this.isMuted || this.volume === 0 ? '🔇' : this.volume < 0.5 ? '🔉' : '🔊')
            .fontSize(20)
            .fontColor($r('sys.color.font_primary'))
        }
        .width(40)
        .height(40)
        .borderRadius(20)
        .backgroundColor($r('sys.color.comp_background_tertiary'))
        .onClick(() => {
          this.toggleMute();
        })
      }
      .width('100%')
      .alignItems(VerticalAlign.Center)

      // 音量滑块（可选，如果需要更精细控制）
      if (this.volume > 0) {
        Row({ space: 8 }) {
          Text('🔊')
            .fontSize(16)
          
          Slider({
            value: this.volume * 100,
            min: 0,
            max: 100,
            step: 1
          })
            .blockColor($r('sys.color.icon_emphasize'))
            .selectedColor($r('sys.color.icon_emphasize'))
            .trackColor($r('sys.color.comp_background_tertiary'))
            .showSteps(false)
            .showTips(false)
            .layoutWeight(1)
            .onChange((value: number) => {
              this.setVolume(value / 100);
            })

          Text(`${Math.round(this.volume * 100)}%`)
            .fontSize($r('sys.float.Body_S'))
            .fontColor($r('sys.color.font_secondary'))
            .width(40)
        }
        .width('100%')
        .alignItems(VerticalAlign.Center)
      }
    }
    .width('100%')
    .padding(16)
    .borderRadius(12)
    .backgroundColor($r('sys.color.comp_background_tertiary'))
  }
}

