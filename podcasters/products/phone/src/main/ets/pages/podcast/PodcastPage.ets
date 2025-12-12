import { BreakpointModel, CommonConstants, RouterMap, RouterUtils, WindowModel } from 'lib_common';
import { NavHeaderBar } from 'lib_widget';
import { MusicPlayController } from 'module_musicplay';
import { CloudStorageMusicUtils, CloudAudioFile } from '../../common/CloudStorageMusicUtils';
import { MediaService, getMusicModel, SongItem, MusicModel } from 'module_musicplay';
import { promptAction } from '@kit.ArkUI';
import { FileUtils, TextFileInfo } from '../../utils/FileUtils';
import { picker } from '@kit.CoreFileKit';
import { common } from '@kit.AbilityKit';
import { Logger } from 'lib_common';
import { podcastService, MultiRoleRequest, PodcastListItem, cloudDatabaseService } from 'lib_api';
import { AppStorageV2 } from '@kit.ArkUI';
import { cloudStorage } from '@kit.CloudFoundationKit';

/**
 * 播客创建页面路由参数
 */
interface PodcastCreatePageParams {
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
  @Local showDeleteMenu: boolean = false; // 是否显示删除菜单
  @Local selectedPodcastId: string = ''; // 选中的播客ID
  @Local searchKeyword: string = ''; // 搜索关键词
  @Local isSearchMode: boolean = false; // 是否处于搜索模式
  @Local filteredPodcasts: SongItem[] = []; // 过滤后的播客列表
  // 存储播客ID到创建时间的映射（用于从云数据库获取的播客）
  private podcastCreatedAtMap: Map<string, number> = new Map();
  @Param headerBarHeight: Length = $r('app.float.nav_header_height');
  @Local windowModel: WindowModel = AppStorageV2.connect(WindowModel, () => new WindowModel())!;
  @Local breakPointModel: BreakpointModel = AppStorageV2.connect(BreakpointModel, () => new BreakpointModel())!;
  @Consumer() isCommentInModalDialog: boolean = false
  @Param customPadding: Padding = {};
  @Param bgColor: ResourceColor = '#00000000';

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
   * 显示云数据库中的播客和云存储中的音频文件
   */
  async loadRecentPodcasts(): Promise<void> {
    try {
      this.isRefreshing = true;

      // 清空之前的映射
      this.podcastCreatedAtMap.clear();
      const allSongItems: SongItem[] = [];
      const urlSet = new Set<string>(); // 用于去重，根据URL去重
      const cloudDbFilePaths = new Set<string>(); // 记录云数据库中已有的文件路径
      let podcastList: PodcastListItem[] = [];

      // 1. 从云数据库获取播客数据（优先显示）
      try {
        podcastList = await podcastService.getPodcastList(); // 获取全部播客

        if (podcastList && podcastList.length > 0) {
          for (const podcast of podcastList) {
            // 只处理有 audio_url 的播客
            if (podcast.audio_url && podcast.audio_url.trim() !== '') {
              // 保存创建时间到映射表
              if (podcast.created_at) {
                this.podcastCreatedAtMap.set(podcast.id, podcast.created_at);
              }

              // 提取云存储路径，用于后续匹配
              const cloudPath = CloudStorageMusicUtils.extractCloudPath(podcast.audio_url);
              if (cloudPath) {
                cloudDbFilePaths.add(cloudPath);
                // 也添加文件名用于匹配
                const fileName = cloudPath.split('/').pop() || '';
                if (fileName) {
                  cloudDbFilePaths.add(fileName);
                }
              }

              // 转换为SongItem
              const songItem = this.convertPodcastToSongItem(podcast);

              // 根据URL去重
              if (songItem.src && !urlSet.has(songItem.src)) {
                urlSet.add(songItem.src);
                allSongItems.push(songItem);
              }
            }
          }
          Logger.info('PodcastPage', `从云数据库加载了 ${allSongItems.length} 个播客`);
        }
      } catch (cloudError) {
        Logger.warn('PodcastPage', `从云数据库获取播客列表失败: ${cloudError}`);
      }

      // 2. 从云存储获取音频文件列表（只添加云数据库中没有的）
      try {
        const audioFiles = await CloudStorageMusicUtils.getAudioFileList('outputs/podcasts/');
        Logger.info('PodcastPage', `从云存储找到 ${audioFiles.length} 个音频文件`);

        if (audioFiles.length > 0) {
          let addedCount = 0;

          // 逐个处理音频文件
          for (const audioFile of audioFiles) {
            // 检查这个文件是否已经在云数据库中
            const filePath = audioFile.filePath;
            const fileName = audioFile.fileName;
            const isInCloudDb = cloudDbFilePaths.has(filePath) || cloudDbFilePaths.has(fileName);

            // 如果不在云数据库中，才添加（使用云存储的元数据）
            if (!isInCloudDb) {
              try {
                // 转换为SongItem
                const songItem = await CloudStorageMusicUtils.convertToSongItem(audioFile);

                // 只添加成功转换的项（src不为空）且未重复的
                if (songItem.src && songItem.src !== '' && !urlSet.has(songItem.src)) {
                  urlSet.add(songItem.src);
                  allSongItems.push(songItem);
                  addedCount++;
                } else {
                  Logger.warn('PodcastPage', `跳过文件 ${fileName}，转换失败或已存在（src为空或重复）`);
                }
              } catch (convertError) {
                Logger.warn('PodcastPage', `转换文件 ${fileName} 失败: ${convertError}`);
              }
            } else {
              Logger.info('PodcastPage', `跳过文件 ${fileName}，已在云数据库中`);
            }
          }
          Logger.info('PodcastPage', `从云存储添加了 ${addedCount} 个云数据库中没有的音频文件`);
        }
      } catch (cloudStorageError) {
        Logger.warn('PodcastPage', `从云存储获取音频文件失败: ${cloudStorageError}`);
      }

      // 3. 按创建时间排序
      const sortedList = allSongItems.sort((a, b) => {
        // 从映射表获取创建时间（数据库中的created_at字段）
        const timestampA = this.podcastCreatedAtMap.get(a.id) || 0;
        const timestampB = this.podcastCreatedAtMap.get(b.id) || 0;

        // 如果都有created_at，按时间倒序
        if (timestampA > 0 && timestampB > 0) {
          return timestampB - timestampA;
        }

        // 如果只有一个有created_at，有created_at的排在前面
        if (timestampA > 0) {
          return -1;
        }
        if (timestampB > 0) {
          return 1;
        }

        // 如果都没有created_at，按ID倒序
        return b.id.localeCompare(a.id);
      });

      // 显示全部播客
      this.recentPodcasts = sortedList;
      // 如果正在搜索，更新过滤列表
      if (this.isSearchMode && this.searchKeyword.trim() !== '') {
        this.filterPodcasts();
      } else {
        this.filteredPodcasts = sortedList;
      }
      Logger.info('PodcastPage', `合并后共显示 ${this.recentPodcasts.length} 个播客`);
    } catch (error) {
      Logger.error('PodcastPage', `加载最近播客失败: ${error}`);
      this.recentPodcasts = [];
    } finally {
      this.isRefreshing = false;
    }
  }

