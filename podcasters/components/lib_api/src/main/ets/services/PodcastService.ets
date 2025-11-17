import { http } from '@kit.NetworkKit';
import { BusinessError } from '@kit.BasicServicesKit';
import { Logger } from 'lib_common';

const TAG = '[PodcastService]';

/**
 * 播客API服务配置
 */
export class PodcastConfig {
  // 配置说明：
  // 1. 使用Cloud Studio（推荐）：设置为Cloud Studio端口转发地址
  //    格式：https://${SPACE_KEY}--8000.${REGION}.cloudstudio.work/
  //    示例：'https://hfrsgm--8000.ap-guangzhou.cloudstudio.work'
  //    获取方式：
  //    - 查看浏览器地址栏：https://hfrsgm.ap-guangzhou.cloudstudio.work/
  //    - 提取SPACE_KEY（hfrsgm）和REGION（ap-guangzhou）
  //    - 构建地址：https://hfrsgm--8000.ap-guangzhou.cloudstudio.work
  // 2. 使用云函数：设置为华为AGC云函数的HTTP触发器URL
  //    例如：'https://your-cloud-function-url.com'
  // 3. 使用本地服务器：设置为本地服务器的IP地址和端口
  //    例如：'http://10.10.210.52:8000'
  // 4. 使用远程服务器：设置为远程服务器的URL
  //    例如：'https://your-server.com'
  // 5. 直连服务器IP（推荐，避免网关超时）：设置为服务器的公网/内网IP和端口
  //    例如：'http://9.165.4.87:8000' 或 'http://192.168.1.100:8000'
  //    注意：确保服务器防火墙允许8000端口访问
  static readonly API_BASE_URL: string = 'http://119.29.189.36:8000/'; // 请替换为实际的服务器IP地址
  static readonly API_TIMEOUT: number = 600000; // 10分钟超时（考虑大文件上传和播客生成时间）

  
  // 是否使用云函数（如果使用云函数，路径可能不同）
  // 云函数通过HTTP触发器调用，URL格式通常为：https://your-cloud-function-url.com
  // 本地/远程服务器URL格式：http://ip:port 或 https://domain.com
  // Cloud Studio URL格式：https://${SPACE_KEY}--${PORT}.${REGION}.cloudstudio.work
  static readonly USE_CLOUD_FUNCTION: boolean = false; // 设置为 true 如果使用云函数
  
  // 是否使用云存储（后端已强制要求使用云存储URL，此配置保留用于兼容性）
  // 注意：后端API现在强制要求使用云存储URL，不再支持base64编码的音频文件
  // 使用云存储的优势：
  // - 减少请求体大小
  // - 提高传输效率
  // - 支持大文件
  // - 文件可重复使用
  static readonly USE_CLOUD_STORAGE: boolean = true; // 必须为 true（后端强制要求）
}

/**
 * 角色信息
 */
export interface CharacterInfo {
  name: string;
  identity?: string;
  personality?: string;
  catchphrase?: string;
  speaking_style?: string;
  relationship?: string;
  voice_url: string; // 云存储URL

}

/**
 * 多角色播客请求
 */
export interface MultiRoleRequest {
  text?: string; // 播客文本（如果使用text_file_url或input_url，此字段可为空）
  text_file_url?: string | string[]; // 文本文件云存储URL（.txt或Word文件，如果提供，优先使用）。支持单个URL或URL数组（多个文件）
  input_type?: string; // 输入类型，可选值：文字、文字+指令、公众号、公众号+指令、网页、文件、文件+指令、文字+英文指令
  input_url?: string; // 输入URL（用于公众号、网页、PDF等类型）
  instruction?: string; // 指令内容（可选，用于控制播客生成过程）
  role_voice_urls: Record<string, string>; // 角色名 -> 云存储URL（必需，后端强制要求）
  role_voices?: Record<string, string>; // [已废弃] 角色名 -> base64音频（已废弃，请使用role_voice_urls）
  silence_interval?: number;
  podcast_name?: string; // 播客名称（可选）
  topic?: string; // 本期主题（可选）
  character_1_name?: string; // 角色1名称（可选）
  character_1_personality?: string; // 角色1性格特点（可选）
  character_1_speaking_style?: string; // 角色1说话风格（可选）
  character_2_name?: string; // 角色2名称（可选）
  character_2_personality?: string; // 角色2性格特点（可选）
  character_2_speaking_style?: string; // 角色2说话风格（可选）
  character_3_name?: string; // 角色3名称（可选）
  character_3_personality?: string; // 角色3性格特点（可选）
  character_3_speaking_style?: string; // 角色3说话风格（可选）
  scene_types?: string[]; // 互动场景类型列表（可选）
  category?: string; // 播客分类（可选），如：社会文化与历史、音乐、影视、书、喜剧/脱口秀、艺术、宗教与灵修、科学与科技、时尚与美妆、健康、健身与养身、育儿与家庭、情感、生活、体育运动、休闲娱乐与爱好、商业与财经、新闻、职场万象、自我成长与自愈、学术研究等
  job_id?: string; // 可选任务ID，用于轮询进度
}

