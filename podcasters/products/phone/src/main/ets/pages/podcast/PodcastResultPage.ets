import { RouterMap, RouterUtils, WindowModel } from 'lib_common';
import { NavHeaderBar } from 'lib_widget';
import { PodcastResult } from 'lib_api';
import { AudioPlayer } from '../../components/AudioPlayer';
import { promptAction, AppStorageV2 } from '@kit.ArkUI';
import { pasteboard } from '@kit.BasicServicesKit';
import { MarkdownV2 } from '@lidary/markdown';

export class PodcastResultPageParams {
  result: PodcastResult;
  pageTitle: string;
  script: string;

  constructor(result: PodcastResult, pageTitle: string, script: string) {
    this.result = result;
    this.pageTitle = pageTitle;
    this.script = script;
  }
}

@Builder
export function PodcastResultPageBuilder() {
  PodcastResultPage()
}

@ComponentV2
export struct PodcastResultPage {
  @Local result?: PodcastResult;
  @Local pageTitle: string = '播客结果';
  @Local script: string = '';
  @Local windowModel: WindowModel = AppStorageV2.connect(WindowModel, () => new WindowModel())!;

  aboutToAppear(): void {
    const params = RouterUtils.getParamByName<PodcastResultPageParams>(RouterMap.PODCAST_RESULT_PAGE);
    if (params) {
      this.result = params.result;
      this.pageTitle = params.pageTitle;
      this.script = params.script || params.result?.script || '';
    }
  }

  /**
   * 复制脚本到剪贴板
   */
  async copyScript(): Promise<void> {
    try {
      if (!this.script || this.script.trim() === '') {
        promptAction.showToast({
          message: '暂无脚本可复制',
          duration: 2000
        });
        return;
      }

      const pasteboardData = pasteboard.createData(pasteboard.MIMETYPE_TEXT_PLAIN, this.script);
      const systemPasteboard = pasteboard.getSystemPasteboard();
      await systemPasteboard.setData(pasteboardData);

      promptAction.showToast({
        message: '已复制到剪贴板',
        duration: 2000
      });
    } catch (error) {
      promptAction.showToast({
        message: '复制失败',
        duration: 2000
      });
    }
  }

  build() {
    NavDestination() {
      Column() {
        NavHeaderBar({
          title: this.pageTitle
        })

        Scroll() {
          Column({ space: 16 }) {
            // 音频播放器
            if (this.result?.audio_base64) {
              Column({ space: 8 }) {
                Text('生成的播客音频')
                  .fontSize($r('sys.float.Subtitle_L'))
                  .fontColor($r('sys.color.font_primary'))
                  .fontWeight(FontWeight.Bold)
                  .alignSelf(ItemAlign.Start)

                AudioPlayer({
                  audioBase64: this.result.audio_base64
                })
              }
              .width('100%')
              .padding(16)
              .borderRadius(12)
              .backgroundColor($r('sys.color.comp_background_tertiary'))
            }

            // 播客信息
            if (this.result) {
              Column({ space: 8 }) {
                Text('播客信息')
                  .fontSize($r('sys.float.Subtitle_L'))
                  .fontColor($r('sys.color.font_primary'))
                  .fontWeight(FontWeight.Bold)
                  .alignSelf(ItemAlign.Start)

                if (this.result.file_size_mb) {
                  Text(`文件大小: ${this.result.file_size_mb.toFixed(2)} MB`)
                    .fontSize($r('sys.float.Body_M'))
                    .fontColor($r('sys.color.font_secondary'))
                    .alignSelf(ItemAlign.Start)
                }

                if (this.result.topic) {
                  Text(`主题: ${this.result.topic}`)
                    .fontSize($r('sys.float.Body_M'))
                    .fontColor($r('sys.color.font_secondary'))
                    .alignSelf(ItemAlign.Start)
                }

                if (this.result.depth_level) {
                  Text(`深度级别: ${this.result.depth_level}`)
                    .fontSize($r('sys.float.Body_M'))
                    .fontColor($r('sys.color.font_secondary'))
                    .alignSelf(ItemAlign.Start)
                }

                if (this.result.roles && this.result.roles.length > 0) {
                  Text(`角色: ${this.result.roles.join(', ')}`)
                    .fontSize($r('sys.float.Body_M'))
                    .fontColor($r('sys.color.font_secondary'))
                    .alignSelf(ItemAlign.Start)
                }

                if (this.result.characters && this.result.characters.length > 0) {
                  Text(`角色: ${this.result.characters.join(', ')}`)
                    .fontSize($r('sys.float.Body_M'))
                    .fontColor($r('sys.color.font_secondary'))
                    .alignSelf(ItemAlign.Start)
                }
              }
              .width('100%')
              .padding(16)
              .borderRadius(12)
              .backgroundColor($r('sys.color.comp_background_tertiary'))
              .alignItems(HorizontalAlign.Start)
            }

            // 播客脚本
            if (this.script) {
              Column({ space: 8 }) {
                Text('播客脚本')
                  .fontSize($r('sys.float.Subtitle_L'))
                  .fontColor($r('sys.color.font_primary'))
                  .fontWeight(FontWeight.Bold)
                  .alignSelf(ItemAlign.Start)

                Scroll() {
                  Column() {
                    MarkdownV2({
                      content: this.script,
                      lineSpace: 4,
                      fontStyle: {
                        fontSize: $r('sys.float.Body_M'),
                        fontColor: $r('sys.color.font_primary')
                      }
                    })
                  }
                  .width('100%')
                  .alignItems(HorizontalAlign.Start)
                  .padding(12)
                }
                .height(200)
                .borderRadius(8)
                .backgroundColor($r('sys.color.background_primary'))
              }
              .width('100%')
              .padding(16)
              .borderRadius(12)
              .backgroundColor($r('sys.color.comp_background_tertiary'))
              .alignItems(HorizontalAlign.Start)
            }
          }
          .width('100%')
          .padding({ left: 16, right: 16, top: 16, bottom: 16 })
        }
        .layoutWeight(1)

        // 操作按钮
        Column() {
          Button('复制脚本')
            .width('100%')
            .height(40)
            .enabled(!!this.script)
            .onClick(() => {
              this.copyScript();
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

