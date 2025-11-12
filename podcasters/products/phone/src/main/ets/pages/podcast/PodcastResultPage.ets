import { RouterMap, RouterUtils, WindowModel } from 'lib_common';
import { NavHeaderBar } from 'lib_widget';
import { PodcastResult } from 'lib_api';
import { AudioPlayer } from '../../components/AudioPlayer';
import { promptAction, AppStorageV2 } from '@kit.ArkUI';
import { pasteboard } from '@kit.BasicServicesKit';
import { MarkdownV2 } from '@lidary/markdown';
import { MediaService, SongItem } from 'module_musicplay';
import { PodcastMusicUtils } from '../../common/PodcastMusicUtils';
import { Logger } from 'lib_common';

const TAG = 'PodcastResultPage';

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
  @Local localAudioPath: string = '';
  @Local cachedSongItem?: SongItem;
  @Local isAutoImporting: boolean = false;
  @Local hasAutoImported: boolean = false;

  aboutToAppear(): void {
    const params = RouterUtils.getParamByName<PodcastResultPageParams>(RouterMap.PODCAST_RESULT_PAGE);
    if (params) {
      this.result = params.result;
      this.pageTitle = params.pageTitle;
      this.script = params.script || params.result?.script || '';
    }

    if (!this.hasAutoImported) {
      this.hasAutoImported = true;
      Promise.resolve().then(() => this.autoDownloadAndPlay());
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

  /**
   * 添加到播放列表并播放
   */
  async addToPlaylistAndPlay(): Promise<void> {
    if (!this.result || !PodcastMusicUtils.hasAudio(this.result)) {
      promptAction.showToast({
        message: '暂无音频可播放',
        duration: 2000
      });
      return;
    }

    try {
      const songItem = await this.prepareSongItem();
      if (!songItem || !songItem.src) {
        promptAction.showToast({
          message: '音频准备失败，请稍后重试',
          duration: 2000
        });
        return;
      }
      MediaService.getInstance().playSong(songItem);
      promptAction.showToast({
        message: '已添加到播放列表并开始播放',
        duration: 2000
      });
    } catch (error) {
      Logger.error(TAG, `addToPlaylistAndPlay 出错: ${error}`);
      promptAction.showToast({
        message: '添加失败',
        duration: 2000
      });
    }
  }

  /**
   * 仅添加到播放列表（不播放）
   */
  async addToPlaylist(): Promise<void> {
    if (!this.result || !PodcastMusicUtils.hasAudio(this.result)) {
      promptAction.showToast({
        message: '暂无音频可添加',
        duration: 2000
      });
      return;
    }

    try {
      const songItem = await this.prepareSongItem();
      if (!songItem || !songItem.src) {
        promptAction.showToast({
          message: '音频准备失败，请稍后重试',
          duration: 2000
        });
        return;
      }
      MediaService.getInstance().addToSongList(songItem);
      promptAction.showToast({
        message: '已添加到播放列表',
        duration: 2000
      });
    } catch (error) {
      Logger.error(TAG, `addToPlaylist 出错: ${error}`);
      promptAction.showToast({
        message: '添加失败',
        duration: 2000
      });
    }
  }

  private async prepareSongItem(): Promise<SongItem | null> {
    if (this.cachedSongItem && this.cachedSongItem.src) {
      return this.cloneSongItem(this.cachedSongItem);
    }
    if (!this.result) {
      return null;
    }
    try {
      const songItem = await PodcastMusicUtils.convertToSongItem(this.result, this.pageTitle);
      if (!songItem.src) {
        return null;
      }
      this.cachedSongItem = songItem;
      this.localAudioPath = songItem.isLocal ? songItem.src : '';
      return this.cloneSongItem(songItem);
    } catch (error) {
      Logger.error(TAG, `prepareSongItem 出错: ${error}`);
      return null;
    }
  }

  private cloneSongItem(source: SongItem): SongItem {
    const clone = new SongItem();
    clone.id = `podcast_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    clone.title = source.title;
    clone.singer = source.singer;
    clone.src = source.src;
    clone.mark = source.mark;
    clone.label = source.label;
    clone.lyric = source.lyric;
    clone.isCollected = source.isCollected;
    clone.isLocal = source.isLocal;
    clone.mvUrl = source.mvUrl;
    clone.isVip = source.isVip;
    clone.collectedCount = source.collectedCount;
    clone.playlistCount = source.playlistCount;
    clone.downloadCount = source.downloadCount;
    clone.shareCount = source.shareCount;
    return clone;
  }

  private async autoDownloadAndPlay(): Promise<void> {
    if (this.isAutoImporting || !this.result || !PodcastMusicUtils.hasAudio(this.result)) {
      return;
    }
    this.isAutoImporting = true;
    try {
      const songItem = await this.prepareSongItem();
      if (!songItem || !songItem.src) {
        Logger.warn(TAG, '自动播放失败，音频未准备好');
        return;
      }
      MediaService.getInstance().playSong(songItem);
      promptAction.showToast({
        message: '已开始播放生成的播客',
        duration: 2000
      });
    } catch (error) {
      Logger.error(TAG, `autoDownloadAndPlay 出错: ${error}`);
    } finally {
      this.isAutoImporting = false;
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
            if (this.result?.audio_url || this.result?.audio_base64) {
              Column({ space: 12 }) {
                Text('生成的播客音频')
                  .fontSize($r('sys.float.Subtitle_L'))
                  .fontColor($r('sys.color.font_primary'))
                  .fontWeight(FontWeight.Bold)
                  .alignSelf(ItemAlign.Start)

                AudioPlayer({
                  audioUrl: this.localAudioPath || this.result?.audio_url,
                  audioBase64: this.localAudioPath ? '' : this.result?.audio_base64
                })

                // 如果上传仍在后台进行，可提示用户云端地址可用性
                if (this.result?.agc_upload_status && this.result.agc_upload_status.status === 'started') {
                  Text('正在后台上传到云存储，您也可先使用本地音频播放')
                    .fontSize($r('sys.float.Body_S'))
                    .fontColor($r('sys.color.font_secondary'))
                    .alignSelf(ItemAlign.Start)
                }

                // 添加到播放列表按钮（仅当有 URL 时显示）
                if (PodcastMusicUtils.hasPlayableUrl(this.result)) {
                  Row({ space: 12 }) {
                    Button('添加到播放列表')
                      .layoutWeight(1)
                      .type(ButtonType.Normal)
                      .backgroundColor($r('sys.color.comp_background_tertiary'))
                      .fontColor($r('sys.color.font_primary'))
                      .onClick(() => {
                        this.addToPlaylist();
                      })

                    Button('播放')
                      .layoutWeight(1)
                      .type(ButtonType.Capsule)
                      .backgroundColor($r('sys.color.icon_emphasize'))
                      .fontColor($r('sys.color.font_on_primary'))
                      .onClick(() => {
                        this.addToPlaylistAndPlay();
                      })
                  }
                  .width('100%')
                }
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