/**
 * 自定义角色播客请求
 */
export interface CharacterRequest {
  characters: CharacterInfo[];
  text: string; // 文本素材（必需）
  topic?: string; // 播客主题（可选，主要用于背景音乐选择）
  silence_interval?: number;
  category?: string; // 播客分类（可选），用于背景音乐选择
  background_volume?: number; // 背景音乐音量（0.0-1.0），默认0.3
  job_id?: string; // 可选任务ID，用于轮询进度
}

/**
 * 主题深度播客请求
 */
export interface DeepPodcastRequest {
  topic: string;
  role_voice_urls: Record<string, string>; // 角色名 -> 云存储URL
  
  num_characters?: number; // 1-3
  depth_level?: string; // "深度" | "中等" | "浅层"
  silence_interval?: number;
  category?: string; // 播客分类（可选），用于背景音乐选择
  background_volume?: number; // 背景音乐音量（0.0-1.0），默认0.3
  job_id?: string; // 可选任务ID，用于轮询进度
}

/**
 * 文本分析请求
 */
export interface AnalyzeTextRequest {
  text: string; // 要分析的文本素材
}

/**
 * 分析结果中的角色信息
 */
export interface AnalyzedCharacterInfo {
  name: string; // 角色名称
  personality: string; // 性格特点
  speaking_style: string; // 说话风格
}

/**
 * 文本分析结果
 */
export interface AnalyzeTextResult {
  podcast_name: string; // 播客名称
  topic: string; // 本期主题
  characters: AnalyzedCharacterInfo[]; // 角色设定列表
  scene_types: string[]; // 互动场景类型列表
}

/**
 * 进度状态
 */
export interface ProgressStatus {
  job_id: string;
  phase: string;
  percent: number; // 0-100
  message: string;
  done: boolean;
  error?: string;
  ts?: number;
  // 新增：云存储URL（生成完成时返回）
  audio_url?: string;
}

/**
 * 批量任务项
 */
export interface BatchTaskItem {
  task_type: 'multi_role' | 'character' | 'deep'; // 任务类型
  task_id?: string; // 可选的任务ID，如果不提供则自动生成
  request_data: MultiRoleRequest | CharacterRequest | DeepPodcastRequest; // 任务请求数据
}

/**
 * 批量生成请求
 */
export interface BatchRequest {
  tasks: BatchTaskItem[]; // 任务列表（最多50个）
}

/**
 * 批量生成响应
 */
export interface BatchResponse {
  task_ids: string[]; // 任务ID列表
  total: number; // 总任务数
  queue_size: number; // 队列大小
  active_tasks: number; // 活跃任务数
}

/**
 * 任务结果
 */
export interface TaskResult {
  file_size_mb?: number;
  output_path?: string;
  audio_url?: string;
}

/**
 * 任务状态
 */
export interface TaskStatus {
  task_id: string;
  task_type: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  message: string;
  created_at?: number;
  started_at?: number;
  completed_at?: number;
  error?: string;
  result?: TaskResult;
}

/**
 * 多角色播客请求体（API请求用）
 */
class MultiRoleRequestBody {
  text?: string; // 播客文本（如果使用text_file_url或input_url，此字段可为空）
  text_file_url?: string | string[]; // 文本文件云存储URL（支持单个URL或URL数组）
  input_type?: string; // 输入类型
  input_url?: string; // 输入URL（用于公众号、网页、PDF等类型）
  instruction?: string; // 指令内容
  role_voices?: Record<string, string>; // base64音频（如果不使用云存储）
  role_voice_urls?: Record<string, string>; // 云存储URL（如果使用云存储）
  silence_interval: number;
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

  constructor(
    text: string | undefined,
    text_file_url: string | string[] | undefined,
    input_type: string | undefined,
    input_url: string | undefined,
    instruction: string | undefined,
    role_voices: Record<string, string> | undefined,
    role_voice_urls: Record<string, string> | undefined,
    silence_interval: number,
    podcast_name?: string,
    topic?: string,
    character_1_name?: string,
    character_1_personality?: string,
    character_1_speaking_style?: string,
    character_2_name?: string,
    character_2_personality?: string,
    character_2_speaking_style?: string,
    character_3_name?: string,
    character_3_personality?: string,
    character_3_speaking_style?: string,
    scene_types?: string[],
    category?: string,
    job_id?: string
  ) {
    this.text = text;
    this.text_file_url = text_file_url;
    this.input_type = input_type;
    this.input_url = input_url;
    this.instruction = instruction;
    this.role_voices = role_voices;
    this.role_voice_urls = role_voice_urls;
    this.silence_interval = silence_interval;
    this.podcast_name = podcast_name;
    this.topic = topic;
    this.character_1_name = character_1_name;
    this.character_1_personality = character_1_personality;
    this.character_1_speaking_style = character_1_speaking_style;
    this.character_2_name = character_2_name;
    this.character_2_personality = character_2_personality;
    this.character_2_speaking_style = character_2_speaking_style;
    this.character_3_name = character_3_name;
    this.character_3_personality = character_3_personality;
    this.character_3_speaking_style = character_3_speaking_style;
    this.scene_types = scene_types;
    this.category = category;
    this.job_id = job_id;
  }
}

