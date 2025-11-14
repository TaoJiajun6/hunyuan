import { WindowModel } from 'lib_common';
import { NavHeaderBar } from 'lib_widget';
import { podcastService, DeepPodcastRequest, PodcastResult, ProgressStatus } from 'lib_api';
import { FileUtils } from '../../utils/FileUtils';
import { promptAction, AppStorageV2 } from '@kit.ArkUI';
import { common } from '@kit.AbilityKit';
import { MediaService, SongItem } from 'module_musicplay';
import { CloudStorageMusicUtils, CloudAudioFile } from '../../common/CloudStorageMusicUtils';
import { Logger } from 'lib_common';

// Select 选项类型定义
interface SelectOption {
  value: string;
}

@Builder
export function PodcastDeepPageBuilder() {
  PodcastDeepPage()
}

@ComponentV2
export struct PodcastDeepPage {
  @Local topic: string = '';
  @Local category: string = ''; // 播客分类（可选）
  @Local roleVoiceUrls: Record<string, string> = {}; // 角色名 -> 云存储URL（必需）
  @Local numCharacters: number = 2;
  @Local depthLevel: string = '深度';
  @Local isLoading: boolean = false;
  @Local jobId: string = '';
  @Local progressPercent: number = 0;
  @Local progressMessage: string = '';
  private targetProgress: number = 0; // 目标进度值，用于平滑动画
  private progressAnimationTimer: number = 0; // 进度条动画定时器
  @Local windowModel: WindowModel = AppStorageV2.connect(WindowModel, () => new WindowModel())!;

