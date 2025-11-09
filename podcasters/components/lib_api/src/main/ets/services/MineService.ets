import { AuthorService } from './AuthorService';
import { BaseAuthor } from '../database/AuthorType';
import { ModifyPersonalInfoRequest } from '../params/request/CommonRequest';

/**
 * 我的管理类
 */
export class MineService extends AuthorService {
  /**
   * 修改个人信息
   * @param nickName
   */
  public modifyPersonalInfo(params: ModifyPersonalInfoRequest) {
    const mineUserInfo = this.queryAuthorRaw() as BaseAuthor;
    if (params.authorIcon) {
      mineUserInfo.authorIcon = params.authorIcon;
    }
    if (params.authorNickName) {
      mineUserInfo.authorNickName = params.authorNickName;
    }
    if (params.authorPhone) {
      mineUserInfo.authorPhone = params.authorPhone;
    }
    if (params.authorDesc) {
      mineUserInfo.authorDesc = params.authorDesc;
    }
  }
}

const instance = new MineService();

export { instance as MineServiceApi };