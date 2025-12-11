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

import { WindowModel } from 'lib_common';
import { NavHeaderBar } from 'lib_widget';
import { podcastService, MultiRoleRequest, CharacterRequest, DeepPodcastRequest, CharacterInfo, PodcastResult, ProgressStatus } from 'lib_api';
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

// Select 选项类型定义
interface SelectOption {
  value: string;
}

@Builder
export function PodcastCreatePageBuilder() {
  PodcastCreatePage()
}

@ComponentV2
export struct PodcastCreatePage {
  // 当前选择的播客类型
  @Local currentPodcastType: PodcastType = PodcastType.MULTI_ROLE;
  
  // ========== 通用字段 ==========
  @Local text: string = ''; // 文本内容
  @Local textFileUrls: string[] = []; // 文本文件云存储URL列表
  @Local textFileNames: string[] = []; // 文本文件名列表
  @Local inputUrl: string = ''; // 输入URL（用于链接等类型）
  @Local instruction: string = ''; // 指令内容（可选）
  @Local category: string = ''; // 播客分类（可选）
  @Local currentInputType: InputType = InputType.TEXT; // 当前输入类型
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
   * 选择角色音色文件（多角色互动播客和主题深度播客）
   */
  async selectVoiceFile(roleName: string): Promise<void> {
    try {
      const context = this.getUIContext().getHostContext() as common.UIAbilityContext;
      const audioFileInfo = await FileUtils.pickAudioFile(context, true);
      
      if (audioFileInfo && audioFileInfo.cloudUrl) {
        const updatedRoleVoiceUrls: Record<string, string> = {};
        const keys = Object.keys(this.roleVoiceUrls);
        for (let i = 0; i < keys.length; i++) {
          updatedRoleVoiceUrls[keys[i]] = this.roleVoiceUrls[keys[i]];
        }
        updatedRoleVoiceUrls[roleName] = audioFileInfo.cloudUrl;
        this.roleVoiceUrls = updatedRoleVoiceUrls;
        
        promptAction.showToast({
          message: `${roleName}音色已选择`,
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
              voice_url: audioFileInfo.cloudUrl
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
      
      const needsInputUrl = [InputType.LINK, InputType.LINK_INSTRUCTION].includes(this.currentInputType);
      const needsFile = [InputType.FILE, InputType.FILE_INSTRUCTION].includes(this.currentInputType);
      const needsText = [InputType.TEXT, InputType.TEXT_INSTRUCTION].includes(this.currentInputType);
      
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
      text_file_url: hasTextFile ? (this.textFileUrls.length === 1 ? this.textFileUrls[0] : this.textFileUrls) : undefined,
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
      if (response.data.script) {
        this.savedScript = response.data.script;
      }
      if (!this.savedAudioUrl && response.data.audio_url) {
        this.savedAudioUrl = response.data.audio_url;
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
      if (response.data.script) {
        this.savedScript = response.data.script;
      }
      if (!this.savedAudioUrl && response.data.audio_url) {
        this.savedAudioUrl = response.data.audio_url;
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
      if (response.data.script) {
        this.savedScript = response.data.script;
      }
      if (!this.savedAudioUrl && response.data.audio_url) {
        this.savedAudioUrl = response.data.audio_url;
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
    Column() {
      // 顶部导航栏
      NavHeaderBar({
        title: 'AI播客',
        onBack: () => {
          // 返回上一页
        }
      })
      
      // 标签页切换
      Row() {
        Button('多角色互动播客')
          .type(ButtonType.Normal)
          .backgroundColor(this.currentPodcastType === PodcastType.MULTI_ROLE ? '#007AFF' : '#F5F5F5')
          .fontColor(this.currentPodcastType === PodcastType.MULTI_ROLE ? '#FFFFFF' : '#000000')
          .onClick(() => this.switchPodcastType(PodcastType.MULTI_ROLE))
        
        Button('自定义角色播客')
          .type(ButtonType.Normal)
          .backgroundColor(this.currentPodcastType === PodcastType.CHARACTER ? '#007AFF' : '#F5F5F5')
          .fontColor(this.currentPodcastType === PodcastType.CHARACTER ? '#FFFFFF' : '#000000')
          .onClick(() => this.switchPodcastType(PodcastType.CHARACTER))
        
        Button('主题深度播客')
          .type(ButtonType.Normal)
          .backgroundColor(this.currentPodcastType === PodcastType.DEEP ? '#007AFF' : '#F5F5F5')
          .fontColor(this.currentPodcastType === PodcastType.DEEP ? '#FFFFFF' : '#000000')
          .onClick(() => this.switchPodcastType(PodcastType.DEEP))
      }
      .width('100%')
      .height(48)
      .padding({ left: 16, right: 16 })
      .justifyContent(FlexAlign.SpaceBetween)
      
      // 主内容区域（可滚动）
      Scroll() {
        Column({ space: 16 }) {
          // 统一的输入区域
          this.buildInputArea()
          
          // 根据选择的类型显示不同的配置区域
          if (this.currentPodcastType === PodcastType.MULTI_ROLE) {
            this.buildMultiRoleConfig()
          } else if (this.currentPodcastType === PodcastType.CHARACTER) {
            this.buildCharacterConfig()
          } else if (this.currentPodcastType === PodcastType.DEEP) {
            this.buildDeepConfig()
          }
          
          // 播客分类（可选）
          this.buildCategorySelector()
        }
        .width('100%')
        .padding({ left: 16, right: 16, top: 16, bottom: 16 })
      }
      .layoutWeight(1)
      .width('100%')
      
      // 底部生成按钮
      Button('开始生成')
        .type(ButtonType.Normal)
        .width('90%')
        .height(48)
        .backgroundColor('#007AFF')
        .fontColor('#FFFFFF')
        .fontSize(16)
        .fontWeight(FontWeight.Bold)
        .enabled(!this.isLoading)
        .onClick(() => this.generatePodcast())
        .margin({ bottom: 16 })
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#FFFFFF')
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
        .padding({ left: 12, right: 12, top: 8, bottom: 8 })
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
          .height(120)
          .backgroundColor('#F5F5F5')
          .borderRadius(8)
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
            .height(80)
            .backgroundColor('#F5F5F5')
            .borderRadius(8)
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
              .padding({ left: 12, right: 12, top: 8, bottom: 8 })
              .backgroundColor('#F5F5F5')
              .borderRadius(8)
            })
          }
          
          Button('选择文件')
            .type(ButtonType.Normal)
            .width('100%')
            .height(40)
            .backgroundColor('#F5F5F5')
            .fontColor('#000000')
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
            .height(80)
            .backgroundColor('#F5F5F5')
            .borderRadius(8)
            .onChange((value: string) => {
              this.instruction = value;
            })
        }
      } else if (this.currentInputType === InputType.LINK || this.currentInputType === InputType.LINK_INSTRUCTION) {
        // 链接输入
        Row({ space: 8 }) {
          TextInput({
            placeholder: '请输入链接',
            text: $$this.inputUrl
          })
            .layoutWeight(1)
            .backgroundColor('#F5F5F5')
            .borderRadius(8)
            .onChange((value: string) => {
              this.inputUrl = value;
            })
          
          Button('粘贴')
            .type(ButtonType.Normal)
            .onClick(() => this.pasteLink())
        }
        .width('100%')
        
        // 如果是链接+指令，显示指令输入框
        if (this.currentInputType === InputType.LINK_INSTRUCTION) {
          TextArea({
            placeholder: '请输入指令内容（可选）',
            text: $$this.instruction
          })
            .width('100%')
            .height(80)
            .backgroundColor('#F5F5F5')
            .borderRadius(8)
            .onChange((value: string) => {
              this.instruction = value;
            })
        }
      } else if (this.currentInputType === InputType.IMAGE_VIDEO) {
        // 图片和视频上传
        Button('选择图片或视频')
          .type(ButtonType.Normal)
          .width('100%')
          .height(40)
          .backgroundColor('#F5F5F5')
          .fontColor('#000000')
          .onClick(() => this.selectImageVideoFile())
      }
    }
    .width('100%')
    .padding({ top: 16, bottom: 16 })
  }
  
  @Builder
  buildMultiRoleConfig() {
    Column({ space: 12 }) {
      Text('角色音色')
        .fontSize(16)
        .fontWeight(FontWeight.Bold)
        .fontColor('#000000')
      
      ForEach(this.roleNames, (roleName: string) => {
        Row() {
          Text(roleName)
            .fontSize(14)
            .fontColor('#000000')
            .layoutWeight(1)
          
          Button(this.roleVoiceUrls[roleName] ? '已选择' : '选择音色')
            .type(ButtonType.Normal)
            .backgroundColor(this.roleVoiceUrls[roleName] ? '#E8F5E9' : '#F5F5F5')
            .fontColor(this.roleVoiceUrls[roleName] ? '#4CAF50' : '#000000')
            .onClick(() => this.selectVoiceFile(roleName))
        }
        .width('100%')
        .height(48)
        .padding({ left: 12, right: 12 })
        .backgroundColor('#F5F5F5')
        .borderRadius(8)
      })
    }
    .width('100%')
  }
  
  @Builder
  buildCharacterConfig() {
    Column({ space: 12 }) {
      Row() {
        Text('角色配置')
          .fontSize(16)
          .fontWeight(FontWeight.Bold)
          .fontColor('#000000')
        
        Blank()
        
        Button('+ 新增角色')
          .type(ButtonType.Normal)
          .backgroundColor('#007AFF')
          .fontColor('#FFFFFF')
          .onClick(() => this.addCharacter())
      }
      .width('100%')
      
      ForEach(this.characters, (character: CharacterInfo, index: number) => {
        Column({ space: 8 }) {
          Text(`角色 ${index + 1}`)
            .fontSize(14)
            .fontWeight(FontWeight.Bold)
            .fontColor('#000000')
          
          TextInput({
            placeholder: '角色名称',
            text: character.name || ''
          })
            .width('100%')
            .backgroundColor('#F5F5F5')
            .borderRadius(8)
            .onChange((value: string) => {
              this.updateCharacter(index, 'name', value);
            })
          
          TextInput({
            placeholder: '身份/职业（可选）',
            text: character.identity || ''
          })
            .width('100%')
            .backgroundColor('#F5F5F5')
            .borderRadius(8)
            .onChange((value: string) => {
              this.updateCharacter(index, 'identity', value);
            })
          
          TextInput({
            placeholder: '核心性格（可选）',
            text: character.personality || ''
          })
            .width('100%')
            .backgroundColor('#F5F5F5')
            .borderRadius(8)
            .onChange((value: string) => {
              this.updateCharacter(index, 'personality', value);
            })
          
          Row({ space: 8 }) {
            Button('选择音色文件')
              .type(ButtonType.Normal)
              .layoutWeight(1)
              .backgroundColor('#F5F5F5')
              .fontColor('#000000')
              .onClick(() => this.selectCharacterVoiceFile(index))
            
            Button(this.isRecording && this.recordingIndex === index ? `停止录制 (${this.recordingDuration}s)` : '录制音色')
              .type(ButtonType.Normal)
              .layoutWeight(1)
              .backgroundColor(this.isRecording && this.recordingIndex === index ? '#FF5722' : '#F5F5F5')
              .fontColor(this.isRecording && this.recordingIndex === index ? '#FFFFFF' : '#000000')
              .onClick(() => this.recordVoice(index))
          }
          .width('100%')
          
          if (this.characters.length > 2) {
            Button('删除角色')
              .type(ButtonType.Normal)
              .width('100%')
              .backgroundColor('#FFEBEE')
              .fontColor('#F44336')
              .onClick(() => this.removeCharacter(index))
          }
        }
        .width('100%')
        .padding({ top: 12, bottom: 12, left: 12, right: 12 })
        .backgroundColor('#FAFAFA')
        .borderRadius(8)
      })
    }
    .width('100%')
  }
  
  @Builder
  buildDeepConfig() {
    Column({ space: 12 }) {
      Text('播客主题')
        .fontSize(16)
        .fontWeight(FontWeight.Bold)
        .fontColor('#000000')
      
      TextInput({
        placeholder: '请输入播客主题',
        text: $$this.topic
      })
        .width('100%')
        .height(48)
        .backgroundColor('#F5F5F5')
        .borderRadius(8)
        .onChange((value: string) => {
          this.topic = value;
        })
      
      Text('角色数量')
        .fontSize(16)
        .fontWeight(FontWeight.Bold)
        .fontColor('#000000')
      
      Row({ space: 8 }) {
        Button('1个角色')
          .type(ButtonType.Normal)
          .layoutWeight(1)
          .backgroundColor(this.numCharacters === 1 ? '#007AFF' : '#F5F5F5')
          .fontColor(this.numCharacters === 1 ? '#FFFFFF' : '#000000')
          .onClick(() => {
            this.numCharacters = 1;
            // 更新角色列表
            this.roleNames = ['角色A'];
          })
        
        Button('2个角色')
          .type(ButtonType.Normal)
          .layoutWeight(1)
          .backgroundColor(this.numCharacters === 2 ? '#007AFF' : '#F5F5F5')
          .fontColor(this.numCharacters === 2 ? '#FFFFFF' : '#000000')
          .onClick(() => {
            this.numCharacters = 2;
            this.roleNames = ['角色A', '角色B'];
          })
        
        Button('3个角色')
          .type(ButtonType.Normal)
          .layoutWeight(1)
          .backgroundColor(this.numCharacters === 3 ? '#007AFF' : '#F5F5F5')
          .fontColor(this.numCharacters === 3 ? '#FFFFFF' : '#000000')
          .onClick(() => {
            this.numCharacters = 3;
            this.roleNames = ['角色A', '角色B', '角色C'];
          })
      }
      .width('100%')
      
      Text('深度级别')
        .fontSize(16)
        .fontWeight(FontWeight.Bold)
        .fontColor('#000000')
      
      Row({ space: 8 }) {
        ForEach(this.depthLevels, (level: string) => {
          Button(level)
            .type(ButtonType.Normal)
            .layoutWeight(1)
            .backgroundColor(this.depthLevel === level ? '#007AFF' : '#F5F5F5')
            .fontColor(this.depthLevel === level ? '#FFFFFF' : '#000000')
            .onClick(() => {
              this.depthLevel = level;
            })
        })
      }
      .width('100%')
      
      Text('角色音色')
        .fontSize(16)
        .fontWeight(FontWeight.Bold)
        .fontColor('#000000')
      
      ForEach(this.roleNames, (roleName: string) => {
        Row() {
          Text(roleName)
            .fontSize(14)
            .fontColor('#000000')
            .layoutWeight(1)
          
          Button(this.roleVoiceUrls[roleName] ? '已选择' : '选择音色')
            .type(ButtonType.Normal)
            .backgroundColor(this.roleVoiceUrls[roleName] ? '#E8F5E9' : '#F5F5F5')
            .fontColor(this.roleVoiceUrls[roleName] ? '#4CAF50' : '#000000')
            .onClick(() => this.selectVoiceFile(roleName))
        }
        .width('100%')
        .height(48)
        .padding({ left: 12, right: 12 })
        .backgroundColor('#F5F5F5')
        .borderRadius(8)
      })
    }
    .width('100%')
  }
  
  @Builder
  buildCategorySelector() {
    Column({ space: 8 }) {
      Text('播客分类（可选）')
        .fontSize(16)
        .fontWeight(FontWeight.Bold)
        .fontColor('#000000')
      
      // TODO: 实现分类选择器
      TextInput({
        placeholder: '请选择播客分类',
        text: $$this.category
      })
        .width('100%')
        .height(48)
        .backgroundColor('#F5F5F5')
        .borderRadius(8)
        .onChange((value: string) => {
          this.category = value;
        })
    }
    .width('100%')
  }
}

