import { RouterMap, RouterUtils, WindowModel } from 'lib_common';
import { NavHeaderBar } from 'lib_widget';
import { podcastService, MultiRoleRequest, PodcastResult } from 'lib_api';
import { FileUtils } from '../../utils/FileUtils';
import { promptAction, AppStorageV2 } from '@kit.ArkUI';
import { PodcastResultPageParams } from './PodcastResultPage';
import { common } from '@kit.AbilityKit';

@Builder
export function PodcastMultiRolePageBuilder() {
  PodcastMultiRolePage()
}

@ComponentV2
export struct PodcastMultiRolePage {
  @Local text: string = '';
  @Local roleAVoices: Record<string, string> = {}; // 角色名 -> base64音频
  @Local roleNames: string[] = ['角色A', '角色B'];
  @Local isLoading: boolean = false;
  @Local windowModel: WindowModel = AppStorageV2.connect(WindowModel, () => new WindowModel())!;

  /**
   * 选择角色音色文件
   */
  async selectVoiceFile(roleName: string): Promise<void> {
    try {
      // 获取UIAbility上下文
      const context = this.getUIContext().getHostContext() as common.UIAbilityContext;
      const audioData = await FileUtils.pickAudioFile(context);
      if (audioData) {
        const base64 = FileUtils.uint8ArrayToBase64(audioData);
        this.roleAVoices[roleName] = base64;
        promptAction.showToast({
          message: `${roleName}音色已选择`,
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
    if (!this.text.trim()) {
      promptAction.showToast({
        message: '请输入播客文本',
        duration: 2000
      });
      return;
    }

    if (Object.keys(this.roleAVoices).length < 2) {
      promptAction.showToast({
        message: '请至少为2个角色选择音色文件',
        duration: 2000
      });
      return;
    }

    this.isLoading = true;
    try {
      const request: MultiRoleRequest = {
        text: this.text,
        role_voices: this.roleAVoices,
        silence_interval: 300
      };

      const response = await podcastService.generateMultiRolePodcast(request);

      if (response.success && response.data) {
        const params = new PodcastResultPageParams(
          response.data,
          '多角色互动播客',
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
          title: '多角色互动播客'
        })

        Scroll() {
          Column({ space: 16 }) {
            // 文本输入
            Column({ space: 12 }) {
              Text('播客文本')
                .fontSize($r('sys.float.Subtitle_L'))
                .fontColor($r('sys.color.font_primary'))
                .fontWeight(FontWeight.Bold)
                .alignSelf(ItemAlign.Start)

              TextArea({
                placeholder: '请输入播客文本，支持角色标记（如[角色A]你好 [角色B]你好啊）或普通文本',
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
                .constraintSize({ minHeight: 120 })
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

                  Button(this.roleAVoices[roleName] ? '已选择' : '选择音色')
                    .fontSize($r('sys.float.Body_S'))
                    .type(ButtonType.Normal)
                    .backgroundColor(this.roleAVoices[roleName] ?
                      $r('sys.color.icon_emphasize') :
                      $r('sys.color.comp_background_tertiary'))
                    .fontColor(this.roleAVoices[roleName] ?
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
            .enabled(!this.isLoading && this.text.trim().length > 0 && Object.keys(this.roleAVoices).length >= 2)
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

