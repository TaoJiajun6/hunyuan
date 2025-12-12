/*
 * Copyright (c) 2024 Huawei Device Co., Ltd.
 * Licensed under the Apache License, Version 2.0 (the 'License');
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an 'AS IS' BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { WindowModel, RouterUtils, RouterMap } from 'lib_common';
import { NavHeaderBar } from 'lib_widget';
import {
  podcastService,
  MultiRoleRequest,
  CharacterRequest,
  DeepPodcastRequest,
  CharacterInfo,
  PodcastResult,
  ProgressStatus,
  VoiceInfo
} from 'lib_api';
import { FileUtils, TextFileInfo } from '../../utils/FileUtils';
import { AudioRecorderUtils } from '../../utils/AudioRecorderUtils';
import { promptAction, AppStorageV2 } from '@kit.ArkUI';
import { common } from '@kit.AbilityKit';
import { MediaService, SongItem } from 'module_musicplay';
import { CloudStorageMusicUtils, CloudAudioFile } from '../../common/CloudStorageMusicUtils';
import { Logger } from 'lib_common';

// 播客类型枚举
enum PodcastType {
  MULTI_ROLE = 'multi_role', // 多角色互动播客
  CHARACTER = 'character', // 自定义角色播客
  DEEP = 'deep' // 主题深度播客
}

// 输入类型枚举
enum InputType {
  TEXT = '文字',
  TEXT_INSTRUCTION = '文字+指令',
  FILE = '文件',
  FILE_INSTRUCTION = '文件+指令',
  LINK = '链接',
  LINK_INSTRUCTION = '链接+指令',
  IMAGE_VIDEO = '图片和视频'
}

// 引导步骤枚举
enum WizardStep {
  STEP1_MATERIAL = 1, // 步骤1：上传素材
  STEP2_TYPE = 2, // 步骤2：选择播客类型
  STEP3_CONFIG = 3 // 步骤3：填写配置
}

// Select 选项类型定义
interface SelectOption {
  value: string;
}

// 按钮颜色数组常量
const BUTTON_COLORS = ['#ffb3e0', '#ffc78cfd', '#a0e5ff'];
const BUTTON_COLORS_4 = ['#ffb3e0', '#ffc78cfd', '#a0e5ff', '#ffb3e0'];

// 预设音色信息接口
interface PresetVoice {
  id: string;
  name: string;
  gender: 'male' | 'female';
  url?: string;
}

/**
 * 页面参数接口
 */
interface PodcastCreatePageParams {
  initialInputType?: string;
}

@Builder
export function PodcastCreatePageBuilder() {
  PodcastCreatePage()
}

@ComponentV2
export struct PodcastCreatePage {
  // ========== 引导步骤 ==========
  @Local currentStep: WizardStep = WizardStep.STEP1_MATERIAL; // 当前步骤
  // 当前选择的播客类型
  @Local currentPodcastType: PodcastType | null = null;
  // ========== 通用字段 ==========
  @Local text: string = ''; // 文本内容
  @Local textFileUrls: string[] = []; // 文本文件云存储URL列表
  @Local textFileNames: string[] = []; // 文本文件名列表
  @Local inputUrl: string = ''; // 输入URL（用于链接等类型）
  @Local instruction: string = ''; // 指令内容（可选）
  @Local category: string = ''; // 播客分类（可选）
  @Local currentInputType: InputType | null = null; // 当前输入类型
  @Local showInputTypeMenu: boolean = false; // 是否显示输入类型菜单
  // ========== 多角色互动播客字段 ==========
  @Local roleVoiceUrls: Record<string, string> = {}; // 角色名 -> 云存储URL
  @Local roleNames: string[] = ['角色A', '角色B'];
  // ========== 自定义角色播客字段 ==========
  @Local characters: CharacterInfo[] = [
    { name: '', voice_url: '' },
    { name: '', voice_url: '' }
  ];
  @Local recordingIndex: number = -1; // 当前正在录制的角色索引
  @Local isRecording: boolean = false; // 是否正在录制
  @Local recordingDuration: number = 0; // 录音时长（秒）
  @Local recordingTimer: number = 0; // 录音计时器
  // ========== 主题深度播客字段 ==========
  @Local topic: string = ''; // 播客主题
  @Local numCharacters: number = 2; // 角色数量
  @Local depthLevel: string = '深度'; // 深度级别
  // ========== 通用状态 ==========
  @Local isLoading: boolean = false;
  @Local jobId: string = '';
  @Local progressPercent: number = 0;
  @Local progressMessage: string = '';
  @Local savedAudioUrl: string = '';
  @Local savedScript: string = '';
  @Local windowModel: WindowModel = AppStorageV2.connect(WindowModel, () => new WindowModel())!;
  // ========== 音色选择相关 ==========
  @Local showVoiceSelector: boolean = false; // 是否显示音色选择器
  @Local currentSelectingRole: string = ''; // 当前正在选择音色的角色名
  @Local playingVoiceId: string = ''; // 正在播放预览的音色ID
  @Local voiceList: VoiceInfo[] = []; // 从API获取的音色列表
  // ========== 分类选择相关 ==========
  @Local showCategoryPicker: boolean = false; // 是否显示分类选择器
  // 播客分类选项列表
  private readonly categoryOptions: SelectOption[] = [
    { value: '社会文化与历史' },
    { value: '音乐' },
    { value: '影视' },
    { value: '书' },
    { value: '喜剧/脱口秀' },
    { value: '艺术' },
    { value: '宗教与灵修' },
    { value: '科学与科技' },
    { value: '时尚与美妆' },
    { value: '健康、健身与养身' },
    { value: '育儿与家庭' },
    { value: '情感' },
    { value: '生活' },
    { value: '体育运动' },
    { value: '休闲娱乐与爱好' },
    { value: '商业与财经' },
    { value: '新闻' },
    { value: '职场万象' },
    { value: '自我成长与自愈' },
    { value: '学术研究' }
  ];
  // 输入类型选项列表
  private readonly inputTypeOptions: SelectOption[] = [
    { value: InputType.TEXT },
    { value: InputType.TEXT_INSTRUCTION },
    { value: InputType.FILE },
    { value: InputType.FILE_INSTRUCTION },
    { value: InputType.LINK },
    { value: InputType.LINK_INSTRUCTION },
    { value: InputType.IMAGE_VIDEO }
  ];
  // 深度级别选项
  readonly depthLevels: string[] = ['深度', '中等', '浅层'];
  // 预设音色列表
  private readonly presetVoices: PresetVoice[] = [
    { id: 'xiaoman', name: '晓曼', gender: 'female' },
    { id: 'gaoqing', name: '高晴', gender: 'female' },
    { id: 'zhiboxuejie', name: '直播雪姐', gender: 'female' },
    { id: 'guodong', name: '国栋', gender: 'male' },
    { id: 'yuanye', name: '原野', gender: 'male' },
    { id: 'suzhe', name: '苏哲', gender: 'male' },
    { id: 'zimo', name: '子墨', gender: 'male' },
    { id: 'taiwan_nv', name: '台湾女声', gender: 'female' }
  ];
  @Local routeParams: PodcastCreatePageParams | null = null;

  aboutToAppear(): void {
    // 从路由参数获取初始输入类型
    const params = RouterUtils.getParamByName(RouterMap.PODCAST_CREATE_PAGE) as PodcastCreatePageParams | null;
    if (params && params.initialInputType) {
      this.routeParams = params;
      // 将字符串转换为 InputType 枚举
      const inputTypeStr = params.initialInputType;
      if (inputTypeStr === '文字') {
        this.currentInputType = InputType.TEXT;
      } else if (inputTypeStr === '文字+指令') {
        this.currentInputType = InputType.TEXT_INSTRUCTION;
      } else if (inputTypeStr === '文件') {
        this.currentInputType = InputType.FILE;
      } else if (inputTypeStr === '文件+指令') {
        this.currentInputType = InputType.FILE_INSTRUCTION;
      } else if (inputTypeStr === '链接') {
        this.currentInputType = InputType.LINK;
      } else if (inputTypeStr === '链接+指令') {
        this.currentInputType = InputType.LINK_INSTRUCTION;
      } else if (inputTypeStr === '图片和视频') {
        this.currentInputType = InputType.IMAGE_VIDEO;
      }
      // 如果已经选择了输入类型，保持在步骤1，直接显示对应的输入区域
      // 不再自动跳转到步骤2
    }
  }

  /**
   * 下一步
   */
  nextStep(): void {
    if (this.currentStep === WizardStep.STEP1_MATERIAL) {
      // 验证素材是否已上传
      const hasMaterial = this.text.trim().length > 0 ||
        this.textFileUrls.length > 0 ||
        this.inputUrl.trim().length > 0;
      if (!hasMaterial) {
        promptAction.showToast({
          message: '请先上传素材',
          duration: 2000
        });
        return;
      }
      this.currentStep = WizardStep.STEP2_TYPE;
    } else if (this.currentStep === WizardStep.STEP2_TYPE) {
      // 验证是否选择了播客类型
      if (!this.currentPodcastType) {
        promptAction.showToast({
          message: '请选择播客类型',
          duration: 2000
        });
        return;
      }
      this.currentStep = WizardStep.STEP3_CONFIG;
    } else if (this.currentStep === WizardStep.STEP3_CONFIG) {
      // 最后一步，开始生成
      this.generatePodcast();
    }
  }

  /**
   * 上一步
   */
  previousStep(): void {
    if (this.currentStep === WizardStep.STEP2_TYPE) {
      this.currentStep = WizardStep.STEP1_MATERIAL;
    } else if (this.currentStep === WizardStep.STEP3_CONFIG) {
      this.currentStep = WizardStep.STEP2_TYPE;
    }
  }

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
   * 切换播客类型
   */
  switchPodcastType(type: PodcastType): void {
    this.currentPodcastType = type;
    // 切换类型时重置相关字段
    this.resetFieldsForType(type);
  }

  /**
   * 根据类型重置字段
   */
  resetFieldsForType(type: PodcastType): void {
    // 根据不同类型重置特定字段
    if (type === PodcastType.CHARACTER) {
      // 自定义角色播客：重置角色列表
      this.characters = [
        { name: '', voice_url: '' },
        { name: '', voice_url: '' }
      ];
    } else if (type === PodcastType.DEEP) {
      // 主题深度播客：重置主题和角色数量
      this.topic = '';
      this.numCharacters = 2;
      this.depthLevel = '深度';
    } else {
      // 多角色互动播客：重置角色音色
      this.roleVoiceUrls = {};
      this.roleNames = ['角色A', '角色B'];
    }
  }

  /**
   * 选择输入类型
   */
  selectInputType(type: InputType): void {
    this.currentInputType = type;
    this.showInputTypeMenu = false;

    // 根据输入类型重置相关字段
    if (type === InputType.TEXT || type === InputType.TEXT_INSTRUCTION) {
      this.textFileUrls = [];
      this.textFileNames = [];
      this.inputUrl = '';
    } else if (type === InputType.FILE || type === InputType.FILE_INSTRUCTION) {
      this.text = '';
      this.inputUrl = '';
    } else if (type === InputType.LINK || type === InputType.LINK_INSTRUCTION) {
      this.text = '';
      this.textFileUrls = [];
      this.textFileNames = [];
    }
  }

