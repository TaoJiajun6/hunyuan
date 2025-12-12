import { WindowModel, RouterUtils, RouterMap } from 'lib_common';
import { NavHeaderBar } from 'lib_widget';
import { promptAction, AppStorageV2 } from '@kit.ArkUI';
import { common } from '@kit.AbilityKit';
import { AudioRecorderUtils, RecordProgressCallback } from '../../utils/AudioRecorderUtils';
import { FileUtils } from '../../utils/FileUtils';
import { Logger } from 'lib_common';

/**
 * 音色克隆模式
 */
enum CloneMode {
  DIALOGUE = 'dialogue', // 对话模式
  UPLOAD = 'upload'      // 上传文件模式
}

@Builder
export function VoiceClonePageBuilder() {
  VoiceClonePage()
}

@ComponentV2
export struct VoiceClonePage {
  @Local currentMode: CloneMode = CloneMode.DIALOGUE; // 当前模式
  @Local isRecording: boolean = false; // 是否正在录制
  @Local recordingDuration: number = 0; // 录制时长（秒）
  @Local recordingTimer: number = 0; // 录制计时器
  @Local audioWaveform: number[] = []; // 音频波形数据（用于可视化）
  @Local uploadedFileUrl: string = ''; // 上传的文件URL
  @Local isProcessing: boolean = false; // 是否正在处理
  @Local windowModel: WindowModel = AppStorageV2.connect(WindowModel, () => new WindowModel())!;

  aboutToDisappear(): void {
    // 页面销毁时，如果正在录制，停止录制并释放资源
    if (this.isRecording) {
      this.stopRecording();
    }
    // 清理计时器
    if (this.recordingTimer) {
      clearInterval(this.recordingTimer);
      this.recordingTimer = 0;
    }
    // 释放录制器资源
    AudioRecorderUtils.release();
  }

  /**
   * 切换模式
   */
  switchMode(mode: CloneMode): void {
    if (this.isRecording) {
      promptAction.showToast({
        message: '请先停止录制',
        duration: 2000
      });
      return;
    }
    this.currentMode = mode;
    this.uploadedFileUrl = '';
  }

  /**
   * 开始对话录制
   */
  async startDialogue(): Promise<void> {
    if (this.isRecording) {
      this.stopRecording();
      return;
    }

    try {
      const context = this.getUIContext().getHostContext() as common.UIAbilityContext;
      const fileName = `voice_clone_${Date.now()}`;

      // 初始化录制器
      const initSuccess = await AudioRecorderUtils.initRecorder(context);
      if (!initSuccess) {
        promptAction.showToast({
          message: '初始化录制器失败',
          duration: 2000
        });
        return;
      }

      // 开始录制
      const startSuccess = await AudioRecorderUtils.startRecording(fileName, (progress: RecordProgressCallback) => {
        this.recordingDuration = Math.floor(progress.duration / 1000);
        // 模拟音频波形数据（实际应该从音频数据中提取）
        this.updateWaveform(progress.bytesRecorded);
      });

      if (startSuccess) {
        this.isRecording = true;
        this.recordingDuration = 0;
        this.audioWaveform = [];

        // 开始计时
        this.recordingTimer = setInterval(() => {
          this.recordingDuration++;
        }, 1000);

        promptAction.showToast({
          message: '开始对话，再次点击停止',
          duration: 2000
        });
      } else {
        promptAction.showToast({
          message: '开始录制失败',
          duration: 2000
        });
      }
    } catch (error) {
      Logger.error('VoiceClonePage', `开始录制失败: ${error}`);
      promptAction.showToast({
        message: `开始录制失败: ${error}`,
        duration: 2000
      });
    }
  }

