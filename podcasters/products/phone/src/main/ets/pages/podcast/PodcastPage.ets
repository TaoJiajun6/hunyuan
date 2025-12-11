import { CommonConstants, RouterMap, RouterUtils } from 'lib_common';
import { NavHeaderBar } from 'lib_widget';
import { MusicPlayController } from 'module_musicplay';
import { CloudStorageMusicUtils, CloudAudioFile } from '../../common/CloudStorageMusicUtils';
import { MediaService, getMusicModel, SongItem, MusicModel } from 'module_musicplay';
import { promptAction } from '@kit.ArkUI';
import { FileUtils, TextFileInfo } from '../../utils/FileUtils';
import { picker } from '@kit.CoreFileKit';
import { common } from '@kit.AbilityKit';
import { Logger } from 'lib_common';
import { podcastService, MultiRoleRequest } from 'lib_api';

/**
 * 多角色播客页面路由参数
 */
interface PodcastMultiRolePageParams {
  initialInputType?: string;
}

@Builder
export function PodcastPageBuilder() {
  PodcastPage()
}

@ComponentV2
export struct PodcastPage {
  @Local isLoading: boolean = false;
  @Local isUploadingMusic: boolean = false;
  @Local hasAutoImported: boolean = false; // 标记是否已自动导入过
  @Local recentPodcasts: SongItem[] = []; // 最近播客列表
  @Local isRefreshing: boolean = false; // 是否正在刷新
  @Local musicModel: MusicModel = getMusicModel(); // 音乐模型
  @Local isShowUploadMenu: boolean = false; // 是否显示上传菜单
  @Local isGenerating: boolean = false; // 是否正在生成播客

  /**
   * 页面加载时自动导入播放列表（如果为空）
   */
  async aboutToAppear(): Promise<void> {
    // 检查播放列表是否为空，如果为空则自动导入
    const songList = this.musicModel.getSongList();

    if (songList.length === 0 && !this.hasAutoImported) {
      Logger.info('PodcastPage', '播放列表为空，自动从云存储导入音频');
      this.hasAutoImported = true;
      // 静默导入，不显示加载提示（避免影响用户体验）
      await this.importAudioFromCloudSilently();
    }

    // 加载最近播客列表
    await this.loadRecentPodcasts();
  }

  /**
   * 监听播放列表变化，自动更新最近播客列表
   */
  @Monitor('musicModel.songList')
  onSongListChanged() {
    this.loadRecentPodcasts();
  }

  /**
   * 静默导入音频（不显示加载提示）
   */
  private async importAudioFromCloudSilently(): Promise<void> {
    if (this.isLoading) {
      return;
    }

    try {
      this.isLoading = true;

      // 从云存储导入音频
      const songItems = await CloudStorageMusicUtils.importAudioFromCloudStorage('outputs/podcasts/');

      if (songItems.length === 0) {
        Logger.info('PodcastPage', '未找到音频文件');
        return;
      }

      // 添加到播放列表
      for (const songItem of songItems) {
        MediaService.getInstance().addToSongList(songItem);
      }

      Logger.info('PodcastPage', `自动导入 ${songItems.length} 个音频文件到播放列表`);
    } catch (error) {
      Logger.error('PodcastPage', `自动导入失败: ${error}`);
    } finally {
      this.isLoading = false;
    }
  }

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