  readonly depthLevels: string[] = ['深度', '中等', '浅层'];
  readonly roleNames: string[] = ['角色A', '角色B', '角色C'];
  // 播客分类选项列表
  private readonly categoryOptions: SelectOption[] = [
    { value: '商业' },
    { value: '科技' },
    { value: '财经' },
    { value: '新闻' },
    { value: '影视' },
    { value: '音乐' },
    { value: '文化艺术' },
    { value: '历史' },
    { value: '哲学思考' },
    { value: '自我成长' },
    { value: '职场' },
    { value: '学习' },
    { value: '教育育儿' },
    { value: '情感恋爱' },
    { value: '健康养生' },
    { value: '旅游' },
    { value: '美食' },
    { value: '生活方式' },
    { value: '娱乐' },
    { value: '游戏电竞' },
    { value: '体育' },
    { value: '时尚美妆' },
    { value: '汽车' },
    { value: '法律' },
    { value: '宠物' }
  ];

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
   * 从云存储获取最新音频并播放
   * @param audioUrl 可选的音频URL，如果提供则优先使用
   */
  private async getLatestAudioAndPlay(audioUrl?: string): Promise<void> {
    try {
      // 显示加载提示
      promptAction.showToast({
        message: '正在获取最新音频...',
        duration: 2000
      });

      let audioFile: CloudAudioFile | null = null;

      // 如果提供了 audioUrl，尝试从 URL 提取云侧路径
      if (audioUrl) {
        const cloudPath = CloudStorageMusicUtils.extractCloudPath(audioUrl);
        if (cloudPath) {
          // 从路径中提取文件名
          const fileName = cloudPath.split('/').pop() || '';
          if (fileName) {
            audioFile = {
              fileName: fileName,
              filePath: cloudPath
            };
            Logger.info('PodcastDeepPage', `使用提供的音频URL: ${fileName}`);
          }
        }
      }

      // 如果无法从 URL 获取，则从云存储列表中选择最新的
      if (!audioFile) {
        // 从云存储获取音频文件列表
        const audioFiles = await CloudStorageMusicUtils.getAudioFileList('outputs/podcasts/');
        
        if (audioFiles.length === 0) {
          promptAction.showToast({
            message: '未找到音频文件，请稍后重试',
            duration: 3000
          });
          return;
        }

        // 按文件名排序，获取最新的音频文件（文件名通常包含时间戳）
        // 例如：podcast_1763144806.wav，数字越大越新
        const sortedFiles = audioFiles.sort((a, b) => {
          // 提取文件名中的数字部分进行比较
          const getTimestamp = (fileName: string): number => {
            const match = fileName.match(/(\d+)/);
            return match ? parseInt(match[1]) : 0;
          };
          return getTimestamp(b.fileName) - getTimestamp(a.fileName);
        });

        // 获取最新的音频文件
        audioFile = sortedFiles[0];
        Logger.info('PodcastDeepPage', `找到最新音频文件: ${audioFile.fileName}`);
      }

      // 转换为 SongItem
      const songItem = await CloudStorageMusicUtils.convertToSongItem(audioFile);
      
      if (!songItem || !songItem.src) {
        promptAction.showToast({
          message: '音频文件准备失败，请稍后重试',
          duration: 3000
        });
        return;
      }

      // 设置标题
      songItem.title = audioFile.fileName.replace(/\.[^/.]+$/, '');
      songItem.singer = '主题深度播客';

      // 播放音频并显示播放页面
      MediaService.getInstance().playSong(songItem, true);
      
      promptAction.showToast({
        message: '已开始播放最新播客',
        duration: 2000
      });
    } catch (error) {
      Logger.error('PodcastDeepPage', `获取最新音频失败: ${error}`);
      promptAction.showToast({
        message: `获取音频失败: ${error}`,
        duration: 3000
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
    // 生成一个任务ID用于SSE进度推送
    this.jobId = `${Date.now()}_${Math.floor(Math.random() * 1000000)}`;
    this.progressPercent = 1;
    this.progressMessage = '任务已提交';
    
    // 进度回调
    const onProgress = (progress: ProgressStatus) => {
      // 更新目标进度值，触发平滑动画
      this.targetProgress = progress.percent || 0;
      this.progressMessage = progress.message || '';
      // 启动平滑动画
      this.startProgressAnimation();
      
      // 如果任务完成，获取最新音频并播放
      if (progress.done && progress.audio_url) {
        this.isLoading = false;
        // 等待一小段时间确保文件已上传到云存储
        setTimeout(() => {
          this.getLatestAudioAndPlay(progress.audio_url);
        }, 1000);
      }
      
      // 如果任务失败，显示错误
      if (progress.done && progress.error) {
        promptAction.showToast({
          message: progress.error || '生成失败',
          duration: 3000
        });
      }
    };
    
    try {
      // 构建请求对象（先创建基础对象，避免结构化类型错误）
      let request: DeepPodcastRequest = {
        topic: this.topic,
        role_voice_urls: this.roleVoiceUrls, // 强制使用云存储URL
        num_characters: this.numCharacters,
        depth_level: this.depthLevel,
        silence_interval: 300,
        background_volume: 0.3, // 背景音乐音量，默认0.3
        job_id: this.jobId
      };
      
      // 根据条件添加可选属性（避免使用 undefined）
      if (this.category.trim().length > 0) {
        request.category = this.category; // 播客分类
      }

      const response = await podcastService.generateDeepPodcast(request, this.jobId, onProgress);

      if (response.success && response.data) {
        // 确保进度条到达100%
        this.targetProgress = 100;
        this.startProgressAnimation();
        // 等待一小段时间确保文件已上传到云存储，然后获取最新音频并播放
        setTimeout(() => {
          this.getLatestAudioAndPlay(response.data!.audio_url);
        }, 1000);
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

  /**
   * 启动进度条平滑动画
   * 将当前进度值平滑过渡到目标进度值
   */
  private startProgressAnimation(): void {
    // 清除之前的动画定时器
    if (this.progressAnimationTimer) {
      clearInterval(this.progressAnimationTimer);
    }

    // 如果目标进度和当前进度相同，不需要动画
    if (Math.abs(this.progressPercent - this.targetProgress) < 0.1) {
      this.progressPercent = this.targetProgress;
      return;
    }

    // 计算动画步长（每次增加约1%，约50ms更新一次，总共约5秒完成）
    const animationDuration = 5000; // 5秒完成动画
    const updateInterval = 50; // 每50ms更新一次
    const steps = animationDuration / updateInterval; // 总步数
    const stepSize = (this.targetProgress - this.progressPercent) / steps;

    // 启动动画
    this.progressAnimationTimer = setInterval(() => {
      if (Math.abs(this.progressPercent - this.targetProgress) < 0.1) {
        // 接近目标值，直接设置为目标值并停止动画
        this.progressPercent = this.targetProgress;
        if (this.progressAnimationTimer) {
          clearInterval(this.progressAnimationTimer);
          this.progressAnimationTimer = 0;
        }
      } else {
        // 继续向目标值移动
        this.progressPercent += stepSize;
        // 确保不超过目标值
        if ((stepSize > 0 && this.progressPercent > this.targetProgress) ||
            (stepSize < 0 && this.progressPercent < this.targetProgress)) {
          this.progressPercent = this.targetProgress;
          if (this.progressAnimationTimer) {
            clearInterval(this.progressAnimationTimer);
            this.progressAnimationTimer = 0;
          }
        }
      }
    }, updateInterval)  as number;
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
                placeholder: '请输入播客主题',
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
                  Text('1个角色')
                    .fontSize($r('sys.float.Body_M'))
                    .fontColor(this.numCharacters === 1 ?
                      $r('sys.color.font_on_primary') :
                      $r('sys.color.font_primary'))
                }
                .width(100)
                .height(36)
                .borderRadius(18)
                .backgroundColor(this.numCharacters === 1 ?
                  $r('sys.color.icon_emphasize') :
                  $r('sys.color.comp_background_tertiary'))
                .onClick(() => {
                  this.numCharacters = 1;
                })

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

            // 播客分类选择
            Column({ space: 12 }) {
              Text('播客分类（可选）')
                .fontSize($r('sys.float.Subtitle_L'))
                .fontColor($r('sys.color.font_primary'))
                .fontWeight(FontWeight.Bold)
                .alignSelf(ItemAlign.Start)

              Select(this.categoryOptions)
                .value(this.category || '')
                .onSelect((index: number, value: string) => {
                  this.category = value;
                })
                .width('100%')
            }

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
                    .borderRadius(10)
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
          // 进度条与提示
          if (this.isLoading) {
            Column({ space: 6 }) {
              Progress({ value: this.progressPercent })
                .style({
                  strokeWidth: 12
                })
                .width('100%')
              Text(this.progressMessage || '生成中...')
                .fontSize($r('sys.float.Body_S'))
                .fontColor($r('sys.color.font_secondary'))
                .alignSelf(ItemAlign.Start)
            }
            .width('100%')
            .padding({ left: 16, right: 16, bottom: 8 })
          }
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

