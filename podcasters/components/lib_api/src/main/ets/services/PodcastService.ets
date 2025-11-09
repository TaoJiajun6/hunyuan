import { http } from '@kit.NetworkKit';
import { BusinessError } from '@kit.BasicServicesKit';
import { Logger } from 'lib_common';

const TAG = '[PodcastService]';

/**
 * 播客API服务配置
 */
export class PodcastConfig {
  // 配置说明：
  // 1. 使用云函数：设置为华为AGC云函数的HTTP触发器URL
  //    例如：'https://your-cloud-function-url.com'
  // 2. 使用本地服务器：设置为本地服务器的IP地址和端口
  //    例如：'http://10.10.210.52:8000'
  // 3. 使用远程服务器：设置为远程服务器的URL
  //    例如：'https://your-server.com'
  static readonly API_BASE_URL: string = 'http://10.10.210.52:8000'; // 请替换为实际的服务器地址或云函数URL
  static readonly API_TIMEOUT: number = 300000; // 5分钟超时（播客生成可能需要较长时间）
  
  // 是否使用云函数（如果使用云函数，路径可能不同）
  // 云函数通过HTTP触发器调用，URL格式通常为：https://your-cloud-function-url.com
  // 本地/远程服务器URL格式：http://ip:port 或 https://domain.com
  static readonly USE_CLOUD_FUNCTION: boolean = false; // 设置为 true 如果使用云函数
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
  voice: string; // base64编码的音频数据
}

/**
 * 多角色播客请求
 */
export interface MultiRoleRequest {
  text: string;
  role_voices: Record<string, string>; // 角色名 -> base64音频
  silence_interval?: number;
}

/**
 * 自定义角色播客请求
 */
export interface CharacterRequest {
  characters: CharacterInfo[];
  topic?: string;
  silence_interval?: number;
}

/**
 * 主题深度播客请求
 */
export interface DeepPodcastRequest {
  topic: string;
  role_voices: Record<string, string>; // 角色名 -> base64音频
  num_characters?: number; // 2-3
  depth_level?: string; // "深度" | "中等" | "浅层"
  silence_interval?: number;
}

/**
 * 多角色播客请求体（API请求用）
 */
class MultiRoleRequestBody {
  text: string;
  role_voices: Record<string, string>;
  silence_interval: number;

  constructor(text: string, role_voices: Record<string, string>, silence_interval: number) {
    this.text = text;
    this.role_voices = role_voices;
    this.silence_interval = silence_interval;
  }
}

/**
 * 自定义角色播客请求体（API请求用）
 */
class CharacterRequestBody {
  characters: CharacterInfo[];
  topic?: string;
  silence_interval: number;

  constructor(characters: CharacterInfo[], topic: string | undefined, silence_interval: number) {
    this.characters = characters;
    this.topic = topic;
    this.silence_interval = silence_interval;
  }
}

/**
 * 主题深度播客请求体（API请求用）
 */
class DeepPodcastRequestBody {
  topic: string;
  role_voices: Record<string, string>;
  num_characters: number;
  depth_level: string;
  silence_interval: number;

