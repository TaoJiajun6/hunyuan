import { cloudDatabase } from '@kit.CloudFoundationKit';
import { hilog } from '@kit.PerformanceAnalysisKit';
import { PodcastInfo } from '../database/PodcastInfo';
import { Logger } from 'lib_common';

const TAG = '[CloudDatabaseService]';

/**
 * 云数据库服务配置
 */
export class CloudDatabaseConfig {
  /**
   * 存储区名称
   * 需要在AGC控制台创建对应的存储区
   */
  static readonly ZONE_NAME: string = 'podcast';

  /**
   * 是否启用云数据库
   */
  static readonly ENABLED: boolean = true;
}

/**
 * 播客查询结果
 */
export interface PodcastQueryResult {
  /**
   * 播客列表
   */
  podcasts: PodcastInfo[];
  /**
   * 总数
   */
  total: number;
}

/**
 * 云数据库服务类
 * 用于访问AGC云数据库，查询和管理播客数据
 */
export class CloudDatabaseService {
  private static instance: CloudDatabaseService;
  private databaseZone: cloudDatabase.DatabaseZone | null = null;
  private initialized: boolean = false;

  private constructor() {
    Logger.info(TAG, '初始化CloudDatabaseService');
  }

  /**
   * 获取单例实例
   */
  public static getInstance(): CloudDatabaseService {
    if (!CloudDatabaseService.instance) {
      CloudDatabaseService.instance = new CloudDatabaseService();
    }
    return CloudDatabaseService.instance;
  }

  /**
   * 初始化数据库访问
   * 需要在应用启动时调用
   */
  public initialize(): void {
    if (this.initialized) {
      Logger.info(TAG, '数据库已初始化，跳过重复初始化');
      return;
    }

    if (!CloudDatabaseConfig.ENABLED) {
      Logger.warn(TAG, '云数据库未启用');
      return;
    }

    try {
      // 初始化DatabaseZone
      this.databaseZone = cloudDatabase.zone(CloudDatabaseConfig.ZONE_NAME);
      this.initialized = true;
      Logger.info(TAG, `数据库初始化成功，存储区: ${CloudDatabaseConfig.ZONE_NAME}`);
    } catch (error) {
      Logger.error(TAG, `数据库初始化失败: ${JSON.stringify(error)}`);
      this.initialized = false;
    }
  }

  /**
   * 检查是否已初始化
   */
  private checkInitialized(): boolean {
    if (!this.initialized || !this.databaseZone) {
      Logger.error(TAG, '数据库未初始化，请先调用initialize()');
      return false;
    }
    return true;
  }

  /**
   * 查询所有播客
   * @param limit 限制返回数量，默认不限制
   * @param category 按分类筛选，可选
   * @returns 播客列表
   */
  public async queryAllPodcasts(
    limit?: number,
    category?: string
  ): Promise<PodcastQueryResult> {
    if (!this.checkInitialized()) {
      return { podcasts: [], total: 0 };
    }

    try {
      // 创建查询条件
      const condition = new cloudDatabase.DatabaseQuery(PodcastInfo);

      // 如果指定了分类，添加分类筛选条件
      if (category && category.trim() !== '') {
        condition.equalTo('category', category);
      }

      // 按创建时间倒序排序
      condition.orderByDesc('created_at');

      // 如果指定了限制数量，添加limit
      if (limit && limit > 0) {
        condition.limit(limit);
      }

      // 执行查询
      const resultArray = await this.databaseZone!.query(condition);

      Logger.info(TAG, `查询成功，找到 ${resultArray.length} 条播客记录`);

      // 转换结果
      const podcasts = resultArray as PodcastInfo[];

      return {
        podcasts: podcasts,
        total: podcasts.length
      };
    } catch (error) {
      Logger.error(TAG, `查询播客失败: ${JSON.stringify(error)}`);
      hilog.error(0x0000, TAG, `查询播客失败: ${JSON.stringify(error)}`);
      return { podcasts: [], total: 0 };
    }
  }

  /**
   * 根据ID查询播客
   * @param id 播客ID
   * @returns 播客信息，如果不存在返回null
   */
  public async queryPodcastById(id: string): Promise<PodcastInfo | null> {
    if (!this.checkInitialized()) {
      return null;
    }

    try {
      const condition = new cloudDatabase.DatabaseQuery(PodcastInfo);
      condition.equalTo('id', id);

      const resultArray = await this.databaseZone!.query(condition);

      if (resultArray.length > 0) {
        return resultArray[0] as PodcastInfo;
      }

      return null;
    } catch (error) {
      Logger.error(TAG, `根据ID查询播客失败: ${JSON.stringify(error)}`);
      hilog.error(0x0000, TAG, `根据ID查询播客失败: ${JSON.stringify(error)}`);
      return null;
    }
  }