      // 刷新最近播客列表
      await this.loadRecentPodcasts();
    } catch (error) {
      promptAction.showToast({
        message: `导入失败: ${error}`,
        duration: 3000
      });
    } finally {
      this.isLoading = false;
    }
  }

  /**
   * 加载最近播客列表
   */
  async loadRecentPodcasts(): Promise<void> {
    try {
      this.isRefreshing = true;
      const songList = this.musicModel.getSongList();

      if (songList.length === 0) {
        this.recentPodcasts = [];
        return;
      }

      // 按时间排序，最新的在前（假设id包含时间戳）
      const sortedList = [...songList].sort((a, b) => {
        const getTimestamp = (id: string): number => {
          const match = id.match(/(\d+)/);
          return match ? parseInt(match[1]) : 0;
        };
        return getTimestamp(b.id) - getTimestamp(a.id);
      });

      // 只显示最近20个
      this.recentPodcasts = sortedList.slice(0, 20);
    } catch (error) {
      Logger.error('PodcastPage', `加载最近播客失败: ${error}`);
    } finally {
      this.isRefreshing = false;
    }
  }

  /**
   * 格式化日期显示
   */
  formatDate(timestamp: number): string {
    const date = new Date(timestamp);
    const month = date.getMonth() + 1;
    const day = date.getDate();
    return `${month}月${day}日`;
  }

  /**
   * 从文件名或ID提取时间戳
   */
  extractTimestamp(song: SongItem): number {
    const match = song.id.match(/(\d+)/);
    if (match) {
      return parseInt(match[1]) * 1000; // 转换为毫秒
    }
    return Date.now();
  }

  /**
   * 播放播客
   */
  playPodcast(song: SongItem): void {
    MediaService.getInstance().playSong(song);
  }

  /**
   * 上传文字内容并生成播客
   */
  async uploadText(): Promise<void> {
    // 跳转到多角色播客页面，预设输入类型为文字
    const params: PodcastMultiRolePageParams = {
      initialInputType: '文字'
    };
    RouterUtils.pushPathByName(RouterMap.PODCAST_MULTI_ROLE_PAGE, params);
  }

  /**
   * 上传文件并生成播客
   */
  async uploadFile(): Promise<void> {
    try {
      const context = this.getUIContext().getHostContext() as common.UIAbilityContext;

      // 选择文本文件（支持.txt、.doc、.docx、.pdf）
      const textFileInfos = await FileUtils.pickTextFiles(context, true);
      if (textFileInfos && textFileInfos.length > 0) {
        // 获取云存储URL列表
        const fileUrls: string[] = [];
        for (let i = 0; i < textFileInfos.length; i++) {
          const fileInfo = textFileInfos[i];
          if (fileInfo && fileInfo.cloudUrl) {
            fileUrls.push(fileInfo.cloudUrl);
          }
        }

        if (fileUrls.length > 0) {
          await this.generatePodcastFromFiles(fileUrls);
        } else {
          promptAction.showToast({
            message: '文件上传失败，请重试',
            duration: 2000
          });
        }
      }
    } catch (error) {
      Logger.error('PodcastPage', `上传文件失败: ${error}`);
      promptAction.showToast({
        message: `上传文件失败: ${error}`,
        duration: 2000
      });
    }
  }

  /**
   * 上传链接并生成播客
   */
  async uploadLink(): Promise<void> {
    // 跳转到多角色播客页面，预设输入类型为网页
    const params: PodcastMultiRolePageParams = {
      initialInputType: '网页'
    };
    RouterUtils.pushPathByName(RouterMap.PODCAST_MULTI_ROLE_PAGE, params);
  }

  /**
   * 上传图片和视频并生成播客
   */
  async uploadImageAndVideo(): Promise<void> {
    try {
      promptAction.showToast({
        message: '图片和视频功能开发中',
        duration: 2000
      });
      // TODO: 实现图片和视频上传功能
    } catch (error) {
      Logger.error('PodcastPage', `上传图片和视频失败: ${error}`);
      promptAction.showToast({
        message: `上传失败: ${error}`,
        duration: 2000
      });
    }
  }

  /**
   * 从文字生成播客
   */
  async generatePodcastFromText(text: string): Promise<void> {
    if (this.isGenerating) {
      return;
    }

    try {
      this.isGenerating = true;
      promptAction.showToast({
        message: '正在生成播客...',
        duration: 2000
      });

      // 调用多角色播客生成API（使用默认角色）
      const request: MultiRoleRequest = {
        text: text,
        input_type: '文字',
        role_voice_urls: {
          '角色A': '', // 使用默认音色
          '角色B': ''
        },
        silence_interval: 800
      };

      const result = await podcastService.generateMultiRolePodcast(request);

      if (result && result.success && result.data && result.data.audio_path) {
        promptAction.showToast({
          message: '播客生成成功！',
          duration: 2000
        });

        // 刷新播客列表
        await this.importAudioFromCloud();
      } else {
        promptAction.showToast({
          message: '播客生成失败，请重试',
          duration: 2000
        });
      }
    } catch (error) {
      Logger.error('PodcastPage', `生成播客失败: ${error}`);
      promptAction.showToast({
        message: `生成播客失败: ${error}`,
        duration: 3000
      });
    } finally {
      this.isGenerating = false;
    }
  }

  /**
   * 从文件生成播客
   */
  async generatePodcastFromFiles(fileUrls: string[]): Promise<void> {
    if (this.isGenerating) {
      return;
    }

    try {
      this.isGenerating = true;
      promptAction.showToast({
        message: '正在生成播客...',
        duration: 2000
      });

      // 调用多角色播客生成API
      const request: MultiRoleRequest = {
        text_file_url: fileUrls.length === 1 ? fileUrls[0] : fileUrls,
        input_type: '文件',
        role_voice_urls: {
          '角色A': '',
          '角色B': ''
        },
        silence_interval: 800
      };

      const result = await podcastService.generateMultiRolePodcast(request);

      if (result && result.success && result.data && result.data.audio_path) {
        promptAction.showToast({
          message: '播客生成成功！',
          duration: 2000
        });

        // 刷新播客列表
        await this.importAudioFromCloud();
      } else {
        promptAction.showToast({
          message: '播客生成失败，请重试',
          duration: 2000
        });
      }
    } catch (error) {
      Logger.error('PodcastPage', `生成播客失败: ${error}`);
      promptAction.showToast({
        message: `生成播客失败: ${error}`,
        duration: 3000
      });
    } finally {
      this.isGenerating = false;
    }
  }

  /**
   * 从链接生成播客
   */
  async generatePodcastFromLink(url: string): Promise<void> {
    if (this.isGenerating) {
      return;
    }

    try {
      this.isGenerating = true;
      promptAction.showToast({
        message: '正在生成播客...',
        duration: 2000
      });

      // 判断链接类型（公众号或网页）
      let inputType = '网页';
      if (url.includes('mp.weixin.qq.com') || url.includes('weixin')) {
        inputType = '公众号';
      }

      // 调用多角色播客生成API
      const request: MultiRoleRequest = {
        input_url: url,
        input_type: inputType,
        role_voice_urls: {
          '角色A': '',
          '角色B': ''
        },
        silence_interval: 800
      };

      const result = await podcastService.generateMultiRolePodcast(request);

      if (result && result.success && result.data && result.data.audio_path) {
        promptAction.showToast({
          message: '播客生成成功！',
          duration: 2000
        });

        // 刷新播客列表
        await this.importAudioFromCloud();
      } else {
        promptAction.showToast({
          message: '播客生成失败，请重试',
          duration: 2000
        });
      }
    } catch (error) {
      Logger.error('PodcastPage', `生成播客失败: ${error}`);
      promptAction.showToast({
        message: `生成播客失败: ${error}`,
        duration: 3000
      });
    } finally {
      this.isGenerating = false;
    }
  }

  build() {
    NavDestination() {
      Column() {
        // 顶部标题栏，带右侧操作按钮
        Row(){
          Text('真AI播客')
            .fontSize($r('sys.float.Title_M'))
            .fontColor($r('sys.color.font_primary'))
            .fontWeight(FontWeight.Bold)
            .margin({ left: CommonConstants.SPACE_S })
        }


        Scroll() {
          Column({ space: 20 }) {
            // 播客功能卡片区域（横向滚动）
            Column({ space: 12 }) {
              Row() {
                Text('播客功能')
                  .fontSize(20)
                  .fontColor($r('sys.color.font_primary'))
                  .fontWeight(FontWeight.Bold)
                Blank()
                Text('更多>')
                  .fontSize(14)
                  .fontColor($r('sys.color.font_secondary'))
                  .onClick(() => {
                    // 可以跳转到功能详情页
                  })
              }
              .width('100%')
              .padding({ left: 16, right: 16 })

              Scroll() {
                Row({ space: 12 }) {
                  // 多角色互动播客卡片
                  this.podcastFunctionCard(
                    '多角色互动播客',
                    '将文本素材转化为多角色自然互动的播客音频',
                    () => {
                      RouterUtils.pushPathByName(RouterMap.PODCAST_MULTI_ROLE_PAGE)
                    }
                  )

                  // 自定义角色播客卡片
                  this.podcastFunctionCard(
                    '自定义角色播客',
                    '根据用户自定义的角色人设和音色生成契合风格的播客音频',
                    () => {
                      RouterUtils.pushPathByName(RouterMap.PODCAST_CHARACTER_PAGE)
                    }
                  )

                  // 主题深度播客卡片
                  this.podcastFunctionCard(
                    '主题深度播客',
                    '基于指定主题生成有深度、引发思考的播客音频',
                    () => {
                      RouterUtils.pushPathByName(RouterMap.PODCAST_DEEP_PAGE)
                    }
                  )

                  // 上传背景音乐卡片
                  this.podcastFunctionCard(
                    '上传背景音乐',
                    '将本地背景音乐文件上传到云存储',
                    () => {
                      this.uploadBackgroundMusic();
                    },
                    this.isUploadingMusic
                  )

                  // 导入音频卡片
                  this.podcastFunctionCard(
                    '导入音频',
                    '从云存储中导入已生成的播客音频',
                    () => {
                      this.importAudioFromCloud();
                    },
                    this.isLoading
                  )
                }
                .padding({ left: 16, right: 16 })
              }
              .scrollable(ScrollDirection.Horizontal)
              .scrollBar(BarState.Off)
            }
            .width('100%')
            .padding({ top: 16, bottom: 8 })

            // 最近播客列表区域
            Column({ space: 12 }) {
              Row() {
                Text('最近播客')
                  .fontSize(20)
                  .fontColor($r('sys.color.font_primary'))
                  .fontWeight(FontWeight.Bold)
                Blank()
              }
              .width('100%')
              .padding({ left: 16, right: 16 })

              if (this.recentPodcasts.length === 0) {
                Column() {
                  Text('暂无播客内容')
                    .fontSize(14)
                    .fontColor($r('sys.color.font_secondary'))
                    .margin({ top: 40, bottom: 40 })
                }
                .width('100%')
              } else {
                Column({ space: 0 }) {
                  ForEach(this.recentPodcasts, (song: SongItem, index: number) => {
                    this.podcastListItem(song, index)
                  }, (song: SongItem) => song.id)
                }
                .width('100%')
                .padding({ left: 16, right: 16 })
              }
            }
            .width('100%')
            .padding({ top: 8, bottom: 16 })
          }
          .width('100%')
        }
        .layoutWeight(1)
        .scrollBar(BarState.Off)

        // 播放器组件 - 放在底部导航栏上方
        MusicPlayController()
      }
      .width('100%')
      .height('100%')
      .backgroundColor($r('sys.color.background_primary'))

    }
    .hideTitleBar(true)
  }

  /**
   * 标题栏右侧按钮构建器
   */
  @Builder
  headerRightBuilder() {
    Row({ space: 12 }) {
      // 加号按钮（上传内容）
      Button() {
        Image($r('app.media.plus'))
          .width(18)
          .height(18)
          .fillColor(Color.White)
      }
      .type(ButtonType.Normal)
      .backgroundColor($r('sys.color.icon_emphasize'))
      .borderRadius(20)
      .width(40)
      .height(40)
      //.bindMenu(this.MyMenu)

      // 搜索按钮
      Button() {
        SymbolGlyph($r('sys.symbol.magnifyingglass'))
          .fontSize(18)
          .fontColor([$r('sys.color.font_primary')])
      }
      .type(ButtonType.Normal)
      .backgroundColor(Color.Transparent)
      .borderRadius(20)
      .width(40)
      .height(40)
      .onClick(() => {
        // 搜索功能
        promptAction.showToast({ message: '搜索功能开发中', duration: 2000 });
      })

      // 更多选项按钮
      Button() {
        SymbolGlyph($r('sys.symbol.list_bullet'))
          .fontSize(18)
          .fontColor([$r('sys.color.font_primary')])
      }
      .type(ButtonType.Normal)
      .backgroundColor(Color.Transparent)
      .borderRadius(20)
      .width(40)
      .height(40)
      .onClick(() => {
        // 更多选项
        promptAction.showToast({ message: '更多选项开发中', duration: 2000 });
      })
    }
  }

  /**
   * 上传菜单
   */
  @Builder
  MyMenu() {
    Menu() {
      MenuItem({ 
        startIcon: $r("sys.symbol.doc_text"), 
        content: "文字" 
      })
      .onChange(() => {
        this.uploadText();
      })

      MenuItem({ 
        startIcon: $r("sys.symbol.folder"), 
        content: "文件" 
      })
      .onChange(() => {
        this.uploadFile();
      })

      MenuItem({ 
        startIcon: $r("sys.symbol.link"), 
        content: "链接" 
      })
      .onChange(() => {
        this.uploadLink();
      })

      MenuItem({ 
        startIcon: $r("sys.symbol.camera"), 
        content: "图片和视频" 
      })
      .onChange(() => {
        this.uploadImageAndVideo();
      })
    }
  }

  /**
   * 播客功能卡片
   */
  @Builder
  podcastFunctionCard(title: string, description: string, onClick: () => void, disabled: boolean = false) {
    Column({ space: 8 }) {
      // 图标区域
      Column() {
        Image($r('app.media.zhibozhong'))
          .width(40)
          .height(40)
          .fillColor($r('sys.color.icon_emphasize'))
      }
      .width(60)
      .height(60)
      .borderRadius(12)
      .backgroundColor($r('sys.color.comp_background_tertiary'))
      .justifyContent(FlexAlign.Center)

      // 标题
      Text(title)
        .fontSize(14)
        .fontColor($r('sys.color.font_primary'))
        .fontWeight(FontWeight.Medium)
        .maxLines(1)
        .textOverflow({ overflow: TextOverflow.Ellipsis })
        .width(120)
        .textAlign(TextAlign.Center)

      // 描述
      Text(description)
        .fontSize(12)
        .fontColor($r('sys.color.font_secondary'))
        .maxLines(2)
        .textOverflow({ overflow: TextOverflow.Ellipsis })
        .width(120)
        .textAlign(TextAlign.Center)
    }
    .width(140)
    .padding(12)
    .borderRadius(16)
    .backgroundColor($r('sys.color.comp_background_primary'))
    .opacity(disabled ? 0.6 : 1)
    .enabled(!disabled)
    .onClick(() => {
      if (!disabled) {
        onClick();
      }
    })
  }

  /**
   * 播客列表项
   */
  @Builder
  podcastListItem(song: SongItem, index: number) {
    Row({ space: 12 }) {
      // 左侧图标
      Column() {
        Image(song.label)
          .width(48)
          .height(48)
          .borderRadius(8)
      }
      .width(48)
      .height(48)
      .borderRadius(8)
      .backgroundColor($r('sys.color.comp_background_tertiary'))
      .justifyContent(FlexAlign.Center)

      // 中间内容
      Column({ space: 4 }) {
        Text(song.title || '未知播客')
          .fontSize(16)
          .fontColor($r('sys.color.font_primary'))
          .fontWeight(FontWeight.Medium)
          .maxLines(1)
          .textOverflow({ overflow: TextOverflow.Ellipsis })
          .width('100%')

        if (song.singer) {
          Text(song.singer)
            .fontSize(12)
            .fontColor($r('sys.color.font_secondary'))
            .maxLines(1)
            .textOverflow({ overflow: TextOverflow.Ellipsis })
            .width('100%')
        }

        Row({ space: 8 }) {
          Text('播客')
            .fontSize(11)
            .fontColor($r('sys.color.font_secondary'))
            .padding({
              left: 6,
              right: 6,
              top: 2,
              bottom: 2
            })
            .borderRadius(4)
            .backgroundColor($r('sys.color.comp_background_tertiary'))
        }
        .margin({ top: 4 })
      }
      .layoutWeight(1)
      .alignItems(HorizontalAlign.Start)
      .justifyContent(FlexAlign.Center)

      // 右侧日期
      Column() {
        Text(this.formatDate(this.extractTimestamp(song)))
          .fontSize(12)
          .fontColor($r('sys.color.font_secondary'))
      }
      .alignItems(HorizontalAlign.End)
      .justifyContent(FlexAlign.Center)
    }
    .width('100%')
    .padding(12)
    .borderRadius(12)
    .backgroundColor($r('sys.color.comp_background_primary'))
    .margin({ bottom: index < this.recentPodcasts.length - 1 ? 8 : 0 })
    .onClick(() => {
      this.playPodcast(song);
    })
  }
}










