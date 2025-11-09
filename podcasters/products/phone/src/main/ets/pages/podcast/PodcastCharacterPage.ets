import { RouterMap, RouterUtils, WindowModel } from 'lib_common';
import { NavHeaderBar } from 'lib_widget';
import { podcastService, CharacterRequest, CharacterInfo, PodcastResult } from 'lib_api';
import { FileUtils } from '../../utils/FileUtils';
import { promptAction, AppStorageV2 } from '@kit.ArkUI';
import { PodcastResultPageParams } from './PodcastResultPage';
import { common } from '@kit.AbilityKit';

@Builder
export function PodcastCharacterPageBuilder() {
  PodcastCharacterPage()
}

@ComponentV2
export struct PodcastCharacterPage {
  @Local topic: string = '';
  @Local characters: CharacterInfo[] = [
    { name: '角色A', voice: '' },
    { name: '角色B', voice: '' }
  ];
  @Local isLoading: boolean = false;
  @Local windowModel: WindowModel = AppStorageV2.connect(WindowModel, () => new WindowModel())!;

  /**
   * 复制CharacterInfo对象并更新指定属性
   */
  private copyCharacterInfo(character: CharacterInfo, updates: Partial<CharacterInfo>): CharacterInfo {
    return {
      name: updates.name !== undefined ? updates.name : character.name,
      identity: updates.identity !== undefined ? updates.identity : character.identity,
      personality: updates.personality !== undefined ? updates.personality : character.personality,
      catchphrase: updates.catchphrase !== undefined ? updates.catchphrase : character.catchphrase,
      speaking_style: updates.speaking_style !== undefined ? updates.speaking_style : character.speaking_style,
      relationship: updates.relationship !== undefined ? updates.relationship : character.relationship,
      voice: updates.voice !== undefined ? updates.voice : character.voice
    };
  }

  /**
   * 选择角色音色文件
   */
  async selectVoiceFile(index: number): Promise<void> {
    try {
      // 获取UIAbility上下文
      const context = this.getUIContext().getHostContext() as common.UIAbilityContext;
      const audioData = await FileUtils.pickAudioFile(context);
      if (audioData) {
        const base64 = FileUtils.uint8ArrayToBase64(audioData);
        // 创建新数组以触发状态更新
        const newCharacters: CharacterInfo[] = [];
        for (let i = 0; i < this.characters.length; i++) {
          if (i === index) {
            newCharacters.push(this.copyCharacterInfo(this.characters[i], { voice: base64 }));
          } else {
            newCharacters.push(this.characters[i]);
          }
        }
        this.characters = newCharacters;
        promptAction.showToast({
          message: `${this.characters[index].name}音色已选择`,
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
    // 检查所有角色是否都有音色
    const hasAllVoices = this.characters.every(char => char.voice);
    if (!hasAllVoices) {
      promptAction.showToast({
        message: '请为所有角色选择音色文件',
        duration: 2000
      });
      return;
    }

    this.isLoading = true;
    try {
      const request: CharacterRequest = {
        characters: this.characters,
        topic: this.topic || undefined,
        silence_interval: 300
      };

      const response = await podcastService.generateCharacterPodcast(request);

      if (response.success && response.data) {
        const params = new PodcastResultPageParams(
          response.data,
          '自定义角色播客',
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
          title: '自定义角色播客'
        })

        Scroll() {
          Column({ space: 16 }) {
            // 主题输入
            Column({ space: 12 }) {
              Text('播客主题（可选）')
                .fontSize($r('sys.float.Subtitle_L'))
                .fontColor($r('sys.color.font_primary'))
                .fontWeight(FontWeight.Bold)
                .alignSelf(ItemAlign.Start)

              TextArea({
                placeholder: '请输入播客主题，如：人工智能的发展',
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

            // 角色配置
            Column({ space: 12 }) {
              Text('角色配置')
                .fontSize($r('sys.float.Subtitle_L'))
                .fontColor($r('sys.color.font_primary'))
                .fontWeight(FontWeight.Bold)
                .alignSelf(ItemAlign.Start)

              ForEach(this.characters, (character: CharacterInfo, index: number) => {
                Column({ space: 8 }) {
                  Text(`角色${index + 1}`)
                    .fontSize($r('sys.float.Body_M'))
                    .fontColor($r('sys.color.font_primary'))
                    .fontWeight(FontWeight.Bold)
                    .alignSelf(ItemAlign.Start)

                  TextInput({
                    placeholder: '角色名称',
                    text: character.name || ''
                  })
                    .placeholderColor($r('sys.color.font_secondary'))
                    .fontSize($r('sys.float.Body_M'))
                    .fontColor($r('sys.color.font_primary'))
                    .borderRadius(8)
                    .padding({ left: 12 })
                    .height(40)
                    .onChange((value: string) => {
                      // 创建新数组以触发状态更新
                      const newCharacters: CharacterInfo[] = [];
                      for (let i = 0; i < this.characters.length; i++) {
                        if (i === index) {
                          newCharacters.push(this.copyCharacterInfo(this.characters[i], { name: value }));
                        } else {
                          newCharacters.push(this.characters[i]);
                        }
                      }
                      this.characters = newCharacters;
                    })

                  TextInput({
                    placeholder: '身份/职业（可选）',
                    text: character.identity || ''
                  })
                    .placeholderColor($r('sys.color.font_secondary'))
                    .fontSize($r('sys.float.Body_M'))
                    .fontColor($r('sys.color.font_primary'))
                    .borderRadius(8)
                    .padding({ left: 12 })
                    .height(40)
                    .onChange((value: string) => {
                      // 创建新数组以触发状态更新
                      const newCharacters: CharacterInfo[] = [];
                      for (let i = 0; i < this.characters.length; i++) {
                        if (i === index) {
                          newCharacters.push(this.copyCharacterInfo(this.characters[i], { identity: value }));
                        } else {
                          newCharacters.push(this.characters[i]);
                        }
                      }
                      this.characters = newCharacters;
                    })

                  TextInput({
                    placeholder: '核心性格（可选）',
                    text: character.personality || ''
                  })
                    .placeholderColor($r('sys.color.font_secondary'))
                    .fontSize($r('sys.float.Body_M'))
                    .fontColor($r('sys.color.font_primary'))
                    .borderRadius(8)
                    .padding({ left: 12 })
                    .height(40)
                    .onChange((value: string) => {
                      // 创建新数组以触发状态更新
                      const newCharacters: CharacterInfo[] = [];
                      for (let i = 0; i < this.characters.length; i++) {
                        if (i === index) {
                          newCharacters.push(this.copyCharacterInfo(this.characters[i], { personality: value }));
                        } else {
                          newCharacters.push(this.characters[i]);
                        }
                      }
                      this.characters = newCharacters;
                    })

                  Button(character.voice ? '已选择音色' : '选择音色文件')
                    .width('100%')
                    .fontSize($r('sys.float.Body_S'))
                    .type(ButtonType.Normal)
                    .backgroundColor(character.voice ?
                      $r('sys.color.icon_emphasize') :
                      $r('sys.color.comp_background_tertiary'))
                    .fontColor(character.voice ?
                      $r('sys.color.font_on_primary') :
                      $r('sys.color.font_primary'))
                    .onClick(() => {
                      this.selectVoiceFile(index);
                    })
                }
                .width('100%')
                .padding(12)
                .borderRadius(8)
                .backgroundColor($r('sys.color.comp_background_tertiary'))
              }, (character: CharacterInfo, index: number) => `${character.name}_${index}`)
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
            .enabled(!this.isLoading && this.characters.every(char => char.voice))
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

