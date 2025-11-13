import { RouterMap, RouterUtils } from 'lib_common';
import { NavHeaderBar } from 'lib_widget';
import { MusicPlayController } from 'module_musicplay';
import { CloudStorageMusicUtils } from '../../common/CloudStorageMusicUtils';
import { MediaService } from 'module_musicplay';
import { promptAction } from '@kit.ArkUI';
import { FileUtils } from '../../utils/FileUtils';
import { picker } from '@kit.CoreFileKit';
import { common } from '@kit.AbilityKit';
import { Logger } from 'lib_common';

@Builder
export function PodcastPageBuilder() {
  PodcastPage()
}

@ComponentV2
export struct PodcastPage {
  @Local isLoading: boolean = false;
  @Local isUploadingMusic: boolean = false;

  /**
   * 上传背景音乐到云存储
   */
  async uploadBackgroundMusic() {
    if (this.isUploadingMusic) {
      return;
    }

    try {
      this.isUploadingMusic = true;
      
      // 获取UIAbility上下文
      const context = this.getUIContext().getHostContext() as common.UIAbilityContext;
      
      // 使用文件选择器选择音频文件
      const filePicker = new picker.DocumentViewPicker();
      const documentSelectOptions = new picker.DocumentSelectOptions();
      documentSelectOptions.maxSelectNumber = 1;
      documentSelectOptions.fileSuffixFilters = ['.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac'];
      
      try {
        const documentSelectResult = await filePicker.select(documentSelectOptions);
        if (documentSelectResult && documentSelectResult.length > 0) {
          const fileUri = documentSelectResult[0];
          
          promptAction.showToast({
            message: '正在上传背景音乐到云存储...',
            duration: 2000
          });
          
          // 上传到云存储
          const cloudInfo = await FileUtils.uploadBackgroundMusicToCloud(context, fileUri);
          
          if (cloudInfo && cloudInfo.cloudUrl) {
            promptAction.showToast({
              message: `背景音乐上传成功！\n文件已保存到云存储 music/ 目录`,
              duration: 3000
            });
            Logger.info('PodcastPage', `背景音乐上传成功: ${cloudInfo.cloudUrl}`);
          } else {
            promptAction.showToast({
              message: '背景音乐上传失败，请重试',
              duration: 2000
            });
          }
        } else {
          // 用户取消了选择
          Logger.info('PodcastPage', '用户取消了文件选择');
        }
      } catch (error) {
        Logger.error('PodcastPage', `选择文件失败: ${error}`);
        promptAction.showToast({
          message: `选择文件失败: ${error}`,
          duration: 2000
        });
      }
    } catch (error) {
      Logger.error('PodcastPage', `上传背景音乐失败: ${error}`);
      promptAction.showToast({
        message: `上传失败: ${error}`,
        duration: 3000
      });
    } finally {
      this.isUploadingMusic = false;
    }
  }

