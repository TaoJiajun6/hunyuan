import { BaseViewModel, RouterMap, RouterUtils } from 'lib_common';
import { FeedbackModel } from 'module_feedback';
import { SettingItem } from 'business_setting';
import { MineGridItem } from '../types/Types';

@ObservedV2
export class MineViewModel extends BaseViewModel {
  @Trace feedbackItem: SettingItem = new SettingItem({
    icon: $r('app.media.ic_public_edit'),
    label: '意见反馈',
    routerName: RouterMap.FEEDBACK_PAGE,
    routerParams: {
      windowTopPadding: this.windowModel.windowTopPadding,
      windowBottomPadding: this.windowModel.windowBottomPadding,
      fontSizeRatio: this.settingInfo.fontSizeRatio,
    } as FeedbackModel,
  });
  serviceList: SettingItem[] = [
    this.feedbackItem,
    new SettingItem({
      icon: $r('app.media.ic_public_setting'),
      label: '设置',
      routerName: RouterMap.SETTING_PAGE,
    }),
  ];

  @Monitor('settingInfo.fontSizeRatio')
  onFontRatioChange() {
    this.feedbackItem.routerParams = {
      windowTopPadding: this.windowModel.windowTopPadding,
      windowBottomPadding: this.windowModel.windowBottomPadding,
      fontSizeRatio: this.settingInfo.fontSizeRatio,
    } as FeedbackModel
  }

  jumpLogin() {
    RouterUtils.pushPathByName(RouterMap.HUAWEI_LOGIN_PAGE);
  }

  jumpProfile() {
    RouterUtils.pushPathByName(RouterMap.PROFILE_HOME);
  }

  gridClick(v: MineGridItem) {
    RouterUtils.pushPathByName(v.routerName);
  }

  @Computed
  get userIcon() {
    return this.userInfoModel.authorIcon || $r('app.media.ic_user_default');
  }

  @Computed
  get pagePaddingBottom() {
    if (this.tabModel.isTabVertical) {
      return this.windowModel.windowBottomPadding;
    }
    return 48;
  }
}