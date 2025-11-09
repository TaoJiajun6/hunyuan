import { CommonConstants, GridRowColSetting } from 'lib_common';
import { NavHeaderBar } from 'lib_widget';
import { AgreePrivacyBox } from '../components/AgreePrivacyBox';
import { Constants } from '../constants/Constants';
import { LoginVM } from '../viewmodels/LoginVM'

@Builder
export function OtherLoginPageBuilder() {
  OtherLoginPage()
}

@ComponentV2
struct OtherLoginPage {
  @Local vm: LoginVM = LoginVM.getInstance(false);

  aboutToAppear(): void {
    this.vm.resetInput();
    this.vm.registerOnWXRespCallback();
  }

  aboutToDisappear(): void {
    this.vm.unregisterOnWXRespCallback();
  }

  build() {
    NavDestination() {
      Column() {
        if (!this.vm.isSheet) {
          NavHeaderBar({
            onBack: () => {
              this.vm.handleClose();
            },
          })
        }

        if (this.vm.isSheet) {
          this.mainBody()
        } else {
          GridRow(GridRowColSetting.DEFAULT_GRID_ROW_OPTIONS) {
            GridCol({
              span: GridRowColSetting.SMALL_CENTER_COL_SPAN,
              offset: GridRowColSetting.SMALL_CENTER_COL_OFFSET,
            }) {
              this.mainBody()
            }
          }
          .layoutWeight(1)
          .padding({
            left: this.vm.breakPointModel.pagePadding,
            right: this.vm.breakPointModel.pagePadding,
          })
        }
      }
    }
    .hideTitleBar(true)
    .backgroundColor(this.vm.pageBgColor())
    .onWillShow(() => {
      this.vm.setPrivacyMode(this.getUIContext().getHostContext());
    })
    .onWillHide(() => {
      this.vm.cancelPrivacyMode(this.getUIContext().getHostContext());
    })
    .onBackPressed(() => {
      this.vm.handleClose();
      return true;
    })
  }

  @Builder
  mainBody() {
    Column() {
      Scroll() {
        Column() {
          if (this.vm.isSheet) {
            Column().height(Constants.SHEET_TITLE_H)
          } else {
            Column().layoutWeight(1)
          }
          this.coreInfo()
          Column().layoutWeight(4)
        }
      }
      .layoutWeight(1)
      .align(Alignment.Top)
      .scrollBar(BarState.Off)

      AgreePrivacyBox()
    }
    .height(CommonConstants.FULL_PERCENT)
    .width(CommonConstants.FULL_PERCENT)
    .padding({
      left: this.vm.isSheet ? CommonConstants.PADDING_L : 0,
      right: this.vm.isSheet ? CommonConstants.PADDING_L : 0,
      bottom: this.vm.getPagePaddingBottom(),
    })
  }

  @Builder
  coreInfo() {
    Column() {
      Image($r('app.media.startIcon'))
        .width(Constants.START_ICON_WIDTH)
        .aspectRatio(1)
        .draggable(false)
        .borderRadius($r('app.float.large_radius'))
      TextInput({ text: $$this.vm.accountInput, placeholder: '请输入账号' })
        .width(CommonConstants.FULL_PERCENT)
        .height(Constants.INPUT_HEIGHT)
        .fontSize($r('sys.float.Body_L'))
        .fontColor($r('sys.color.font_primary'))
        .backgroundColor($r('sys.color.comp_background_tertiary'))
        .borderRadius($r('app.float.radius_20'))
        .placeholderFont({ size: $r('sys.float.Body_L') })
        .placeholderColor($r('sys.color.font_secondary'))
        .padding({
          top: CommonConstants.PADDING_S,
          bottom: CommonConstants.PADDING_S,
          left: CommonConstants.PADDING_L,
          right: CommonConstants.PADDING_L,
        })
        .margin({
          top: Constants.PADDING_40,
        })

      TextInput({ text: $$this.vm.passwordInput, placeholder: '请输入密码' })
        .type(InputType.Password)
        .width(CommonConstants.FULL_PERCENT)
        .height(Constants.INPUT_HEIGHT)
        .fontSize($r('sys.float.Body_L'))
        .fontColor($r('sys.color.font_primary'))
        .backgroundColor($r('sys.color.comp_background_tertiary'))
        .borderRadius($r('app.float.radius_20'))
        .placeholderFont({ size: $r('sys.float.Body_L') })
        .placeholderColor($r('sys.color.font_secondary'))
        .padding({
          top: CommonConstants.PADDING_S,
          bottom: CommonConstants.PADDING_S,
          left: CommonConstants.PADDING_L,
          right: CommonConstants.PADDING_L,
        })
        .margin({
          top: CommonConstants.PADDING_L,
        })

      Button('登录')
        .width(CommonConstants.FULL_PERCENT)
        .margin({
          top: Constants.PADDING_40 + CommonConstants.PADDING_S,
          bottom: CommonConstants.PADDING_S,
        })
        .backgroundColor($r('sys.color.icon_emphasize'))
        .onClick(() => {
          this.vm.accountPasswordLogin();
        })

      Column({ space: CommonConstants.SPACE_M }) {
        Text('其他方式登录')
          .fontSize($r('sys.float.Caption_L'))
          .fontColor($r('sys.color.font_tertiary'))

        Row({ space: 48 }) {
          Column({ space: CommonConstants.SPACE_S }) {
            Image($r('app.media.ic_huawei'))
              .width(Constants.WAY_ICON_WIDTH)
              .draggable(false)
            Text('华为账号一键登录')
              .fontSize($r('sys.float.Caption_L'))
              .fontColor($r('sys.color.font_tertiary'))
          }
          .width(Constants.WAY_WIDTH)
          .onClick(() => {
            this.vm.jumpHuaweiLogin();
          })

          Column({ space: CommonConstants.SPACE_S }) {
            Image($r('app.media.ic_wechat'))
              .width(Constants.WAY_ICON_WIDTH)
              .draggable(false)
            Text('微信')
              .fontSize($r('sys.float.Caption_L'))
              .fontColor($r('sys.color.font_tertiary'))
          }
          .width(Constants.WAY_WIDTH)
          .onClick(() => {
            this.vm.jumpWX();
          })
        }
      }
      .margin({
        top: this.vm.otherWayMarginTop(),
      })
    }
  }
}