  /**
   * 从云存储导入音频
   */
  async importAudioFromCloud() {
    if (this.isLoading) {
      return;
    }

    try {
      this.isLoading = true;
      promptAction.showToast({
        message: '正在从云存储导入音频...',
        duration: 2000
      });

      // 从云存储导入音频
      const songItems = await CloudStorageMusicUtils.importAudioFromCloudStorage('outputs/podcasts/');

      if (songItems.length === 0) {
        promptAction.showToast({
          message: '未找到音频文件',
          duration: 2000
        });
        return;
      }

      // 添加到播放列表
      for (const songItem of songItems) {
        MediaService.getInstance().addToSongList(songItem);
      }

      promptAction.showToast({
        message: `成功导入 ${songItems.length} 个音频文件`,
        duration: 2000
      });
    } catch (error) {
      promptAction.showToast({
        message: `导入失败: ${error}`,
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
          title: 'AI播客',
          isSubTitle: false,
          showBackBtn: false
        })

        Scroll() {
          Column({ space: 16 }) {
            // 多角色互动播客
            Row() {
              Column({ space: 8 }) {
                Text('多角色互动播客')
                  .fontSize($r('sys.float.Title_M'))
                  .fontColor($r('sys.color.font_primary'))
                  .fontWeight(FontWeight.Bold)

                Text('将文本素材转化为多角色自然互动的播客音频')
                  .fontSize($r('sys.float.Body_M'))
                  .fontColor($r('sys.color.font_secondary'))
                  .maxLines(2)
                  .textOverflow({ overflow: TextOverflow.Ellipsis })
              }
              .alignItems(HorizontalAlign.Start)
              .layoutWeight(1)
            }
            .width('100%')
            .padding(16)
            .borderRadius(12)
            .backgroundColor($r('sys.color.comp_background_tertiary'))
            .onClick(() => {
              RouterUtils.pushPathByName(RouterMap.PODCAST_MULTI_ROLE_PAGE)
            })

            // 自定义角色播客
            Row() {
              Column({ space: 8 }) {
                Text('自定义角色播客')
                  .fontSize($r('sys.float.Title_M'))
                  .fontColor($r('sys.color.font_primary'))
                  .fontWeight(FontWeight.Bold)

                Text('根据用户自定义的角色人设和音色生成契合风格的播客音频')
                  .fontSize($r('sys.float.Body_M'))
                  .fontColor($r('sys.color.font_secondary'))
                  .maxLines(2)
                  .textOverflow({ overflow: TextOverflow.Ellipsis })
              }
              .alignItems(HorizontalAlign.Start)
              .layoutWeight(1)
            }
            .width('100%')
            .padding(16)
            .borderRadius(12)
            .backgroundColor($r('sys.color.comp_background_tertiary'))
            .onClick(() => {
              RouterUtils.pushPathByName(RouterMap.PODCAST_CHARACTER_PAGE)
            })

            // 主题深度播客
            Row() {
              Column({ space: 8 }) {
                Text('主题深度播客')
                  .fontSize($r('sys.float.Title_M'))
                  .fontColor($r('sys.color.font_primary'))
                  .fontWeight(FontWeight.Bold)

                Text('基于指定主题生成有深度、引发思考的播客音频')
                  .fontSize($r('sys.float.Body_M'))
                  .fontColor($r('sys.color.font_secondary'))
                  .maxLines(2)
                  .textOverflow({ overflow: TextOverflow.Ellipsis })
              }
              .alignItems(HorizontalAlign.Start)
              .layoutWeight(1)
            }
            .width('100%')
            .padding(16)
            .borderRadius(12)
            .backgroundColor($r('sys.color.comp_background_tertiary'))
            .onClick(() => {
              RouterUtils.pushPathByName(RouterMap.PODCAST_DEEP_PAGE)
            })

            // 上传背景音乐到云存储
            Row() {
              Column({ space: 8 }) {
                Text('上传背景音乐')
                  .fontSize($r('sys.float.Title_M'))
                  .fontColor($r('sys.color.font_primary'))
                  .fontWeight(FontWeight.Bold)

                Text('将本地背景音乐文件上传到云存储 music/ 目录')
                  .fontSize($r('sys.float.Body_M'))
                  .fontColor($r('sys.color.font_secondary'))
                  .maxLines(2)
                  .textOverflow({ overflow: TextOverflow.Ellipsis })
              }
              .alignItems(HorizontalAlign.Start)
              .layoutWeight(1)
            }
            .width('100%')
            .padding(16)
            .borderRadius(12)
            .backgroundColor($r('sys.color.comp_background_tertiary'))
            .opacity(this.isUploadingMusic ? 0.6 : 1)
            .enabled(!this.isUploadingMusic)
            .onClick(() => {
              this.uploadBackgroundMusic();
            })

            // 从云存储导入音频
            Row() {
              Column({ space: 8 }) {
                Text('从云存储导入音频')
                  .fontSize($r('sys.float.Title_M'))
                  .fontColor($r('sys.color.font_primary'))
                  .fontWeight(FontWeight.Bold)

                Text('从云存储中导入已生成的播客音频到播放列表')
                  .fontSize($r('sys.float.Body_M'))
                  .fontColor($r('sys.color.font_secondary'))
                  .maxLines(2)
                  .textOverflow({ overflow: TextOverflow.Ellipsis })
              }
              .alignItems(HorizontalAlign.Start)
              .layoutWeight(1)
            }
            .width('100%')
            .padding(16)
            .borderRadius(12)
            .backgroundColor($r('sys.color.comp_background_tertiary'))
            .opacity(this.isLoading ? 0.6 : 1)
            .enabled(!this.isLoading)
            .onClick(() => {
              this.importAudioFromCloud();
            })
          }
          .width('100%')
          .padding({ left: 16, right: 16, top: 16, bottom: 16 })
        }
        .layoutWeight(1)
        // 播放器组件 - 放在底部导航栏上方
        MusicPlayController()
      }
      .width('100%')
      .height('100%')
      .backgroundColor($r('sys.color.background_primary'))
    }
    .hideTitleBar(true)
  }
}










