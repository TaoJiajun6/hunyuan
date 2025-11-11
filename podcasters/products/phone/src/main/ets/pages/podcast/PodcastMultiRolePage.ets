import { RouterMap, RouterUtils, WindowModel } from 'lib_common';
import { NavHeaderBar } from 'lib_widget';
import { podcastService, MultiRoleRequest, PodcastResult } from 'lib_api';
import { FileUtils, TextFileInfo } from '../../utils/FileUtils';
import { promptAction, AppStorageV2 } from '@kit.ArkUI';
import { PodcastResultPageParams } from './PodcastResultPage';
import { common } from '@kit.AbilityKit';

@Builder
export function PodcastMultiRolePageBuilder() {
  PodcastMultiRolePage()
}

@ComponentV2
export struct PodcastMultiRolePage {
  @Local text: string = ''; // 保留用于兼容，但优先使用textFileUrl
  @Local textFileUrl: string = ''; // 文本文件云存储URL
  @Local textFileName: string = ''; // 文本文件名
  @Local roleVoiceUrls: Record<string, string> = {}; // 角色名 -> 云存储URL（必需）
  @Local roleNames: string[] = ['角色A', '角色B'];
  @Local isLoading: boolean = false;
  @Local jobId: string = '';
  @Local progressPercent: number = 0;
  @Local progressMessage: string = '';
  private progressTimer: number = 0;
  @Local windowModel: WindowModel = AppStorageV2.connect(WindowModel, () => new WindowModel())!;

  /**
   * 选择角色音色文件
   */
  async selectVoiceFile(roleName: string): Promise<void> {
    try {
      // 获取UIAbility上下文
      const context = this.getUIContext().getHostContext() as common.UIAbilityContext;
      // 强制使用云存储上传（后端要求）
      const audioFileInfo = await FileUtils.pickAudioFile(context, true);
      if (audioFileInfo && audioFileInfo.cloudUrl) {
        // 保存云存储URL
        if (!this.roleVoiceUrls) {
          this.roleVoiceUrls = {};
        }
        this.roleVoiceUrls[roleName] = audioFileInfo.cloudUrl;
        promptAction.showToast({
          message: `${roleName}音色已选择并上传到云存储`,
          duration: 2000
        });
      } else {
        // 上传失败或未获取到URL
        promptAction.showToast({
          message: `${roleName}音色上传失败，请重试`,
          duration: 2000
        });
      }
    } catch (error) {
      promptAction.showToast({
        message: `选择文件失败: ${error}`,
        duration: 2000
      });
    }
  }

  /**
   * 选择播客文本文件
   */
  async selectTextFile(): Promise<void> {
    try {
      // 获取UIAbility上下文
      const context = this.getUIContext().getHostContext() as common.UIAbilityContext;
      // 使用云存储上传
      const textFileInfo = await FileUtils.pickTextFile(context, true);
      if (textFileInfo && textFileInfo.cloudUrl) {
        // 保存云存储URL
        this.textFileUrl = textFileInfo.cloudUrl;
        this.textFileName = textFileInfo.fileName;
        // 如果文件已读取内容，也保存到text字段（用于兼容）
        if (textFileInfo.content) {
          this.text = textFileInfo.content;
        }
        promptAction.showToast({
          message: `文本文件已选择并上传到云存储: ${textFileInfo.fileName}`,
          duration: 2000
        });
      } else {
        // 上传失败或未获取到URL
        promptAction.showToast({
          message: '文本文件上传失败，请重试',
          duration: 2000
        });
      }
    } catch (error) {
      promptAction.showToast({
        message: `选择文件失败: ${error}`,
        duration: 2000
      });
    }
  }

