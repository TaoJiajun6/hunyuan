import { RouterMap, RouterUtils, WindowModel } from 'lib_common';
import { NavHeaderBar } from 'lib_widget';
import { podcastService, DeepPodcastRequest, PodcastResult } from 'lib_api';
import { FileUtils } from '../../utils/FileUtils';
import { promptAction, AppStorageV2 } from '@kit.ArkUI';
import { PodcastResultPageParams } from './PodcastResultPage';
import { common } from '@kit.AbilityKit';

@Builder
export function PodcastDeepPageBuilder() {
  PodcastDeepPage()
}

@ComponentV2
export struct PodcastDeepPage {
  @Local topic: string = '';
  @Local roleVoiceUrls: Record<string, string> = {}; // 角色名 -> 云存储URL（必需）
  @Local numCharacters: number = 2;
  @Local depthLevel: string = '深度';
  @Local isLoading: boolean = false;
  @Local windowModel: WindowModel = AppStorageV2.connect(WindowModel, () => new WindowModel())!;

  readonly depthLevels: string[] = ['深度', '中等', '浅层'];
  readonly roleNames: string[] = ['角色A', '角色B', '角色C'];

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
   * 生成播客
   */
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
    try {
      const request: DeepPodcastRequest = {
        topic: this.topic,
        role_voice_urls: this.roleVoiceUrls, // 强制使用云存储URL
        num_characters: this.numCharacters,
        depth_level: this.depthLevel,
        silence_interval: 300
      };

      const response = await podcastService.generateDeepPodcast(request);

      if (response.success && response.data) {
        const params = new PodcastResultPageParams(
          response.data,
          '主题深度播客',
          response.data.script
        );
        RouterUtils.pushPathByName(RouterMap.PODCAST_RESULT_PAGE, params);
      } else {
        promptAction.showToast({
          message: response.error || response.message || '生成失败',
          duration: 3000
        });
      }
    } catch (error) {
      promptAction.showToast({
        message: `生成失败: ${error}`,
        duration: 3000
      });
    } finally {
      this.isLoading = false;
    }
  }

  build() {
    NavDestination() {
      Column() {
        NavHeaderBar({
          title: '主题深度播客'
        })

        Scroll() {
          Column({ space: 16 }) {
            // 主题输入
            Column({ space: 12 }) {
              Text('播客主题')
                .fontSize($r('sys.float.Subtitle_L'))
                .fontColor($r('sys.color.font_primary'))
                .fontWeight(FontWeight.Bold)
                .alignSelf(ItemAlign.Start)

              TextArea({
                placeholder: '请输入播客主题，如：人工智能的未来发展',
                text: $$this.topic
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
                .constraintSize({ minHeight: 60 })
            }
            .width('100%')
            .alignItems(HorizontalAlign.Start)

            // 角色数量选择
            Column({ space: 12 }) {
              Text('角色数量')
                .fontSize($r('sys.float.Subtitle_L'))
                .fontColor($r('sys.color.font_primary'))
                .fontWeight(FontWeight.Bold)
                .alignSelf(ItemAlign.Start)

              Row({ space: 8 }) {
                Button() {
                  Text('2个角色')
                    .fontSize($r('sys.float.Body_M'))
                    .fontColor(this.numCharacters === 2 ?
                      $r('sys.color.font_on_primary') :
                      $r('sys.color.font_primary'))
                }
                .width(100)
                .height(36)
                .borderRadius(18)
                .backgroundColor(this.numCharacters === 2 ?
                  $r('sys.color.icon_emphasize') :
                  $r('sys.color.comp_background_tertiary'))
                .onClick(() => {
                  this.numCharacters = 2;
                })

                Button() {
                  Text('3个角色')
                    .fontSize($r('sys.float.Body_M'))
                    .fontColor(this.numCharacters === 3 ?
                      $r('sys.color.font_on_primary') :
                      $r('sys.color.font_primary'))
                }
                .width(100)
                .height(36)
                .borderRadius(18)
                .backgroundColor(this.numCharacters === 3 ?
                  $r('sys.color.icon_emphasize') :
                  $r('sys.color.comp_background_tertiary'))
                .onClick(() => {
                  this.numCharacters = 3;
                })
              }
            }
            .width('100%')
            .alignItems(HorizontalAlign.Start)

            // 深度级别选择
            Column({ space: 12 }) {
              Text('深度级别')
                .fontSize($r('sys.float.Subtitle_L'))
                .fontColor($r('sys.color.font_primary'))
                .fontWeight(FontWeight.Bold)
                .alignSelf(ItemAlign.Start)

              Row({ space: 8 }) {
                ForEach(this.depthLevels, (level: string) => {
                  Button() {
                    Text(level)
                      .fontSize($r('sys.float.Body_M'))
                      .fontColor(this.depthLevel === level ?
                        $r('sys.color.font_on_primary') :
                        $r('sys.color.font_primary'))
                  }
                  .width(80)
                  .height(36)
                  .borderRadius(18)
                  .backgroundColor(this.depthLevel === level ?
                    $r('sys.color.icon_emphasize') :
                    $r('sys.color.comp_background_tertiary'))
                  .onClick(() => {
                    this.depthLevel = level;
                  })
                }, (level: string) => level)
              }
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

              ForEach(this.roleNames.slice(0, this.numCharacters), (roleName: string) => {
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
          Button(this.isLoading ? '生成中...' : '开始生成')
            .width('100%')
            .height(40)
            .enabled(!this.isLoading && this.topic.trim().length > 0 &&
              this.roleNames.slice(0, this.numCharacters).every(role => this.roleVoiceUrls[role]))
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

