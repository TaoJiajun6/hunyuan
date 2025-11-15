import { WindowModel } from 'lib_common';
import { NavHeaderBar } from 'lib_widget';
import { podcastService, CharacterRequest, CharacterInfo, PodcastResult, ProgressStatus } from 'lib_api';
import { FileUtils } from '../../utils/FileUtils';
import { AudioRecorderUtils } from '../../utils/AudioRecorderUtils';
import { promptAction, AppStorageV2 } from '@kit.ArkUI';
import { common } from '@kit.AbilityKit';
import { MediaService, SongItem } from 'module_musicplay';
import { CloudStorageMusicUtils, CloudAudioFile } from '../../common/CloudStorageMusicUtils';
import { Logger } from 'lib_common';

@Builder
export function PodcastCharacterPageBuilder() {
  PodcastCharacterPage()
}

// Select 选项类型定义
interface SelectOption {
  value: string;
}

@ComponentV2
export struct PodcastCharacterPage {
  @Local text: string = ''; // 文本素材（文字输入）
  @Local category: string = ''; // 播客分类（可选）
  @Local characters: CharacterInfo[] = [
    { name: '', voice_url: '' },
    { name: '', voice_url: '' }
  ];
  @Local isLoading: boolean = false;
  @Local jobId: string = '';
  @Local progressPercent: number = 0;
  @Local progressMessage: string = '';
  private targetProgress: number = 0; // 目标进度值，用于平滑动画
  private progressAnimationTimer: number = 0; // 进度条动画定时器
  @Local windowModel: WindowModel = AppStorageV2.connect(WindowModel, () => new WindowModel())!;
  @Local recordingIndex: number = -1; // 当前正在录制的角色索引，-1表示未在录制
  @Local isRecording: boolean = false; // 是否正在录制
  @Local recordingDuration: number = 0; // 录音时长（秒）
  @Local recordingTimer: number = 0; // 录音计时器
  @Local savedScript: string = ''; // 保存的对话内容
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

