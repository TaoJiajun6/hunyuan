import { cloudDatabase } from '@kit.CloudFoundationKit';

/**
 * 播客信息对象类型
 * 对应云数据库中的PodcastInfo对象类型
 */
export class PodcastInfo extends cloudDatabase.DatabaseObject {
  /**
   * 返回对象类型名称
   */
  public naturalbase_ClassName(): string {
    return "PodcastInfo";
  }

  /**
   * 播客ID（主键）
   */
  public id: string | undefined;

  /**
   * 播客标题
   */
  public title: string | undefined;

  /**
   * 音频文件URL（云存储地址）
   */
  public audio_url: string | undefined;

  /**
   * 本地文件名
   */
  public local_file: string | undefined;

  /**
   * 创建时间戳（Long类型，Unix时间戳）
   */
  public created_at: number | undefined;

  /**
   * 播客时长（秒，Long类型）
   */
  public duration: number | undefined;

  /**
   * 播客分类
   */
  public category: string | undefined;

  /**
   * 播客状态（如：completed, processing等）
   */
  public status: string | undefined;

  /**
   * 播客脚本内容（Text类型，可能很长）
   */
  public script: string | undefined;

  /**
   * 文件大小（MB，Double类型）
   */
  public file_size_mb: number | undefined;

  /**
   * 播客主题
   */
  public topic: string | undefined;

  /**
   * 角色列表（JSON字符串格式，存储为String类型）
   */
  public roles: string | undefined;

  /**
   * 将roles字符串解析为数组
   */
  public getRolesArray(): string[] {
    if (!this.roles) {
      return [];
    }
    try {
      return JSON.parse(this.roles);
    } catch (e) {
      return [];
    }
  }

  /**
   * 将roles数组转换为JSON字符串
   */
  public setRolesArray(roles: string[]): void {
    this.roles = JSON.stringify(roles);
  }

  /**
   * 获取内容预览（script的前100个字符）
   */
  public getContentPreview(): string {
    if (!this.script) {
      return '';
    }
    if (this.script.length <= 100) {
      return this.script;
    }
    return this.script.substring(0, 100) + '...';
  }
}