  /**
   * 选择文本文件
   */
  async selectTextFile(): Promise<void> {
    try {
      const context = this.getUIContext().getHostContext() as common.UIAbilityContext;
      const textFileInfos = await FileUtils.pickTextFiles(context, true);

      if (textFileInfos && textFileInfos.length > 0) {
        const newUrls: string[] = [];
        const newNames: string[] = [];
        let combinedText = '';

        for (let i = 0; i < textFileInfos.length; i++) {
          const textFileInfo = textFileInfos[i];
          if (textFileInfo && textFileInfo.cloudUrl) {
            newUrls.push(textFileInfo.cloudUrl);
            newNames.push(textFileInfo.fileName);

            // 如果是txt文件，合并内容
            const fileName = textFileInfo.fileName.toLowerCase();
            const fileExtension = fileName.split('.').pop() || '';
            if (fileExtension === 'txt' && textFileInfo.content) {
              if (combinedText) {
                combinedText += '\n\n';
              }
              combinedText += textFileInfo.content;
            }
          }
        }

        if (newUrls.length > 0) {
          this.textFileUrls = newUrls;
          this.textFileNames = newNames;
          if (combinedText) {
            this.text = combinedText;
          }
          promptAction.showToast({
            message: `已选择 ${newUrls.length} 个文件`,
            duration: 2000
          });
        }
      }
    } catch (error) {
      promptAction.showToast({
        message: `选择文件失败: ${error}`,
        duration: 2000
      });
    }
  }

  /**
   * 选择图片或视频文件
   */
  async selectImageVideoFile(): Promise<void> {
    try {
      const context = this.getUIContext().getHostContext() as common.UIAbilityContext;
      // TODO: 实现图片和视频文件选择
      promptAction.showToast({
        message: '图片和视频功能开发中',
        duration: 2000
      });
    } catch (error) {
      promptAction.showToast({
        message: `选择文件失败: ${error}`,
        duration: 2000
      });
    }
  }

  /**
   * 粘贴链接
   */
  pasteLink(): void {
    // TODO: 实现粘贴链接功能
    promptAction.showToast({
      message: '请手动输入链接',
      duration: 2000
    });
  }

  /**
   * 打开音色选择器
   */
  openVoiceSelector(roleName: string): void {
    this.currentSelectingRole = roleName;
    this.showVoiceSelector = true;
  }

  /**
   * 关闭音色选择器
   */
  closeVoiceSelector(): void {
    this.showVoiceSelector = false;
    this.currentSelectingRole = '';
    this.playingVoiceId = '';
  }

  /**
   * 选择预设音色
   */
  selectPresetVoice(voiceId: string): void {
    if (!this.currentSelectingRole) {
      return;
    }

    // TODO: 从后端获取预设音色的URL，这里先用空字符串占位
    // 实际应该调用API获取预设音色的云存储URL
    const voiceUrl = `preset://${voiceId}`; // 使用预设音色标识符

    const updatedRoleVoiceUrls: Record<string, string> = {};
    const keys = Object.keys(this.roleVoiceUrls);
    for (let i = 0; i < keys.length; i++) {
      updatedRoleVoiceUrls[keys[i]] = this.roleVoiceUrls[keys[i]];
    }
    updatedRoleVoiceUrls[this.currentSelectingRole] = voiceUrl;
    this.roleVoiceUrls = updatedRoleVoiceUrls;

    promptAction.showToast({
      message: `${this.currentSelectingRole}已选择${this.getVoiceName(voiceId)}`,
      duration: 2000
    });

    this.closeVoiceSelector();
  }

  /**
   * 上传自定义音色文件
   */
  async uploadCustomVoice(): Promise<void> {
    try {
      const context = this.getUIContext().getHostContext() as common.UIAbilityContext;
      const audioFileInfo = await FileUtils.pickAudioFile(context, true);

      if (audioFileInfo && audioFileInfo.cloudUrl && this.currentSelectingRole) {
        const updatedRoleVoiceUrls: Record<string, string> = {};
        const keys = Object.keys(this.roleVoiceUrls);
        for (let i = 0; i < keys.length; i++) {
          updatedRoleVoiceUrls[keys[i]] = this.roleVoiceUrls[keys[i]];
        }
        updatedRoleVoiceUrls[this.currentSelectingRole] = audioFileInfo.cloudUrl;
        this.roleVoiceUrls = updatedRoleVoiceUrls;

        promptAction.showToast({
          message: `${this.currentSelectingRole}自定义音色已上传`,
          duration: 2000
        });

        this.closeVoiceSelector();
      }
    } catch (error) {
      promptAction.showToast({
        message: `上传失败: ${error}`,
        duration: 2000
      });
    }
  }

  /**
   * 播放音色预览
   */
  playVoicePreview(voiceId: string): void {
    // TODO: 实现音色预览播放
    this.playingVoiceId = voiceId;
    promptAction.showToast({
      message: `播放 ${this.getVoiceName(voiceId)} 预览`,
      duration: 1500
    });

    // 模拟播放，3秒后停止
    setTimeout(() => {
      this.playingVoiceId = '';
    }, 3000);
  }

  /**
   * 获取音色名称
   */
  getVoiceName(voiceId: string): string {
    const voice = this.presetVoices.find(v => v.id === voiceId);
    return voice ? voice.name : '';
  }

  /**
   * 选择角色音色文件（多角色互动播客和主题深度播客）
   * 现在改为打开音色选择器
   */
  async selectVoiceFile(roleName: string): Promise<void> {
    this.openVoiceSelector(roleName);
  }