  aboutToDisappear(): void {
    // 页面销毁时，如果正在录制，停止录制并释放资源
    if (this.isRecording) {
      this.stopRecordingVoice();
    }
    // 清理计时器
    if (this.recordingTimer) {
      clearInterval(this.recordingTimer);
      this.recordingTimer = 0;
    }
    // 释放录制器资源
    AudioRecorderUtils.release();
  }

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
      voice_url: updates.voice_url !== undefined ? updates.voice_url : character.voice_url
    };
  }

  /**
   * 新增角色（最多4个角色）
   */
  addCharacter(): void {
    // 最多允许4个角色
    if (this.characters.length >= 4) {
      promptAction.showToast({
        message: '最多只能添加4个角色',
        duration: 2000
      });
      return;
    }
    
    // 生成新角色名称：角色A, 角色B, 角色C, 角色D
    const newCharacterName = `角色${String.fromCharCode(65 + this.characters.length)}`; // 角色A-D
    
    const newCharacter: CharacterInfo = {
      name: newCharacterName,
      voice_url: ''
    };
    // 创建新数组以触发状态更新
    const newCharacters: CharacterInfo[] = [];
    for (let i = 0; i < this.characters.length; i++) {
      newCharacters.push(this.copyCharacterInfo(this.characters[i], {}));
    }
    newCharacters.push(newCharacter);
    this.characters = newCharacters;
  }

  /**
   * 删除角色
   */
  removeCharacter(index: number): void {
    // 至少保留2个角色
    if (this.characters.length <= 2) {
      promptAction.showToast({
        message: '至少需要保留2个角色',
        duration: 2000
      });
      return;
    }
    
    // 如果正在录制要删除的角色，先停止录制
    if (this.isRecording && this.recordingIndex === index) {
      this.stopRecordingVoice();
    }
    
    // 创建新数组，移除指定索引的角色
    const newCharacters: CharacterInfo[] = [];
    for (let i = 0; i < this.characters.length; i++) {
      if (i !== index) {
        newCharacters.push(this.copyCharacterInfo(this.characters[i], {}));
      }
    }
    this.characters = newCharacters;
    
    // 如果删除的角色索引小于当前录制索引，需要调整录制索引
    if (this.recordingIndex > index) {
      this.recordingIndex = this.recordingIndex - 1;
    } else if (this.recordingIndex === index) {
      this.recordingIndex = -1;
      this.isRecording = false;
    }
  }

  /**
   * 选择角色音色文件
   */
  async selectVoiceFile(index: number): Promise<void> {
    try {
      // 获取UIAbility上下文
      const context = this.getUIContext().getHostContext() as common.UIAbilityContext;
      // 强制使用云存储上传（后端要求）
      const audioFileInfo = await FileUtils.pickAudioFile(context, true);
      if (audioFileInfo && audioFileInfo.cloudUrl) {
        // 创建新数组以触发状态更新
        const newCharacters: CharacterInfo[] = [];
        for (let i = 0; i < this.characters.length; i++) {
          if (i === index) {
            newCharacters.push(this.copyCharacterInfo(this.characters[i], { voice_url: audioFileInfo.cloudUrl }));
          } else {
            newCharacters.push(this.characters[i]);
          }
        }
        this.characters = newCharacters;
        promptAction.showToast({
          message: `${this.characters[index].name}音色已选择并上传到云存储`,
          duration: 2000
        });
      } else {
        // 上传失败或未获取到URL
        promptAction.showToast({
          message: `${this.characters[index].name}音色上传失败，请重试`,
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
   * 开始录制音色
   */
  async startRecordingVoice(index: number): Promise<void> {
    try {
      // 如果正在录制其他角色，先停止
      if (this.isRecording && this.recordingIndex !== index) {
        await this.stopRecordingVoice();
      }

      // 如果已经在录制当前角色，直接返回
      if (this.isRecording && this.recordingIndex === index) {
        return;
      }

      const context = this.getUIContext().getHostContext() as common.UIAbilityContext;
      const fileName = `voice_${this.characters[index].name}_${Date.now()}`;

      // 初始化并开始录制
      const initSuccess = await AudioRecorderUtils.initRecorder(context);
      if (!initSuccess) {
        return;
      }

      const startSuccess = await AudioRecorderUtils.startRecording(fileName, (progress) => {
        this.recordingDuration = Math.floor(progress.duration / 1000);
      });

      if (startSuccess) {
        this.recordingIndex = index;
        this.isRecording = true;
        this.recordingDuration = 0;

        // 启动计时器
        this.recordingTimer = setInterval(() => {
          this.recordingDuration++;
        }, 1000);

        promptAction.showToast({
          message: `开始录制 ${this.characters[index].name} 的音色`,
          duration: 1000
        });
      }
    } catch (error) {
      promptAction.showToast({
        message: `开始录制失败: ${error}`,
        duration: 2000
      });
    }
  }

  /**
   * 停止录制音色并上传
   */
  async stopRecordingVoice(): Promise<void> {
    if (!this.isRecording) {
      return;
    }

    try {
      // 停止计时器
      if (this.recordingTimer) {
        clearInterval(this.recordingTimer);
        this.recordingTimer = 0;
      }

      // 停止录制并上传
      const result = await AudioRecorderUtils.stopRecordingAndUpload();

      if (result && result.cloudUrl) {
        const index = this.recordingIndex;
        // 创建新数组以触发状态更新
        const newCharacters: CharacterInfo[] = [];
        for (let i = 0; i < this.characters.length; i++) {
          if (i === index) {
            newCharacters.push(this.copyCharacterInfo(this.characters[i], { voice_url: result.cloudUrl! }));
          } else {
            newCharacters.push(this.characters[i]);
          }
        }
        this.characters = newCharacters;

        promptAction.showToast({
          message: `${this.characters[index].name}音色录制完成并已上传`,
          duration: 2000
        });
      } else {
        promptAction.showToast({
          message: '录制失败或上传失败',
          duration: 2000
        });
      }
    } catch (error) {
      promptAction.showToast({
        message: `停止录制失败: ${error}`,
        duration: 2000
      });
    } finally {
      this.isRecording = false;
      this.recordingIndex = -1;
      this.recordingDuration = 0;
    }
  }

  /**
   * 格式化录制时长
   */
  formatDuration(seconds: number): string {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
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
            Logger.info('PodcastCharacterPage', `使用提供的音频URL: ${fileName}`);
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
        Logger.info('PodcastCharacterPage', `找到最新音频文件: ${audioFile.fileName}`);
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
      songItem.singer = '自定义角色播客';
      
      // 保存对话内容到 SongItem
      if (this.savedScript && this.savedScript.trim().length > 0) {
        songItem.script = this.savedScript;
        Logger.info('PodcastCharacterPage', `已保存对话内容到 SongItem，长度: ${this.savedScript.length} 字符`);
      }

      // 播放音频并显示播放页面
      MediaService.getInstance().playSong(songItem, true);
      
      promptAction.showToast({
        message: '已开始播放最新播客',
        duration: 2000
      });
    } catch (error) {
      Logger.error('PodcastCharacterPage', `获取最新音频失败: ${error}`);
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
    // 检查文本素材输入
    const hasText = this.text.trim().length > 0;
    if (!hasText) {
      promptAction.showToast({
        message: '请输入文本素材',
        duration: 2000
      });
      return;
    }

    // 检查所有角色是否都有名称
    const hasAllNames = this.characters.every(char => char.name && char.name.trim().length > 0);
    if (!hasAllNames) {
      promptAction.showToast({
        message: '请为所有角色填写名称',
        duration: 2000
      });
      return;
    }

    // 检查所有角色是否都有音色URL（必须使用云存储）
    const hasAllVoices = this.characters.every(char => char.voice_url);
    if (!hasAllVoices) {
      promptAction.showToast({
        message: '请为所有角色选择音色文件',
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
          this.savedScript = '';
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
      // 构建请求对象
      let request: CharacterRequest = {
        characters: this.characters,
        text: this.text, // 文本素材（必需）
        silence_interval: 300,
        background_volume: 0.3, // 背景音乐音量，默认0.3
        job_id: this.jobId
      };
      
      // 根据条件添加可选属性
      if (this.category.trim().length > 0) {
        request.category = this.category; // 播客分类
      }

      const response = await podcastService.generateCharacterPodcast(request, this.jobId, onProgress);

      if (response.success && response.data) {
        // 保存 script，以便在播放时使用
        if (response.data.script) {
          this.savedScript = response.data.script;
        }
        // 确保进度条到达100%
        this.targetProgress = 100;
        this.startProgressAnimation();
        // 等待一小段时间确保文件已上传到云存储，然后获取最新音频并播放
        setTimeout(() => {
          this.getLatestAudioAndPlay(response.data!.audio_url);
          this.savedScript = '';
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
          title: '自定义角色播客'
        })

        Scroll() {
          Column({ space: 16 }) {
            // 文本素材输入
            Column({ space: 12 }) {
              Text('文本素材')
                .fontSize($r('sys.float.Subtitle_L'))
                .fontColor($r('sys.color.font_primary'))
                .fontWeight(FontWeight.Bold)
                .alignSelf(ItemAlign.Start)

              TextArea({
                placeholder: '请输入文本素材内容，N个角色将基于此素材进行高度拟人化的互动对话',
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
                .constraintSize({ minHeight: 80 })
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

            // 角色配置
            Column({ space: 12 }) {
              Row() {
                Text('角色配置')
                  .fontSize($r('sys.float.Subtitle_L'))
                  .fontColor($r('sys.color.font_primary'))
                  .fontWeight(FontWeight.Bold)
                Blank()
                Button('+ 新增角色')
                  .fontSize($r('sys.float.Body_S'))
                  .type(ButtonType.Normal)
                  .borderRadius(10)
                  .backgroundColor($r('sys.color.icon_emphasize'))
                  .fontColor($r('sys.color.font_on_primary'))
                  .enabled(this.characters.length < 4)
                  .onClick(() => {
                    this.addCharacter();
                  })
              }
              .width('100%')

              ForEach(this.characters, (character: CharacterInfo, index: number) => {
                Column({ space: 8 }) {
                  Row() {
                    Text(`角色${index + 1}`)
                      .fontSize($r('sys.float.Body_M'))
                      .fontColor($r('sys.color.font_primary'))
                      .fontWeight(FontWeight.Bold)
                    Blank()
                    if (this.characters.length > 2) {
                      Button('-')
                        .fontSize($r('sys.float.Body_L'))
                        .type(ButtonType.Circle)
                        .backgroundColor(Color.Red)
                        .fontColor($r('sys.color.font_on_primary'))
                        .width(36)
                        .aspectRatio(1)
                        .enabled(!this.isRecording || this.recordingIndex !== index)
                        .onClick(() => {
                          this.removeCharacter(index);
                        })
                    }
                  }
                  .width('100%')

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
                      // 创建新数组以触发状态更新，确保每个角色对象都是新对象
                      const newCharacters: CharacterInfo[] = [];
                      for (let i = 0; i < this.characters.length; i++) {
                        if (i === index) {
                          // 为当前角色创建新对象
                          newCharacters.push(this.copyCharacterInfo(this.characters[i], { name: value }));
                        } else {
                          // 其他角色也要复制，确保数组引用完全改变
                          newCharacters.push(this.copyCharacterInfo(this.characters[i], {}));
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
                      // 创建新数组以触发状态更新，确保每个角色对象都是新对象
                      const newCharacters: CharacterInfo[] = [];
                      for (let i = 0; i < this.characters.length; i++) {
                        if (i === index) {
                          // 为当前角色创建新对象
                          newCharacters.push(this.copyCharacterInfo(this.characters[i], { identity: value }));
                        } else {
                          // 其他角色也要复制，确保数组引用完全改变
                          newCharacters.push(this.copyCharacterInfo(this.characters[i], {}));
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
                      // 创建新数组以触发状态更新，确保每个角色对象都是新对象
                      const newCharacters: CharacterInfo[] = [];
                      for (let i = 0; i < this.characters.length; i++) {
                        if (i === index) {
                          // 为当前角色创建新对象
                          newCharacters.push(this.copyCharacterInfo(this.characters[i], { personality: value }));
                        } else {
                          // 其他角色也要复制，确保数组引用完全改变
                          newCharacters.push(this.copyCharacterInfo(this.characters[i], {}));
                        }
                      }
                      this.characters = newCharacters;
                    })

                  Row({ space: 8 }) {
                    Button(character.voice_url ? '已选择音色' : '选择音色文件')
                      .layoutWeight(1)
                      .fontSize($r('sys.float.Body_S'))
                      .type(ButtonType.Normal)
                      .borderRadius(10)
                      .backgroundColor(character.voice_url ?
                        $r('sys.color.icon_emphasize') :
                        $r('sys.color.comp_background_tertiary'))
                      .fontColor(character.voice_url ?
                        $r('sys.color.font_on_primary') :
                        $r('sys.color.font_primary'))
                      .enabled(!this.isRecording || this.recordingIndex === index)
                      .onClick(() => {
                        this.selectVoiceFile(index);
                      })

                    if (this.isRecording && this.recordingIndex === index) {
                      Button(`停止录制 (${this.formatDuration(this.recordingDuration)})`)
                        .layoutWeight(1)
                        .fontSize($r('sys.float.Body_S'))
                        .type(ButtonType.Normal)
                        .borderRadius(10)
                        .backgroundColor($r('sys.color.alert'))
                        .fontColor($r('sys.color.font_on_primary'))
                        .onClick(() => {
                          this.stopRecordingVoice();
                        })
                    } else {
                      Button('录制音色')
                        .layoutWeight(1)
                        .fontSize($r('sys.float.Body_S'))
                        .type(ButtonType.Normal)
                        .borderRadius(10)
                        .backgroundColor($r('sys.color.comp_background_tertiary'))
                        .fontColor($r('sys.color.font_primary'))
                        .enabled(!this.isRecording)
                        .onClick(() => {
                          this.startRecordingVoice(index);
                        })
                    }
                  }
                  .width('100%')
                }
                .width('100%')
                .padding(12)
                .borderRadius(8)
                .backgroundColor($r('sys.color.comp_background_tertiary'))
              }, (character: CharacterInfo, index: number) => `character_${index}`)
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
            .enabled(!this.isLoading &&
              this.text.trim().length > 0 &&
              this.characters.every(char => char.name && char.name.trim().length > 0 && char.voice_url))
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

