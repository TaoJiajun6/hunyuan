import { CommonConstants, RouterMap } from 'lib_common';
import { ProtocolRouterParams } from '../constants/Types';
import { LoginVM } from '../viewmodels/LoginVM';

@ComponentV2
export struct AgreePrivacyBox {
  @Local vm: LoginVM = LoginVM.getInstance(false);

  build() {
    Row({ space: CommonConstants.SPACE_M }) {
      Checkbox()
        .select(false)
        .shape(CheckBoxShape.CIRCLE)
        .onChange((value: boolean) => {
          this.vm.agreePrivacyChange(value);
        })
      Text() {
        Span('已阅读并同意')
          .fontSize($r('sys.float.Caption_L'))
          .fontColor('#666666')
        Span('《用户协议》')
          .fontSize($r('sys.float.Caption_L'))
          .fontColor($r('app.color.app_theme'))
          .fontWeight(FontWeight.Medium)
          .onClick(() => {
            this.vm.stack.pushPathByName(RouterMap.PROTOCOL_WEBVIEW, {
              content: this.vm.userProtocolInfo,
              isSheet: this.vm.isSheet,
              sheetType: this.vm.sheetParams.sheetType,
            } as ProtocolRouterParams, true);
          })
        Span('《xxxx隐私政策》')
          .fontSize($r('sys.float.Caption_L'))
          .fontColor($r('app.color.app_theme'))
          .fontWeight(FontWeight.Medium)
          .onClick(() => {
            this.vm.stack.pushPathByName(RouterMap.PROTOCOL_WEBVIEW, {
              content: this.vm.privacyInfo,
              isSheet: this.vm.isSheet,
              sheetType: this.vm.sheetParams.sheetType,
            } as ProtocolRouterParams, true);
          })
        Span('和')
          .fontSize($r('sys.float.Caption_L'))
          .fontColor('#666666')
        Span('《华为账号用户认证协议》')
          .fontSize($r('sys.float.Caption_L'))
          .fontColor($r('app.color.app_theme'))
          .fontWeight(FontWeight.Medium)
          .onClick(() => {
            this.vm.stack.pushPathByName(RouterMap.PROTOCOL_WEBVIEW, {
              content: this.vm.huaweiUserProtocolInfo,
              isSheet: this.vm.isSheet,
              sheetType: this.vm.sheetParams.sheetType,
            } as ProtocolRouterParams, true);
          })
      }
      .layoutWeight(1)
    }
    .width(CommonConstants.FULL_PERCENT)
    .padding({
      top: CommonConstants.PADDING_L,
      bottom: CommonConstants.PADDING_L,
    })
  }
}