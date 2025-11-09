import { BaseAuthor } from '../database/AuthorType';
import { AuthorResponse } from '../params/response/AuthorResponse';
import { MockUser } from './mockdata/MockUser';

/**
 * 用户管理类
 */
export class AuthorService {
  /**
   * 查询用户信息数据库字段
   * @param userId
   * @returns
   */
  public queryAuthorRaw(userId?: string): BaseAuthor | undefined {
    if (userId) {
      return [MockUser.myself].find(v => v.authorId === userId)!;
    }
    // 获取本人信息
    return MockUser.myself;
  }

  /**
   * 数据库字段转换成云侧模型
   * @param author
   * @returns
   */
  private handleRawInfo(author: BaseAuthor): AuthorResponse {
    const copyItem = JSON.parse(JSON.stringify(author)) as AuthorResponse;
    return copyItem;
  }

  /**
   * 查询作者信息
   * @param userId
   * @returns
   */
  public queryAuthorInfo(userId?: string, loginChannel?: string): AuthorResponse | undefined {
    if (loginChannel) {
      return this.signIn(loginChannel);
    }
    const raw = this.queryAuthorRaw(userId);
    if (raw) {
      return this.handleRawInfo(raw);
    }
    return undefined;
  }

  /**
   * 登录
   * @param loginChannel 渠道
   */
  public signIn(loginChannel?: string, nickPhone?: string) {
    const raw = this.queryAuthorRaw();
    if (raw) {
      if (loginChannel === 'wechat') {
        raw.authorNickName = '微信用户';
      } else {
        raw.authorNickName = '华为用户';
      }
      if (nickPhone) {
        raw.authorPhone = nickPhone;
      }
      return this.handleRawInfo(raw);
    }
    return undefined;
  }
}

const instance = new AuthorService();

export { instance as AuthorServiceApi }