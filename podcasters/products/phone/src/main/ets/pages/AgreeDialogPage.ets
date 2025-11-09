import { CommonConstants } from 'lib_common';
import { SafePageVM } from '../viewmodels/SafePageVM';

@Builder
export function AgreePrivacyPageBuilder() {
  AgreePrivacyPage()
}

@ComponentV2
struct AgreePrivacyPage {
  vm: SafePageVM = new SafePageVM();

  build() {
    NavDestination() {
      Column() {
        Column() {
          Text('您需要同意协议才能体验AI写作模板')
            .fontSize($r('sys.float.Title_S'))
            .fontColor($r('sys.color.font_primary'))
            .fontWeight(FontWeight.Bold)
          Text() {
            Span('本应用需联网，调用XX、XX权限，获取XX信息，以为您提供XX服务。我们仅在您使用具体功能业务时，才会触发上述行为收集使用相关的个人信息。详情请参阅')
              .fontColor($r('sys.color.font_secondary'))
            Span('XX业务与隐私的声明、权限使用说明')
              .fontColor($r('app.color.app_theme'))
              .onClick(() => {
                this.vm.privacyClick();
              })
            Span('。')
              .fontColor($r('sys.color.font_secondary'))
          }
          .fontSize($r('sys.float.Caption_M'))
          .margin({ top: 16, bottom: 16 })

          Text('请您仔细阅读上述声明，点击“同意”，即表示您知悉并同意我们向您提供本应用服务。')
            .fontSize($r('sys.float.Caption_M'))
            .fontColor($r('sys.color.font_secondary'))
          Row({ space: CommonConstants.SPACE_L }) {
            Button('退出应用')
              .buttonStyle(ButtonStyleMode.NORMAL)
              .role(ButtonRole.NORMAL)
              .height(40)
              .layoutWeight(1)
              .onClick(() => {
                this.vm.quitApp();
              })
            Button('同意并继续')
              .height(40)
              .layoutWeight(1)
              .onClick(() => {
                this.vm.agreeBtnClick();
              })
          }
          .margin({ top: 24 })
        }
        .backgroundColor($r('sys.color.comp_background_primary'))
        .width(CommonConstants.FULL_PERCENT)
        .borderRadius($r('app.float.xxl_radius'))
        .padding(CommonConstants.PADDING_L)
      }
      .justifyContent(FlexAlign.Center)
      .height(CommonConstants.FULL_PERCENT)
      .width(CommonConstants.FULL_PERCENT)
      .padding({
        left: CommonConstants.PADDING_PAGE,
        right: CommonConstants.PADDING_PAGE,
      })
    }
    .hideTitleBar(true)
    .mode(NavDestinationMode.DIALOG)
    .backgroundColor('rgba(0,0,0,0.5)')
    .onBackPressed(() => {
      return true;
    })
  }
}
