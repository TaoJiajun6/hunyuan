import { media } from '@kit.MediaKit';
import { fileIo } from '@kit.CoreFileKit';
import { common } from '@kit.AbilityKit';
import { promptAction } from '@kit.ArkUI';
import { util } from '@kit.ArkTS';
import { BusinessError } from '@kit.BasicServicesKit';

/**
 * 音频播放器组件
 * 注意：这是一个简化版本的音频播放器，实际使用时可能需要根据HarmonyOS的媒体API进行调整
 */
@ComponentV2
export struct AudioPlayer {
  @Local isPlaying: boolean = false;
  @Local duration: number = 0;
  @Local currentTime: number = 0;
  @Local audioPlayer?: media.AVPlayer;
  @Local tempFilePath: string = '';
  @Param audioBase64: string = '';
  @Param onStateChange: (isPlaying: boolean) => void = () => {};

  async aboutToAppear(): Promise<void> {
    if (this.audioBase64) {
      await this.initPlayer();
    }
  }

  aboutToDisappear(): void {
    this.releasePlayer();
  }

  /**
   * 初始化播放器
   */
  async initPlayer(): Promise<void> {
    if (!this.audioBase64) {
      return;
    }

    try {
      // 将base64数据转换为Uint8Array
      const audioData = this.base64ToUint8Array(this.audioBase64);

      // 创建临时文件
      const context = getContext(this) as common.UIAbilityContext;
      const tempDir = context.cacheDir;
      this.tempFilePath = `${tempDir}/temp_audio_${Date.now()}.wav`;

      // 写入临时文件
      const file = await fileIo.open(this.tempFilePath, fileIo.OpenMode.CREATE | fileIo.OpenMode.READ_WRITE | fileIo.OpenMode.TRUNC);
      await fileIo.write(file.fd, audioData.buffer);
      await fileIo.close(file.fd);

      // 创建播放器
      this.audioPlayer = await media.createAVPlayer();
      this.audioPlayer.url = this.tempFilePath;

      // 监听播放状态
      this.audioPlayer.on('stateChange', (state: string) => {
        if (state === 'playing') {
          this.isPlaying = true;
          this.onStateChange?.(true);
        } else if (state === 'paused' || state === 'stopped') {
          this.isPlaying = false;
          this.onStateChange?.(false);
        }
      });

      // 监听时间更新
      this.audioPlayer.on('timeUpdate', (time: number) => {
        this.currentTime = time;
      });

      // 获取时长
      this.audioPlayer.on('durationUpdate', (duration: number) => {
        this.duration = duration;
      });

    } catch (error) {
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
   * 格式化时间
   */
  private formatTime(seconds: number): string {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }

  build() {
    Row({ space: 12 }) {
      Button() {
        Text(this.isPlaying ? '⏸️' : '▶️')
          .fontSize(20)
      }
      .width(40)
      .height(40)
      .borderRadius(20)
      .onClick(() => {
        this.togglePlay();
      })

      Column({ space: 4 }) {
        if (this.duration > 0) {
          Text(`${this.formatTime(this.currentTime / 1000)} / ${this.formatTime(this.duration / 1000)}`)
            .fontSize($r('sys.float.Body_S'))
            .fontColor($r('sys.color.font_secondary'))
        } else {
          Text('准备播放')
            .fontSize($r('sys.float.Body_S'))
            .fontColor($r('sys.color.font_secondary'))
        }
      }
      .alignItems(HorizontalAlign.Start)
      .layoutWeight(1)
    }
    .width('100%')
    .padding(12)
    .borderRadius(8)
    .backgroundColor($r('sys.color.comp_background_tertiary'))
  }
}