  /**
   * 生成播客
   */
  async generatePodcast(): Promise<void> {
    // 检查文本输入（text或textFileUrl至少有一个）
    const hasText = this.text.trim().length > 0;
    const hasTextFile = this.textFileUrl.trim().length > 0;
    
    if (!hasText && !hasTextFile) {
      promptAction.showToast({
        message: '请上传播客文本文件或输入文本',
        duration: 2000
      });
      return;
    }

    // 检查音色文件（必须使用云存储URL）
    if (!this.roleVoiceUrls || Object.keys(this.roleVoiceUrls).length < 2) {
      promptAction.showToast({
        message: '请至少为2个角色选择音色文件',
        duration: 2000
      });
      return;
    }

    this.isLoading = true;
    // 生成一个任务ID用于进度轮询
    this.jobId = `${Date.now()}_${Math.floor(Math.random() * 1000000)}`;
    this.progressPercent = 1;
    this.progressMessage = '任务已提交';
    // 启动进度轮询
    this.startProgressPolling();
    try {
      const request: MultiRoleRequest = {
        text: hasText ? this.text : '', // 如果使用文件，text可以为空
        text_file_url: hasTextFile ? this.textFileUrl : undefined, // 文本文件云存储URL
        role_voice_urls: this.roleVoiceUrls, // 强制使用云存储URL
        silence_interval: 300,
        job_id: this.jobId
      };

      // 改为异步任务提交
      const queued = await podcastService.generateMultiRolePodcastAsync(request);
      if (!queued.success || !queued.data?.job_id) {
        promptAction.showToast({
          message: queued.error || queued.message || '提交任务失败',
          duration: 3000
        });
        return;
      }
      this.jobId = queued.data.job_id;
      // 继续轮询，等进度完成后主动获取结果
      // 此处不再立即跳转，等待 done 后获取结果再跳转
    } catch (error) {
      promptAction.showToast({
        message: `生成失败: ${error}`,
        duration: 3000
      });
    } finally {
      this.isLoading = false;
      this.stopProgressPolling();
      this.progressPercent = 0;
      this.progressMessage = '';
      this.jobId = '';
    }
  }

  private startProgressPolling(): void {
    if (!this.jobId) return;
    // 每 1 秒轮询一次
    this.progressTimer = setInterval(async () => {
      const status = await podcastService.getProgress(this.jobId);
      if (!status) return;
      this.progressPercent = status.percent || 0;
      this.progressMessage = status.message || '';
      if (status.done) {
        this.stopProgressPolling();
        // 获取最终结果并跳转
        const res = await podcastService.getAsyncResult(this.jobId);
        if (res.success && res.data) {
          const params = new PodcastResultPageParams(
            res.data,
            '多角色互动播客',
            res.data.script
          );
          RouterUtils.pushPathByName(RouterMap.PODCAST_RESULT_PAGE, params);
        } else {
          promptAction.showToast({
            message: res.error || res.message || '结果获取失败',
            duration: 3000
          });
        }
      }
    }, 1000);
  }

  private stopProgressPolling(): void {
    if (this.progressTimer) {
      clearInterval(this.progressTimer);
      this.progressTimer = 0;
    }
  }

