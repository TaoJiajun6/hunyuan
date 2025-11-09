import { RouterMap, RouterUtils } from 'lib_common';
import { AccountApi, ProtocolRouterParams } from 'lib_account'

@Builder
export function SettingH5Builder() {
  SettingH5()
}

@ComponentV2
struct SettingH5 {
  @Local content: string = '';
  private accountInstance: AccountApi = new AccountApi();

  aboutToAppear(): void {
    this.getParams();
  }

  getParams() {
    const param = RouterUtils.getParamByName(RouterMap.SETTING_H5) as number
    switch (param) {
      case 1:
        this.content = this.accountInstance.getUserAgreeInfo();
        break;
      case 2:
        this.content = this.accountInstance.getPrivacyInfo();
        break;
      case 3:
        this.content = this.accountInstance.getThirdPartyInfo();
        break;
      case 4:
        this.content = this.accountInstance.getPersonalInfoCollection();
        break;
      default:
        this.content = '';
    }
    RouterUtils.replacePathByName(RouterMap.PROTOCOL_WEBVIEW, {
      content: this.content,
      isSheet: false,
    } as ProtocolRouterParams, false);
  }

  build() {
    NavDestination() {
    }
    .hideTitleBar(true)
  }
}