  constructor(topic: string, role_voices: Record<string, string>, num_characters: number, depth_level: string, silence_interval: number) {
    this.topic = topic;
    this.role_voices = role_voices;
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
 * 播客生成结果
 */
export interface PodcastResult {
  audio_base64: string;
  audio_path: string;
  file_size_mb: number;
  script: string;
  roles?: string[];
  characters?: string[];
  topic?: string;
  depth_level?: string;
}

/**
 * 播客服务类
 */
export class PodcastService {
  private static instance: PodcastService;

  private constructor() {
  }

  public static getInstance(): PodcastService {
    if (!PodcastService.instance) {
      PodcastService.instance = new PodcastService();
    }
    return PodcastService.instance;
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
        };

        // 健康检查路径：云函数使用查询参数，本地服务器使用路径
        const healthPath = PodcastConfig.USE_CLOUD_FUNCTION 
          ? `${PodcastConfig.API_BASE_URL}?path=health` 
          : `${PodcastConfig.API_BASE_URL}/health`;
        httpRequest.request(
          healthPath,
          options,
          (err: BusinessError, data: http.HttpResponse) => {
            httpRequest.destroy();
            if (err) {
              Logger.error(TAG, `健康检查失败: ${JSON.stringify(err)}`);
              resolve(false);
            } else if (data.responseCode === 200) {
              Logger.info(TAG, '健康检查成功');
              resolve(true);
            } else {
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
   */
  async generateMultiRolePodcast(request: MultiRoleRequest): Promise<ApiResponse<PodcastResult>> {
    return new Promise<ApiResponse<PodcastResult>>((resolve) => {
      try {
        const requestBody = new MultiRoleRequestBody(
          request.text,
          request.role_voices,
          request.silence_interval || 300
        );

        Logger.info(TAG, `开始生成多角色播客: ${JSON.stringify({ text: request.text, roles: Object.keys(request.role_voices) })}`);

        const httpRequest = http.createHttp();
        const options: http.HttpRequestOptions = {
          method: http.RequestMethod.POST,
          header: {
            'Content-Type': 'application/json',
          },
          extraData: JSON.stringify(requestBody),
          connectTimeout: PodcastConfig.API_TIMEOUT,
          readTimeout: PodcastConfig.API_TIMEOUT,
        };

        // 多角色播客路径：云函数直接使用根路径，本地服务器使用完整路径
        const multiRolePath = PodcastConfig.USE_CLOUD_FUNCTION 
          ? PodcastConfig.API_BASE_URL 
          : `${PodcastConfig.API_BASE_URL}/api/v1/podcast/multi_role`;
        httpRequest.request(
          multiRolePath,
          options,
          (err: BusinessError, data: http.HttpResponse) => {
            httpRequest.destroy();
            if (err) {
              Logger.error(TAG, `多角色播客生成异常: ${JSON.stringify(err)}`);
              resolve({
                success: false,
                message: '播客生成失败',
                error: err.message || String(err),
              });
            } else {
              try {
                const result = JSON.parse(data.result.toString()) as ApiResponse<PodcastResult>;
                if (data.responseCode === 200 && result.success) {
                  Logger.info(TAG, '多角色播客生成成功');
                  resolve(result);
                } else {
                  Logger.error(TAG, `多角色播客生成失败: ${result.error || result.message}`);
                  resolve(result);
                }
              } catch (parseError) {
                Logger.error(TAG, `解析响应失败: ${JSON.stringify(parseError)}`);
                resolve({
                  success: false,
                  message: '解析响应失败',
                  error: parseError instanceof Error ? parseError.message : String(parseError),
                });
              }
            }
          }
        );
      } catch (error) {
        Logger.error(TAG, `多角色播客生成异常: ${JSON.stringify(error)}`);
        resolve({
          success: false,
          message: '播客生成失败',
          error: error instanceof Error ? error.message : String(error),
        });
      }
    });
  }

  /**
   * 生成自定义角色播客
   */
  async generateCharacterPodcast(request: CharacterRequest): Promise<ApiResponse<PodcastResult>> {
    return new Promise<ApiResponse<PodcastResult>>((resolve) => {
      try {
        const requestBody = new CharacterRequestBody(
          request.characters,
          request.topic,
          request.silence_interval || 300
        );

        Logger.info(TAG, `开始生成自定义角色播客: ${JSON.stringify({ topic: request.topic, characters: request.characters.map(c => c.name) })}`);

        const httpRequest = http.createHttp();
        const options: http.HttpRequestOptions = {
          method: http.RequestMethod.POST,
          header: {
            'Content-Type': 'application/json',
          },
          extraData: JSON.stringify(requestBody),
          connectTimeout: PodcastConfig.API_TIMEOUT,
          readTimeout: PodcastConfig.API_TIMEOUT,
        };

        // 自定义角色播客路径：云函数直接使用根路径，本地服务器使用完整路径
        const characterPath = PodcastConfig.USE_CLOUD_FUNCTION 
          ? PodcastConfig.API_BASE_URL 
          : `${PodcastConfig.API_BASE_URL}/api/v1/podcast/character`;
        httpRequest.request(
          characterPath,
          options,
          (err: BusinessError, data: http.HttpResponse) => {
            httpRequest.destroy();
            if (err) {
              Logger.error(TAG, `自定义角色播客生成异常: ${JSON.stringify(err)}`);
              resolve({
                success: false,
                message: '播客生成失败',
                error: err.message || String(err),
              });
            } else {
              try {
                const result = JSON.parse(data.result.toString()) as ApiResponse<PodcastResult>;
                if (data.responseCode === 200 && result.success) {
                  Logger.info(TAG, '自定义角色播客生成成功');
                  resolve(result);
                } else {
                  Logger.error(TAG, `自定义角色播客生成失败: ${result.error || result.message}`);
                  resolve(result);
                }
              } catch (parseError) {
                Logger.error(TAG, `解析响应失败: ${JSON.stringify(parseError)}`);
                resolve({
                  success: false,
                  message: '解析响应失败',
                  error: parseError instanceof Error ? parseError.message : String(parseError),
                });
              }
            }
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
   * 生成主题深度播客
   */
  async generateDeepPodcast(request: DeepPodcastRequest): Promise<ApiResponse<PodcastResult>> {
    return new Promise<ApiResponse<PodcastResult>>((resolve) => {
      try {
        const requestBody = new DeepPodcastRequestBody(
          request.topic,
          request.role_voices,
          request.num_characters || 2,
          request.depth_level || '深度',
          request.silence_interval || 300
        );

        Logger.info(TAG, `开始生成主题深度播客: ${JSON.stringify({ topic: request.topic, depth_level: request.depth_level })}`);

        const httpRequest = http.createHttp();
        const options: http.HttpRequestOptions = {
          method: http.RequestMethod.POST,
          header: {
            'Content-Type': 'application/json',
          },
          extraData: JSON.stringify(requestBody),
          connectTimeout: PodcastConfig.API_TIMEOUT,
          readTimeout: PodcastConfig.API_TIMEOUT,
        };

        // 主题深度播客路径：云函数直接使用根路径，本地服务器使用完整路径
        const deepPath = PodcastConfig.USE_CLOUD_FUNCTION 
          ? PodcastConfig.API_BASE_URL 
          : `${PodcastConfig.API_BASE_URL}/api/v1/podcast/deep`;
        httpRequest.request(
          deepPath,
          options,
          (err: BusinessError, data: http.HttpResponse) => {
            httpRequest.destroy();
            if (err) {
              Logger.error(TAG, `主题深度播客生成异常: ${JSON.stringify(err)}`);
              resolve({
                success: false,
                message: '播客生成失败',
                error: err.message || String(err),
              });
            } else {
              try {
                const result = JSON.parse(data.result.toString()) as ApiResponse<PodcastResult>;
                if (data.responseCode === 200 && result.success) {
                  Logger.info(TAG, '主题深度播客生成成功');
                  resolve(result);
                } else {
                  Logger.error(TAG, `主题深度播客生成失败: ${result.error || result.message}`);
                  resolve(result);
                }
              } catch (parseError) {
                Logger.error(TAG, `解析响应失败: ${JSON.stringify(parseError)}`);
                resolve({
                  success: false,
                  message: '解析响应失败',
                  error: parseError instanceof Error ? parseError.message : String(parseError),
                });
              }
            }
          }
        );
      } catch (error) {
        Logger.error(TAG, `主题深度播客生成异常: ${JSON.stringify(error)}`);
        resolve({
          success: false,
          message: '播客生成失败',
          error: error instanceof Error ? error.message : String(error),
        });
      }
    });
  }
}

export const podcastService = PodcastService.getInstance();