/**
 * 自定义角色播客请求体（API请求用）
 */
class CharacterRequestBody {
  characters: CharacterInfo[];
  text: string; // 文本素材（必需）
  topic?: string;
  silence_interval: number;

  constructor(characters: CharacterInfo[], text: string, topic: string | undefined, silence_interval: number) {
    // 后端强制要求使用voice_url（云存储URL）
    // characters中的voice_url字段会被后端直接使用
    this.characters = characters;
    this.text = text; // 文本素材（必需）
    this.topic = topic;
    this.silence_interval = silence_interval;
  }
}

/**
 * 主题深度播客请求体（API请求用）
 */
class DeepPodcastRequestBody {
  topic: string;
  role_voices?: Record<string, string>; // base64音频（如果不使用云存储）
  role_voice_urls?: Record<string, string>; // 云存储URL（如果使用云存储）
  num_characters: number;
  depth_level: string;
  silence_interval: number;

  constructor(
    topic: string,
    role_voices: Record<string, string> | undefined,
    role_voice_urls: Record<string, string> | undefined,
    num_characters: number,
    depth_level: string,
    silence_interval: number
  ) {
    this.topic = topic;
    this.role_voices = role_voices;
    this.role_voice_urls = role_voice_urls;
    this.num_characters = num_characters;
    this.depth_level = depth_level;
    this.silence_interval = silence_interval;
  }
}

/**
 * API响应
 */
export interface ApiResponse<T = Record<string, Object>> {
  success: boolean;
  message: string;
  data?: T;
  error?: string;
}

/**
 * 错误响应（用于错误处理）
 */
interface ErrorResponse {
  success?: boolean;
  message?: string;
  error?: string;
}

/**
 * 播客生成结果
 */
interface UploadStatus {
  status: string;
  bucket?: string;
  object?: string;
  url?: string;
  http_status?: number;
  response_text?: string;
  reason?: string;
}

export interface PodcastResult {
  // 音频数据（如果已上传到云存储，此字段可能为空，优先使用audio_url）
  audio_base64?: string;
  audio_path: string;
  file_size_mb: number;
  script: string;
  roles?: string[];
  characters?: string[];
  topic?: string;
  depth_level?: string;

  // 云存储直链（优先使用，避免响应体过大）
  audio_url?: string;

  // 上传状态信息（可用于前端展示）
  agc_upload_status?: UploadStatus;
}

/**
 * 播客服务类
 */
export class PodcastService {
  private static instance: PodcastService;
  private baseUrl: string;

  private constructor() {
    // 规范化base URL（移除末尾斜杠）
    this.baseUrl = PodcastConfig.API_BASE_URL.replace(/\/+$/, '');
    Logger.info(TAG, `初始化PodcastService，Base URL: ${this.baseUrl}`);
  }

  public static getInstance(): PodcastService {
    if (!PodcastService.instance) {
      PodcastService.instance = new PodcastService();
    }
    return PodcastService.instance;
  }

  /**
   * 构建完整的API URL
   */
  private buildApiUrl(path: string): string {
    if (PodcastConfig.USE_CLOUD_FUNCTION) {
      // 云函数模式：直接使用base URL
      return this.baseUrl;
    } else {
      // 直接API模式：拼接路径
      const cleanPath = path.startsWith('/') ? path : `/${path}`;
      return `${this.baseUrl}${cleanPath}`;
    }
  }

  /**
   * 获取任务进度
   */
  async getProgress(jobId: string): Promise<ProgressStatus | null> {
    return new Promise<ProgressStatus | null>((resolve) => {
      try {
        // 验证 jobId 是否有效（不能为空字符串、null 或 undefined）
        if (!jobId || jobId.trim().length === 0) {
          Logger.warn(TAG, `getProgress: jobId 为空，跳过请求`);
          resolve(null);
          return;
        }
        const httpRequest = http.createHttp();
        const url = this.buildApiUrl(`/api/v1/podcast/progress/${jobId}`);
        const options: http.HttpRequestOptions = {
          method: http.RequestMethod.GET,
          connectTimeout: 10000,
          readTimeout: 10000
        };
        httpRequest.request(url, options, (err: BusinessError, data: http.HttpResponse) => {
          httpRequest.destroy();
          if (err || !data || data.responseCode !== 200) {
            resolve(null);
            return;
          }
          try {
            resolve(JSON.parse(data.result.toString()) as ProgressStatus);
          } catch {
            resolve(null);
          }
        });
      } catch {
        resolve(null);
      }
    });
  }

