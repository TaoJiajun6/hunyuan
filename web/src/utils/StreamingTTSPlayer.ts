/**
 * StreamingTTSPlayer.ts
 * 
 * 一个用于播放「流式 Base64 MP3」音频的播放器。
 * 使用 MediaSource + SourceBuffer 实现边接收边播放，不卡顿无杂音。
 */

export interface StreamingTTSPlayerOptions {
  /** 用于监听播放器状态（ready、error 等）的回调 */
  onEvent?: (event: string, data?: any) => void;
}

export class StreamingTTSPlayer {
  private audio: HTMLAudioElement;           // 播放用的 <audio> 元素
  private mediaSource: MediaSource;           // 媒体源（支持流式拼接）
  private sourceBuffer: SourceBuffer | null = null; // 用于接收音频块的缓冲区
  private queue: ArrayBuffer[] = [];          // 等待写入 SourceBuffer 的音频块队列
  private isBufferUpdating = false;            // 是否正在写入数据（避免并发）
  private onEvent?: (event: string, data?: any) => void; // 事件回调

  constructor(options?: StreamingTTSPlayerOptions) {
    this.onEvent = options?.onEvent;

    // 1. 创建 HTMLAudioElement
    this.audio = new Audio();

    // 2. 创建 MediaSource 并挂载到 audio 元素
    this.mediaSource = new MediaSource();
    this.audio.src = URL.createObjectURL(this.mediaSource);

    // 3. 等待 mediaSource 初始化完成
    this.mediaSource.addEventListener("sourceopen", () => {
      try {
        // 4. 创建一个音频类型的 SourceBuffer，用于接收音频块
        // 注意：优先使用 MP3，如果不支持则尝试 WAV
        try {
          // 优先尝试 MP3（更小的文件大小）
          this.sourceBuffer = this.mediaSource.addSourceBuffer('audio/mpeg');
        } catch (e) {
          // 如果 MP3 不支持，尝试 WAV
          try {
            this.sourceBuffer = this.mediaSource.addSourceBuffer('audio/wav');
          } catch (e2) {
            // 如果都不支持，尝试 WebM（通用格式）
            try {
              this.sourceBuffer = this.mediaSource.addSourceBuffer('audio/webm; codecs="opus"');
            } catch (e3) {
              // 最后尝试通用音频格式
              this.sourceBuffer = this.mediaSource.addSourceBuffer('audio/mp4');
            }
          }
        }

        // 5. 设置拼接模式为 sequence（自动按顺序拼接）
        this.sourceBuffer.mode = 'sequence';

        // 6. 每次 appendBuffer 完成后触发 updateend，继续处理队列
        this.sourceBuffer.addEventListener('updateend', () => {
          this.isBufferUpdating = false;
          this.feedQueue();
        });

        this.emit("ready");
      } catch (err) {
        console.error("Failed to add sourceBuffer:", err);
        this.emit("error", err);
      }
    });

    // 监听 audio 元素播放错误
    this.audio.addEventListener("error", (e) => {
      this.emit("error", e);
    });

    // 监听播放状态变化
    this.audio.addEventListener("play", () => {
      this.emit("play");
    });

    this.audio.addEventListener("pause", () => {
      this.emit("pause");
    });

    this.audio.addEventListener("ended", () => {
      this.emit("ended");
    });

    // 监听时间更新
    this.audio.addEventListener("timeupdate", () => {
      this.emit("timeupdate", {
        currentTime: this.audio.currentTime,
        duration: this.audio.duration
      });
    });
  }

  /**
   * 接收一段 base64 MP3 数据块并放入播放队列
   * @param base64 base64 编码的 MP3 数据块
   * @param autoPlay 是否自动开始播放（默认 true）
   */
  receiveBase64(base64: string, autoPlay = true) {
    try {
      const buffer = this.base64ToArrayBuffer(base64);
      this.queue.push(buffer);
      this.feedQueue(); // 立即尝试送入 SourceBuffer
      if (autoPlay && this.audio.paused) {
        this.play();
      }
    } catch (err) {
      console.error("TTS decode error:", err);
      this.emit("error", err);
    }
  }

  /** 播放（如果已暂停） */
  play() {
    if (this.audio.paused) {
      this.audio.play().catch((err) => {
        console.error("Play failed:", err);
        this.emit("error", err);
      });
    }
  }

  /** 暂停播放 */
  pause() {
    if (!this.audio.paused) {
      this.audio.pause();
    }
  }

  /**
   * 停止播放并清空缓冲
   * （会丢弃所有未播放的数据）
   */
  stop() {
    this.pause();
    this.queue = [];
    if (this.mediaSource.readyState === "open" && this.sourceBuffer && !this.sourceBuffer.updating) {
      try {
        this.sourceBuffer.abort(); // 终止当前的缓冲区写入
      } catch {}
    }
    this.audio.currentTime = 0;
  }

  /**
   * 结束流式传输（关闭 MediaSource）
   */
  endOfStream() {
    if (this.mediaSource.readyState === "open") {
      try {
        // 等待队列处理完成
        if (this.queue.length === 0 && !this.isBufferUpdating) {
          this.mediaSource.endOfStream();
          this.emit("ended");
        } else {
          // 如果还有数据在队列中，等待处理完成
          const checkEnd = () => {
            if (this.queue.length === 0 && !this.isBufferUpdating) {
              this.mediaSource.endOfStream();
              this.emit("ended");
            } else {
              setTimeout(checkEnd, 100);
            }
          };
          checkEnd();
        }
      } catch (err) {
        console.error("Failed to end stream:", err);
      }
    }
  }

  /**
   * 内部方法：尝试把队列中的数据 append 到 SourceBuffer
   */
  private feedQueue() {
    // 没有 SourceBuffer 或正在写入时不处理
    if (!this.sourceBuffer || this.isBufferUpdating) return;
    if (this.queue.length === 0) return;

    if (!this.sourceBuffer.updating) {
      const chunk = this.queue.shift()!;
      try {
        this.isBufferUpdating = true;
        this.sourceBuffer.appendBuffer(chunk); // 核心：追加 MP3 数据到播放流
      } catch (err) {
        console.error("Failed to append buffer:", err);
        this.isBufferUpdating = false;
        this.emit("error", err);
      }
    }
  }

  /**
   * Base64 -> ArrayBuffer 转换工具
   */
  private base64ToArrayBuffer(base64: string): ArrayBuffer {
    // 移除 data URL 前缀（如果有）
    const base64Data = base64.replace(/^data:audio\/\w+;base64,/, "");
    const binary = atob(base64Data);
    const len = binary.length;
    const buffer = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
      buffer[i] = binary.charCodeAt(i);
    }
    return buffer.buffer;
  }

  /** 触发事件回调 */
  private emit(event: string, data?: any) {
    this.onEvent?.(event, data);
  }

  /** 获取当前播放时间 */
  getCurrentTime(): number {
    return this.audio.currentTime || 0;
  }

  /** 获取总时长 */
  getDuration(): number {
    return this.audio.duration || 0;
  }

  /** 获取是否正在播放 */
  isPlaying(): boolean {
    return !this.audio.paused;
  }

  /** 获取音频元素（用于外部控制） */
  getAudioElement(): HTMLAudioElement {
    return this.audio;
  }

  /** 清理资源 */
  destroy() {
    this.stop();
    if (this.audio.src) {
      URL.revokeObjectURL(this.audio.src);
    }
    if (this.mediaSource.readyState === "open") {
      try {
        this.mediaSource.endOfStream();
      } catch {}
    }
  }
}