  /**
   * 根据标题查询播客（模糊匹配）
   * @param title 标题关键词
   * @param limit 限制返回数量
   * @returns 播客列表
   */
  public async queryPodcastsByTitle(
    title: string,
    limit?: number
  ): Promise<PodcastQueryResult> {
    if (!this.checkInitialized()) {
      return { podcasts: [], total: 0 };
    }

    try {
      const condition = new cloudDatabase.DatabaseQuery(PodcastInfo);
      condition.contains('title', title);
      condition.orderByDesc('created_at');

      if (limit && limit > 0) {
        condition.limit(limit);
      }

      const resultArray = await this.databaseZone!.query(condition);
      const podcasts = resultArray as PodcastInfo[];

      return {
        podcasts: podcasts,
        total: podcasts.length
      };
    } catch (error) {
      Logger.error(TAG, `根据标题查询播客失败: ${JSON.stringify(error)}`);
      hilog.error(0x0000, TAG, `根据标题查询播客失败: ${JSON.stringify(error)}`);
      return { podcasts: [], total: 0 };
    }
  }

  /**
   * 根据分类查询播客
   * @param category 分类名称
   * @param limit 限制返回数量
   * @returns 播客列表
   */
  public async queryPodcastsByCategory(
    category: string,
    limit?: number
  ): Promise<PodcastQueryResult> {
    if (!this.checkInitialized()) {
      return { podcasts: [], total: 0 };
    }

    try {
      const condition = new cloudDatabase.DatabaseQuery(PodcastInfo);
      condition.equalTo('category', category);
      condition.orderByDesc('created_at');

      if (limit && limit > 0) {
        condition.limit(limit);
      }

      const resultArray = await this.databaseZone!.query(condition);
      const podcasts = resultArray as PodcastInfo[];

      return {
        podcasts: podcasts,
        total: podcasts.length
      };
    } catch (error) {
      Logger.error(TAG, `根据分类查询播客失败: ${JSON.stringify(error)}`);
      hilog.error(0x0000, TAG, `根据分类查询播客失败: ${JSON.stringify(error)}`);
      return { podcasts: [], total: 0 };
    }
  }

  /**
   * 保存或更新播客信息
   * @param podcast 播客信息对象
   * @returns 是否保存成功
   */
  public async upsertPodcast(podcast: PodcastInfo): Promise<boolean> {
    if (!this.checkInitialized()) {
      return false;
    }

    try {
      const record = await this.databaseZone!.upsert(podcast);
      Logger.info(TAG, `保存播客成功: ${podcast.id}`);
      hilog.info(0x0000, TAG, `保存播客成功: ${podcast.id}`);
      return true;
    } catch (error) {
      Logger.error(TAG, `保存播客失败: ${JSON.stringify(error)}`);
      hilog.error(0x0000, TAG, `保存播客失败: ${JSON.stringify(error)}`);
      return false;
    }
  }

  /**
   * 删除播客
   * @param podcast 播客信息对象（至少需要包含id字段）
   * @returns 是否删除成功
   */
  public async deletePodcast(podcast: PodcastInfo): Promise<boolean> {
    if (!this.checkInitialized()) {
      return false;
    }

    try {
      const deleteNum = await this.databaseZone!.delete(podcast);
      Logger.info(TAG, `删除播客成功: ${podcast.id}, 删除数量: ${deleteNum}`);
      hilog.info(0x0000, TAG, `删除播客成功: ${podcast.id}, 删除数量: ${deleteNum}`);
      return true;
    } catch (error) {
      Logger.error(TAG, `删除播客失败: ${JSON.stringify(error)}`);
      hilog.error(0x0000, TAG, `删除播客失败: ${JSON.stringify(error)}`);
      return false;
    }
  }

  /**
   * 根据ID删除播客
   * @param id 播客ID
   * @returns 是否删除成功
   */
  public async deletePodcastById(id: string): Promise<boolean> {
    const podcast = new PodcastInfo();
    podcast.id = id;
    return await this.deletePodcast(podcast);
  }

  /**
   * 随机查询播客（用于推荐）
   * @param limit 返回数量
   * @returns 播客列表
   */
  public async queryRandomPodcasts(limit: number = 10): Promise<PodcastQueryResult> {
    if (!this.checkInitialized()) {
      return { podcasts: [], total: 0 };
    }

    try {
      const condition = new cloudDatabase.DatabaseQuery(PodcastInfo);
      condition.orderByRandom();
      condition.limit(limit);

      const resultArray = await this.databaseZone!.query(condition);
      const podcasts = resultArray as PodcastInfo[];

      return {
        podcasts: podcasts,
        total: podcasts.length
      };
    } catch (error) {
      Logger.error(TAG, `随机查询播客失败: ${JSON.stringify(error)}`);
      hilog.error(0x0000, TAG, `随机查询播客失败: ${JSON.stringify(error)}`);
      return { podcasts: [], total: 0 };
    }
  }
}

// 导出单例实例
export const cloudDatabaseService = CloudDatabaseService.getInstance();