  /**
   * 启动进度轮询
   * 使用HTTP GET请求定期获取任务进度（每5秒一次）
   * 注意：HarmonyOS的http模块不支持SSE流式读取，因此使用轮询方式
   * @param jobId 任务ID
   * @param onProgress 进度回调
   * @returns 返回清理函数，用于停止轮询
   */
  private startProgressPolling(
    jobId: string,
    onProgress: (progress: ProgressStatus) => void
  ): () => void {
    let pollingInterval: number | null = null;
    let isPolling = true;

    const poll = async () => {
      if (!isPolling) {
        return;
      }

      try {
        const progress = await this.getProgress(jobId);
        if (progress) {
          onProgress(progress);
          
          // 如果任务完成，停止轮询
          if (progress.done) {
            Logger.info(TAG, `任务完成，停止轮询: job_id=${jobId}`);
            isPolling = false;
            if (pollingInterval !== null) {
              clearTimeout(pollingInterval);
              pollingInterval = null;
            }
            return;
          }
        }
      } catch (error) {
        Logger.error(TAG, `轮询进度失败: ${JSON.stringify(error)}`);
      }

      // 继续轮询（如果还在运行）
      if (isPolling) {
        pollingInterval = setTimeout(poll, 5000) as number; // 每5秒轮询一次
      }
    };

    // 立即开始第一次轮询
    poll();

    // 返回清理函数
    return () => {
      isPolling = false;
      if (pollingInterval !== null) {
        clearTimeout(pollingInterval);
        pollingInterval = null;
      }
    };
  }

  /**
   * 处理HTTP响应
   */
  private handleResponse<T>(
    err: BusinessError | null,
    data: http.HttpResponse | null,
    defaultError: string
  ): ApiResponse<T> {
    if (err) {
      Logger.error(TAG, `${defaultError}: ${JSON.stringify(err)}`);
      return {
        success: false,
        message: defaultError,
        error: err.message || String(err) || '网络请求失败',
      };
    }

    if (!data) {
      Logger.error(TAG, `${defaultError}: 响应数据为空`);
      return {
        success: false,
        message: defaultError,
        error: '响应数据为空',
      };
    }

    // 处理非200状态码
    if (data.responseCode !== 200) {
      Logger.error(TAG, `${defaultError}: HTTP ${data.responseCode}`);
      try {
        const errorResult = JSON.parse(data.result.toString()) as ErrorResponse;
        return {
          success: false,
          message: errorResult.message || defaultError,
          error: errorResult.error || `HTTP ${data.responseCode}`,
        };
      } catch {
        return {
          success: false,
          message: defaultError,
          error: `HTTP ${data.responseCode}: ${data.result.toString()}`,
        };
      }
    }

    // 解析响应数据
    try {
      const result = JSON.parse(data.result.toString()) as ApiResponse<T>;
      return result;
    } catch (parseError) {
      Logger.error(TAG, `解析响应失败: ${JSON.stringify(parseError)}`);
      return {
        success: false,
        message: '解析响应失败',
        error: parseError instanceof Error ? parseError.message : String(parseError),
      };
    }
  }

  /**
   * 健康检查
   */
  async healthCheck(): Promise<boolean> {
    return new Promise<boolean>((resolve) => {
      try {
        const httpRequest = http.createHttp();
        const options: http.HttpRequestOptions = {
          method: http.RequestMethod.GET,
          connectTimeout: 10000,
          readTimeout: 10000,
          header: {
            'Content-Type': 'application/json',
          },
        };

        // 健康检查路径
        const healthUrl = PodcastConfig.USE_CLOUD_FUNCTION
          ? `${this.baseUrl}?path=health`
          : this.buildApiUrl('/health');

        Logger.info(TAG, `健康检查请求: ${healthUrl}`);

        httpRequest.request(
          healthUrl,
          options,
          (err: BusinessError, data: http.HttpResponse) => {
            httpRequest.destroy();
            if (err) {
              Logger.error(TAG, `健康检查失败: ${JSON.stringify(err)}`);
              resolve(false);
            } else if (data && data.responseCode === 200) {
              Logger.info(TAG, '健康检查成功');
              resolve(true);
            } else {
              Logger.warn(TAG, `健康检查返回非200状态码: ${data?.responseCode}`);
              resolve(false);
            }
          }
        );
      } catch (error) {
        Logger.error(TAG, `健康检查异常: ${JSON.stringify(error)}`);
        resolve(false);
      }
    });
  }