  build() {
    NavDestination() {
      Column() {
        NavHeaderBar({
          title: '多角色互动播客'
        })

        Scroll() {
          Column({ space: 16 }) {
            // 文本文件上传
            Column({ space: 12 }) {
              Text('播客文本文件')
                .fontSize($r('sys.float.Subtitle_L'))
                .fontColor($r('sys.color.font_primary'))
                .fontWeight(FontWeight.Bold)
                .alignSelf(ItemAlign.Start)

              Row({ space: 12 }) {
                Column({ space: 4 }) {
                  Text(this.textFileName || '未选择文件')
                    .fontSize($r('sys.float.Body_M'))
                    .fontColor(this.textFileUrl ? $r('sys.color.font_primary') : $r('sys.color.font_secondary'))
                    .maxLines(1)

                  Text('支持.txt、.doc、.docx格式，最大10MB')
                    .fontSize($r('sys.float.Body_S'))
                    .fontColor($r('sys.color.font_secondary'))
                }
                .layoutWeight(1)
                .alignItems(HorizontalAlign.Start)

                Button(this.textFileUrl ? '已选择' : '选择文件')
                  .fontSize($r('sys.float.Body_S'))
                  .type(ButtonType.Normal)
                  .backgroundColor(this.textFileUrl ?
                    $r('sys.color.icon_emphasize') :
                    $r('sys.color.comp_background_tertiary'))
                  .fontColor(this.textFileUrl ?
                    $r('sys.color.font_on_primary') :
                    $r('sys.color.font_primary'))
                  .onClick(() => {
                    this.selectTextFile();
                  })
              }
              .width('100%')
              .padding(12)
              .borderRadius(8)
              .backgroundColor($r('sys.color.comp_background_tertiary'))

              // 保留文本输入框作为备选（可选）
              TextArea({
                placeholder: '或直接输入播客文本',
                text: $$this.text
              })
                .placeholderColor($r('sys.color.font_secondary'))
                .placeholderFont({
                  size: $r('sys.float.Body_L'),
                  weight: FontWeight.Regular,
                })
                .fontSize($r('sys.float.Body_L'))
                .fontColor($r('sys.color.font_primary'))
                .fontWeight(FontWeight.Regular)
                .borderRadius(8)
                .padding({ left: 12, top: 8 })
                .constraintSize({ minHeight: 80 })
                .maxLines(6)
            }
            .width('100%')
            .alignItems(HorizontalAlign.Start)

            // 角色音色选择
            Column({ space: 12 }) {
              Text('角色音色')
                .fontSize($r('sys.float.Subtitle_L'))
                .fontColor($r('sys.color.font_primary'))
                .fontWeight(FontWeight.Bold)
                .alignSelf(ItemAlign.Start)

              ForEach(this.roleNames, (roleName: string) => {
                Row({ space: 12 }) {
                  Text(roleName)
                    .fontSize($r('sys.float.Body_M'))
                    .fontColor($r('sys.color.font_primary'))
                    .layoutWeight(1)

                  Button(this.roleVoiceUrls[roleName] ? '已选择' : '选择音色')
                    .fontSize($r('sys.float.Body_S'))
                    .type(ButtonType.Normal)
                    .backgroundColor(this.roleVoiceUrls[roleName] ?
                      $r('sys.color.icon_emphasize') :
                      $r('sys.color.comp_background_tertiary'))
                    .fontColor(this.roleVoiceUrls[roleName] ?
                      $r('sys.color.font_on_primary') :
                      $r('sys.color.font_primary'))
                    .onClick(() => {
                      this.selectVoiceFile(roleName);
                    })
                }
                .width('100%')
                .padding(12)
                .borderRadius(8)
                .backgroundColor($r('sys.color.comp_background_tertiary'))
              }, (roleName: string) => roleName)
            }
            .width('100%')
            .alignItems(HorizontalAlign.Start)
          }
          .width('100%')
          .padding({ left: 16, right: 16, top: 16, bottom: 16 })
        }
        .layoutWeight(1)

        // 生成按钮
        Column() {
          // 进度条与提示
          if (this.isLoading) {
            Column({ space: 6 }) {
              Progress({ value: this.progressPercent })
                .style({
                  strokeWidth: 12
                })
                .width('100%')
              Text(this.progressMessage || '生成中...')
                .fontSize($r('sys.float.Body_S'))
                .fontColor($r('sys.color.font_secondary'))
                .alignSelf(ItemAlign.Start)
            }
            .width('100%')
            .padding({ left: 16, right: 16, bottom: 8 })
          }
          Button(this.isLoading ? '生成中...' : '开始生成')
            .width('100%')
            .height(40)
            .enabled(!this.isLoading && 
              (this.text.trim().length > 0 || this.textFileUrl.length > 0) && 
              Object.keys(this.roleVoiceUrls).length >= 2)
            .onClick(() => {
              this.generatePodcast();
            })
        }
        .padding({ left: 16, right: 16, bottom: this.windowModel.windowBottomPadding + 12 })
      }
      .width('100%')
      .height('100%')
      .backgroundColor($r('sys.color.background_primary'))
    }
    .hideTitleBar(true)
  }
}

