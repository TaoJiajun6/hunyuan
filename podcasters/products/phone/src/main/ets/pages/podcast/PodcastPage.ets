import { RouterMap, RouterUtils } from 'lib_common';
import { NavHeaderBar } from 'lib_widget';
import { MusicPlayController } from 'module_musicplay';
import { CloudStorageMusicUtils } from '../../common/CloudStorageMusicUtils';
import { MediaService } from 'module_musicplay';
import { promptAction } from '@kit.ArkUI';

@Builder
export function PodcastPageBuilder() {
  PodcastPage()
}

@ComponentV2
export struct PodcastPage {
  @Local isLoading: boolean = false;

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