  /**
   * 生成多角色互动播客
   * @param request 播客生成请求
   * @param onProgress 进度回调（可选，通过HTTP轮询获取进度更新）
   */
  async generateMultiRolePodcast(
    request: MultiRoleRequest,
    onProgress?: (progress: ProgressStatus) => void
  ): Promise<ApiResponse<PodcastResult>> {
    return new Promise<ApiResponse<PodcastResult>>((resolve) => {
      try {
        // 验证请求参数（text、text_file_url或input_url至少有一个）
        const hasText = request.text && request.text.trim().length > 0;
        // 支持单个URL字符串或URL数组
        const hasTextFile = request.text_file_url && (
          Array.isArray(request.text_file_url) 
            ? request.text_file_url.length > 0 && request.text_file_url.some(url => url && url.trim().length > 0)
            : request.text_file_url.trim().length > 0
        );
        const hasInputUrl = request.input_url && request.input_url.trim().length > 0;
        
        if (!hasText && !hasTextFile && !hasInputUrl) {
          resolve({
            success: false,
            message: '播客文本不能为空，请上传文本文件、输入文本或提供输入URL',
            error: '文本内容为空',
          });
          return;
        }

        // 强制使用云存储URL（后端已强制要求）
        const roleVoiceUrls = request.role_voice_urls;
        
        // 验证音色数据
        if (!roleVoiceUrls || Object.keys(roleVoiceUrls).length === 0) {
          resolve({
            success: false,
            message: '至少需要一个角色的音色文件URL',
            error: '角色音色URL为空',
          });
          return;
        }

        const requestBody = new MultiRoleRequestBody(
          request.text, // text
          request.text_file_url, // text_file_url
          request.input_type, // input_type
          request.input_url, // input_url
          request.instruction, // instruction
          undefined, // role_voices已废弃
          roleVoiceUrls, // role_voice_urls - 使用云存储URL
          request.silence_interval || 300, // silence_interval
          request.podcast_name,
          request.topic,
          request.character_1_name,
          request.character_1_personality,
          request.character_1_speaking_style,
          request.character_2_name,
          request.character_2_personality,
          request.character_2_speaking_style,
          request.character_3_name,
          request.character_3_personality,
          request.character_3_speaking_style,
          request.scene_types,
          request.category,
          request.job_id
        );

        const roleCount = Object.keys(roleVoiceUrls).length;
        const textLength = request.text ? request.text.length : 0;
        const textFileStatus = request.text_file_url 
          ? (Array.isArray(request.text_file_url) ? `${request.text_file_url.length}个文件` : '是')
          : '否';
        Logger.info(TAG,
          `开始生成多角色播客: 文本长度=${textLength}, 文本文件=${textFileStatus}, 角色数=${roleCount}, 使用云存储`);

        const httpRequest = http.createHttp();
        const requestData = JSON.stringify(requestBody);
        const options: http.HttpRequestOptions = {
          method: http.RequestMethod.POST,
          header: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          },
          extraData: requestData,
          connectTimeout: PodcastConfig.API_TIMEOUT,
          readTimeout: PodcastConfig.API_TIMEOUT,
        };

        const apiUrl = PodcastConfig.USE_CLOUD_FUNCTION
          ? this.baseUrl
          : this.buildApiUrl('/api/v1/podcast/multi_role');

        Logger.info(TAG, `请求URL: ${apiUrl}, 请求体大小: ${requestData.length} bytes`);

        // 如果提供了job_id和进度回调，启动HTTP轮询获取进度
        // 注意：HarmonyOS的http模块不支持SSE流式读取，因此直接使用轮询方式
        let stopPolling: (() => void) | null = null;
        
        if (request.job_id && onProgress) {
          stopPolling = this.startProgressPolling(request.job_id, onProgress);
          Logger.info(TAG, `已启动HTTP轮询进度更新: job_id=${request.job_id}`);
        }

        httpRequest.request(
          apiUrl,
          options,
          (err: BusinessError, data: http.HttpResponse) => {
            httpRequest.destroy();
            
            // 停止轮询（如果正在运行）
            if (stopPolling) {
              stopPolling();
            }
            
            const result = this.handleResponse<PodcastResult>(err, data || null, '多角色播客生成失败');
            if (result.success) {
              Logger.info(TAG, '多角色播客生成成功');
            } else {
              Logger.error(TAG, `多角色播客生成失败: ${result.error || result.message}`);
            }
            resolve(result);
          }
        );
      } catch (error) {
        // 提取详细的错误信息
        let errorMessage = '未知错误';
        let errorDetails = '';
        
        if (error instanceof Error) {
          errorMessage = error.message || '错误对象没有消息';
          errorDetails = error.stack || error.toString();
        } else if (error && typeof error === 'object') {
          // 尝试提取 BusinessError 的属性
          const businessError = error as BusinessError;
          errorMessage = businessError.message || businessError.code?.toString() || '业务错误';
          errorDetails = `code: ${businessError.code}, message: ${businessError.message}`;
        } else {
          errorMessage = String(error) || '未知错误';
        }
        
        Logger.error(TAG, `多角色播客生成异常: ${errorMessage}`);
        Logger.error(TAG, `错误详情: ${errorDetails}`);
        Logger.error(TAG, `错误对象类型: ${typeof error}, 值: ${JSON.stringify(error)}`);
        
        resolve({
          success: false,
          message: '播客生成失败',
          error: errorMessage,
        });
      }
    });
  }

  /**
   * 生成自定义角色播客
   * @param request 播客生成请求
   * @param jobId 任务ID（可选，用于HTTP轮询进度更新）
   * @param onProgress 进度回调（可选，通过HTTP轮询获取进度更新）
   */
  async generateCharacterPodcast(
    request: CharacterRequest,
    jobId?: string,
    onProgress?: (progress: ProgressStatus) => void
  ): Promise<ApiResponse<PodcastResult>> {
    return new Promise<ApiResponse<PodcastResult>>((resolve) => {
      try {
        // 验证请求参数
        if (!request.characters || request.characters.length < 2) {
          resolve({
            success: false,
            message: '至少需要2个角色',
            error: '角色数量不足',
          });
          return;
        }

        if (request.characters.length > 4) {
          resolve({
            success: false,
            message: '最多支持4个角色',
            error: '角色数量过多',
          });
          return;
        }

        // 验证文本素材（必需）
        if (!request.text || request.text.trim().length === 0) {
          resolve({
            success: false,
            message: '文本素材不能为空',
            error: '文本素材缺失',
          });
          return;
        }

        // 验证角色信息（强制使用云存储URL）
        for (const char of request.characters) {
          if (!char.name) {
            resolve({
              success: false,
              message: '角色名称不能为空',
              error: '角色信息不完整',
            });
            return;
          }
          if (!char.voice_url) {
            resolve({
              success: false,
              message: `角色 ${char.name} 的音色文件URL不能为空`,
              error: '角色音色URL缺失',
            });
            return;
          }
        }

        const requestBody = new CharacterRequestBody(
          request.characters,
          request.text, // 文本素材（必需）
          request.topic,
          request.silence_interval || 300
        );

        Logger.info(TAG,
          `开始生成自定义角色播客: 主题=${request.topic || '无'}, 角色数=${request.characters.length}, 使用云存储`);

        const httpRequest = http.createHttp();
        const requestData = JSON.stringify(requestBody);
        const options: http.HttpRequestOptions = {
          method: http.RequestMethod.POST,
          header: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          },
          extraData: requestData,
          connectTimeout: PodcastConfig.API_TIMEOUT,
          readTimeout: PodcastConfig.API_TIMEOUT,
        };

        const apiUrl = PodcastConfig.USE_CLOUD_FUNCTION
          ? this.baseUrl
          : this.buildApiUrl('/api/v1/podcast/character');

        Logger.info(TAG, `请求URL: ${apiUrl}, 请求体大小: ${requestData.length} bytes`);

        // 如果提供了jobId和进度回调，启动HTTP轮询获取进度
        // 注意：HarmonyOS的http模块不支持SSE流式读取，因此直接使用轮询方式
        let stopPolling: (() => void) | null = null;
        
        if (jobId && onProgress) {
          stopPolling = this.startProgressPolling(jobId, onProgress);
          Logger.info(TAG, `已启动HTTP轮询进度更新: job_id=${jobId}`);
        }

        httpRequest.request(
          apiUrl,
          options,
          (err: BusinessError, data: http.HttpResponse) => {
            httpRequest.destroy();
            
            // 停止轮询（如果正在运行）
            if (stopPolling) {
              stopPolling();
            }
            
            const result = this.handleResponse<PodcastResult>(err, data || null, '自定义角色播客生成失败');
            if (result.success) {
              Logger.info(TAG, '自定义角色播客生成成功');
            } else {
              Logger.error(TAG, `自定义角色播客生成失败: ${result.error || result.message}`);
            }
            resolve(result);
          }
        );
      } catch (error) {
        Logger.error(TAG, `自定义角色播客生成异常: ${JSON.stringify(error)}`);
        resolve({
          success: false,
          message: '播客生成失败',
          error: error instanceof Error ? error.message : String(error),
        });
      }
    });
  }

  /**
   * 分析文本素材，自动推断播客信息
   */
  async analyzeTextForPodcast(request: AnalyzeTextRequest): Promise<ApiResponse<AnalyzeTextResult>> {
    return new Promise<ApiResponse<AnalyzeTextResult>>((resolve) => {
      try {
        // 验证请求参数
        if (!request.text || request.text.trim().length === 0) {
          resolve({
            success: false,
            message: '文本内容不能为空',
            error: '文本内容为空',
          });
          return;
        }

        Logger.info(TAG, `开始分析文本素材: 文本长度=${request.text.length}`);

        const httpRequest = http.createHttp();
        const requestData = JSON.stringify({ text: request.text });
        const options: http.HttpRequestOptions = {
          method: http.RequestMethod.POST,
          header: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          },
          extraData: requestData,
          connectTimeout: 30000, // 30秒超时
          readTimeout: 30000,
        };

        const apiUrl = PodcastConfig.USE_CLOUD_FUNCTION
          ? this.baseUrl
          : this.buildApiUrl('/api/v1/podcast/analyze');

        Logger.info(TAG, `请求URL: ${apiUrl}`);

        httpRequest.request(
          apiUrl,
          options,
          (err: BusinessError, data: http.HttpResponse) => {
            httpRequest.destroy();
            const result = this.handleResponse<AnalyzeTextResult>(err, data || null, '文本分析失败');
            if (result.success) {
              Logger.info(TAG, '文本分析成功');
            } else {
              Logger.error(TAG, `文本分析失败: ${result.error || result.message}`);
            }
            resolve(result);
          }
        );
      } catch (error) {
        Logger.error(TAG, `文本分析异常: ${JSON.stringify(error)}`);
        resolve({
          success: false,
          message: '分析失败',
          error: error instanceof Error ? error.message : String(error),
        });
      }
    });
  }

  /**
   * 生成主题深度播客
   * @param request 播客生成请求
   * @param jobId 任务ID（可选，用于HTTP轮询进度更新）
   * @param onProgress 进度回调（可选，通过HTTP轮询获取进度更新）
   */
  async generateDeepPodcast(
    request: DeepPodcastRequest,
    jobId?: string,
    onProgress?: (progress: ProgressStatus) => void
  ): Promise<ApiResponse<PodcastResult>> {
    return new Promise<ApiResponse<PodcastResult>>((resolve) => {
      try {
        // 验证请求参数
        if (!request.topic || request.topic.trim().length === 0) {
          resolve({
            success: false,
            message: '播客主题不能为空',
            error: '主题为空',
          });
          return;
        }

        const numCharacters = request.num_characters || 2;
        if (numCharacters < 1 || numCharacters > 3) {
          resolve({
            success: false,
            message: '角色数量必须在1-3个之间',
            error: '角色数量无效',
          });
          return;
        }

        const depthLevel = request.depth_level || '深度';
        if (!['深度', '中等', '浅层'].includes(depthLevel)) {
          resolve({
            success: false,
            message: '深度级别必须是：深度、中等或浅层',
            error: '深度级别无效',
          });
          return;
        }

        // 强制使用云存储URL（后端已强制要求）
        const roleVoiceUrls = request.role_voice_urls;
        const roleNames = ['角色A', '角色B', '角色C'].slice(0, numCharacters);
        
        // 验证音色数据
        if (!roleVoiceUrls || Object.keys(roleVoiceUrls).length !== numCharacters) {
          resolve({
            success: false,
            message: `角色音色URL数量必须与角色数量(${numCharacters})一致`,
            error: '角色音色URL数量不匹配',
          });
          return;
        }
        // 验证每个角色都有音色URL
        for (const roleName of roleNames) {
          if (!roleVoiceUrls[roleName]) {
            resolve({
              success: false,
              message: `缺少角色 ${roleName} 的音色文件URL`,
              error: '角色音色URL缺失',
            });
            return;
          }
        }

        const requestBody = new DeepPodcastRequestBody(
          request.topic,
          undefined, // role_voices已废弃
          roleVoiceUrls, // 使用云存储URL
          numCharacters,
          depthLevel,
          request.silence_interval || 300
        );

        Logger.info(TAG,
          `开始生成主题深度播客: 主题=${request.topic}, 深度=${depthLevel}, 角色数=${numCharacters}, 使用云存储`);

        const httpRequest = http.createHttp();
        const requestData = JSON.stringify(requestBody);
        const options: http.HttpRequestOptions = {
          method: http.RequestMethod.POST,
          header: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          },
          extraData: requestData,
          connectTimeout: PodcastConfig.API_TIMEOUT,
          readTimeout: PodcastConfig.API_TIMEOUT,
        };

        const apiUrl = PodcastConfig.USE_CLOUD_FUNCTION
          ? this.baseUrl
          : this.buildApiUrl('/api/v1/podcast/deep');

        Logger.info(TAG, `请求URL: ${apiUrl}, 请求体大小: ${requestData.length} bytes`);

        // 如果提供了jobId和进度回调，启动HTTP轮询获取进度
        // 注意：HarmonyOS的http模块不支持SSE流式读取，因此直接使用轮询方式
        let stopPolling: (() => void) | null = null;
        
        if (jobId && onProgress) {
          stopPolling = this.startProgressPolling(jobId, onProgress);
          Logger.info(TAG, `已启动HTTP轮询进度更新: job_id=${jobId}`);
        }

        httpRequest.request(
          apiUrl,
          options,
          (err: BusinessError, data: http.HttpResponse) => {
            httpRequest.destroy();
            
            // 停止轮询（如果正在运行）
            if (stopPolling) {
              stopPolling();
            }
            
            const result = this.handleResponse<PodcastResult>(err, data || null, '主题深度播客生成失败');
            if (result.success) {
              Logger.info(TAG, '主题深度播客生成成功');
            } else {
              Logger.error(TAG, `主题深度播客生成失败: ${result.error || result.message}`);
            }
            resolve(result);
          }
        );
      } catch (error) {
        // 提取详细的错误信息
        let errorMessage = '未知错误';
        let errorDetails = '';
        
        if (error instanceof Error) {
          errorMessage = error.message || '错误对象没有消息';
          errorDetails = error.stack || error.toString();
        } else if (error && typeof error === 'object') {
          // 尝试提取 BusinessError 的属性
          const businessError = error as BusinessError;
          errorMessage = businessError.message || businessError.code?.toString() || '业务错误';
          errorDetails = `code: ${businessError.code}, message: ${businessError.message}`;
        } else {
          errorMessage = String(error) || '未知错误';
        }
        
        Logger.error(TAG, `主题深度播客生成异常: ${errorMessage}`);
        Logger.error(TAG, `错误详情: ${errorDetails}`);
        Logger.error(TAG, `错误对象类型: ${typeof error}, 值: ${JSON.stringify(error)}`);
        
        resolve({
          success: false,
          message: '播客生成失败',
          error: errorMessage,
        });
      }
    });
  }

  /**
   * 批量生成播客
   * @param request 批量生成请求
   * @returns 批量任务响应
   */
  async batchGeneratePodcasts(
    request: BatchRequest
  ): Promise<ApiResponse<BatchResponse>> {
    return new Promise<ApiResponse<BatchResponse>>((resolve) => {
      try {
        // 验证请求参数
        if (!request.tasks || request.tasks.length === 0) {
          resolve({
            success: false,
            message: '任务列表不能为空',
            error: '任务列表为空',
          });
          return;
        }

        if (request.tasks.length > 50) {
          resolve({
            success: false,
            message: '单次批量任务数量不能超过50个',
            error: '任务数量过多',
          });
          return;
        }

        Logger.info(TAG, `开始批量生成播客: 任务数量=${request.tasks.length}`);

        const httpRequest = http.createHttp();
        const requestData = JSON.stringify(request);
        const options: http.HttpRequestOptions = {
          method: http.RequestMethod.POST,
          header: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          },
          extraData: requestData,
          connectTimeout: PodcastConfig.API_TIMEOUT,
          readTimeout: PodcastConfig.API_TIMEOUT,
        };

        const apiUrl = PodcastConfig.USE_CLOUD_FUNCTION
          ? this.baseUrl
          : this.buildApiUrl('/api/v1/podcast/batch');

        Logger.info(TAG, `批量生成请求URL: ${apiUrl}, 任务数量: ${request.tasks.length}`);

        httpRequest.request(
          apiUrl,
          options,
          (err: BusinessError, data: http.HttpResponse) => {
            httpRequest.destroy();
            
            const result = this.handleResponse<BatchResponse>(err, data || null, '批量生成播客失败');
            if (result.success) {
              Logger.info(TAG, `批量生成播客成功: 已提交 ${result.data?.total || 0} 个任务`);
            } else {
              Logger.error(TAG, `批量生成播客失败: ${result.error || result.message}`);
            }
            resolve(result);
          }
        );
      } catch (error) {
        let errorMessage = '未知错误';
        if (error instanceof Error) {
          errorMessage = error.message || '错误对象没有消息';
        } else if (error && typeof error === 'object') {
          const businessError = error as BusinessError;
          errorMessage = businessError.message || businessError.code?.toString() || '业务错误';
        } else {
          errorMessage = String(error) || '未知错误';
        }
        
        Logger.error(TAG, `批量生成播客异常: ${errorMessage}`);
        
        resolve({
          success: false,
          message: '批量生成播客失败',
          error: errorMessage,
        });
      }
    });
  }

  /**
   * 查询任务状态
   * @param taskId 任务ID
   * @returns 任务状态
   */
  async getTaskStatus(taskId: string): Promise<ApiResponse<TaskStatus>> {
    return new Promise<ApiResponse<TaskStatus>>((resolve) => {
      try {
        const httpRequest = http.createHttp();
        const options: http.HttpRequestOptions = {
          method: http.RequestMethod.GET,
          header: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          },
          connectTimeout: PodcastConfig.API_TIMEOUT,
          readTimeout: PodcastConfig.API_TIMEOUT,
        };

        const apiUrl = PodcastConfig.USE_CLOUD_FUNCTION
          ? this.baseUrl
          : this.buildApiUrl(`/api/v1/podcast/task/${taskId}`);

        Logger.info(TAG, `查询任务状态: ${apiUrl}`);

        httpRequest.request(
          apiUrl,
          options,
          (err: BusinessError, data: http.HttpResponse) => {
            httpRequest.destroy();
            
            const result = this.handleResponse<TaskStatus>(err, data || null, '查询任务状态失败');
            if (result.success) {
              Logger.info(TAG, `任务状态查询成功: ${taskId}, 状态=${result.data?.status}`);
            } else {
              Logger.error(TAG, `任务状态查询失败: ${result.error || result.message}`);
            }
            resolve(result);
          }
        );
      } catch (error) {
        let errorMessage = '未知错误';
        if (error instanceof Error) {
          errorMessage = error.message || '错误对象没有消息';
        } else if (error && typeof error === 'object') {
          const businessError = error as BusinessError;
          errorMessage = businessError.message || businessError.code?.toString() || '业务错误';
        } else {
          errorMessage = String(error) || '未知错误';
        }
        
        Logger.error(TAG, `查询任务状态异常: ${errorMessage}`);
        
        resolve({
          success: false,
          message: '查询任务状态失败',
          error: errorMessage,
        });
      }
    });
  }
}

export const podcastService = PodcastService.getInstance();