  /**
   * 停止录制
   */
  async stopRecording(): Promise<void> {
    if (!this.isRecording) {
      return;
    }

    try {
      const result = await AudioRecorderUtils.stopRecording();
      
      if (this.recordingTimer) {
        clearInterval(this.recordingTimer);
        this.recordingTimer = 0;
      }

      if (result) {
        const context = this.getUIContext().getHostContext() as common.UIAbilityContext;
        const fileName = `voice_clone_${Date.now()}.wav`;
        
        // 上传到云存储
        const cloudInfo = await FileUtils.uploadAudioToCloud(context, result.filePath, fileName);
        
        if (cloudInfo && cloudInfo.cloudUrl) {
          this.uploadedFileUrl = cloudInfo.cloudUrl;
          promptAction.showToast({
            message: '录制完成并已上传',
            duration: 2000
          });
          
          // 开始处理音色克隆
          this.processVoiceClone(cloudInfo.cloudUrl);
        } else {
          promptAction.showToast({
            message: '上传失败，请重试',
            duration: 2000
          });
        }
      }
    } catch (error) {
      Logger.error('VoiceClonePage', `停止录制失败: ${error}`);
      promptAction.showToast({
        message: `停止录制失败: ${error}`,
        duration: 2000
      });
    } finally {
      this.isRecording = false;
      this.recordingDuration = 0;
    }
  }

  /**
   * 选择并上传文件
   */
  async selectAndUploadFile(): Promise<void> {
    try {
      const context = this.getUIContext().getHostContext() as common.UIAbilityContext;
      const audioFileInfo = await FileUtils.pickAudioFile(context, true);

      if (audioFileInfo && audioFileInfo.cloudUrl) {
        this.uploadedFileUrl = audioFileInfo.cloudUrl;
        promptAction.showToast({
          message: '文件已上传',
          duration: 2000
        });
        
        // 开始处理音色克隆
        this.processVoiceClone(audioFileInfo.cloudUrl);
      }
    } catch (error) {
      Logger.error('VoiceClonePage', `选择文件失败: ${error}`);
      promptAction.showToast({
        message: `选择文件失败: ${error}`,
        duration: 2000
      });
    }
  }

  /**
   * 处理音色克隆
   */
  async processVoiceClone(audioUrl: string): Promise<void> {
    this.isProcessing = true;
    
    try {
      // TODO: 调用后端API进行音色克隆
      // const response = await voiceCloneService.cloneVoice(audioUrl);
      
      promptAction.showToast({
        message: '音色克隆处理中...',
        duration: 2000
      });
      
      // 模拟处理过程
      setTimeout(() => {
        this.isProcessing = false;
        promptAction.showToast({
          message: '音色克隆完成',
          duration: 2000
        });
      }, 3000);
    } catch (error) {
      Logger.error('VoiceClonePage', `音色克隆失败: ${error}`);
      this.isProcessing = false;
      promptAction.showToast({
        message: `音色克隆失败: ${error}`,
        duration: 2000
      });
    }
  }

  /**
   * 更新音频波形（模拟）
   */
  updateWaveform(bytesRecorded: number): void {
    // 模拟生成波形数据
    const waveCount = 20;
    const newWaveform: number[] = [];
    for (let i = 0; i < waveCount; i++) {
      const amplitude = Math.random() * 30 + 10;
      newWaveform.push(amplitude);
    }
    this.audioWaveform = newWaveform;
  }

