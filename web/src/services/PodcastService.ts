import axios, { AxiosInstance } from 'axios';

// API配置
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://123.207.14.127:8000';
const API_TIMEOUT = 600000; // 10分钟超时

// 类型定义
export interface CharacterInfo {
  name: string;
  identity?: string;
  personality?: string;
  catchphrase?: string;
  speaking_style?: string;
  relationship?: string;
  voice_url?: string; // 云存储URL（已废弃，使用voice_base64）
  voice_base64?: string; // base64编码的音频数据（本地模式）
}

export interface MultiRoleRequest {
  text?: string;
  text_file_url?: string | string[];
  input_type?: string;
  input_url?: string;
  instruction?: string;
  role_voice_urls?: Record<string, string>; // 云存储URL（已废弃，使用role_voices）
  role_voices?: Record<string, string>; // base64编码的音频数据（本地模式）
  silence_interval?: number;
  podcast_name?: string;
  topic?: string;
  character_1_name?: string;
  character_1_personality?: string;
  character_1_speaking_style?: string;
  character_2_name?: string;
  character_2_personality?: string;
  character_2_speaking_style?: string;
  character_3_name?: string;
  character_3_personality?: string;
  character_3_speaking_style?: string;
  scene_types?: string[];
  category?: string;
  job_id?: string;
}

export interface CharacterRequest {
  characters: CharacterInfo[];
  text: string;
  topic?: string;
  silence_interval?: number;
  category?: string;
  background_volume?: number;
  job_id?: string;
}

export interface DeepPodcastRequest {
  topic: string;
  role_voice_urls?: Record<string, string>; // 云存储URL（已废弃，使用role_voices）
  role_voices?: Record<string, string>; // base64编码的音频数据（本地模式）
  num_characters?: number;
  depth_level?: string;
  silence_interval?: number;
  category?: string;
  background_volume?: number;
  job_id?: string;
}

export interface ProgressStatus {
  job_id: string;
  phase: string;
  percent: number;
  message: string;
  done: boolean;
  error?: string;
  ts?: number;
  audio_url?: string;
  audio_base64?: string;
  script?: string;
  roles?: string[];
  characters?: string[];
  topic?: string;
}

export interface PodcastResult {
  audio_base64?: string;
  audio_path: string;
  file_size_mb: number;
  script: string;
  roles?: string[];
  characters?: string[];
  topic?: string;
  depth_level?: string;
  audio_url?: string;
}

export interface ApiResponse<T = any> {
  success: boolean;
  message: string;
  data?: T;
  error?: string;
}

export interface StreamingScriptRequest {
  text_material: string;
  instruction?: string;
}

export interface StreamingScriptResult {
  script: string;
}

export interface AnalyzeTextRequest {
  text: string;
}

export interface AnalyzedCharacterInfo {
  name: string;
  personality: string;
  speaking_style: string;
}

export interface AnalyzeTextResult {
  podcast_name: string;
  topic: string;
  characters: AnalyzedCharacterInfo[];
  scene_types: string[];
}

/**
 * 播客服务类
 */
class PodcastService {
  private axiosInstance: AxiosInstance;

