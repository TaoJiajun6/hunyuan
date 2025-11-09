import { RouterMap } from 'lib_common';

export interface TabBarItem {
  id: TabBarType;
  title: ResourceStr;
  activeIcon: ResourceStr;
}

export enum TabBarType {
  HOME = 0,
  OFFICE,
  MINE
}

export const TABS_INFO: TabBarItem[] = [
  {
    id: TabBarType.HOME,
    title: 'AI对话',
    activeIcon: $r('app.media.icon_ai_dialog_on'),
  },
  {
    id: TabBarType.OFFICE,
    title: 'AI办公',
    activeIcon: $r('app.media.icon_ai_office_on'),
  },
  {
    id: TabBarType.MINE,
    title: '我的',
    activeIcon: $r('app.media.icon_my_on'),
  },
]

/**
 * 依赖登录的页面
 */
export const REQUIRE_LOGIN_PAGE_LIST: RouterMap[] = [
  RouterMap.FEEDBACK_PAGE,
];

export const agreePrivacyKey: string = 'isAgreePrivacy';

export const SOURCE_FORM_CARD: string = 'FormCard';

export class PhoneConstants {
  static readonly LEFT_TAB_BAR_WIDTH: number = 96;
  static readonly LEFT_TAB_BAR_ITEM_HEIGHT: number = 100;
  static readonly BOTTOM_TAB_BAR_HEIGHT: number = 48;
}