  build() {
    NavDestination() {
      Column() {
        // 顶部导航栏
        NavHeaderBar({
          title: '音色克隆',
          showBackBtn: true
        })

        // 主内容区域（可滚动）
        Scroll() {
          Column({ space: 24 }) {
            // 标题和副标题
            Column({ space: 8 }) {
              Text('音色克隆')
                .fontSize(18)
                .fontWeight(FontWeight.Bold)
                .fontColor('#1A1A1A')
              
              Text('在几秒钟内克隆你的声音——让它为你发声')
                .fontSize(14)
                .fontColor('#666666')
                .lineHeight(20)
            }
            .width('100%')
            .padding({ top: 20 })

            // 模式选择按钮
            Row({ space: 12 }) {
              Button() {
                Row({ space: 8 }) {
                  Image($r("sys.symbol.message"))
                    .width(20)
                    .height(20)
                    .fillColor(this.currentMode === CloneMode.DIALOGUE ? '#FFFFFF' : '#666666')
                  Text('对话')
                    .fontSize(16)
                    .fontWeight(FontWeight.Medium)
                    .fontColor(this.currentMode === CloneMode.DIALOGUE ? '#FFFFFF' : '#333333')
                }
              }
              .type(ButtonType.Normal)
              .layoutWeight(1)
              .height(52)
              .backgroundColor(this.currentMode === CloneMode.DIALOGUE ? '#ffc78cfd' : '#FFFFFF')
              .borderRadius(26)
              .border({
                width: this.currentMode === CloneMode.DIALOGUE ? 0 : 1,
                color: '#E0E0E0',
                style: BorderStyle.Solid
              })
              .shadow(this.currentMode === CloneMode.DIALOGUE ? {
                radius: 14,
                color: '#1F000000',
                offsetX: 0,
                offsetY: 20
              } : {
                radius: 14,
                color: '#1F000000',
                offsetX: 0,
                offsetY: 20
              })
              .onClick(() => this.switchMode(CloneMode.DIALOGUE))

              Button() {
                Row({ space: 8 }) {
                  Image($r("sys.symbol.arrow_up"))
                    .width(20)
                    .height(20)
                    .fillColor(this.currentMode === CloneMode.UPLOAD ? '#FFFFFF' : '#666666')
                  Text('上传文件')
                    .fontSize(16)
                    .fontWeight(FontWeight.Medium)
                    .fontColor(this.currentMode === CloneMode.UPLOAD ? '#FFFFFF' : '#333333')
                }
              }
              .type(ButtonType.Normal)
              .layoutWeight(1)
              .height(52)
              .backgroundColor(this.currentMode === CloneMode.UPLOAD ? '#ffc78cfd' : '#FFFFFF')
              .borderRadius(26)
              .border({
                width: this.currentMode === CloneMode.UPLOAD ? 0 : 1,
                color: '#E0E0E0',
                style: BorderStyle.Solid
              })
              .shadow(this.currentMode === CloneMode.UPLOAD ? {
                radius: 14,
                color: '#1F000000',
                offsetX: 0,
                offsetY: 20
              } : {
                radius: 14,
                color: '#1F000000',
                offsetX: 0,
                offsetY: 20
              })
              .onClick(() => this.switchMode(CloneMode.UPLOAD))
            }
            .width('100%')

            // 分隔线
            Blank()
              .height(1)
              .backgroundColor('#E0E0E0')
              .width('100%')

            // 根据模式显示不同内容
            if (this.currentMode === CloneMode.DIALOGUE) {
              this.buildDialogueMode()
            } else {
              this.buildUploadMode()
            }
          }
          .width('100%')
          .padding({ left: 20, right: 20, top: 24, bottom: 24 })
        }
        .layoutWeight(1)
        .width('100%')
        .backgroundColor('#FAFAFA')
      }
      .width('100%')
      .height('100%')
      .backgroundColor('#F8F8F8')
    }
    .hideTitleBar(true)
  }

