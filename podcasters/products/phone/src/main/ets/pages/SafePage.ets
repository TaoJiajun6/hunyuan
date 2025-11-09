import { CommonConstants } from 'lib_common';
import { SafePageVM } from '../viewmodels/SafePageVM';

@Builder
export function SafePageBuilder() {
  SafePage()
}

@ComponentV2
struct SafePage {
  vm: SafePageVM = new SafePageVM();

  build() {
    NavDestination() {
      Column() {
        Scroll() {
          Column() {
            Image($r('app.media.icon_flip_foreground'))
              .width(72)
              .draggable(false)
              .margin({ top: 136 })
            Text($r('app.string.app_name'))
              .fontSize($r('sys.float.Title_L'))
              .fontColor($r('sys.color.font_primary'))
              .fontWeight(FontWeight.Medium)
              .margin({
                top: CommonConstants.PADDING_XXL,
                bottom: 2,
              })
            Text('业务描述')
              .fontSize($r('sys.float.Body_M'))
              .fontColor($r('sys.color.font_secondary'))
          }
        }
        .align(Alignment.Top)
        .scrollBar(BarState.Off)
        .layoutWeight(1)

        Column() {
          Image($r('app.media.ic_security'))
            .width($r('app.float.normal_img_size'))
            .draggable(false)
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
          .margin({
            top: CommonConstants.PADDING_L,
            bottom: 6,
          })

          Text('请您仔细阅读上述声明，点击“同意”，即表示您知悉并同意我们向您提供本应用服务。')
            .fontSize($r('sys.float.Caption_M'))
            .fontColor($r('sys.color.font_secondary'))
          Row({ space: CommonConstants.SPACE_M }) {
            Button('取消')
              .buttonStyle(ButtonStyleMode.NORMAL)
              .role(ButtonRole.NORMAL)
              .height(40)
              .layoutWeight(1)
              .onClick(() => {
                this.vm.cancelBtnClick();
              })
            Button('同意')
              .height(40)
              .layoutWeight(1)
              .onClick(() => {
                this.vm.agreeBtnClick();
              })
          }
          .padding({
            top: CommonConstants.PADDING_L,
            bottom: CommonConstants.PADDING_L,
          })
        }
        .margin({
          top: CommonConstants.PADDING_M,
        })
      }
      .height(CommonConstants.FULL_PERCENT)
      .width(CommonConstants.FULL_PERCENT)
      .padding({
        left: CommonConstants.PADDING_PAGE,
        right: CommonConstants.PADDING_PAGE,
        bottom: this.vm.windowModel.windowBottomPadding,
      })
    }
    .hideTitleBar(true)
  }
}
