import { RouterMap, RouterUtils, WindowModel } from 'lib_common';
import { NavHeaderBar } from 'lib_widget';
import { podcastService, MultiRoleRequest, PodcastResult, ProgressStatus } from 'lib_api';
import { FileUtils, TextFileInfo } from '../../utils/FileUtils';
import { promptAction, AppStorageV2 } from '@kit.ArkUI';
import { PodcastResultPageParams } from './PodcastResultPage';
import { common } from '@kit.AbilityKit';

// Select 选项类型定义
interface SelectOption {
  value: string;
}

@Builder
export function PodcastMultiRolePageBuilder() {
  PodcastMultiRolePage()
}

@ComponentV2
export struct PodcastMultiRolePage {
  @Local text: string = ''; // 保留用于兼容，但优先使用textFileUrl
  @Local textFileUrl: string = ''; // 文本文件云存储URL
  @Local textFileName: string = ''; // 文本文件名
  @Local inputType: string = '文字'; // 输入类型：文字、文字+指令、公众号、公众号+指令、网页、文件、文件+指令、文字+英文指令
  @Local inputUrl: string = ''; // 输入URL（用于公众号、网页等类型）
  @Local instruction: string = ''; // 指令内容（可选）
  @Local category: string = ''; // 播客分类（可选）
  @Local roleVoiceUrls: Record<string, string> = {}; // 角色名 -> 云存储URL（必需）
  @Local roleNames: string[] = ['角色A', '角色B'];
  @Local isLoading: boolean = false;
  @Local jobId: string = '';
  @Local progressPercent: number = 0;
  @Local progressMessage: string = '';
  private progressTimer: number = 0; // 保留用于fallback轮询
  @Local windowModel: WindowModel = AppStorageV2.connect(WindowModel, () => new WindowModel())!;
  // 输入类型选项列表
  private readonly inputTypeOptions: SelectOption[] = [
    { value: '文字' },
    { value: '文字+指令' },
    { value: '公众号' },
    { value: '公众号+指令' },
    { value: '网页' },
    { value: '文件' },
    { value: '文件+指令' },
    { value: '文字+英文指令' }
  ];
  // 播客分类选项列表（已合并重复分类）
  private readonly categoryOptions: SelectOption[] = [
    { value: '商业' }, // 包含创业创新
    { value: '科技' }, // 包含科学科普
    { value: '财经' },
    { value: '新闻' },
    { value: '影视' },
    { value: '音乐' },
    { value: '文化艺术' }, // 包含读书阅读
    { value: '历史' },
    { value: '哲学思考' },
    { value: '自我成长' }, // 包含自我成长与自愈、心理学
    { value: '职场' }, // 包含职场万象、职场人际关系、求职就业
    { value: '学习' }, // 包含学习类、考题
    { value: '教育育儿' },
    { value: '情感恋爱' },
    { value: '健康养生' }, // 包含运动健身
    { value: '旅游' },
    { value: '美食' },
    { value: '生活方式' },
    { value: '娱乐' }, // 包含娱乐八卦、喜剧
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
        // 保存云存储URL（重新创建对象以触发响应式更新）
        // ArkTS不支持展开运算符，需要手动构建新对象
        // 使用Object.keys获取所有键，然后构建新对象
        const keys = Object.keys(this.roleVoiceUrls);
        const updatedRoleVoiceUrls: Record<string, string> = {};
        // 复制现有的键值对（局部变量的索引访问是允许的）
        for (let i = 0; i < keys.length; i++) {
          const key = keys[i];
          const value = this.roleVoiceUrls[key];
          updatedRoleVoiceUrls[key] = value;
        }
        // 添加新的键值对（局部变量的索引访问是允许的）
        updatedRoleVoiceUrls[roleName] = audioFileInfo.cloudUrl;
        this.roleVoiceUrls = updatedRoleVoiceUrls;
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
   * 选择播客文本文件（支持.txt、.doc、.docx、.pdf）
   */
  async selectTextFile(): Promise<void> {
    try {
      // 获取UIAbility上下文
      const context = this.getUIContext().getHostContext() as common.UIAbilityContext;

      // 检查当前输入类型，如果是文件类型
      const isFileType = ['文件', '文件+指令'].includes(this.inputType);

      // 使用云存储上传（文件必须上传到云存储）
      const textFileInfo = await FileUtils.pickTextFile(context, true);
      if (textFileInfo && textFileInfo.cloudUrl) {
        // 文件类型支持.txt、.doc、.docx、.pdf等格式，不需要特殊验证
        const fileName = textFileInfo.fileName.toLowerCase();
        const fileExtension = fileName.split('.').pop() || '';

        // 保存云存储URL
        this.textFileUrl = textFileInfo.cloudUrl;
        this.textFileName = textFileInfo.fileName;

        // 如果文件是.txt格式且已读取内容，保存到text字段（用于兼容）
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
   * 生成播客
   */
  async generatePodcast(): Promise<void> {
    // 检查文本输入（text、textFileUrl或inputUrl至少有一个）
    const hasText = this.text.trim().length > 0;
    const hasTextFile = this.textFileUrl.trim().length > 0;
    const hasInputUrl = this.inputUrl.trim().length > 0;

    // 根据输入类型验证
    const needsInputUrl = ['公众号', '公众号+指令', '网页'].includes(this.inputType);
    const needsFile = ['文件', '文件+指令'].includes(this.inputType);
    const needsText = ['文字', '文字+指令', '文字+英文指令'].includes(this.inputType);

    // 文件类型需要文件上传
    if (needsFile && !hasTextFile) {
      promptAction.showToast({
        message: '请上传文件（支持.txt、.doc、.docx、.pdf等格式）',
        duration: 2000
      });
      return;
    }

    // 公众号、网页类型需要URL
    if (needsInputUrl && !hasInputUrl && !hasTextFile) {
      promptAction.showToast({
        message: `请输入${this.inputType}类型的URL或上传文件`,
        duration: 2000
      });
      return;
    }

    // 文字类型需要文本内容
    if (needsText && !hasText) {
      promptAction.showToast({
        message: '请输入文本内容',
        duration: 2000
      });
      return;
    }

    // 通用检查：至少需要一个输入
    if (!hasText && !hasTextFile && !hasInputUrl) {
      promptAction.showToast({
        message: '请上传文件、输入文本或提供输入URL',
        duration: 2000
      });
      return;
    }

    // 检查音色文件（必须使用云存储URL）
    if (!this.roleVoiceUrls || Object.keys(this.roleVoiceUrls).length < 2) {
      promptAction.showToast({
        message: '请至少为2个角色选择音色文件',
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
      
      // 如果任务完成且有音频URL，保存并跳转
      if (progress.done && progress.audio_url) {
        this.savedAudioUrl = progress.audio_url;
        // 如果已有保存的script，可以跳转到结果页
        if (this.savedScript) {
          const resultData: PodcastResult = {
            audio_path: '',
            file_size_mb: 0,
            script: this.savedScript,
            audio_url: progress.audio_url
          };
          const params = new PodcastResultPageParams(
            resultData,
            '多角色互动播客',
            this.savedScript
          );
          RouterUtils.pushPathByName(RouterMap.PODCAST_RESULT_PAGE, params);
          this.savedAudioUrl = '';
          this.savedScript = '';
        }
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
      const request: MultiRoleRequest = {
        text: hasText ? this.text : '', // 如果使用文件或URL，text可以为空
        text_file_url: hasTextFile ? this.textFileUrl : undefined, // 文本文件云存储URL
        input_type: this.inputType, // 输入类型
        input_url: hasInputUrl ? this.inputUrl : undefined, // 输入URL
        instruction: this.instruction.trim().length > 0 ? this.instruction : undefined, // 指令内容
        role_voice_urls: this.roleVoiceUrls, // 强制使用云存储URL
        silence_interval: 800,
        category: this.category.trim().length > 0 ? this.category : undefined, // 播客分类
        job_id: this.jobId
      } as MultiRoleRequest;

      const response = await podcastService.generateMultiRolePodcast(request, onProgress);

      if (response.success && response.data) {
        // 保存 script，以便在响应失败时也能使用
        if (response.data.script) {
          this.savedScript = response.data.script;
        }
        // 如果进度中已有URL，说明已通过SSE回调处理，不再重复跳转
        if (!this.savedAudioUrl) {
        const params = new PodcastResultPageParams(
          response.data,
          '多角色互动播客',
          response.data.script
        );
        RouterUtils.pushPathByName(RouterMap.PODCAST_RESULT_PAGE, params);
        // 清除保存的 URL（已成功获取响应）
        this.savedAudioUrl = '';
        this.savedScript = '';
        }
      } else {
        // 响应失败，但如果进度中有 URL，会在SSE回调中处理
        // 这里只显示错误提示，不阻止使用进度中的 URL
        if (!this.savedAudioUrl) {
          promptAction.showToast({
            message: response.error || response.message || '生成失败，请检查进度',
            duration: 3000
          });
        }
      }
    } catch (error) {
      promptAction.showToast({
        message: `生成失败: ${error}`,
        duration: 3000
      });
    } finally {
      this.isLoading = false;
      // 停止轮询（如果SSE失败，可能启动了fallback轮询）
      this.stopProgressPolling();
      // 不立即清除进度，让用户看到最终状态
      // this.progressPercent = 0;
      // this.progressMessage = '';
      // this.jobId = '';
    }
  }

  @Local savedAudioUrl: string = '';
  @Local savedScript: string = '';

  private startProgressPolling(): void {
    if (!this.jobId || this.jobId.trim().length === 0) {
      return;
    }
    // 每 1 秒轮询一次
    this.progressTimer = setInterval(async () => {
      // 在每次轮询时检查 jobId 是否仍然有效
      if (!this.jobId || this.jobId.trim().length === 0) {
        this.stopProgressPolling();
        return;
      }
      const status = await podcastService.getProgress(this.jobId);
      if (!status) {
        return;
      }
      this.progressPercent = status.percent || 0;
      this.progressMessage = status.message || '';

      // 如果进度中包含 audio_url，保存它（即使最终响应失败也能使用）
      if (status.audio_url) {
        this.savedAudioUrl = status.audio_url;
      }

      if (status.done) {
        this.stopProgressPolling();
        // 生成完成，如果进度中有 audio_url（云存储URL），立即跳转到结果页面
        // 结果页面会自动从云存储下载音频并播放
        if (status.audio_url && !this.isLoading) {
          console.info(`[PodcastMultiRolePage] 播客生成完成，音频URL: ${status.audio_url}，跳转到结果页面`);
          // 使用进度中的云存储URL和脚本创建结果并跳转
          // AudioPlayer 会自动从云存储下载音频并播放
          const result: PodcastResult = {
            audio_url: status.audio_url, // 云存储URL，前端将从云存储下载
            audio_path: '',
            file_size_mb: 0,
            script: this.savedScript || '脚本内容请从进度中查看'
          };
          const params = new PodcastResultPageParams(
            result,
            '多角色互动播客',
            this.savedScript || ''
          );
          RouterUtils.pushPathByName(RouterMap.PODCAST_RESULT_PAGE, params);
          // 清除保存的数据
          this.savedAudioUrl = '';
          this.savedScript = '';
          // 停止加载状态（如果有）
          this.isLoading = false;
        } else if (this.savedAudioUrl && !this.isLoading) {
          // 如果进度中没有 audio_url，但之前保存了，也跳转
          console.info(`[PodcastMultiRolePage] 使用保存的音频URL: ${this.savedAudioUrl}，跳转到结果页面`);
          const result: PodcastResult = {
            audio_url: this.savedAudioUrl, // 云存储URL，前端将从云存储下载
            audio_path: '',
            file_size_mb: 0,
            script: this.savedScript || '脚本内容请从进度中查看'
          };
          const params = new PodcastResultPageParams(
            result,
            '多角色互动播客',
            this.savedScript || ''
          );
          RouterUtils.pushPathByName(RouterMap.PODCAST_RESULT_PAGE, params);
          this.savedAudioUrl = '';
          this.savedScript = '';
          this.isLoading = false;
        }
      }
    }, 1000);
  }

  private stopProgressPolling(): void {
    if (this.progressTimer) {
      clearInterval(this.progressTimer);
      this.progressTimer = 0;
    }
  }

  build() {
    NavDestination() {
      Column() {
        NavHeaderBar({
          title: '多角色互动播客'
        })

        Scroll() {
          Column({ space: 16 }) {
            // 输入类型选择
            Column({ space: 12 }) {
              Text('输入类型')
                .fontSize($r('sys.float.Subtitle_L'))
                .fontColor($r('sys.color.font_primary'))
                .fontWeight(FontWeight.Bold)
                .alignSelf(ItemAlign.Start)

              Select(this.inputTypeOptions)
                .value(this.inputType)
                .selected(0)
                .onSelect((index: number, value: string) => {
                  this.inputType = value;
                  // 根据类型清空不需要的字段
                  if (!['公众号', '公众号+指令', '网页'].includes(value)) {
                    this.inputUrl = '';
                  }
                })
                .width('100%')
            }

            // URL输入（当选择公众号、网页等类型时显示，PDF通过文件上传）
            if (['公众号', '公众号+指令', '网页'].includes(this.inputType)) {
              Column({ space: 12 }) {
                Text('输入URL')
                  .fontSize($r('sys.float.Subtitle_L'))
                  .fontColor($r('sys.color.font_primary'))
                  .fontWeight(FontWeight.Bold)
                  .alignSelf(ItemAlign.Start)

                TextInput({
                  placeholder: `请输入${this.inputType}的URL`,
                  text: $$this.inputUrl
                })
                  .type(InputType.URL)
                  .width('100%')
                  .fontSize($r('sys.float.Body_M'))
                  .padding(12)
                  .backgroundColor($r('sys.color.comp_background_tertiary'))
                  .borderRadius(8)
              }
            }

            // 指令输入（当选择包含指令的类型时显示）
            if (['文字+指令', '公众号+指令', '文件+指令', '文字+英文指令'].includes(this.inputType)) {
              Column({ space: 12 }) {
                Text('指令内容（可选）')
                  .fontSize($r('sys.float.Subtitle_L'))
                  .fontColor($r('sys.color.font_primary'))
                  .fontWeight(FontWeight.Bold)
                  .alignSelf(ItemAlign.Start)

                TextArea({
                  placeholder: '例如：生成5分钟播客、使用轻松风格等',
                  text: $$this.instruction
                })
                  .width('100%')
                  .height(80)
                  .fontSize($r('sys.float.Body_M'))
                  .padding(12)
                  .backgroundColor($r('sys.color.comp_background_tertiary'))
                  .borderRadius(8)
              }
            }

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

            // 文本输入（文字类型使用）
            if (['文字', '文字+指令', '文字+英文指令'].includes(this.inputType)) {
              Column({ space: 12 }) {
                Text('播客文本')
                  .fontSize($r('sys.float.Subtitle_L'))
                  .fontColor($r('sys.color.font_primary'))
                  .fontWeight(FontWeight.Bold)
                  .alignSelf(ItemAlign.Start)

                TextArea({
                  placeholder: '请输入播客文本内容',
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
            }

            // 文件上传（文件类型必需，其他类型可选）
            Column({ space: 12 }) {
              Text(['文件', '文件+指令'].includes(this.inputType) ?
                '播客文件（必需）' :
                '播客文件（可选，支持.txt、.doc、.docx、.pdf）')
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

                  Text(['文件', '文件+指令'].includes(this.inputType) ?
                    '支持.txt、.doc、.docx、.pdf格式，最大50MB' :
                    '支持.txt、.doc、.docx、.pdf格式，最大50MB')
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

            // 角色音色选择
            Column({ space: 12 }) {
              Text('角色音色')
                .fontSize($r('sys.float.Subtitle_L'))
                .fontColor($r('sys.color.font_primary'))
                .fontWeight(FontWeight.Bold)
                .alignSelf(ItemAlign.Start)

              ForEach(this.roleNames, (roleName: string) => {
                Row({ space: 12 }) {
                  Text(roleName)
                    .fontSize($r('sys.float.Body_M'))
                    .fontColor($r('sys.color.font_primary'))
                    .layoutWeight(1)

                  Button(this.roleVoiceUrls[roleName] ? '已选择' : '选择音色')
                    .fontSize($r('sys.float.Body_S'))
                    .type(ButtonType.Normal)
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
          .padding({
            left: 16,
            right: 16,
            top: 16,
            bottom: 16
          })
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
              (this.text.trim().length > 0 || this.textFileUrl.length > 0 || this.inputUrl.trim().length > 0) &&
              Object.keys(this.roleVoiceUrls).length >= 2)
            .onClick(() => {
              this.generatePodcast();
            })
        }
        .padding({ left: 16, right: 16, bottom: this.windowModel.windowBottomPadding + 12 })
      }
      .width('100%')
      .height('100%')
      .backgroundColor($r('sys.color.background_primary'))
    }.hideTitleBar(true)
  }
}
