import { WindowModel } from 'lib_common';
import { NavHeaderBar } from 'lib_widget';
import { RouterMap, RouterUtils } from 'lib_common';
import { promptAction, AppStorageV2, ButtonType, FontWeight, FlexAlign, TextAlign, TextOverflow, HorizontalAlign } from '@kit.ArkUI';
import { common } from '@kit.AbilityKit';
import { FileUtils } from '../../utils/FileUtils';
import { Logger } from 'lib_common';

/**
 * AI播客主页面
 * 参考图五的UI框架，整合三个模块
 */
@Builder
export function AIPodcastPageBuilder() {
  AIPodcastPage()
}

@ComponentV2
export struct AIPodcastPage {
  @Local windowModel: WindowModel = AppStorageV2.connect(WindowModel, () => new WindowModel())!;
  @Local showCreateMenu: boolean = false; // 是否显示创建菜单
  @Local inputText: string = ''; // 输入文本
  @Local selectedInputType: string = '文字'; // 选中的输入类型

  // 输入类型选项（整合三个模块的所有输入类型）
  private readonly inputTypeOptions: string[] = [
    '文字',
    '文字+指令',
    '文字+英文指令',
    '文件',
    '文件+指令',
    '链接',
    '链接+指令',
    '公众号',
    '公众号+指令',
    '图片和视频'
  ];

  // 播客类型选项
  private readonly podcastTypeOptions: PodcastTypeOption[] = [
    { 
      type: 'multi_role', 
      name: '多角色互动播客', 
      description: '将文本素材转化为多角色自然互动的播客音频',
      icon: '🎙️'
    },
    { 
      type: 'character', 
      name: '自定义角色播客', 
      description: '根据自定义角色人设生成契合风格的播客',
      icon: '👤'
    },
    { 
      type: 'deep', 
      name: '主题深度播客', 
      description: '基于指定主题生成有深度、引发思考的播客',
      icon: '💭'
    }
  ];

  /**
   * 处理输入类型选择
   */
  async handleInputTypeSelect(inputType: string): Promise<void> {
    this.selectedInputType = inputType;
    this.showCreateMenu = false;

    try {
      const context = this.getUIContext().getHostContext() as common.UIAbilityContext;

      if (inputType === '文字' || inputType === '文字+指令' || inputType === '文字+英文指令') {
        // 文字输入，跳转到多角色互动播客页面
        RouterUtils.pushPathByName(RouterMap.PODCAST_MULTI_ROLE_PAGE, {
          initialInputType: inputType
        });
      } else if (inputType === '文件' || inputType === '文件+指令') {
        // 文件上传
        const textFileInfo = await FileUtils.pickTextFile(context, true);
        if (textFileInfo && textFileInfo.cloudUrl) {
          // 跳转到多角色互动播客页面，并传递文件URL
          RouterUtils.pushPathByName(RouterMap.PODCAST_MULTI_ROLE_PAGE, {
            initialInputType: inputType,
            textFileUrl: textFileInfo.cloudUrl
          });
        }
      } else if (inputType === '链接' || inputType === '链接+指令' || 
                 inputType === '公众号' || inputType === '公众号+指令') {
        // 链接输入，跳转到多角色互动播客页面
        RouterUtils.pushPathByName(RouterMap.PODCAST_MULTI_ROLE_PAGE, {
          initialInputType: inputType
        });
      } else if (inputType === '图片和视频') {
        // 图片和视频上传（暂时跳转到多角色互动播客页面）
        promptAction.showToast({
          message: '图片和视频功能开发中',
          duration: 2000
        });
      }
    } catch (error) {
      Logger.error('AIPodcastPage', `处理输入类型选择失败: ${error}`);
      promptAction.showToast({
        message: `操作失败: ${error}`,
        duration: 2000
      });
    }
  }

  /**
   * 处理播客类型选择
   */
  handlePodcastTypeSelect(podcastType: string): void {
    this.showCreateMenu = false;

    if (podcastType === 'multi_role') {
      // 跳转到多角色互动播客页面
      RouterUtils.pushPathByName(RouterMap.PODCAST_MULTI_ROLE_PAGE);
    } else if (podcastType === 'character') {
      // 跳转到自定义角色播客页面
      RouterUtils.pushPathByName(RouterMap.PODCAST_CHARACTER_PAGE);
    } else if (podcastType === 'deep') {
      // 跳转到主题深度播客页面
      RouterUtils.pushPathByName(RouterMap.PODCAST_DEEP_PAGE);
    }
  }