  constructor() {
    const baseURL = API_BASE_URL.replace(/\/+$/, '');
    this.axiosInstance = axios.create({
      baseURL,
      timeout: API_TIMEOUT,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  /**
   * 健康检查
   */
  async healthCheck(): Promise<boolean> {
    try {
      const response = await this.axiosInstance.get('/health');
      return response.status === 200;
    } catch (error) {
      console.error('健康检查失败:', error);
      return false;
    }
  }

  /**
   * 获取任务进度
   */
  async getProgress(jobId: string): Promise<ProgressStatus | null> {
    try {
      if (!jobId || jobId.trim().length === 0) {
        return null;
      }
      const response = await this.axiosInstance.get(`/api/v1/podcast/progress/${jobId}`);
      return response.data as ProgressStatus;
    } catch (error: any) {
      // 检查是否是网络错误
      const isNetworkError = error.code === 'ERR_NETWORK' || 
                             error.message?.includes('Network Error') ||
                             error.message?.includes('ERR_CONNECTION_REFUSED');
      
      if (isNetworkError) {
        console.error('无法连接到服务器，请确保后端服务正在运行:', error);
        // 返回一个错误状态的进度对象
        return {
          job_id: jobId,
          phase: 'error',
          percent: 0,
          message: '无法连接到服务器，请检查后端服务是否运行',
          done: true,
          error: '网络连接失败，请确保后端服务器正在运行',
        };
      }
      
      console.error('获取进度失败:', error);
      return null;
    }
  }

  /**
   * 启动进度轮询
   */
  startProgressPolling(
    jobId: string,
    onProgress: (progress: ProgressStatus) => void,
    interval: number = 5000
  ): () => void {
    let pollingInterval: number | null = null;
    let isPolling = true;
    let consecutiveErrors = 0;
    const MAX_CONSECUTIVE_ERRORS = 3; // 连续错误3次后停止轮询

    const poll = async () => {
      if (!isPolling) return;

      try {
        const progress = await this.getProgress(jobId);
        if (progress) {
          // 重置错误计数
          consecutiveErrors = 0;
          
          onProgress(progress);
          
          // 如果进度包含错误信息，停止轮询
          if (progress.done || progress.error) {
            isPolling = false;
            if (pollingInterval) {
              clearInterval(pollingInterval);
              pollingInterval = null;
            }
            return;
          }
        } else {
          // 如果返回null，可能是网络错误，增加错误计数
          consecutiveErrors++;
          if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS) {
            console.error('连续多次获取进度失败，停止轮询');
            isPolling = false;
            if (pollingInterval) {
              clearInterval(pollingInterval);
              pollingInterval = null;
            }
            // 通知用户连接失败
            onProgress({
              job_id: jobId,
              phase: 'error',
              percent: 0,
              message: '无法连接到服务器，请检查后端服务是否运行',
              done: true,
              error: '网络连接失败，请确保后端服务器正在运行',
            });
            return;
          }
        }
      } catch (error) {
        consecutiveErrors++;
        console.error('轮询进度失败:', error);
        
        if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS) {
          console.error('连续多次轮询失败，停止轮询');
          isPolling = false;
          if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
          }
          // 通知用户连接失败
          onProgress({
            job_id: jobId,
            phase: 'error',
            percent: 0,
            message: '无法连接到服务器，请检查后端服务是否运行',
            done: true,
            error: '网络连接失败，请确保后端服务器正在运行',
          });
          return;
        }
      }

      if (isPolling) {
        pollingInterval = setTimeout(poll, interval);
      }
    };

    poll();

    return () => {
      isPolling = false;
      if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
      }
    };
  }

  /**
   * 生成多角色互动播客
   */
  async generateMultiRolePodcast(
    request: MultiRoleRequest,
    onProgress?: (progress: ProgressStatus) => void
  ): Promise<ApiResponse<PodcastResult>> {
    try {
      const hasText = request.text && request.text.trim().length > 0;
      const hasTextFile = request.text_file_url && (
        Array.isArray(request.text_file_url)
          ? request.text_file_url.length > 0
          : request.text_file_url.trim().length > 0
      );
      const hasInputUrl = request.input_url && request.input_url.trim().length > 0;

      if (!hasText && !hasTextFile && !hasInputUrl) {
        return {
          success: false,
          message: '播客文本不能为空，请上传文本文件、输入文本或提供输入URL',
          error: '文本内容为空',
        };
      }

      // 检查音色数据（优先使用base64，兼容URL）
      const hasRoleVoices = request.role_voices && Object.keys(request.role_voices).length > 0;
      const hasRoleVoiceUrls = request.role_voice_urls && Object.keys(request.role_voice_urls).length > 0;
      
      if (!hasRoleVoices && !hasRoleVoiceUrls) {
        return {
          success: false,
          message: '至少需要一个角色的音色数据',
          error: '角色音色数据为空',
        };
      }

      const response = await this.axiosInstance.post<ApiResponse<PodcastResult>>(
        '/api/v1/podcast/multi_role',
        request
      );

      if (request.job_id && onProgress) {
        this.startProgressPolling(request.job_id, onProgress);
      }

      return response.data;
    } catch (error: any) {
      return {
        success: false,
        message: '多角色播客生成失败',
        error: error.response?.data?.error || error.message || '未知错误',
      };
    }
  }

  /**
   * 生成自定义角色播客
   */
  async generateCharacterPodcast(
    request: CharacterRequest,
    onProgress?: (progress: ProgressStatus) => void
  ): Promise<ApiResponse<PodcastResult>> {
    try {
      if (!request.characters || request.characters.length < 2) {
        return {
          success: false,
          message: '至少需要2个角色',
          error: '角色数量不足',
        };
      }

      if (request.characters.length > 4) {
        return {
          success: false,
          message: '最多支持4个角色',
          error: '角色数量过多',
        };
      }

      if (!request.text || request.text.trim().length === 0) {
        return {
          success: false,
          message: '文本素材不能为空',
          error: '文本素材缺失',
        };
      }

      for (const char of request.characters) {
        if (!char.name || (!char.voice_base64 && !char.voice_url)) {
          return {
            success: false,
            message: `角色 ${char.name || '未知'} 的信息不完整（缺少音色数据）`,
            error: '角色信息不完整',
          };
        }
      }

      const response = await this.axiosInstance.post<ApiResponse<PodcastResult>>(
        '/api/v1/podcast/character',
        request
      );

      if (request.job_id && onProgress) {
        this.startProgressPolling(request.job_id, onProgress);
      }

      return response.data;
    } catch (error: any) {
      return {
        success: false,
        message: '自定义角色播客生成失败',
        error: error.response?.data?.error || error.message || '未知错误',
      };
    }
  }

  /**
   * 生成主题深度播客
   */
  async generateDeepPodcast(
    request: DeepPodcastRequest,
    onProgress?: (progress: ProgressStatus) => void
  ): Promise<ApiResponse<PodcastResult>> {
    try {
      if (!request.topic || request.topic.trim().length === 0) {
        return {
          success: false,
          message: '播客主题不能为空',
          error: '主题为空',
        };
      }

      const numCharacters = request.num_characters || 2;
      if (numCharacters < 1 || numCharacters > 3) {
        return {
          success: false,
          message: '角色数量必须在1-3个之间',
          error: '角色数量无效',
        };
      }

      const depthLevel = request.depth_level || '深度';
      if (!['深度', '中等', '浅层'].includes(depthLevel)) {
        return {
          success: false,
          message: '深度级别必须是：深度、中等或浅层',
          error: '深度级别无效',
        };
      }

      const roleNames = ['角色A', '角色B', '角色C'].slice(0, numCharacters);
      
      // 检查音色数据（优先使用base64，兼容URL）
      const roleVoices = request.role_voices || {};
      const roleVoiceUrls = request.role_voice_urls || {};
      const hasRoleVoices = Object.keys(roleVoices).length > 0;
      const hasRoleVoiceUrls = Object.keys(roleVoiceUrls).length > 0;
      
      if (!hasRoleVoices && !hasRoleVoiceUrls) {
        return {
          success: false,
          message: `需要为所有${numCharacters}个角色提供音色数据`,
          error: '角色音色数据缺失',
        };
      }
      
      // 验证每个角色都有音色数据
      for (const roleName of roleNames) {
        if (!roleVoices[roleName] && !roleVoiceUrls[roleName]) {
          return {
            success: false,
            message: `缺少角色 ${roleName} 的音色数据`,
            error: '角色音色数据缺失',
          };
        }
      }

      const response = await this.axiosInstance.post<ApiResponse<PodcastResult>>(
        '/api/v1/podcast/deep',
        request
      );

      if (request.job_id && onProgress) {
        this.startProgressPolling(request.job_id, onProgress);
      }

      return response.data;
    } catch (error: any) {
      return {
        success: false,
        message: '主题深度播客生成失败',
        error: error.response?.data?.error || error.message || '未知错误',
      };
    }
  }

  /**
   * 生成流式播客脚本
   */
  async generateStreamingScript(
    request: StreamingScriptRequest
  ): Promise<ApiResponse<StreamingScriptResult>> {
    try {
      if (!request.text_material || request.text_material.trim().length === 0) {
        return {
          success: false,
          message: '输入内容不能为空',
          error: 'text_material为空',
        };
      }

      const response = await this.axiosInstance.post<ApiResponse<StreamingScriptResult>>(
        '/api/v1/podcast/streaming_script',
        request
      );

      return response.data;
    } catch (error: any) {
      return {
        success: false,
        message: '流式播客脚本生成失败',
        error: error.response?.data?.error || error.message || '未知错误',
      };
    }
  }

  /**
   * 分析文本素材
   */
  async analyzeTextForPodcast(request: AnalyzeTextRequest): Promise<ApiResponse<AnalyzeTextResult>> {
    try {
      if (!request.text || request.text.trim().length === 0) {
        return {
          success: false,
          message: '文本内容不能为空',
          error: '文本内容为空',
        };
      }

      const response = await this.axiosInstance.post<ApiResponse<AnalyzeTextResult>>(
        '/api/v1/podcast/analyze',
        request
      );

      return response.data;
    } catch (error: any) {
      return {
        success: false,
        message: '文本分析失败',
        error: error.response?.data?.error || error.message || '未知错误',
      };
    }
  }

  /**
   * 上传文件到云存储（已废弃 - 本地模式不再需要）
   * @deprecated 本地模式下，文件直接转换为base64，不再上传到云存储
   */
  async uploadFile(file: File, fileType: 'audio' | 'text' = 'audio'): Promise<ApiResponse<{ url: string }>> {
    // 本地模式下，此方法不再使用
    // 如果需要，可以返回一个错误提示
    return {
      success: false,
      message: '本地模式下不支持文件上传，请直接使用base64编码',
      error: '本地模式不支持上传',
    };
  }
}

export const podcastService = new PodcastService();