  @Builder
  buildDialogueMode() {
    Column({ space: 20 }) {
      // 说明文字卡片
      Column({ space: 8 }) {
        Text('通过对话克隆你的音色')
          .fontSize(18)
          .fontWeight(FontWeight.Bold)
          .fontColor('#1A1A1A')
          .alignSelf(ItemAlign.Start)
        
        Row({ space: 4 }) {
          Text('请在安静的环境下对话')
            .fontSize(14)
            .fontColor('#666666')
          
          Text('使用说明 >')
            .fontSize(14)
            .fontColor('#ffc78cfd')
            .onClick(() => {
              promptAction.showToast({
                message: '使用说明功能开发中',
                duration: 2000
              });
            })
        }
        .width('100%')
      }
      .width('100%')
      .padding({ top: 16, bottom: 16, left: 16, right: 16 })
      .backgroundColor('#FFFFFF')
      .borderRadius(16)
      .shadow({
        radius: 14,
        color: '#1F000000',
        offsetX: 0,
        offsetY: 20
      })

      // 音频波形可视化卡片
      Column() {
        if (this.isRecording || this.audioWaveform.length > 0) {
          Row({ space: 4 }) {
            ForEach(this.audioWaveform, (amplitude: number, index: number) => {
              Blank()
                .width(3)
                .height(amplitude)
                .backgroundColor('#ffc78cfd')
                .borderRadius(1.5)
            })
          }
          .width('100%')
          .height(60)
          .justifyContent(FlexAlign.Center)
          .alignItems(VerticalAlign.Bottom)
        } else {
          Blank()
            .height(60)
        }
      }
      .width('100%')
      .height(100)
      .padding({ top: 20, bottom: 20, left: 16, right: 16 })
      .backgroundColor('#FFFFFF')
      .borderRadius(16)
      .shadow({
        radius: 14,
        color: '#1F000000',
        offsetX: 0,
        offsetY: 20
      })

      // 开始对话按钮
      Button() {
        Row({ space: 8 }) {
          Image($r("sys.symbol.message"))
            .width(24)
            .height(24)
            .fillColor('#FFFFFF')
          Text(this.isRecording ? `停止对话 (${this.recordingDuration}s)` : '开始对话')
            .fontSize(18)
            .fontWeight(FontWeight.Bold)
            .fontColor('#FFFFFF')
        }
      }
      .type(ButtonType.Normal)
      .width('100%')
      .height(52)
      .backgroundColor(this.isRecording ? '#FF5722' : '#ffc78cfd')
      .borderRadius(26)
      .shadow({
        radius: 14,
        color: '#1F000000',
        offsetX: 0,
        offsetY: 20
      })
      .onClick(() => this.startDialogue())
    }
    .width('100%')
    .padding({ top: 20 })
  }

  @Builder
  buildUploadMode() {
    Column({ space: 20 }) {
      // 说明文字卡片
      Column({ space: 8 }) {
        Text('通过上传文件克隆你的音色')
          .fontSize(18)
          .fontWeight(FontWeight.Bold)
          .fontColor('#1A1A1A')
          .alignSelf(ItemAlign.Start)
        
        Text('请上传包含你声音的音频文件（支持 WAV、MP3 等格式）')
          .fontSize(14)
          .fontColor('#666666')
      }
      .width('100%')
      .padding({ top: 16, bottom: 16, left: 16, right: 16 })
      .backgroundColor('#FFFFFF')
      .borderRadius(16)
      .shadow({
        radius: 14,
        color: '#1F000000',
        offsetX: 0,
        offsetY: 20
      })

      // 上传文件按钮
      Button() {
        Row({ space: 8 }) {
          Image($r("sys.symbol.arrow_up"))
            .width(24)
            .height(24)
            .fillColor('#FFFFFF')
          Text(this.uploadedFileUrl ? '重新选择文件' : '选择文件')
            .fontSize(18)
            .fontWeight(FontWeight.Bold)
            .fontColor('#FFFFFF')
        }
      }
      .type(ButtonType.Normal)
      .width('100%')
      .height(52)
      .backgroundColor('#ffc78cfd')
      .borderRadius(26)
      .shadow({
        radius: 14,
        color: '#1F000000',
        offsetX: 0,
        offsetY: 20
      })
      .onClick(() => this.selectAndUploadFile())

      // 如果已上传文件，显示文件信息卡片
      if (this.uploadedFileUrl) {
        Column({ space: 8 }) {
          Text('文件已上传')
            .fontSize(14)
            .fontColor('#4CAF50')
            .fontWeight(FontWeight.Medium)
        }
        .width('100%')
        .padding({ top: 16, bottom: 16, left: 16, right: 16 })
        .backgroundColor('#FFFFFF')
        .borderRadius(16)
        .shadow({
          radius: 14,
          color: '#1F000000',
          offsetX: 0,
          offsetY: 20
        })
      }
    }
    .width('100%')
    .padding({ top: 20 })
  }
}

