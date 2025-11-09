/**
 * 用户信息
 */
@ObservedV2
export class UserInfoModel {
  @Trace isLogin: boolean = false;
  @Trace authorId: string = '';
  @Trace authorNickName: string = '';
  @Trace authorIcon: string = '';
  @Trace authorDesc: string = '';
  @Trace authorPhone: string = '';
  @Trace loginChannel: string = '';
}