  /**
   * 选择角色音色文件（自定义角色播客）
   */
  async selectCharacterVoiceFile(index: number): Promise<void> {
    try {
      const context = this.getUIContext().getHostContext() as common.UIAbilityContext;
      const audioFileInfo = await FileUtils.pickAudioFile(context, true);

      if (audioFileInfo && audioFileInfo.cloudUrl) {
        const updatedCharacters: CharacterInfo[] = [];
        for (let i = 0; i < this.characters.length; i++) {
          if (i === index) {
            const char = this.characters[i];
            updatedCharacters.push({
              name: char.name,
              identity: char.identity,
              personality: char.personality,
              catchphrase: char.catchphrase,
              speaking_style: char.speaking_style,
              relationship: char.relationship,
              voice_url: audioFileInfo.cloudUrl
            });
          } else {
            updatedCharacters.push(this.characters[i]);
          }
        }
        this.characters = updatedCharacters;

        promptAction.showToast({
          message: `${this.characters[index].name || '角色'}音色已选择`,
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
   * 录制音色（自定义角色播客）
   */
  async recordVoice(index: number): Promise<void> {
    if (this.isRecording && this.recordingIndex === index) {
      // 如果正在录制同一个角色，则停止录制
      this.stopRecordingVoice();
      return;
    }

    // 如果正在录制其他角色，先停止
    if (this.isRecording) {
      this.stopRecordingVoice();
    }

    try {
      const context = this.getUIContext().getHostContext() as common.UIAbilityContext;
      const fileName = `voice_${this.characters[index].name || 'role'}_${Date.now()}`;

      // 初始化录制器
      const initSuccess = await AudioRecorderUtils.initRecorder(context);
      if (!initSuccess) {
        promptAction.showToast({
          message: '初始化录制器失败',
          duration: 2000
        });
        return;
      }

      // 开始录制
      const startSuccess = await AudioRecorderUtils.startRecording(fileName, (progress) => {
        this.recordingDuration = Math.floor(progress.duration / 1000);
      });

      if (startSuccess) {
        this.isRecording = true;
        this.recordingIndex = index;
        this.recordingDuration = 0;

        // 开始计时
        this.recordingTimer = setInterval(() => {
          this.recordingDuration++;
        }, 1000);

        promptAction.showToast({
          message: '开始录制，再次点击停止',
          duration: 2000
        });
      } else {
        promptAction.showToast({
          message: '开始录制失败',
          duration: 2000
        });
      }
    } catch (error) {
      promptAction.showToast({
        message: `录制失败: ${error}`,
        duration: 2000
      });
      this.isRecording = false;
      this.recordingIndex = -1;
    }
  }

  /**
   * 停止录制音色
   */
  async stopRecordingVoice(): Promise<void> {
    if (!this.isRecording) {
      return;
    }

    try {
      const audioFileInfo = await AudioRecorderUtils.stopRecording();

      if (audioFileInfo && audioFileInfo.cloudUrl && this.recordingIndex >= 0) {
        const cloudUrl = audioFileInfo.cloudUrl;
        if (cloudUrl) {
          const updatedCharacters: CharacterInfo[] = [];
          for (let i = 0; i < this.characters.length; i++) {
            if (i === this.recordingIndex) {
              const char = this.characters[i];
              updatedCharacters.push({
                name: char.name,
                identity: char.identity,
                personality: char.personality,
                catchphrase: char.catchphrase,
                speaking_style: char.speaking_style,
                relationship: char.relationship,
                voice_url: cloudUrl
              });
            } else {
              updatedCharacters.push(this.characters[i]);
            }
          }
          this.characters = updatedCharacters;

          promptAction.showToast({
            message: '录制完成并已上传',
            duration: 2000
          });
        }
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

      if (this.recordingTimer) {
        clearInterval(this.recordingTimer);
        this.recordingTimer = 0;
      }
    }
  }

  /**
   * 新增角色（自定义角色播客）
   */
  addCharacter(): void {
    if (this.characters.length >= 4) {
      promptAction.showToast({
        message: '最多只能添加4个角色',
        duration: 2000
      });
      return;
    }

    const newCharacterName = `角色${String.fromCharCode(65 + this.characters.length)}`;
    const newCharacter: CharacterInfo = {
      name: newCharacterName,
      voice_url: ''
    };

    const newCharacters: CharacterInfo[] = [];
    for (let i = 0; i < this.characters.length; i++) {
      const char = this.characters[i];
      newCharacters.push({
        name: char.name,
        identity: char.identity,
        personality: char.personality,
        catchphrase: char.catchphrase,
        speaking_style: char.speaking_style,
        relationship: char.relationship,
        voice_url: char.voice_url
      });
    }
    newCharacters.push(newCharacter);
    this.characters = newCharacters;
  }

  /**
   * 删除角色（自定义角色播客）
   */
  removeCharacter(index: number): void {
    if (this.characters.length <= 2) {
      promptAction.showToast({
        message: '至少需要保留2个角色',
        duration: 2000
      });
      return;
    }

    if (this.isRecording && this.recordingIndex === index) {
      this.stopRecordingVoice();
    }

    const newCharacters: CharacterInfo[] = [];
    for (let i = 0; i < this.characters.length; i++) {
      if (i !== index) {
        const char = this.characters[i];
        newCharacters.push({
          name: char.name,
          identity: char.identity,
          personality: char.personality,
          catchphrase: char.catchphrase,
          speaking_style: char.speaking_style,
          relationship: char.relationship,
          voice_url: char.voice_url
        });
      }
    }
    this.characters = newCharacters;
  }

  /**
   * 更新角色信息（自定义角色播客）
   */
  updateCharacter(index: number, field: keyof CharacterInfo, value: string): void {
    const updatedCharacters: CharacterInfo[] = [];
    for (let i = 0; i < this.characters.length; i++) {
      if (i === index) {
        const char = this.characters[i];
        const updatedChar: CharacterInfo = {
          name: char.name,
          identity: char.identity,
          personality: char.personality,
          catchphrase: char.catchphrase,
          speaking_style: char.speaking_style,
          relationship: char.relationship,
          voice_url: char.voice_url
        };
        if (field === 'name') {
          updatedChar.name = value;
        } else if (field === 'identity') {
          updatedChar.identity = value;
        } else if (field === 'personality') {
          updatedChar.personality = value;
        } else if (field === 'catchphrase') {
          updatedChar.catchphrase = value;
        } else if (field === 'speaking_style') {
          updatedChar.speaking_style = value;
        } else if (field === 'relationship') {
          updatedChar.relationship = value;
        } else if (field === 'voice_url') {
          updatedChar.voice_url = value;
        }
        updatedCharacters.push(updatedChar);
      } else {
        updatedCharacters.push(this.characters[i]);
      }
    }
    this.characters = updatedCharacters;
  }

  /**
   * 生成播客
   */
  async generatePodcast(): Promise<void> {
    // 验证输入
    if (!this.validateInput()) {
      return;
    }

    this.isLoading = true;
    this.jobId = `${Date.now()}_${Math.floor(Math.random() * 1000000)}`;
    this.progressPercent = 1;
    this.progressMessage = '任务已提交';

    const onProgress = (progress: ProgressStatus) => {
      const targetPercent = progress.percent || 0;
      const maxIncrement = 10;
      if (targetPercent > this.progressPercent) {
        const increment = Math.min(targetPercent - this.progressPercent, maxIncrement);
        this.progressPercent = Math.min(this.progressPercent + increment, 100);
      } else {
        this.progressPercent = targetPercent;
      }
      this.progressMessage = progress.message || '';

      if (progress.done && progress.audio_url) {
        this.savedAudioUrl = progress.audio_url;
        this.isLoading = false;
        setTimeout(() => {
          this.getLatestAudioAndPlay(this.savedAudioUrl);
          this.savedAudioUrl = '';
          this.savedScript = '';
        }, 1000);
      }

      if (progress.done && progress.error) {
        promptAction.showToast({
          message: progress.error || '生成失败',
          duration: 3000
        });
      }
    };

    try {
      if (this.currentPodcastType === PodcastType.MULTI_ROLE) {
        await this.generateMultiRolePodcast(onProgress);
      } else if (this.currentPodcastType === PodcastType.CHARACTER) {
        await this.generateCharacterPodcast(onProgress);
      } else if (this.currentPodcastType === PodcastType.DEEP) {
        await this.generateDeepPodcast(onProgress);
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
   * 验证输入
   */
  validateInput(): boolean {
    if (this.currentPodcastType === PodcastType.MULTI_ROLE) {
      // 多角色互动播客验证
      const hasText = this.text.trim().length > 0;
      const hasTextFile = this.textFileUrls.length > 0;
      const hasInputUrl = this.inputUrl.trim().length > 0;

      const needsInputUrl =
        this.currentInputType !== null && [InputType.LINK, InputType.LINK_INSTRUCTION].includes(this.currentInputType);
      const needsFile =
        this.currentInputType !== null && [InputType.FILE, InputType.FILE_INSTRUCTION].includes(this.currentInputType);
      const needsText =
        this.currentInputType !== null && [InputType.TEXT, InputType.TEXT_INSTRUCTION].includes(this.currentInputType);

      if (needsFile && !hasTextFile) {
        promptAction.showToast({
          message: '请上传文件',
          duration: 2000
        });
        return false;
      }

      if (needsInputUrl && !hasInputUrl && !hasTextFile) {
        promptAction.showToast({
          message: '请输入URL或上传文件',
          duration: 2000
        });
        return false;
      }

      if (needsText && !hasText) {
        promptAction.showToast({
          message: '请输入文本内容',
          duration: 2000
        });
        return false;
      }

      if (!hasText && !hasTextFile && !hasInputUrl) {
        promptAction.showToast({
          message: '请提供输入内容',
          duration: 2000
        });
        return false;
      }

      if (!this.roleVoiceUrls || Object.keys(this.roleVoiceUrls).length < 2) {
        promptAction.showToast({
          message: '请至少为2个角色选择音色文件',
          duration: 2000
        });
        return false;
      }
    } else if (this.currentPodcastType === PodcastType.CHARACTER) {
      // 自定义角色播客验证
      if (!this.text.trim()) {
        promptAction.showToast({
          message: '请输入文本素材',
          duration: 2000
        });
        return false;
      }

      if (this.characters.length < 2) {
        promptAction.showToast({
          message: '至少需要2个角色',
          duration: 2000
        });
        return false;
      }

      for (let i = 0; i < this.characters.length; i++) {
        if (!this.characters[i].name || !this.characters[i].name.trim()) {
          promptAction.showToast({
            message: `请为角色${i + 1}设置名称`,
            duration: 2000
          });
          return false;
        }

        if (!this.characters[i].voice_url) {
          promptAction.showToast({
            message: `请为${this.characters[i].name}选择或录制音色`,
            duration: 2000
          });
          return false;
        }
      }
    } else if (this.currentPodcastType === PodcastType.DEEP) {
      // 主题深度播客验证
      if (!this.topic.trim()) {
        promptAction.showToast({
          message: '请输入播客主题',
          duration: 2000
        });
        return false;
      }

      const requiredRoles = this.numCharacters === 2 ? ['角色A', '角色B'] : ['角色A', '角色B', '角色C'];
      for (const roleName of requiredRoles) {
        if (!this.roleVoiceUrls[roleName]) {
          promptAction.showToast({
            message: `请为${roleName}选择音色文件`,
            duration: 2000
          });
          return false;
        }
      }
    }

    return true;
  }

  /**
   * 生成多角色互动播客
   */
  async generateMultiRolePodcast(onProgress: (progress: ProgressStatus) => void): Promise<void> {
    const hasText = this.text.trim().length > 0;
    const hasTextFile = this.textFileUrls.length > 0;
    const hasInputUrl = this.inputUrl.trim().length > 0;

    // 将输入类型转换为API需要的格式
    let inputTypeStr = '文字';
    if (this.currentInputType === InputType.TEXT_INSTRUCTION) {
      inputTypeStr = '文字+指令';
    } else if (this.currentInputType === InputType.FILE) {
      inputTypeStr = '文件';
    } else if (this.currentInputType === InputType.FILE_INSTRUCTION) {
      inputTypeStr = '文件+指令';
    } else if (this.currentInputType === InputType.LINK) {
      inputTypeStr = '网页';
    } else if (this.currentInputType === InputType.LINK_INSTRUCTION) {
      inputTypeStr = '网页+指令';
    }

    const request: MultiRoleRequest = {
      text: hasText ? this.text : '',
      text_file_url: hasTextFile ? (this.textFileUrls.length === 1 ? this.textFileUrls[0] : this.textFileUrls) :
        undefined,
      input_type: inputTypeStr,
      input_url: hasInputUrl ? this.inputUrl : undefined,
      instruction: this.instruction.trim().length > 0 ? this.instruction : undefined,
      role_voice_urls: this.roleVoiceUrls,
      silence_interval: 800,
      category: this.category.trim().length > 0 ? this.category : undefined,
      job_id: this.jobId
    } as MultiRoleRequest;

    const response = await podcastService.generateMultiRolePodcast(request, onProgress);

    if (response.success && response.data) {
      const data = response.data;
      if (data.script) {
        this.savedScript = data.script;
      }
      if (!this.savedAudioUrl && data.audio_url) {
        this.savedAudioUrl = data.audio_url;
        setTimeout(() => {
          this.getLatestAudioAndPlay(this.savedAudioUrl);
          this.savedAudioUrl = '';
          this.savedScript = '';
        }, 1000);
      }
    } else {
      if (!this.savedAudioUrl) {
        promptAction.showToast({
          message: response.error || response.message || '生成失败',
          duration: 3000
        });
      }
    }
  }

  /**
   * 生成自定义角色播客
   */
  async generateCharacterPodcast(onProgress: (progress: ProgressStatus) => void): Promise<void> {
    const request: CharacterRequest = {
      text: this.text,
      category: this.category.trim().length > 0 ? this.category : undefined,
      characters: this.characters,
      job_id: this.jobId
    } as CharacterRequest;

    const response = await podcastService.generateCharacterPodcast(request, this.jobId, onProgress);

    if (response.success && response.data) {
      const data = response.data;
      if (data.script) {
        this.savedScript = data.script;
      }
      if (!this.savedAudioUrl && data.audio_url) {
        this.savedAudioUrl = data.audio_url;
        setTimeout(() => {
          this.getLatestAudioAndPlay(this.savedAudioUrl);
          this.savedAudioUrl = '';
          this.savedScript = '';
        }, 1000);
      }
    } else {
      if (!this.savedAudioUrl) {
        promptAction.showToast({
          message: response.error || response.message || '生成失败',
          duration: 3000
        });
      }
    }
  }

  /**
   * 生成主题深度播客
   */
  async generateDeepPodcast(onProgress: (progress: ProgressStatus) => void): Promise<void> {
    const request: DeepPodcastRequest = {
      topic: this.topic,
      category: this.category.trim().length > 0 ? this.category : undefined,
      num_characters: this.numCharacters,
      depth_level: this.depthLevel,
      role_voice_urls: this.roleVoiceUrls,
      job_id: this.jobId
    } as DeepPodcastRequest;

    const response = await podcastService.generateDeepPodcast(request, this.jobId, onProgress);

    if (response.success && response.data) {
      const data = response.data;
      if (data.script) {
        this.savedScript = data.script;
      }
      if (!this.savedAudioUrl && data.audio_url) {
        this.savedAudioUrl = data.audio_url;
        setTimeout(() => {
          this.getLatestAudioAndPlay(this.savedAudioUrl);
          this.savedAudioUrl = '';
          this.savedScript = '';
        }, 1000);
      }
    } else {
      if (!this.savedAudioUrl) {
        promptAction.showToast({
          message: response.error || response.message || '生成失败',
          duration: 3000
        });
      }
    }
  }

  /**
   * 从云存储获取最新音频并播放
   */
  private async getLatestAudioAndPlay(audioUrl?: string): Promise<void> {
    try {
      promptAction.showToast({
        message: '正在获取最新音频...',
        duration: 2000
      });

      let audioFile: CloudAudioFile | null = null;

      if (audioUrl) {
        const cloudPath = CloudStorageMusicUtils.extractCloudPath(audioUrl);
        if (cloudPath) {
          const fileName = cloudPath.split('/').pop() || '';
          if (fileName) {
            audioFile = {
              fileName: fileName,
              filePath: cloudPath
            };
            Logger.info('PodcastCreatePage', `使用提供的音频URL: ${fileName}`);
          }
        }
      }

      if (!audioFile) {
        const audioFiles = await CloudStorageMusicUtils.getAudioFileList('outputs/podcasts/');

        if (audioFiles.length === 0) {
          promptAction.showToast({
            message: '未找到音频文件，请稍后重试',
            duration: 3000
          });
          return;
        }

        const sortedFiles = audioFiles.sort((a, b) => {
          const getTimestamp = (fileName: string): number => {
            const match = fileName.match(/(\d+)/);
            return match ? parseInt(match[1]) : 0;
          };
          return getTimestamp(b.fileName) - getTimestamp(a.fileName);
        });

        audioFile = sortedFiles[0];
      }

      if (audioFile) {
        const songItem = await CloudStorageMusicUtils.convertToSongItem(audioFile);
        if (songItem) {
          MediaService.getInstance().playSong(songItem);
          promptAction.showToast({
            message: '开始播放生成的播客',
            duration: 2000
          });
        }
      }
    } catch (error) {
      Logger.error('PodcastCreatePage', `获取音频失败: ${error}`);
      promptAction.showToast({
        message: `获取音频失败: ${error}`,
        duration: 3000
      });
    }
  }

  build() {
    NavDestination() {
      Column() {
        // 顶部导航栏
        NavHeaderBar({
          title: 'AI播客',
          showBackBtn: true
        })

        // 主内容区域（可滚动）
        Scroll() {
          Column({ space: 24 }) {
            // 根据当前步骤显示不同的内容
            if (this.currentStep === WizardStep.STEP1_MATERIAL) {
              this.buildStep1Material()
            } else if (this.currentStep === WizardStep.STEP2_TYPE) {
              this.buildStep2Type()
            } else if (this.currentStep === WizardStep.STEP3_CONFIG) {
              this.buildStep3Config()
            }
          }
          .width('100%')
          .padding({
            left: 20,
            right: 20,
            top: 24,
            bottom: 24
          })
        }
        .layoutWeight(1)
        .width('100%')
        .backgroundColor('#FAFAFA')

        // 底部按钮区域（优化设计）
        Row({ space: 14 }) {
          // 如果不是第一步，显示"上一步"按钮
          if (this.currentStep !== WizardStep.STEP1_MATERIAL) {
            Button('上一步')
              .type(ButtonType.Normal)
              .layoutWeight(1)
              .height(52)
              .linearGradient({
                angle: 90,
                colors: [
                  ['#ffb3e0', 0.0],
                  ['#ffc78cfd', 0.6],
                  ['#a0e5ff', 1.0]
                ]
              })
              .fontColor('#FFFFFF')
              .fontSize(17)
              .fontWeight(FontWeight.Bold)
              .borderRadius(28)
              .shadow({
                radius: 14,
                color: '#1F000000',
                offsetX: 0,
                offsetY: 20
              })
              .enabled(!this.isLoading)
              .opacity(this.isLoading ? 0.6 : 1.0)
              .onClick(() => this.previousStep())
          }

          // 下一步/开始生成按钮（优化设计）
          Button(this.currentStep === WizardStep.STEP3_CONFIG ? '开始生成' : '下一步')
            .type(ButtonType.Normal)
            .layoutWeight(1)
            .height(52)
            .linearGradient({
              angle: 90,
              colors: [
                ['#ffb3e0', 0.0],
                ['#ffc78cfd', 0.6],
                ['#a0e5ff', 1.0]
              ]
            })
            .fontColor('#FFFFFF')
            .fontSize(17)
            .fontWeight(FontWeight.Bold)
            .borderRadius(28)
            .shadow({
              radius: 14,
              color: '#1F000000',
              offsetX: 0,
              offsetY: 20
            })
            .enabled(!this.isLoading)
            .opacity(this.isLoading ? 0.6 : 1.0)
            .onClick(() => this.nextStep())
        }
        .width('92%')
        .margin({ bottom: 20 })
      }
      .width('100%')
      .height('100%')
      .backgroundColor('#F8F8F8')
    }
    .hideTitleBar(true)
  }

  @Builder
  buildInputArea() {
    Column({ space: 12 }) {
      // 输入类型选择（带加号按钮）
      Row() {
        Text('输入类型')
          .fontSize(16)
          .fontWeight(FontWeight.Bold)
          .fontColor('#000000')

        Blank()

        // 加号按钮，显示输入类型菜单
        Button() {
          Row({ space: 4 }) {
            Text(this.currentInputType)
              .fontSize(14)
              .fontColor('#000000')
            Image($r('sys.media.ohos_ic_public_arrow_down'))
              .width(16)
              .height(16)
          }
        }
        .type(ButtonType.Normal)
        .backgroundColor('#F5F5F5')
        .borderRadius(8)
        .padding({
          left: 12,
          right: 12,
          top: 8,
          bottom: 8
        })
        .onClick(() => {
          this.showInputTypeMenu = !this.showInputTypeMenu;
        })
      }
      .width('100%')
      .alignItems(VerticalAlign.Center)

      // 输入类型菜单
      if (this.showInputTypeMenu) {
        Column() {
          ForEach(this.inputTypeOptions, (option: SelectOption) => {
            Row() {
              Text(option.value)
                .fontSize(14)
                .fontColor('#000000')
            }
            .width('100%')
            .height(40)
            .padding({ left: 12, right: 12 })
            .onClick(() => {
              this.selectInputType(option.value as InputType);
            })
          })
        }
        .width('100%')
        .backgroundColor('#FFFFFF')
        .borderRadius(8)
        .shadow({
          radius: 8,
          color: '#1F000000',
          offsetX: 0,
          offsetY: 2
        })
        .margin({ top: 4 })
      }

      // 输入内容区域
      if (this.currentInputType === InputType.TEXT || this.currentInputType === InputType.TEXT_INSTRUCTION) {
        // 文本输入
        TextArea({
          placeholder: '请输入播客文本内容',
          text: $$this.text
        })
          .width('100%')
          .height(140)
          .backgroundColor('#FFFFFF')
          .borderRadius(16)
          .border({
            width: 1,
            color: '#E0E0E0',
            style: BorderStyle.Solid
          })
          .shadow({
            radius: 14,
            color: '#1F000000',
            offsetX: 0,
            offsetY: 20
          })
          .onChange((value: string) => {
            this.text = value;
          })

        // 如果是文字+指令，显示指令输入框
        if (this.currentInputType === InputType.TEXT_INSTRUCTION) {
          TextArea({
            placeholder: '请输入指令内容（可选）',
            text: $$this.instruction
          })
            .width('100%')
            .height(100)
            .backgroundColor('#FFFFFF')
            .borderRadius(16)
            .border({
              width: 1,
              color: '#E0E0E0',
              style: BorderStyle.Solid
            })
            .shadow({
              radius: 14,
              color: '#1F000000',
              offsetX: 0,
              offsetY: 20
            })
            .onChange((value: string) => {
              this.instruction = value;
            })
        }
      } else if (this.currentInputType === InputType.FILE || this.currentInputType === InputType.FILE_INSTRUCTION) {
        // 文件上传
        Column({ space: 8 }) {
          if (this.textFileNames.length > 0) {
            ForEach(this.textFileNames, (fileName: string, index: number) => {
              Row() {
                Text(fileName)
                  .fontSize(14)
                  .fontColor('#000000')
                  .layoutWeight(1)
                Button('删除')
                  .type(ButtonType.Normal)
                  .fontSize(12)
                  .onClick(() => {
                    const newUrls: string[] = [];
                    const newNames: string[] = [];
                    for (let i = 0; i < this.textFileUrls.length; i++) {
                      if (i !== index) {
                        newUrls.push(this.textFileUrls[i]);
                        newNames.push(this.textFileNames[i]);
                      }
                    }
                    this.textFileUrls = newUrls;
                    this.textFileNames = newNames;
                  })
              }
              .width('100%')
              .padding({
                left: 16,
                right: 16,
                top: 12,
                bottom: 12
              })
              .backgroundColor('#FFFFFF')
              .borderRadius(16)
              .border({
                width: 1,
                color: '#E0E0E0',
                style: BorderStyle.Solid
              })
              .shadow({
                radius: 14,
                color: '#1F000000',
                offsetX: 0,
                offsetY: 20
              })
            })
          }

          Button('选择文件')
            .type(ButtonType.Normal)
            .width('100%')
            .height(52)
            .backgroundColor('#FFFFFF')
            .fontColor('#333333')
            .fontSize(16)
            .fontWeight(FontWeight.Medium)
            .borderRadius(28)
            .border({
              width: 1,
              color: '#E0E0E0',
              style: BorderStyle.Solid
            })
            .shadow({
              radius: 14,
              color: '#1F000000',
              offsetX: 0,
              offsetY: 20
            })
            .onClick(() => this.selectTextFile())
        }
        .width('100%')

        // 如果是文件+指令，显示指令输入框
        if (this.currentInputType === InputType.FILE_INSTRUCTION) {
          TextArea({
            placeholder: '请输入指令内容（可选）',
            text: $$this.instruction
          })
            .width('100%')
            .height(100)
            .backgroundColor('#FFFFFF')
            .borderRadius(16)
            .border({
              width: 1,
              color: '#E0E0E0',
              style: BorderStyle.Solid
            })
            .shadow({
              radius: 14,
              color: '#1F000000',
              offsetX: 0,
              offsetY: 20
            })
            .onChange((value: string) => {
              this.instruction = value;
            })
        }
      } else if (this.currentInputType === InputType.LINK || this.currentInputType === InputType.LINK_INSTRUCTION) {
        // 链接输入
        Row({ space: 10 }) {
          TextInput({
            placeholder: '请输入链接',
            text: this.inputUrl
          })
            .layoutWeight(1)
            .height(48)
            .backgroundColor('#FFFFFF')
            .borderRadius(16)
            .border({
              width: 1,
              color: '#E0E0E0',
              style: BorderStyle.Solid
            })
            .shadow({
              radius: 14,
              color: '#1F000000',
              offsetX: 0,
              offsetY: 20
            })
            .onChange((value: string) => {
              this.inputUrl = value;
            })

        }
        .width('100%')

        // 如果是链接+指令，显示指令输入框
        if (this.currentInputType === InputType.LINK_INSTRUCTION) {
          TextArea({
            placeholder: '请输入指令内容（可选）',
            text: $$this.instruction
          })
            .width('100%')
            .height(100)
            .backgroundColor('#FFFFFF')
            .borderRadius(16)
            .border({
              width: 1,
              color: '#E0E0E0',
              style: BorderStyle.Solid
            })
            .shadow({
              radius: 14,
              color: '#1F000000',
              offsetX: 0,
              offsetY: 20
            })
            .onChange((value: string) => {
              this.instruction = value;
            })
        }
      } else if (this.currentInputType === InputType.IMAGE_VIDEO) {
        // 图片和视频上传
        Button('选择图片或视频')
          .type(ButtonType.Normal)
          .width('100%')
          .height(52)
          .backgroundColor('#FFFFFF')
          .fontColor('#333333')
          .fontSize(16)
          .fontWeight(FontWeight.Medium)
          .borderRadius(28)
          .border({
            width: 1,
            color: '#E0E0E0',
            style: BorderStyle.Solid
          })
          .shadow({
            radius: 14,
            color: '#1F000000',
            offsetX: 0,
            offsetY: 20
          })
          .onClick(() => this.selectImageVideoFile())
      }
    }
    .width('100%')
    .padding({ top: 16, bottom: 16 })
  }

  @Builder
  buildMultiRoleConfig() {
    Column({ space: 20 }) {
      // 配置卡片
      Column({ space: 16 }) {
        Row() {
          Image($r("sys.symbol.mic_fill"))
            .width(20)
            .height(20)
            .fillColor('#ffc78cfd')
          Text('角色音色')
            .fontSize(18)
            .fontWeight(FontWeight.Bold)
            .fontColor('#1A1A1A')
          Blank()
        }
        .width('100%')

        // 角色音色选择列表
        Column({ space: 12 }) {
          ForEach(this.roleNames, (roleName: string, index: number) => {
            Row({ space: 12 }) {
              // 角色图标
              Column() {
                Text(roleName.charAt(roleName.length - 1))
                  .fontSize(18)
                  .fontWeight(FontWeight.Bold)
                  .fontColor('#FFFFFF')
              }
              .width(44)
              .height(44)
              .borderRadius(22)
              .backgroundColor(BUTTON_COLORS[index % 3])
              .justifyContent(FlexAlign.Center)
              .alignItems(HorizontalAlign.Center)

              Column({ space: 4 }) {
                Text(roleName)
                  .fontSize(16)
                  .fontWeight(FontWeight.Medium)
                  .fontColor('#333333')
                if (this.roleVoiceUrls[roleName]) {
                  Text(this.getSelectedVoiceName(roleName))
                    .fontSize(13)
                    .fontColor('#999999')
                }
              }
              .layoutWeight(1)
              .alignItems(HorizontalAlign.Start)
              .justifyContent(FlexAlign.Center)

              Button(this.roleVoiceUrls[roleName] ? '已选择' : '选择音色')
                .type(ButtonType.Normal)
                .backgroundColor(this.roleVoiceUrls[roleName] ? BUTTON_COLORS[index % 3] : '#FFFFFF')
                .fontColor(this.roleVoiceUrls[roleName] ? '#FFFFFF' : '#333333')
                .fontSize(15)
                .fontWeight(this.roleVoiceUrls[roleName] ? FontWeight.Bold : FontWeight.Medium)
                .borderRadius(20)
                .border({
                  width: this.roleVoiceUrls[roleName] ? 0 : 1,
                  color: '#E0E0E0',
                  style: BorderStyle.Solid
                })
                .padding({ left: 20, right: 20 })
                .height(40)
                .shadow({
                  radius: 14,
                  color: '#1F000000',
                  offsetX: 0,
                  offsetY: 20
                })
                .bindSheet(this.showVoiceSelector, this.voiceSelectorSheet(), {
                  height: '80%',
                  dragBar: true,
                  showClose: true,
                  title: { title: '选择音色' }
                })
                .onClick(() => this.openVoiceSelector(roleName))
            }
            .width('100%')
            .padding({
              left: 16,
              right: 16,
              top: 12,
              bottom: 12
            })
            .backgroundColor('#FAFAFA')
            .borderRadius(16)
          })
        }
        .width('100%')
      }
      .width('100%')
      .padding({
        top: 20,
        bottom: 20,
        left: 20,
        right: 20
      })
      .backgroundColor('#FFFFFF')
      .borderRadius(20)
      .shadow({
        radius: 14,
        color: '#1F000000',
        offsetX: 0,
        offsetY: 20
      })
    }
    .width('100%')
  }

  @Builder
  buildCharacterConfig() {
    Column({ space: 20 }) {
      Row() {
        Text('角色配置')
          .fontSize(18)
          .fontWeight(FontWeight.Bold)
          .fontColor('#1A1A1A')

        Blank()

        Button('新增角色')
          .type(ButtonType.Normal)
          .linearGradient({
            angle: 90,
            colors: [
              ['#ffb3e0', 0.0],
              ['#ffc78cfd', 0.6],
              ['#a0e5ff', 1.0]
            ]
          })
          .fontColor('#FFFFFF')
          .fontSize(14)
          .fontWeight(FontWeight.Bold)
          .borderRadius(24)
          .padding({
            left: 16,
            right: 16,
            top: 8,
            bottom: 8
          })
          .shadow({
            radius: 14,
            color: '#1F000000',
            offsetX: 0,
            offsetY: 20
          })
          .onClick(() => this.addCharacter())
      }
      .width('100%')

      ForEach(this.characters, (character: CharacterInfo, index: number) => {
        Column({ space: 16 }) {
          Row({ space: 12 }) {
            // 角色编号图标
            Column() {
              Text(`${index + 1}`)
                .fontSize(18)
                .fontWeight(FontWeight.Bold)
                .fontColor('#FFFFFF')
            }
            .width(44)
            .height(44)
            .borderRadius(22)
            .backgroundColor(BUTTON_COLORS_4[index % 4])
            .justifyContent(FlexAlign.Center)
            .alignItems(HorizontalAlign.Center)

            Column({ space: 4 }) {
              Text(`角色 ${index + 1}`)
                .fontSize(18)
                .fontWeight(FontWeight.Bold)
                .fontColor('#1A1A1A')
              if (character.name) {
                Text(character.name)
                  .fontSize(14)
                  .fontColor('#999999')
              }
            }
            .layoutWeight(1)
            .alignItems(HorizontalAlign.Start)
            .justifyContent(FlexAlign.Center)
          }
          .width('100%')

          TextInput({
            placeholder: '角色名称',
            text: character.name || ''
          })
            .width('100%')
            .height(52)
            .backgroundColor('#FFFFFF')
            .borderRadius(16)
            .border({
              width: 1,
              color: '#E0E0E0',
              style: BorderStyle.Solid
            })
            .shadow({
              radius: 14,
              color: '#1F000000',
              offsetX: 0,
              offsetY: 20
            })
            .onChange((value: string) => {
              this.updateCharacter(index, 'name', value);
            })

          TextInput({
            placeholder: '身份/职业（可选）',
            text: character.identity || ''
          })
            .width('100%')
            .height(52)
            .backgroundColor('#FFFFFF')
            .borderRadius(16)
            .border({
              width: 1,
              color: '#E0E0E0',
              style: BorderStyle.Solid
            })
            .shadow({
              radius: 14,
              color: '#1F000000',
              offsetX: 0,
              offsetY: 20
            })
            .onChange((value: string) => {
              this.updateCharacter(index, 'identity', value);
            })

          TextInput({
            placeholder: '核心性格（可选）',
            text: character.personality || ''
          })
            .width('100%')
            .height(52)
            .backgroundColor('#FFFFFF')
            .borderRadius(16)
            .border({
              width: 1,
              color: '#E0E0E0',
              style: BorderStyle.Solid
            })
            .shadow({
              radius: 14,
              color: '#1F000000',
              offsetX: 0,
              offsetY: 20
            })
            .onChange((value: string) => {
              this.updateCharacter(index, 'personality', value);
            })

          Row({ space: 10 }) {
            Button('选择音色文件')
              .type(ButtonType.Normal)
              .layoutWeight(1)
              .height(44)
              .backgroundColor(this.characters[index].voice_url ? BUTTON_COLORS_4[index % 4] : '#FFFFFF')
              .fontColor(this.characters[index].voice_url ? '#FFFFFF' : '#666666')
              .fontSize(14)
              .fontWeight(this.characters[index].voice_url ? FontWeight.Bold : FontWeight.Regular)
              .borderRadius(24)
              .border({
                width: this.characters[index].voice_url ? 0 : 1,
                color: '#E0E0E0',
                style: BorderStyle.Solid
              })
              .shadow({
                radius: 14,
                color: '#1F000000',
                offsetX: 0,
                offsetY: 20
              })
              .onClick(() => this.selectCharacterVoiceFile(index))

            Button(this.isRecording && this.recordingIndex === index ? `停止录制 (${this.recordingDuration}s)` :
              '录制音色')
              .type(ButtonType.Normal)
              .layoutWeight(1)
              .height(44)
              .backgroundColor(this.isRecording && this.recordingIndex === index ? '#FF5722' : '#FFFFFF')
              .fontColor(this.isRecording && this.recordingIndex === index ? '#FFFFFF' : '#666666')
              .fontSize(14)
              .fontWeight(this.isRecording && this.recordingIndex === index ? FontWeight.Bold : FontWeight.Regular)
              .borderRadius(24)
              .border({
                width: this.isRecording && this.recordingIndex === index ? 0 : 1,
                color: '#E0E0E0',
                style: BorderStyle.Solid
              })
              .shadow({
                radius: 14,
                color: '#1F000000',
                offsetX: 0,
                offsetY: 20
              })
              .onClick(() => this.recordVoice(index))
          }
          .width('100%')

          if (this.characters.length > 2) {
            Button('删除角色')
              .type(ButtonType.Normal)
              .width('100%')
              .height(44)
              .backgroundColor('#FFFFFF')
              .fontColor('#F44336')
              .fontSize(14)
              .borderRadius(24)
              .border({
                width: 1,
                color: '#FFCDD2',
                style: BorderStyle.Solid
              })
              .shadow({
                radius: 14,
                color: '#1F000000',
                offsetX: 0,
                offsetY: 20
              })
              .onClick(() => this.removeCharacter(index))
          }
        }
        .width('100%')
        .padding({
          top: 20,
          bottom: 20,
          left: 20,
          right: 20
        })
        .backgroundColor('#FFFFFF')
        .borderRadius(20)
        .shadow({
          radius: 14,
          color: '#1F000000',
          offsetX: 0,
          offsetY: 20
        })
      })
    }
    .width('100%')
  }

  @Builder
  buildDeepConfig() {
    Column({ space: 20 }) {
      // 播客主题卡片
      Column({ space: 16 }) {
        Row() {
          Image($r("sys.symbol.lightbulb_fill"))
            .width(20)
            .height(20)
            .fillColor('#ffc78cfd')
          Text('播客主题')
            .fontSize(18)
            .fontWeight(FontWeight.Bold)
            .fontColor('#1A1A1A')
          Blank()
        }
        .width('100%')

        TextInput({
          placeholder: '请输入播客主题，例如：人工智能的未来...',
          text: this.topic
        })
          .width('100%')
          .height(52)
          .backgroundColor('#FAFAFA')
          .borderRadius(16)
          .border({
            width: 1,
            color: '#E0E0E0',
            style: BorderStyle.Solid
          })
          .fontSize(15)
          .padding({ left: 16, right: 16 })
          .onChange((value: string) => {
            this.topic = value;
          })
      }
      .width('100%')
      .padding({
        top: 20,
        bottom: 20,
        left: 20,
        right: 20
      })
      .backgroundColor('#FFFFFF')
      .borderRadius(20)
      .shadow({
        radius: 14,
        color: '#1F000000',
        offsetX: 0,
        offsetY: 20
      })

      // 角色数量卡片
      Column({ space: 16 }) {
        Row() {
          Image($r("sys.symbol.person_2_fill"))
            .width(20)
            .height(20)
            .fillColor('#a0e5ff')
          Text('角色数量')
            .fontSize(18)
            .fontWeight(FontWeight.Bold)
            .fontColor('#1A1A1A')
          Blank()
        }
        .width('100%')

        Row({ space: 10 }) {
          Button('1个角色')
            .type(ButtonType.Normal)
            .layoutWeight(1)
            .height(52)
            .backgroundColor(this.numCharacters === 1 ? BUTTON_COLORS[0] : '#FFFFFF')
            .fontColor(this.numCharacters === 1 ? '#FFFFFF' : '#333333')
            .fontSize(15)
            .fontWeight(this.numCharacters === 1 ? FontWeight.Bold : FontWeight.Regular)
            .borderRadius(28)
            .border({
              width: this.numCharacters === 1 ? 0 : 1,
              color: '#E0E0E0',
              style: BorderStyle.Solid
            })
            .shadow(this.numCharacters === 1 ? {
              radius: 14,
              color: '#1F000000',
              offsetX: 0,
              offsetY: 20
            } : {
              radius: 14,
              color: '#1F000000',
              offsetX: 0,
              offsetY: 20
            })
            .onClick(() => {
              this.numCharacters = 1;
              this.roleNames = ['角色A'];
            })

          Button('2个角色')
            .type(ButtonType.Normal)
            .layoutWeight(1)
            .height(52)
            .backgroundColor(this.numCharacters === 2 ? BUTTON_COLORS[1] : '#FFFFFF')
            .fontColor(this.numCharacters === 2 ? '#FFFFFF' : '#333333')
            .fontSize(15)
            .fontWeight(this.numCharacters === 2 ? FontWeight.Bold : FontWeight.Regular)
            .borderRadius(28)
            .border({
              width: this.numCharacters === 2 ? 0 : 1,
              color: '#E0E0E0',
              style: BorderStyle.Solid
            })
            .shadow(this.numCharacters === 2 ? {
              radius: 14,
              color: '#1F000000',
              offsetX: 0,
              offsetY: 20
            } : {
              radius: 14,
              color: '#1F000000',
              offsetX: 0,
              offsetY: 20
            })
            .onClick(() => {
              this.numCharacters = 2;
              this.roleNames = ['角色A', '角色B'];
            })

          Button('3个角色')
            .type(ButtonType.Normal)
            .layoutWeight(1)
            .height(52)
            .backgroundColor(this.numCharacters === 3 ? BUTTON_COLORS[2] : '#FFFFFF')
            .fontColor(this.numCharacters === 3 ? '#FFFFFF' : '#333333')
            .fontSize(15)
            .fontWeight(this.numCharacters === 3 ? FontWeight.Bold : FontWeight.Regular)
            .borderRadius(28)
            .border({
              width: this.numCharacters === 3 ? 0 : 1,
              color: '#E0E0E0',
              style: BorderStyle.Solid
            })
            .shadow(this.numCharacters === 3 ? {
              radius: 14,
              color: '#1F000000',
              offsetX: 0,
              offsetY: 20
            } : {
              radius: 14,
              color: '#1F000000',
              offsetX: 0,
              offsetY: 20
            })
            .onClick(() => {
              this.numCharacters = 3;
              this.roleNames = ['角色A', '角色B', '角色C'];
            })
        }
        .width('100%')
      }
      .width('100%')
      .padding({
        top: 20,
        bottom: 20,
        left: 20,
        right: 20
      })
      .backgroundColor('#FFFFFF')
      .borderRadius(20)
      .shadow({
        radius: 14,
        color: '#1F000000',
        offsetX: 0,
        offsetY: 20
      })

      // 深度级别卡片
      Column({ space: 16 }) {
        Row() {
          Image($r("sys.symbol.doc"))
            .width(20)
            .height(20)
            .fillColor('#ffb3e0')
          Text('深度级别')
            .fontSize(18)
            .fontWeight(FontWeight.Bold)
            .fontColor('#1A1A1A')
          Blank()
        }
        .width('100%')

        Row({ space: 10 }) {
          ForEach(this.depthLevels, (level: string, index: number) => {
            Button(level)
              .type(ButtonType.Normal)
              .layoutWeight(1)
              .height(52)
              .backgroundColor(this.depthLevel === level ? BUTTON_COLORS[index] : '#FFFFFF')
              .fontColor(this.depthLevel === level ? '#FFFFFF' : '#333333')
              .fontSize(15)
              .fontWeight(this.depthLevel === level ? FontWeight.Bold : FontWeight.Regular)
              .borderRadius(28)
              .border({
                width: this.depthLevel === level ? 0 : 1,
                color: '#E0E0E0',
                style: BorderStyle.Solid
              })
              .shadow({
                radius: 14,
                color: '#1F000000',
                offsetX: 0,
                offsetY: 20
              })
              .onClick(() => {
                this.depthLevel = level;
              })
          })
        }
        .width('100%')
      }
      .width('100%')

      // 角色音色卡片
      Column({ space: 16 }) {
        Row() {
          Image($r("sys.symbol.mic_fill"))
            .width(20)
            .height(20)
            .fillColor('#a0e5ff')
          Text('角色音色')
            .fontSize(18)
            .fontWeight(FontWeight.Bold)
            .fontColor('#1A1A1A')
          Blank()
        }
        .width('100%')

        Column({ space: 12 }) {
          ForEach(this.roleNames, (roleName: string, index: number) => {
            Row({ space: 12 }) {
              // 角色图标
              Column() {
                Text(roleName.charAt(roleName.length - 1))
                  .fontSize(18)
                  .fontWeight(FontWeight.Bold)
                  .fontColor('#FFFFFF')
              }
              .width(44)
              .height(44)
              .borderRadius(22)
              .backgroundColor(BUTTON_COLORS[index % 3])
              .justifyContent(FlexAlign.Center)
              .alignItems(HorizontalAlign.Center)

              Column({ space: 4 }) {
                Text(roleName)
                  .fontSize(16)
                  .fontWeight(FontWeight.Medium)
                  .fontColor('#333333')
                if (this.roleVoiceUrls[roleName]) {
                  Text('音色已选择')
                    .fontSize(13)
                    .fontColor('#999999')
                }
              }
              .layoutWeight(1)
              .alignItems(HorizontalAlign.Start)
              .justifyContent(FlexAlign.Center)

              Button(this.roleVoiceUrls[roleName] ? '已选择' : '选择音色')
                .type(ButtonType.Normal)
                .backgroundColor(this.roleVoiceUrls[roleName] ? BUTTON_COLORS[index % 3] : '#FFFFFF')
                .fontColor(this.roleVoiceUrls[roleName] ? '#FFFFFF' : '#666666')
                .fontSize(14)
                .fontWeight(this.roleVoiceUrls[roleName] ? FontWeight.Bold : FontWeight.Medium)
                .borderRadius(20)
                .border({
                  width: this.roleVoiceUrls[roleName] ? 0 : 1,
                  color: '#E0E0E0',
                  style: BorderStyle.Solid
                })
                .padding({ left: 20, right: 20 })
                .height(40)
                .shadow({
                  radius: 14,
                  color: '#1F000000',
                  offsetX: 0,
                  offsetY: 20
                })
                .onClick(() => this.selectVoiceFile(roleName))
            }
            .width('100%')
            .padding({
              left: 16,
              right: 16,
              top: 12,
              bottom: 12
            })
            .backgroundColor('#FAFAFA')
            .borderRadius(16)
          })
        }
        .width('100%')
      }
      .width('100%')
      .padding({
        top: 20,
        bottom: 20,
        left: 20,
        right: 20
      })
      .backgroundColor('#FFFFFF')
      .borderRadius(20)
      .shadow({
        radius: 14,
        color: '#1F000000',
        offsetX: 0,
        offsetY: 20
      })
    }
    .width('100%')
  }

  @Builder
  buildCategorySelector() {
    Column({ space: 16 }) {
      Row() {
        Image($r("sys.symbol.doc_text"))
          .width(20)
          .height(20)
          .fillColor('#ffc78cfd')
        Text('播客分类（可选）')
          .fontSize(18)
          .fontWeight(FontWeight.Bold)
          .fontColor('#1A1A1A')
        Blank()
      }
      .width('100%')

      // 分类选择输入框
      Row({ space: 12 }) {
        TextInput({
          placeholder: '请选择播客分类',
          text: $$this.category
        })
          .layoutWeight(1)
          .height(52)
          .backgroundColor('#FAFAFA')
          .fontSize(15)
          .fontColor(this.category ? '#333333' : '#999999')
          .borderRadius(16)
          .border({
            width: 1,
            color: '#E0E0E0',
            style: BorderStyle.Solid
          })
          .padding({ left: 16, right: 16 })
          .enabled(false)
          .bindSheet($$this.showCategoryPicker, this.categoryPickerSheet(), {
            height: '50%',
            dragBar: true,
            showClose: true,
            title: { title: '选择播客分类' }
          })
          .onClick(() => {
            // 显示分类选择器
            this.openCategoryPicker();
          })

        Button() {
          Image($r("sys.symbol.chevron_down"))
            .width(20)
            .height(20)
            .fillColor('#FFFFFF')
        }
        .type(ButtonType.Normal)
        .width(52)
        .height(52)
        .linearGradient({
          angle: 90,
          colors: [
            ['#ffb3e0', 0.0],
            ['#ffc78cfd', 0.6],
            ['#a0e5ff', 1.0]
          ]
        })
        .borderRadius(16)
        .shadow({
          radius: 14,
          color: '#1F000000',
          offsetX: 0,
          offsetY: 20
        })
        .onClick(() => {
          this.openCategoryPicker();
        })
      }
      .width('100%')
    }
    .width('100%')
    .padding({
      top: 20,
      bottom: 20,
      left: 20,
      right: 20
    })
    .backgroundColor('#FFFFFF')
    .borderRadius(20)
    .shadow({
      radius: 14,
      color: '#1F000000',
      offsetX: 0,
      offsetY: 20
    })
  }

  /**
   * 显示分类选择器
   */
  openCategoryPicker(): void {
    this.showCategoryPicker = true;
  }

  /**
   * 关闭分类选择器
   */
  closeCategoryPicker(): void {
    this.showCategoryPicker = false;
  }

  /**
   * 选择分类
   */
  selectCategory(categoryValue: string): void {
    this.category = categoryValue;
    this.closeCategoryPicker();
  }

  /**
   * 获取分类选中项的索引
   */
  getCategorySelectedIndex(): number {
    if (!this.category) {
      return -1;
    }
    for (let i = 0; i < this.categoryOptions.length; i++) {
      if (this.categoryOptions[i].value === this.category) {
        return i;
      }
    }
    return -1;
  }

  /**
   * 步骤1：上传素材
   */
  @Builder
  buildStep1Material() {
    Column({ space: 24 }) {
      // 卡片 - 显示问题或已选择的类型
      if (this.currentInputType) {
        Column() {
          Stack({ alignContent: Alignment.TopEnd }) {
            // 主内容
            Column({ space: 8 }) {
              Row({ space: 12 }) {

                Column({ space: 5 }) {
                  Text('当前素材类型')
                    .fontSize(16)
                    .fontColor('#FFFFFF')
                    .opacity(0.9)
                  Text(this.currentInputType)
                    .fontSize(22)
                    .fontWeight(FontWeight.Bold)
                    .fontColor('#FFFFFF')
                }
                .layoutWeight(1)
                .alignItems(HorizontalAlign.Start)
                .justifyContent(FlexAlign.Center)
              }
              .width('100%')
            }
            .width('100%')
            .padding({
              left: 24,
              right: 24,
              top: 24,
              bottom: 24
            })

            // 装饰性图标
            Image($r("sys.symbol.star_fill"))
              .width(80)
              .height(80)
              .fillColor('#FFFFFF')
              .opacity(0.1)
              .margin({ top: -20, right: -20 })
          }
        }
        .width('100%')
        .linearGradient({
          angle: 135,
          colors: [
            ['#ffb3e0', 0.0],
            ['#ffc78cfd', 0.5],
            ['#a0e5ff', 1.0]
          ]
        })
        .borderRadius(24)
        .shadow({
          radius: 20,
          color: '#40000000',
          offsetX: 0,
          offsetY: 12
        })
        .padding({ top: 28, bottom: 28 })

        // 已选择类型，直接显示输入区域
        this.buildMaterialInputArea()
      } else {
        // 未选择类型，显示类型选择界面
        Column({ space: 20 }) {
          // 欢迎卡片
          Column() {
            Row({ space: 12 }) {
              Column() {
                Image($r("sys.symbol.star_fill"))
                  .width(36)
                  .height(36)
                  .fillColor('#FFFFFF')
              }
              .width(52)
              .height(52)
              .borderRadius(26)
              .backgroundColor('#30FFFFFF')
              .justifyContent(FlexAlign.Center)
              .alignItems(HorizontalAlign.Center)

              Column({ space: 4 }) {
                Text('选择素材类型')
                  .fontSize(18)
                  .fontWeight(FontWeight.Bold)
                  .fontColor('#FFFFFF')
                Text('请选择您要上传的素材类型')
                  .fontSize(13)
                  .fontColor('#FFFFFF')
                  .opacity(0.9)
              }
              .layoutWeight(1)
              .alignItems(HorizontalAlign.Start)
              .justifyContent(FlexAlign.Center)
            }
            .width('100%')
            .padding({
              left: 24,
              right: 24,
              top: 24,
              bottom: 24
            })
          }
          .width('100%')
          .linearGradient({
            angle: 135,
            colors: [
              ['#ffb3e0', 0.0],
              ['#ffc78cfd', 0.5],
              ['#a0e5ff', 1.0]
            ]
          })
          .borderRadius(24)
          .shadow({
            radius: 20,
            color: '#40000000',
            offsetX: 0,
            offsetY: 12
          })
          .padding({ top: 28, bottom: 28 })

          // 素材类型选择网格
          Column({ space: 16 }) {
            // 第一行：文字、文件、链接
            Row({ space: 14 }) {
              this.materialTypeButton('文字', InputType.TEXT, $r("sys.symbol.doc_text"))
              this.materialTypeButton('文件', InputType.FILE, $r("sys.symbol.folder"))
              this.materialTypeButton('链接', InputType.LINK, $r("sys.symbol.link"))
            }
            .width('100%')

            // 第二行：文字+指令、文件+指令、链接+指令
            Row({ space: 14 }) {
              this.materialTypeButton('文字+指令', InputType.TEXT_INSTRUCTION, $r("sys.symbol.doc_text"))
              this.materialTypeButton('文件+指令', InputType.FILE_INSTRUCTION, $r("sys.symbol.folder"))
              this.materialTypeButton('链接+指令', InputType.LINK_INSTRUCTION, $r("sys.symbol.link"))
            }
            .width('100%')

            // 第三行：图片和视频
            Row({ space: 14 }) {
              this.materialTypeButton('图片和视频', InputType.IMAGE_VIDEO, $r("sys.symbol.camera"))
            }
            .width('100%')
          }
          .width('100%')
        }
        .width('100%')
      }
    }
    .width('100%')
  }

  /**
   * 获取输入类型对应的图标（用于顶部大卡片）
   */
  private getInputTypeIconForHeader(): Resource {
    if (!this.currentInputType) {
      return $r("sys.symbol.doc_text");
    }
    switch (this.currentInputType) {
      case InputType.TEXT:
      case InputType.TEXT_INSTRUCTION:
        return $r("sys.symbol.doc_text");
      case InputType.FILE:
      case InputType.FILE_INSTRUCTION:
        return $r("sys.symbol.folder");
      case InputType.LINK:
      case InputType.LINK_INSTRUCTION:
        return $r("sys.symbol.link");
      case InputType.IMAGE_VIDEO:
        return $r("sys.symbol.camera");
      default:
        return $r("sys.symbol.doc_text");
    }
  }

  /**
   * 获取已选择音色的名称
   */
  getSelectedVoiceName(roleName: string): string {
    const voiceUrl = this.roleVoiceUrls[roleName];
    if (!voiceUrl) {
      return '已选择';
    }

    // 如果是预设音色
    if (voiceUrl.startsWith('preset://')) {
      const voiceId = voiceUrl.replace('preset://', '');
      const voiceName = this.getVoiceName(voiceId);
      return voiceName || '已选择';
    }

    // 如果是自定义音色
    return '自定义音色';
  }

  /**
   * 音色选择器弹窗内容
   */
  @Builder
  voiceSelectorSheet() {
    Column() {
      // 添加自定义音色选项
      Row({ space: 4 }) {
        Text('添加你自己的音色')
          .fontSize(14)
          .fontColor('#ffc78cfd')
          .fontWeight(FontWeight.Medium)
        Image($r("sys.symbol.star_fill"))
          .width(16)
          .height(16)
          .fillColor('#ffc78cfd')
      }
      .width('100%')
      .padding({
        left: 20,
        right: 20,
        top: 16,
        bottom: 16
      })
      .onClick(() => this.uploadCustomVoice())

      // 音色列表
      Scroll() {
        Grid() {
          ForEach(this.presetVoices, (voice: PresetVoice) => {
            this.voiceSelectorItem(voice)
          })
        }
        .columnsTemplate('1fr 1fr')
        .rowsGap(12)
        .columnsGap(12)
        .width('100%')
      }
      .layoutWeight(1)
      .width('100%')
      .padding({
        left: 20,
        right: 20,
        top: 8,
        bottom: 20
      })
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#FFFFFF')
  }

  /**
   * 分类选择器弹窗
   */
  @Builder
  categoryPickerSheet() {
    Column() {
      // 分类选项列表
      Scroll() {
        Column() {
          ForEach(this.categoryOptions, (option: SelectOption) => {
            Row() {
              Text(option.value)
                .fontSize(16)
                .fontColor(this.category === option.value ? '#ffc78cfd' : '#333333')
                .fontWeight(this.category === option.value ? FontWeight.Bold : FontWeight.Regular)
                .layoutWeight(1)

              if (this.category === option.value) {
                Image($r("sys.symbol.checkmark"))
                  .width(20)
                  .height(20)
                  .fillColor('#ffc78cfd')
              }
            }
            .width('100%')
            .height(56)
            .padding({ left: 20, right: 20 })
            .backgroundColor(this.category === option.value ? '#FFF5E6' : '#FFFFFF')
            .onClick(() => {
              this.selectCategory(option.value);
            })
          })
        }
        .width('100%')
      }
      .layoutWeight(1)
      .width('100%')
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#FFFFFF')
  }

  @Builder
  voiceSelectorItem(voice: PresetVoice) {
    Row({ space: 8 }) {
      // 播放按钮
      Button() {
        Image(this.playingVoiceId === voice.id ? $r("sys.symbol.pause_fill") : $r("sys.symbol.play_fill"))
          .width(20)
          .height(20)
          .fillColor(voice.gender === 'female' ? '#FF6B9D' : '#4A90E2')
      }
      .type(ButtonType.Normal)
      .width(32)
      .height(32)
      .backgroundColor('#FFFFFF')
      .borderRadius(16)
      .onClick(() => this.playVoicePreview(voice.id))

      // 音色名称
      Text(voice.name)
        .fontSize(15)
        .fontWeight(FontWeight.Medium)
        .fontColor('#333333')
        .layoutWeight(1)

      // 选中标记
      if (this.isVoiceSelected(voice.id)) {
        Image($r("sys.symbol.checkmark"))
          .width(20)
          .height(20)
          .fillColor('#4CAF50')
      }
    }
    .width('100%')
    .height(56)
    .padding({
      left: 16,
      right: 16,
      top: 12,
      bottom: 12
    })
    .backgroundColor(this.isVoiceSelected(voice.id) ? '#F3E5F5' : '#FFFFFF')
    .borderRadius(16)
    .border({
      width: this.isVoiceSelected(voice.id) ? 2 : 1,
      color: this.isVoiceSelected(voice.id) ? '#ffc78cfd' : '#E0E0E0',
      style: BorderStyle.Solid
    })
    .shadow({
      radius: 14,
      color: '#1F000000',
      offsetX: 0,
      offsetY: 20
    })
    .onClick(() => this.selectPresetVoice(voice.id))
  }

  /**
   * 检查音色是否被选中
   */
  private isVoiceSelected(voiceId: string): boolean {
    const voiceUrl = this.roleVoiceUrls[this.currentSelectingRole];
    if (!voiceUrl) {
      return false;
    }
    return voiceUrl.includes(voiceId) || voiceUrl === `preset://${voiceId}`;
  }

  /**
   * 素材类型按钮
   */
  @Builder
  materialTypeButton(label: string, type: InputType, icon: Resource) {
    Button() {
      Stack({ alignContent: Alignment.TopEnd }) {
        Column({ space: 12 }) {
          // 图标容器
          Column() {
            Image(icon)
              .width(36)
              .height(36)
              .fillColor(this.currentInputType === type ? '#FFFFFF' : BUTTON_COLORS[0])
          }
          .width(64)
          .height(64)
          .borderRadius(32)
          .backgroundColor(this.currentInputType === type ? '#40FFFFFF' : '#F5F5F5')
          .justifyContent(FlexAlign.Center)
          .alignItems(HorizontalAlign.Center)

          Text(label)
            .fontSize(15)
            .fontWeight(this.currentInputType === type ? FontWeight.Bold : FontWeight.Medium)
            .fontColor(this.currentInputType === type ? '#FFFFFF' : '#333333')
            .textAlign(TextAlign.Center)
            .maxLines(2)
            .textOverflow({ overflow: TextOverflow.Ellipsis })
        }
        .width('100%')
        .padding({ top: 20, bottom: 16 })
        .alignItems(HorizontalAlign.Center)

        // 选中标记
        if (this.currentInputType === type) {
          Image($r("sys.symbol.checkmark_circle_fill"))
            .width(24)
            .height(24)
            .fillColor('#FFFFFF')
            .margin({ top: 8, right: 8 })
        }
      }
    }
    .type(ButtonType.Normal)
    .width('100%')
    .height(140)
    .backgroundColor(this.currentInputType === type ? '#ffc78cfd' : '#FFFFFF')
    .borderRadius(20)
    .border({
      width: this.currentInputType === type ? 0 : 1,
      color: '#E0E0E0',
      style: BorderStyle.Solid
    })
    .shadow({
      radius: 14,
      color: '#1F000000',
      offsetX: 0,
      offsetY: 20
    })
    .onClick(() => {
      this.currentInputType = type;
    })
  }

  /**
   * 素材输入区域
   */
  @Builder
  buildMaterialInputArea() {
    Column({ space: 20 }) {
      // 输入区域标题卡片
      if (this.currentInputType === InputType.TEXT || this.currentInputType === InputType.TEXT_INSTRUCTION) {
        Column({ space: 12 }) {
          TextArea({
            placeholder: '请输入播客文本内容，支持多行输入...',
            text: $$this.text
          })
            .width('100%')
            .height(160)
            .backgroundColor('#FFFFFF')
            .borderRadius(16)
            .border({
              width: 1,
              color: '#ffececec',
              style: BorderStyle.Solid
            })
            .shadow({
              radius: 14,
              color: '#1F000000',
              offsetX: 0,
              offsetY: 20
            })
            .fontSize(15)
            .padding({
              left: 16,
              right: 16,
              top: 16,
              bottom: 16
            })
            .onChange((value: string) => {
              this.text = value;
            })
        }
        .width('100%')

        if (this.currentInputType === InputType.TEXT_INSTRUCTION) {
          TextArea({
            placeholder: '请输入指令内容（可选）',
            text: $$this.instruction
          })
            .width('100%')
            .height(100)
            .backgroundColor('#FFFFFF')
            .borderRadius(16)
            .border({
              width: 1,
              color: '#E0E0E0',
              style: BorderStyle.Solid
            })
            .shadow({
              radius: 14,
              color: '#1F000000',
              offsetX: 0,
              offsetY: 20
            })
            .onChange((value: string) => {
              this.instruction = value;
            })
        }
      } else if (this.currentInputType === InputType.FILE || this.currentInputType === InputType.FILE_INSTRUCTION) {
        Column({ space: 20 }) {
          // 文件上传卡片
          Column({ space: 16 }) {
            Row() {
              Image($r("sys.symbol.folder"))
                .width(20)
                .height(20)
                .fillColor('#ffc78cfd')
              Text('文件上传')
                .fontSize(16)
                .fontWeight(FontWeight.Bold)
                .fontColor('#1A1A1A')
              Blank()
            }
            .width('100%')

            if (this.textFileNames.length > 0) {
              Column({ space: 12 }) {
                ForEach(this.textFileNames, (fileName: string, index: number) => {
                  Row({ space: 12 }) {
                    Image($r("sys.symbol.doc_text"))
                      .width(24)
                      .height(24)
                      .fillColor('#ffc78cfd')
                    Text(fileName)
                      .fontSize(15)
                      .fontColor('#333333')
                      .layoutWeight(1)
                      .maxLines(1)
                      .textOverflow({ overflow: TextOverflow.Ellipsis })
                    Button() {
                      Image($r("sys.symbol.xmark_circle_fill"))
                        .width(20)
                        .height(20)
                        .fillColor('#999999')
                    }
                    .type(ButtonType.Normal)
                    .backgroundColor(Color.Transparent)
                    .width(32)
                    .height(32)
                    .onClick(() => {
                      const newUrls: string[] = [];
                      const newNames: string[] = [];
                      for (let i = 0; i < this.textFileUrls.length; i++) {
                        if (i !== index) {
                          newUrls.push(this.textFileUrls[i]);
                          newNames.push(this.textFileNames[i]);
                        }
                      }
                      this.textFileUrls = newUrls;
                      this.textFileNames = newNames;
                    })
                  }
                  .width('100%')
                  .padding({
                    left: 16,
                    right: 16,
                    top: 14,
                    bottom: 14
                  })
                  .backgroundColor('#FAFAFA')
                  .borderRadius(12)
                })
              }
              .width('100%')
            }

            Button() {
              Row({ space: 10 }) {
                Image($r("sys.symbol.arrow_up_circle_fill"))
                  .width(24)
                  .height(24)
                  .fillColor('#FFFFFF')
                Text(this.textFileNames.length > 0 ? '添加更多文件' : '选择文件')
                  .fontSize(16)
                  .fontWeight(FontWeight.Bold)
                  .fontColor('#FFFFFF')
              }
            }
            .type(ButtonType.Normal)
            .width('100%')
            .height(56)
            .linearGradient({
              angle: 90,
              colors: [
                ['#ffb3e0', 0.0],
                ['#ffc78cfd', 0.6],
                ['#a0e5ff', 1.0]
              ]
            })
            .borderRadius(16)
            .shadow({
              radius: 14,
              color: '#1F000000',
              offsetX: 0,
              offsetY: 20
            })
            .onClick(() => this.selectTextFile())
          }
          .width('100%')
          .padding({
            top: 20,
            bottom: 20,
            left: 20,
            right: 20
          })
          .backgroundColor('#FFFFFF')
          .borderRadius(20)
          .shadow({
            radius: 14,
            color: '#1F000000',
            offsetX: 0,
            offsetY: 20
          })

          if (this.currentInputType === InputType.FILE_INSTRUCTION) {
            Column({ space: 12 }) {
              Row() {
                Image($r("sys.symbol.gearshape_fill"))
                  .width(20)
                  .height(20)
                  .fillColor('#a0e5ff')
                Text('指令内容（可选）')
                  .fontSize(16)
                  .fontWeight(FontWeight.Bold)
                  .fontColor('#1A1A1A')
                Blank()
              }
              .width('100%')

              TextArea({
                placeholder: '请输入指令内容，用于指导AI生成播客...',
                text: $$this.instruction
              })
                .width('100%')
                .height(120)
                .backgroundColor('#FFFFFF')
                .borderRadius(16)
                .border({
                  width: 1,
                  color: '#E0E0E0',
                  style: BorderStyle.Solid
                })
                .shadow({
                  radius: 14,
                  color: '#1F000000',
                  offsetX: 0,
                  offsetY: 20
                })
                .fontSize(15)
                .padding({
                  left: 16,
                  right: 16,
                  top: 16,
                  bottom: 16
                })
                .onChange((value: string) => {
                  this.instruction = value;
                })
            }
            .width('100%')
            .padding({
              top: 20,
              bottom: 20,
              left: 20,
              right: 20
            })
            .backgroundColor('#FFFFFF')
            .borderRadius(20)
            .shadow({
              radius: 14,
              color: '#1F000000',
              offsetX: 0,
              offsetY: 20
            })
          }
        }
        .width('100%')
      } else if (this.currentInputType === InputType.LINK || this.currentInputType === InputType.LINK_INSTRUCTION) {
        Column({ space: 20 }) {
          // 链接输入卡片
          Column({ space: 16 }) {
            Row() {
              Image($r("sys.symbol.link"))
                .width(20)
                .height(20)
                .fillColor('#a0e5ff')
              Text('链接输入')
                .fontSize(16)
                .fontWeight(FontWeight.Bold)
                .fontColor('#1A1A1A')
              Blank()
            }
            .width('100%')

            Row({ space: 12 }) {
              TextInput({
                placeholder: '请输入或粘贴链接地址...',
                text: this.inputUrl
              })
                .layoutWeight(1)
                .height(52)
                .backgroundColor('#FAFAFA')
                .borderRadius(16)
                .border({
                  width: 1,
                  color: '#E0E0E0',
                  style: BorderStyle.Solid
                })
                .fontSize(15)
                .padding({ left: 16, right: 16 })
                .onChange((value: string) => {
                  this.inputUrl = value;
                })

              Button() {
                Row({ space: 6 }) {
                  Image($r("sys.symbol.doc_text"))
                    .width(18)
                    .height(18)
                    .fillColor('#FFFFFF')
                  Text('粘贴')
                    .fontSize(15)
                    .fontWeight(FontWeight.Medium)
                    .fontColor('#FFFFFF')
                }
              }
              .type(ButtonType.Normal)
              .height(52)
              .linearGradient({
                angle: 90,
                colors: [
                  ['#ffb3e0', 0.0],
                  ['#ffc78cfd', 0.6],
                  ['#a0e5ff', 1.0]
                ]
              })
              .borderRadius(16)
              .padding({ left: 20, right: 20 })
              .shadow({
                radius: 14,
                color: '#1F000000',
                offsetX: 0,
                offsetY: 20
              })
              .onClick(() => this.pasteLink())
            }
            .width('100%')
          }
          .width('100%')
          .padding({
            top: 20,
            bottom: 20,
            left: 20,
            right: 20
          })
          .backgroundColor('#FFFFFF')
          .borderRadius(20)
          .shadow({
            radius: 14,
            color: '#1F000000',
            offsetX: 0,
            offsetY: 20
          })

          if (this.currentInputType === InputType.LINK_INSTRUCTION) {
            Column({ space: 12 }) {
              Row() {
                Image($r("sys.symbol.gearshape_fill"))
                  .width(20)
                  .height(20)
                  .fillColor('#a0e5ff')
                Text('指令内容（可选）')
                  .fontSize(16)
                  .fontWeight(FontWeight.Bold)
                  .fontColor('#1A1A1A')
                Blank()
              }
              .width('100%')

              TextArea({
                placeholder: '请输入指令内容，用于指导AI生成播客...',
                text: $$this.instruction
              })
                .width('100%')
                .height(120)
                .backgroundColor('#FFFFFF')
                .borderRadius(16)
                .border({
                  width: 1,
                  color: '#E0E0E0',
                  style: BorderStyle.Solid
                })
                .shadow({
                  radius: 14,
                  color: '#1F000000',
                  offsetX: 0,
                  offsetY: 20
                })
                .fontSize(15)
                .padding({
                  left: 16,
                  right: 16,
                  top: 16,
                  bottom: 16
                })
                .onChange((value: string) => {
                  this.instruction = value;
                })
            }
            .width('100%')
            .padding({
              top: 20,
              bottom: 20,
              left: 20,
              right: 20
            })
            .backgroundColor('#FFFFFF')
            .borderRadius(20)
            .shadow({
              radius: 14,
              color: '#1F000000',
              offsetX: 0,
              offsetY: 20
            })
          }
        }
        .width('100%')
      } else if (this.currentInputType === InputType.IMAGE_VIDEO) {
        Button('选择图片或视频')
          .type(ButtonType.Normal)
          .width('100%')
          .height(52)
          .backgroundColor('#FFFFFF')
          .fontColor('#333333')
          .fontSize(16)
          .fontWeight(FontWeight.Medium)
          .borderRadius(28)
          .border({
            width: 1,
            color: '#E0E0E0',
            style: BorderStyle.Solid
          })
          .shadow({
            radius: 14,
            color: '#1F000000',
            offsetX: 0,
            offsetY: 20
          })
          .onClick(() => this.selectImageVideoFile())
      }
    }
    .width('100%')
    .padding({ top: 16 })
  }

  /**
   * 步骤2：选择播客类型
   */
  @Builder
  buildStep2Type() {
    Column({ space: 24 }) {
      // 大卡片 - 显示问题
      Column() {
        Stack({ alignContent: Alignment.TopEnd }) {
          // 主内容
          Column({ space: 8 }) {
            Row({ space: 12 }) {

              Column({ space: 4 }) {
                Text('选择播客类型')
                  .fontSize(22)
                  .fontWeight(FontWeight.Bold)
                  .fontColor('#FFFFFF')
                Text('选择您想要创建的播客类型')
                  .fontSize(13)
                  .fontColor('#FFFFFF')
                  .opacity(0.9)
              }
              .layoutWeight(1)
              .alignItems(HorizontalAlign.Start)
              .justifyContent(FlexAlign.Center)
            }
            .width('100%')
          }
          .width('100%')
          .padding({
            left: 24,
            right: 24,
            top: 24,
            bottom: 24
          })
        }
      }
      .width('100%')
      .linearGradient({
        angle: 135,
        colors: [
          ['#ffb3e0', 0.0],
          ['#ffc78cfd', 0.5],
          ['#a0e5ff', 1.0]
        ]
      })
      .borderRadius(24)
      .shadow({
        radius: 20,
        color: '#40000000',
        offsetX: 0,
        offsetY: 12
      })
      .padding({ top: 28, bottom: 28 })

      // 播客类型选项卡片
      Column({ space: 16 }) {
        Row() {
          Text('播客类型')
            .fontSize(18)
            .fontWeight(FontWeight.Bold)
            .fontColor('#1A1A1A')
          Blank()
        }
        .width('100%')

        Row({ space: 14 }) {
          this.podcastTypeButton('多角色互动', PodcastType.MULTI_ROLE)
          this.podcastTypeButton('自定义角色', PodcastType.CHARACTER)
          this.podcastTypeButton('主题深度', PodcastType.DEEP)
        }
        .width('100%')
      }
      .width('100%')
      .padding({
        top: 20,
        bottom: 20,
        left: 20,
        right: 20
      })
      .backgroundColor('#FFFFFF')
      .borderRadius(20)
      .shadow({
        radius: 14,
        color: '#1F000000',
        offsetX: 0,
        offsetY: 20
      })

      // 播客分类选择器卡片
      Column({ space: 16 }) {
        Row() {
          Text('播客分类（可选）')
            .fontSize(18)
            .fontWeight(FontWeight.Bold)
            .fontColor('#1A1A1A')
          Blank()
        }
        .width('100%')

        // 分类选择器
        Select(this.categoryOptions)
          .value(this.category)
          .selected(this.getCategorySelectedIndex())
          .onSelect((index: number, value: string) => {
            this.category = value;
          })
          .width('100%')
      }
      .width('100%')
      .padding({
        top: 20,
        bottom: 20,
        left: 20,
        right: 20
      })
      .backgroundColor('#FFFFFF')
      .borderRadius(20)
      .shadow({
        radius: 14,
        color: '#1F000000',
        offsetX: 0,
        offsetY: 20
      })
    }
    .width('100%')
  }

  /**
   * 播客类型按钮
   */
  @Builder
  podcastTypeButton(label: string, type: PodcastType) {
    if (this.currentPodcastType === type) {
      // 选中状态：使用渐变色
      Button() {
        Stack({ alignContent: Alignment.TopEnd }) {
          Column({ space: 12 }) {
            Text(label)
              .fontSize(15)
              .fontWeight(FontWeight.Bold)
              .fontColor('#FFFFFF')
              .textAlign(TextAlign.Center)
              .maxLines(2)
              .textOverflow({ overflow: TextOverflow.Ellipsis })
          }
          .width('100%')
          .padding({ top: 16, bottom: 12 })
          .alignItems(HorizontalAlign.Center)
          .justifyContent(FlexAlign.Center)
        }
      }
      .type(ButtonType.Capsule)
      .borderRadius(10)
      .layoutWeight(1)
      .linearGradient({
        angle: 90,
        colors: [
          ['#ffb3e0', 0.0],
          ['#ffc78cfd', 0.6],
          ['#a0e5ff', 1.0]
        ]
      })
      .shadow({
        radius: 18,
        color: '#30000000',
        offsetX: 0,
        offsetY: 8
      })
      .onClick(() => {
        this.currentPodcastType = type;
        this.resetFieldsForType(type);
      })
    } else {
      // 未选中状态：使用白色背景
      Button() {
        Stack({ alignContent: Alignment.TopEnd }) {
          Column({ space: 12 }) {
            Text(label)
              .fontSize(15)
              .fontWeight(FontWeight.Medium)
              .fontColor('#333333')
              .textAlign(TextAlign.Center)
              .maxLines(2)
              .textOverflow({ overflow: TextOverflow.Ellipsis })
          }
          .width('100%')
          .padding({ top: 16, bottom: 12 })
          .alignItems(HorizontalAlign.Center)
          .justifyContent(FlexAlign.Center)
        }
      }
      .type(ButtonType.Capsule)
      .borderRadius(10)
      .layoutWeight(1)
      .backgroundColor('#FFFFFF')
      .border({
        width: 1,
        color: '#E0E0E0',
        style: BorderStyle.Solid
      })
      .shadow({
        radius: 14,
        color: '#1F000000',
        offsetX: 0,
        offsetY: 20
      })
      .onClick(() => {
        this.currentPodcastType = type;
        this.resetFieldsForType(type);
      })
    }
  }

  /**
   * 步骤3：填写配置
   */
  @Builder
  buildStep3Config() {
    Column({ space: 24 }) {
      if (this.currentPodcastType === PodcastType.MULTI_ROLE) {
        this.buildMultiRoleConfig()
      } else if (this.currentPodcastType === PodcastType.CHARACTER) {
        this.buildCharacterConfig()
      } else if (this.currentPodcastType === PodcastType.DEEP) {
        this.buildDeepConfig()
      }
    }
    .width('100%')
  }
}