  /**
   * 将PodcastListItem转换为SongItem
   */
  convertPodcastToSongItem(podcast: PodcastListItem): SongItem {
    const songItem = new SongItem();

    // 基本信息
    songItem.id = podcast.id || '';
    songItem.title = podcast.title || '未知播客';

    // 设置singer为分类或"云存储音频"
    if (podcast.category) {
      songItem.singer = podcast.category;
    } else if (podcast.roles && podcast.roles.length > 0) {
      songItem.singer = podcast.roles.join('、');
    } else {
      songItem.singer = '云存储音频';
    }

    // 音频URL（优先使用audio_url）
    if (podcast.audio_url) {
      songItem.src = podcast.audio_url;
      songItem.isLocal = false;
    } else if (podcast.local_file) {
      songItem.src = podcast.local_file;
      songItem.isLocal = true;
    } else {
      songItem.src = '';
      songItem.isLocal = false;
    }

    // 设置脚本内容
    songItem.script = podcast.script || '';

    // 设置封面图标（优先使用封面图URL，否则使用默认图标）
    if (podcast.cover_image_url && podcast.cover_image_url.trim() !== '') {
      songItem.label = podcast.cover_image_url;
    } else {
      songItem.label = $r('app.media.zhibozhong');
    }

    // 其他属性
    songItem.isCollected = false;
    songItem.isVip = false;
    songItem.mark = '1';
    songItem.lyric = '';
    songItem.mvUrl = '';

    return songItem;
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
   * 从数据库中获取创建时间戳
   * 直接使用数据库中的created_at字段，不进行其他提取
   */
  extractTimestamp(song: SongItem): number {
    if (!song.id) {
      return Date.now();
    }

    // 直接从映射表中获取创建时间（数据库中的created_at字段）
    const createdAt = this.podcastCreatedAtMap.get(song.id);
    if (createdAt !== undefined && createdAt > 0) {
      // 判断是秒还是毫秒（如果小于当前时间戳的1/1000，则是秒）
      if (createdAt < 10000000000) {
        return createdAt * 1000; // 转换为毫秒
      }
      return createdAt;
    }

    // 如果映射表中没有（可能是本地播客），返回当前时间
    return Date.now();
  }

  /**
   * 播放播客
   */
  playPodcast(song: SongItem): void {
    Logger.info('PodcastPage', `开始播放播客: ${song.title}, id: ${song.id}, src: ${song.src}`);
    try {
      MediaService.getInstance().playSong(song);
      Logger.info('PodcastPage', `已调用MediaService.playSong`);
    } catch (error) {
      Logger.error('PodcastPage', `播放播客失败: ${String(error)}`);
      promptAction.showToast({
        message: `播放失败: ${String(error)}`,
        duration: 3000
      });
    }
  }

  /**
   * 显示删除菜单
   */
  showDeleteActionSheet(song: SongItem): void {
    this.selectedPodcastId = song.id;
    // 使用 promptAction.showDialog 显示删除确认对话框
    promptAction.showDialog({
      title: '删除播客',
      message: '确定要删除这个播客吗？删除后无法恢复。',
      buttons: [
        {
          text: '取消',
          color: $r('sys.color.font_primary')
        },
        {
          text: '删除',
          color: '#FFE94949'
        }
      ]
    }).then((data) => {
      if (data.index === 1) {
        // 用户点击了"删除"按钮
        this.deletePodcast();
      } else {
        // 用户点击了"取消"或关闭对话框
        this.showDeleteMenu = false;
        this.selectedPodcastId = '';
      }
    }).catch(() => {
      this.showDeleteMenu = false;
      this.selectedPodcastId = '';
    });
  }

  /**
   * 删除播客
   */
  async deletePodcast(): Promise<void> {
    if (!this.selectedPodcastId) {
      return;
    }

    try {
      // 先获取要删除的播客信息（用于删除云存储文件）
      const podcastToDelete = this.recentPodcasts.find(song => song.id === this.selectedPodcastId);
      const audioUrl = podcastToDelete?.src;

      // 1. 从云数据库删除
      const deleted = await cloudDatabaseService.deletePodcastById(this.selectedPodcastId);
      if (deleted) {
        Logger.info('PodcastPage', `从云数据库删除播客成功: ${this.selectedPodcastId}`);
      } else {
        Logger.warn('PodcastPage', `从云数据库删除播客失败: ${this.selectedPodcastId}`);
      }

      // 2. 从播放列表删除
      MediaService.getInstance().removeSongById(this.selectedPodcastId);

      // 3. 从映射表删除
      this.podcastCreatedAtMap.delete(this.selectedPodcastId);

      // 4. 从最近播客列表删除
      this.recentPodcasts = this.recentPodcasts.filter(song => song.id !== this.selectedPodcastId);

      // 5. 更新过滤列表（如果正在搜索）
      if (this.isSearchMode) {
        this.filterPodcasts();
      } else {
        this.filteredPodcasts = this.recentPodcasts;
      }

      // 6. 尝试从云存储删除音频文件（如果存在）
      if (audioUrl) {
        try {
          const cloudPath = this.extractCloudPathFromUrl(audioUrl);
          if (cloudPath) {
            const storageBucket = cloudStorage.bucket();
            await storageBucket.deleteFile(cloudPath);
            Logger.info('PodcastPage', `从云存储删除文件成功: ${cloudPath}`);
          }
        } catch (cloudError) {
          Logger.warn('PodcastPage', `从云存储删除文件失败: ${cloudError}`);
        }
      }

      promptAction.showToast({
        message: '播客已删除',
        duration: 2000
      });

      // 刷新列表
      await this.loadRecentPodcasts();
    } catch (error) {
      Logger.error('PodcastPage', `删除播客失败: ${error}`);
      promptAction.showToast({
        message: `删除失败: ${String(error)}`,
        duration: 3000
      });
    } finally {
      this.showDeleteMenu = false;
      this.selectedPodcastId = '';
    }
  }

  /**
   * 从URL提取云存储路径
   */
  extractCloudPathFromUrl(url: string): string | null {
    if (!url) {
      return null;
    }
    try {
      // 匹配 outputs/podcasts/文件名.wav 格式
      const match = url.match(/outputs\/podcasts\/[^\/]+\.(wav|mp3|m4a|aac|flac|ogg|wma)/i);
      if (match && match[0]) {
        return match[0];
      }
      // 如果URL包含 /outputs/，提取后面的路径
      const outputsIndex = url.indexOf('/outputs/');
      if (outputsIndex !== -1) {
        return url.substring(outputsIndex + 1);
      }
    } catch (error) {
      Logger.warn('PodcastPage', `提取云存储路径失败: ${error}`);
    }
    return null;
  }

  /**
   * 上传文字内容并生成播客
   */
  async uploadText(): Promise<void> {
    // 跳转到整合的播客创建页面
    RouterUtils.pushPathByName(RouterMap.PODCAST_CREATE_PAGE);
  }

  /**
   * 上传文件并生成播客
   */
  async uploadFile(): Promise<void> {
    // 跳转到整合的播客创建页面
    RouterUtils.pushPathByName(RouterMap.PODCAST_CREATE_PAGE);
  }

  /**
   * 上传链接并生成播客
   */
  async uploadLink(): Promise<void> {
    // 跳转到整合的播客创建页面
    RouterUtils.pushPathByName(RouterMap.PODCAST_CREATE_PAGE);
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
   * 过滤播客列表
   */
  filterPodcasts(): void {
    if (!this.searchKeyword || this.searchKeyword.trim() === '') {
      this.filteredPodcasts = this.recentPodcasts;
      return;
    }

    const keyword = this.searchKeyword.trim().toLowerCase();
    this.filteredPodcasts = this.recentPodcasts.filter((song: SongItem) => {
      // 搜索标题
      if (song.title && song.title.toLowerCase().includes(keyword)) {
        return true;
      }
      // 搜索歌手/分类
      if (song.singer && song.singer.toLowerCase().includes(keyword)) {
        return true;
      }
      // 搜索脚本内容
      if (song.script && song.script.toLowerCase().includes(keyword)) {
        return true;
      }
      return false;
    });
  }

  /**
   * 切换搜索模式
   */
  toggleSearchMode(): void {
    this.isSearchMode = !this.isSearchMode;
    if (!this.isSearchMode) {
      // 退出搜索模式，清空搜索关键词
      this.searchKeyword = '';
      this.filteredPodcasts = this.recentPodcasts;
    } else {
      // 进入搜索模式，初始化过滤列表
      this.filteredPodcasts = this.recentPodcasts;
    }
  }

  /**
   * 清除搜索
   */
  clearSearch(): void {
    this.searchKeyword = '';
    this.filteredPodcasts = this.recentPodcasts;
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
        Row({ space: 14 }) {
          if (!this.isSearchMode) {
            Text('真AI播客')
              .fontSize($r('sys.float.Title_M'))
              .fontColor($r('sys.color.font_primary'))
              .fontWeight(FontWeight.Bold)
              .margin({ left: CommonConstants.SPACE_S })
          } else {
            // 搜索输入框
            Row({ space: 8 }) {
              TextInput({ placeholder: '搜索播客标题、分类或内容...', text: this.searchKeyword })
                .layoutWeight(1)
                .height(36)
                .fontSize(14)
                .backgroundColor('#ffe5e5e5')
                .borderRadius(18)
                .padding({ left: 12, right: 12 })
                .onChange((value: string) => {
                  this.searchKeyword = value;
                  this.filterPodcasts();
                })

              // 清除按钮
              if (this.searchKeyword.trim() !== '') {
                Button() {
                  SymbolGlyph($r('sys.symbol.xmark_circle_fill'))
                    .fontSize(16)
                    .fontColor([$r('sys.color.font_secondary')])
                }
                .type(ButtonType.Normal)
                .backgroundColor(Color.Transparent)
                .width(32)
                .height(32)
                .onClick(() => {
                  this.clearSearch();
                })
              }
            }
            .layoutWeight(1)
            .margin({ left: CommonConstants.SPACE_S })
          }

          Blank()

          if (!this.isSearchMode) {
            // 加号按钮（上传内容）
            Button() {
              Image($r('app.media.plus'))
                .width(24)
                .aspectRatio(1)
                .fillColor(Color.White)
            }
            .type(ButtonType.Normal)
            //.backgroundColor('#ffc78cfd')
            .linearGradient({
              angle: 140,
              colors: [
                ['#ffb3e0', 0.0],
                ['#ffc78cfd', 0.2],
                ['#a0e5ff', 1.0]
              ]
            })
            .borderRadius(20)
            .width(40)
            .height(40)
            .bindMenu(this.MyMenu)


            // 搜索按钮
            Button() {
              SymbolGlyph($r('sys.symbol.magnifyingglass'))
                .fontSize(18)
                .fontColor([$r('sys.color.font_normal')])
            }
            .type(ButtonType.Normal)
            .backgroundColor($r('app.color.button_background'))
            .borderRadius(20)
            .width(40)
            .height(40)
            .onClick(() => {
              this.toggleSearchMode();
            })
          } else {
            // 取消搜索
            Text('取消')
              .fontSize(14)
              .fontColor($r('sys.color.font_primary'))

              .onClick(() => {
                this.toggleSearchMode();
              })
          }
        }.height(this.headerBarHeight)
        .justifyContent(FlexAlign.SpaceBetween)
        .width(CommonConstants.FULL_PERCENT)


        Scroll() {
          Column({ space: 20 }) {
            // 播客功能卡片区域（横向滚动）
            Column({ space: 12 }) {
              Row() {
                Text('播客功能')
                  .fontSize(20)
                  .fontColor($r('sys.color.font_primary'))
                  .fontWeight(FontWeight.Bold)
              }
              .width('100%')
              .padding({ left: 16, right: 16 })

              Scroll() {
                Row({ space: 12 }) {

                  // 上传背景音乐卡片
                  this.podcastFunctionCard(
                    '上传背景音乐',
                    '将本地背景音乐文件上传到云存储',
                    () => {
                      this.uploadBackgroundMusic();
                    },
                    this.isUploadingMusic
                  )


                  // 音色克隆卡片
                  this.podcastFunctionCard(
                    '音色克隆',
                    '在几秒钟内克隆你的声音',
                    () => {
                      RouterUtils.pushPathByName(RouterMap.VOICE_CLONE_PAGE);
                    }
                  )
                }
                .padding({ left: 16, right: 16 })
              }
              .scrollable(ScrollDirection.Horizontal)
              .scrollBar(BarState.Off)
            }
            .width('100%')
            .padding({ top: 16, bottom: 10 })

            // 最近播客列表区域
            Column({ space: 12 }) {
              Row() {
                Text(this.isSearchMode ? '搜索结果' : '最近播客')
                  .fontSize(20)
                  .fontColor($r('sys.color.font_primary'))
                  .fontWeight(FontWeight.Bold)
                Blank()
                if (this.isSearchMode && this.searchKeyword.trim() !== '') {
                  Text(`共找到 ${this.filteredPodcasts.length} 个结果`)
                    .fontSize(12)
                    .fontColor($r('sys.color.font_secondary'))
                }
              }
              .width('100%')
              .padding({ left: 16, right: 16 })

              if ((this.isSearchMode ? this.filteredPodcasts : this.recentPodcasts).length === 0) {
                Column() {
                  Text(this.isSearchMode && this.searchKeyword.trim() !== '' ? '未找到匹配的播客' : '暂无播客内容')
                    .fontSize(14)
                    .fontColor($r('sys.color.font_secondary'))
                    .margin({ top: 40, bottom: 40 })
                }
                .width('100%')
              } else {
                Column() {
                  ForEach(this.isSearchMode ? this.filteredPodcasts : this.recentPodcasts,
                    (song: SongItem, index: number) => {
                      this.podcastListItem(song, index)
                    }, (song: SongItem) => song.id)
                }
                .width('100%')
                .padding({ left: 10, right: 10 })
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
          .margin({ bottom: 10 })
      }
      .padding({
        left: this.customPadding.left ?? this.breakPointModel.pagePadding,
        right: this.customPadding.right ?? this.breakPointModel.pagePadding,
        top: this.customPadding.top ?? (this.isCommentInModalDialog ? CommonConstants.PADDING_S :
          this.windowModel.windowTopPadding),
        bottom: this.customPadding.bottom ?? 0,
      })
      .width(CommonConstants.FULL_PERCENT)
      .backgroundColor($r('app.color.start_window_background'))
    }
    .hideTitleBar(true)
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
          this.navigateToCreatePage('文字');
        })

      MenuItem({
        startIcon: $r("sys.symbol.doc_text"),
        content: "文字+指令"
      })
        .onChange(() => {
          this.navigateToCreatePage('文字+指令');
        })

      MenuItem({
        startIcon: $r("sys.symbol.folder"),
        content: "文件"
      })
        .onChange(() => {
          this.navigateToCreatePage('文件');
        })

      MenuItem({
        startIcon: $r("sys.symbol.folder"),
        content: "文件+指令"
      })
        .onChange(() => {
          this.navigateToCreatePage('文件+指令');
        })

      MenuItem({
        startIcon: $r("sys.symbol.link"),
        content: "链接"
      })
        .onChange(() => {
          this.navigateToCreatePage('链接');
        })

      MenuItem({
        startIcon: $r("sys.symbol.link"),
        content: "链接+指令"
      })
        .onChange(() => {
          this.navigateToCreatePage('链接+指令');
        })

      MenuItem({
        startIcon: $r("sys.symbol.camera"),
        content: "图片和视频"
      })
        .onChange(() => {
          this.navigateToCreatePage('图片和视频');
        })
    }
  }

  /**
   * 导航到播客创建页面，并设置初始输入类型
   */
  navigateToCreatePage(inputType: string): void {
    const params: PodcastCreatePageParams = { initialInputType: inputType };
    RouterUtils.pushPathByName(RouterMap.PODCAST_CREATE_PAGE, params);
  }

  /**
   * 播客功能卡片
   */
  @Builder
  podcastFunctionCard(title: string, description: string, onClick: () => void, disabled: boolean = false) {
    Column({ space: 8 }) {
      // 图标区域
      Column() {
        Image($r('app.media.music'))
          .width(40)
          .height(40)
          .fillColor('#ffc78cfd')
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
    .border({
      width: 1,
      color: '#fff1f1f1',
      style: BorderStyle.Solid
    })
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
      // 左侧封面图
      Column() {
        // 判断label是URL字符串还是Resource
        if (typeof song.label === 'string' && (song.label.startsWith('http') || song.label.startsWith('data:image'))) {
          // 网络图片或base64图片
          Image(song.label)
            .width(48)
            .height(48)
            .borderRadius(8)
            .objectFit(ImageFit.Cover)
            .alt($r('app.media.zhibozhong'))
            .onError(() => {
              // 如果加载失败，使用默认图标
              song.label = $r('app.media.zhibozhong');
            })
        } else {
          // 本地资源
          Image(song.label)
            .width(48)
            .height(48)
            .borderRadius(8)
            .objectFit(ImageFit.Cover)
        }
      }
      .width(48)
      .height(48)
      .margin({ left: 5 })
      .borderRadius(8)
      .backgroundColor($r('sys.color.comp_background_tertiary'))
      .justifyContent(FlexAlign.Center)
      .clip(true)

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

          // 日期放在播客标签右边
          Text(this.formatDate(this.extractTimestamp(song)))
            .fontSize(11)
            .fontColor($r('sys.color.font_secondary'))
        }
        .margin({ top: 4 })
      }
      .layoutWeight(1)
      .alignItems(HorizontalAlign.Start)
      .justifyContent(FlexAlign.Center)

      // 右侧播放按钮
      Button() {
        SymbolGlyph(
          (this.musicModel.currentSong?.id === song.id && this.musicModel.isPlay)
            ? $r('sys.symbol.pause_fill')
            : $r('sys.symbol.play_fill')
        )
          .fontSize(20)
          .fontColor([$r('sys.color.font_primary')])
      }
      .type(ButtonType.Circle)
      .backgroundColor(Color.Transparent)
      .width(40)
      .height(40)
      .onClick(() => {
        // 如果当前播放的是这个播客，则切换播放/暂停
        if (this.musicModel.currentSong?.id === song.id) {
          MediaService.getInstance().playAndPause();
        } else {
          // 否则播放这个播客
          this.playPodcast(song);
        }
      })
    }
    .width('100%')
    .padding(12)
    .borderRadius(12)
    .border({
      width: 1,
      color: '#fff1f1f1',
      style: BorderStyle.Solid
    })
    .shadow({
      radius: 14,
      color: '#1F000000',
      offsetX: 0,
      offsetY: 20
    })
    .backgroundColor($r('sys.color.comp_background_primary'))
    .margin({ bottom: index < this.recentPodcasts.length - 1 ? 8 : 0 })
    .onClick(() => {
      this.playPodcast(song);
    })
    .gesture(
      LongPressGesture({ duration: 500 }).onAction(() => {
        this.showDeleteActionSheet(song);
      })
    )
  }
}