  build() {
    Column() {
      // 顶部导航栏（参考图五）
      Row() {
        // AI播客按钮（激活状态）
        Button('AI播客')
          .type(ButtonType.Normal)
          .backgroundColor('#FFFFFF')
          .fontColor('#000000')
          .fontSize(16)
          .fontWeight(FontWeight.Medium)
          .borderRadius(20)
          .padding({ left: 16, right: 16, top: 8, bottom: 8 })
          .onClick(() => {
            // 当前页面，无需跳转
          })

        // 其他按钮（未激活状态）
        Button('FlowSpeech')
          .type(ButtonType.Normal)
          .backgroundColor('#00000000')
          .fontColor('#FFFFFF')
          .fontSize(16)
          .borderRadius(20)
          .padding({ left: 16, right: 16, top: 8, bottom: 8 })
          .onClick(() => {
            promptAction.showToast({
              message: 'FlowSpeech功能开发中',
              duration: 2000
            });
          })

        Button('解说视频')
          .type(ButtonType.Normal)
          .backgroundColor('#00000000')
          .fontColor('#FFFFFF')
          .fontSize(16)
          .borderRadius(20)
          .padding({ left: 16, right: 16, top: 8, bottom: 8 })
          .onClick(() => {
            promptAction.showToast({
              message: '解说视频功能开发中',
              duration: 2000
            });
          })

        Button('PPT')
          .type(ButtonType.Normal)
          .backgroundColor('#00000000')
          .fontColor('#FFFFFF')
          .fontSize(16)
          .borderRadius(20)
          .padding({ left: 16, right: 16, top: 8, bottom: 8 })
          .onClick(() => {
            promptAction.showToast({
              message: 'PPT功能开发中',
              duration: 2000
            });
          })
      }
      .width('100%')
      .justifyContent(FlexAlign.Start)
      .padding({ left: 16, right: 16, top: 12, bottom: 12 })

      // 主内容区域（参考图五）
      Column() {
        // 大输入框
        TextArea(this.inputText)
          .placeholder('输入文字、上传文件或粘贴链接，我们帮你生成播客')
          .placeholderColor('#999999')
          .backgroundColor('#1A1A1A')
          .fontColor('#FFFFFF')
          .fontSize(16)
          .borderRadius(12)
          .padding(16)
          .height(200)
          .width('100%')
          .onChange((value: string) => {
            this.inputText = value;
          })

        // 底部控制栏（参考图五）
        Row() {
          // 左侧控制
          Row({ space: 12 }) {
            // 速听精华
            Row({ space: 4 }) {
              Text('⚡')
                .fontSize(18)
                .fontColor('#FFFFFF')
              Text('速听精华')
                .fontSize(14)
                .fontColor('#FFFFFF')
            }
            .onClick(() => {
              promptAction.showToast({
                message: '速听精华功能开发中',
                duration: 2000
              });
            })

            // 分隔线
            Divider()
              .vertical(true)
              .height(20)
              .color('#666666')

            // 语言选择
            Row({ space: 4 }) {
              Text('🌐')
                .fontSize(18)
                .fontColor('#FFFFFF')
              Text('中文(普通话)')
                .fontSize(14)
                .fontColor('#FFFFFF')
            }
            .onClick(() => {
              promptAction.showToast({
                message: '语言选择功能开发中',
                duration: 2000
              });
            })

            // 分隔线
            Divider()
              .vertical(true)
              .height(20)
              .color('#666666')

            // 音色选择
            Row({ space: 4 }) {
              Text('🎵')
                .fontSize(18)
                .fontColor('#FFFFFF')
              Text('选择1种音色')
                .fontSize(14)
                .fontColor('#FFFFFF')
            }
            .onClick(() => {
              promptAction.showToast({
                message: '音色选择功能开发中',
                duration: 2000
              });
            })
          }
          .layoutWeight(1)

          // 右侧控制
          Row({ space: 12 }) {
            // 刷新按钮
            Button() {
              Text('🔄')
                .fontSize(20)
                .fontColor('#FFFFFF')
            }
            .type(ButtonType.Circle)
            .backgroundColor('#00000000')
            .width(40)
            .height(40)
            .onClick(() => {
              this.inputText = '';
              promptAction.showToast({
                message: '已清空',
                duration: 1000
              });
            })

            // 上传按钮（加号按钮）
            Button() {
              Text('➕')
                .fontSize(20)
                .fontColor('#FFFFFF')
            }
            .type(ButtonType.Circle)
            .backgroundColor('#00000000')
            .width(40)
            .height(40)
            .bindSheet($$this.showCreateMenu, this.createMenuSheet(), {
              height: '60%',
              dragBar: true,
              showClose: true,
              title: { title: '创建播客' }
            })
            .onClick(() => {
              this.showCreateMenu = true;
            })

            // 创作按钮
            Button('创作')
              .type(ButtonType.Normal)
              .backgroundColor('#FFFFFF')
              .fontColor('#000000')
              .fontSize(16)
              .fontWeight(FontWeight.Medium)
              .borderRadius(20)
              .padding({ left: 24, right: 24, top: 10, bottom: 10 })
              .onClick(() => {
                if (this.inputText.trim() === '') {
                  promptAction.showToast({
                    message: '请输入内容',
                    duration: 2000
                  });
                  return;
                }
                // 跳转到多角色互动播客页面
                RouterUtils.pushPathByName(RouterMap.PODCAST_MULTI_ROLE_PAGE, {
                  initialInputType: '文字',
                  initialText: this.inputText
                });
              })
          }
        }
        .width('100%')
        .padding({ top: 16, bottom: 16 })
      }
      .layoutWeight(1)
      .width('100%')
      .padding({ left: 16, right: 16 })
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#000000')
  }

  /**
   * 创建菜单Sheet（整合上传素材和三个模块）
   */
  @Builder
  createMenuSheet() {
    Column() {
      // 上传素材部分
      Column({ space: 12 }) {
        Text('上传素材')
          .fontSize(18)
          .fontWeight(FontWeight.Bold)
          .fontColor('#000000')
          .width('100%')
          .textAlign(TextAlign.Start)
          .margin({ bottom: 8 })

        // 文字选项
        Row() {
          Text('文字')
            .fontSize(16)
            .fontColor('#000000')
        }
        .width('100%')
        .height(48)
        .padding({ left: 16, right: 16 })
        .backgroundColor('#F5F5F5')
        .borderRadius(8)
        .onClick(() => {
          this.handleInputTypeSelect('文字');
        })

        // 文字+指令选项
        Row() {
          Text('文字+指令')
            .fontSize(16)
            .fontColor('#000000')
        }
        .width('100%')
        .height(48)
        .padding({ left: 16, right: 16 })
        .backgroundColor('#F5F5F5')
        .borderRadius(8)
        .onClick(() => {
          this.handleInputTypeSelect('文字+指令');
        })

        // 文字+英文指令选项
        Row() {
          Text('文字+英文指令')
            .fontSize(16)
            .fontColor('#000000')
        }
        .width('100%')
        .height(48)
        .padding({ left: 16, right: 16 })
        .backgroundColor('#F5F5F5')
        .borderRadius(8)
        .onClick(() => {
          this.handleInputTypeSelect('文字+英文指令');
        })

        // 文件选项
        Row() {
          Text('文件')
            .fontSize(16)
            .fontColor('#000000')
        }
        .width('100%')
        .height(48)
        .padding({ left: 16, right: 16 })
        .backgroundColor('#F5F5F5')
        .borderRadius(8)
        .onClick(() => {
          this.handleInputTypeSelect('文件');
        })

        // 文件+指令选项
        Row() {
          Text('文件+指令')
            .fontSize(16)
            .fontColor('#000000')
        }
        .width('100%')
        .height(48)
        .padding({ left: 16, right: 16 })
        .backgroundColor('#F5F5F5')
        .borderRadius(8)
        .onClick(() => {
          this.handleInputTypeSelect('文件+指令');
        })

        // 链接选项
        Row() {
          Text('链接')
            .fontSize(16)
            .fontColor('#000000')
        }
        .width('100%')
        .height(48)
        .padding({ left: 16, right: 16 })
        .backgroundColor('#F5F5F5')
        .borderRadius(8)
        .onClick(() => {
          this.handleInputTypeSelect('链接');
        })

        // 链接+指令选项
        Row() {
          Text('链接+指令')
            .fontSize(16)
            .fontColor('#000000')
        }
        .width('100%')
        .height(48)
        .padding({ left: 16, right: 16 })
        .backgroundColor('#F5F5F5')
        .borderRadius(8)
        .onClick(() => {
          this.handleInputTypeSelect('链接+指令');
        })

        // 公众号选项
        Row() {
          Text('公众号')
            .fontSize(16)
            .fontColor('#000000')
        }
        .width('100%')
        .height(48)
        .padding({ left: 16, right: 16 })
        .backgroundColor('#F5F5F5')
        .borderRadius(8)
        .onClick(() => {
          this.handleInputTypeSelect('公众号');
        })

        // 公众号+指令选项
        Row() {
          Text('公众号+指令')
            .fontSize(16)
            .fontColor('#000000')
        }
        .width('100%')
        .height(48)
        .padding({ left: 16, right: 16 })
        .backgroundColor('#F5F5F5')
        .borderRadius(8)
        .onClick(() => {
          this.handleInputTypeSelect('公众号+指令');
        })

        // 图片和视频选项
        Row() {
          Text('图片和视频')
            .fontSize(16)
            .fontColor('#000000')
        }
        .width('100%')
        .height(48)
        .padding({ left: 16, right: 16 })
        .backgroundColor('#F5F5F5')
        .borderRadius(8)
        .onClick(() => {
          this.handleInputTypeSelect('图片和视频');
        })
      }
      .width('100%')
      .margin({ top: 16, bottom: 24 })

      // 分隔线
      Divider()
        .color('#E0E0E0')
        .margin({ top: 8, bottom: 8 })

      // 播客类型部分
      Column({ space: 12 }) {
        Text('播客类型')
          .fontSize(18)
          .fontWeight(FontWeight.Bold)
          .fontColor('#000000')
          .width('100%')
          .textAlign(TextAlign.Start)
          .margin({ bottom: 8 })

        // 多角色互动播客
        Column({ space: 4 }) {
          Row({ space: 8 }) {
            Text(this.podcastTypeOptions[0].icon)
              .fontSize(24)
            Column({ space: 2 }) {
              Text(this.podcastTypeOptions[0].name)
                .fontSize(16)
                .fontColor('#000000')
                .fontWeight(FontWeight.Medium)
              Text(this.podcastTypeOptions[0].description)
                .fontSize(12)
                .fontColor('#666666')
                .maxLines(2)
                .textOverflow({ overflow: TextOverflow.Ellipsis })
            }
            .layoutWeight(1)
            .alignItems(HorizontalAlign.Start)
          }
        }
        .width('100%')
        .padding({ left: 16, right: 16, top: 12, bottom: 12 })
        .backgroundColor('#F5F5F5')
        .borderRadius(8)
        .onClick(() => {
          this.handlePodcastTypeSelect('multi_role');
        })

        // 自定义角色播客
        Column({ space: 4 }) {
          Row({ space: 8 }) {
            Text(this.podcastTypeOptions[1].icon)
              .fontSize(24)
            Column({ space: 2 }) {
              Text(this.podcastTypeOptions[1].name)
                .fontSize(16)
                .fontColor('#000000')
                .fontWeight(FontWeight.Medium)
              Text(this.podcastTypeOptions[1].description)
                .fontSize(12)
                .fontColor('#666666')
                .maxLines(2)
                .textOverflow({ overflow: TextOverflow.Ellipsis })
            }
            .layoutWeight(1)
            .alignItems(HorizontalAlign.Start)
          }
        }
        .width('100%')
        .padding({ left: 16, right: 16, top: 12, bottom: 12 })
        .backgroundColor('#F5F5F5')
        .borderRadius(8)
        .onClick(() => {
          this.handlePodcastTypeSelect('character');
        })

        // 主题深度播客
        Column({ space: 4 }) {
          Row({ space: 8 }) {
            Text(this.podcastTypeOptions[2].icon)
              .fontSize(24)
            Column({ space: 2 }) {
              Text(this.podcastTypeOptions[2].name)
                .fontSize(16)
                .fontColor('#000000')
                .fontWeight(FontWeight.Medium)
              Text(this.podcastTypeOptions[2].description)
                .fontSize(12)
                .fontColor('#666666')
                .maxLines(2)
                .textOverflow({ overflow: TextOverflow.Ellipsis })
            }
            .layoutWeight(1)
            .alignItems(HorizontalAlign.Start)
          }
        }
        .width('100%')
        .padding({ left: 16, right: 16, top: 12, bottom: 12 })
        .backgroundColor('#F5F5F5')
        .borderRadius(8)
        .onClick(() => {
          this.handlePodcastTypeSelect('deep');
        })
      }
      .width('100%')
      .margin({ top: 16, bottom: 16 })
    }
    .width('100%')
    .padding({ left: 16, right: 16, bottom: 16 })
  }
}

// 播客类型选项接口
interface PodcastTypeOption {
  type: string;
  name: string;
  description: string;
  icon: string;
}

