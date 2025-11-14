import { RouterMap, RouterUtils, WindowModel } from 'lib_common';
import { NavHeaderBar } from 'lib_widget';
import { podcastService, CharacterRequest, CharacterInfo, PodcastResult, ProgressStatus } from 'lib_api';
import { FileUtils } from '../../utils/FileUtils';
import { AudioRecorderUtils } from '../../utils/AudioRecorderUtils';
import { promptAction, AppStorageV2 } from '@kit.ArkUI';
import { PodcastResultPageParams } from './PodcastResultPage';
import { common } from '@kit.AbilityKit';

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
  @Local textFileUrl: string = ''; // 文本文件云存储URL
  @Local textFileName: string = ''; // 文本文件名
  @Local category: string = ''; // 播客分类（可选）
  @Local characters: CharacterInfo[] = [
    { name: '角色A', voice_url: '' },
    { name: '角色B', voice_url: '' }
  ];
  @Local isLoading: boolean = false;
  @Local jobId: string = '';
  @Local progressPercent: number = 0;
  @Local progressMessage: string = '';
  @Local windowModel: WindowModel = AppStorageV2.connect(WindowModel, () => new WindowModel())!;
  @Local recordingIndex: number = -1; // 当前正在录制的角色索引，-1表示未在录制
  @Local isRecording: boolean = false; // 是否正在录制
  @Local recordingDuration: number = 0; // 录音时长（秒）
  @Local recordingTimer: number = 0; // 录音计时器
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
   * 选择文本素材文件（支持.txt、.doc、.docx、.pdf）
   */
  async selectTextFile(): Promise<void> {
    try {
      // 获取UIAbility上下文
      const context = this.getUIContext().getHostContext() as common.UIAbilityContext;

      // 使用云存储上传（文件必须上传到云存储）
      const textFileInfo = await FileUtils.pickTextFile(context, true);
      if (textFileInfo && textFileInfo.cloudUrl) {
        // 保存云存储URL
        this.textFileUrl = textFileInfo.cloudUrl;
        this.textFileName = textFileInfo.fileName;

        // 如果文件是.txt格式且已读取内容，保存到text字段（用于兼容）
        const fileName = textFileInfo.fileName.toLowerCase();
        const fileExtension = fileName.split('.').pop() || '';
        if (fileExtension === 'txt' && textFileInfo.content) {
          this.text = textFileInfo.content;
        } else {
          // PDF和Word文件不需要保存内容到text字段
          this.text = '';
        }

        // 根据文件类型显示不同的提示信息
        const fileTypeName = fileExtension === 'pdf' ? 'PDF' :
          fileExtension === 'docx' || fileExtension === 'doc' ? 'Word' :
            '文本';

        promptAction.showToast({
          message: `${fileTypeName}文件已选择并上传到云存储: ${textFileInfo.fileName}`,
          duration: 2000
        });
      } else {
        // 上传失败或未获取到URL
        promptAction.showToast({
          message: '文件上传失败，请重试',
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
   * 生成播客
   */
  async generatePodcast(): Promise<void> {
    // 检查所有角色是否都有音色URL（必须使用云存储）
    const hasAllVoices = this.characters.every(char => char.voice_url);
    if (!hasAllVoices) {
      promptAction.showToast({
        message: '请为所有角色选择音色文件',
        duration: 2000
      });
      return;
    }

    // 检查文本素材输入（text或textFileUrl至少有一个）
    const hasText = this.text.trim().length > 0;
    const hasTextFile = this.textFileUrl.trim().length > 0;

    if (!hasText && !hasTextFile) {
      promptAction.showToast({
        message: '请输入文本素材或上传文本文件',
        duration: 2000
      });
      return;
    }

    this.isLoading = true;
    // 生成一个任务ID用于SSE进度推送
    this.jobId = `${Date.now()}_${Math.floor(Math.random() * 1000000)}`;
    this.progressPercent = 1;
    this.progressMessage = '任务已提交';
    
    // SSE进度回调
    const onProgress = (progress: ProgressStatus) => {
      this.progressPercent = progress.percent || 0;
      this.progressMessage = progress.message || '';
      
      // 如果任务失败，显示错误
      if (progress.done && progress.error) {
        promptAction.showToast({
          message: progress.error || '生成失败',
          duration: 3000
        });
      }
    };
    
    try {
      const request: CharacterRequest = {
        characters: this.characters,
        text: hasText ? this.text : undefined, // 文本素材（文字输入）
        text_file_url: hasTextFile ? this.textFileUrl : undefined, // 文本文件云存储URL
        silence_interval: 300,
        category: this.category.trim().length > 0 ? this.category : undefined, // 播客分类
        background_volume: 0.3, // 背景音乐音量，默认0.3
        job_id: this.jobId
      };

      const response = await podcastService.generateCharacterPodcast(request, this.jobId, onProgress);

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

            // 文本文件上传
            Column({ space: 12 }) {
              Text('文本文件（可选，支持.txt、.doc、.docx、.pdf）')
                .fontSize($r('sys.float.Subtitle_L'))
                .fontColor($r('sys.color.font_primary'))
                .fontWeight(FontWeight.Bold)
                .alignSelf(ItemAlign.Start)

              Row({ space: 12 }) {
                Column({ space: 4 }) {
                  Text(this.textFileName || '未选择文件')
                    .fontSize($r('sys.float.Body_M'))
                    .fontColor(this.textFileUrl ? $r('sys.color.font_primary') : $r('sys.color.font_secondary'))
                    .maxLines(1)

                  Text('支持.txt、.doc、.docx、.pdf格式，最大50MB')
                    .fontSize($r('sys.float.Body_S'))
                    .fontColor($r('sys.color.font_secondary'))
                }
                .layoutWeight(1)
                .alignItems(HorizontalAlign.Start)

                Button(this.textFileUrl ? '已选择' : '选择文件')
                  .fontSize($r('sys.float.Body_S'))
                  .type(ButtonType.Normal)
                  .backgroundColor(this.textFileUrl ?
                    $r('sys.color.icon_emphasize') :
                    $r('sys.color.comp_background_tertiary'))
                  .fontColor(this.textFileUrl ?
                    $r('sys.color.font_on_primary') :
                    $r('sys.color.font_primary'))
                  .onClick(() => {
                    this.selectTextFile();
                  })
              }
              .width('100%')
              .padding(12)
              .borderRadius(8)
              .backgroundColor($r('sys.color.comp_background_tertiary'))
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
                        .type(ButtonType.Normal)
                        .backgroundColor($r('sys.color.alert'))
                        .fontColor($r('sys.color.font_on_primary'))
                        .width(32)
                        .height(32)
                        .borderRadius(16)
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
              (this.text.trim().length > 0 || this.textFileUrl.length > 0) &&
              this.characters.every(char => char.voice_url))
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

