import { loginComponentManager, LoginWithHuaweiIDButton } from '@kit.AccountKit';
import { CommonConstants, GridRowColSetting } from 'lib_common';
import { NavHeaderBar } from 'lib_widget';
import { AgreePrivacyBox } from '../components/AgreePrivacyBox';
import { Constants } from '../constants/Constants';
import { LoginRouterParams } from '../constants/Types';
import { LoginVM } from '../viewmodels/LoginVM'

@Builder
export function HuaweiLoginPageBuilder() {
  HuaweiLoginPage()
}

@ComponentV2
struct HuaweiLoginPage {
  @Local vm: LoginVM = LoginVM.getInstance(false);

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
      .height(CommonConstants.FULL_PERCENT)
      .width(CommonConstants.FULL_PERCENT)
    }
    .hideTitleBar(true)
    .backgroundColor(this.vm.pageBgColor())
    .onReady((context) => {
      const param = context.pathInfo.param as LoginRouterParams
      if (!param || !param?.keepVM) {
        this.vm = LoginVM.getInstance(true);
        this.vm.isSheet = param?.isSheet ?? false;
      } else {
        this.vm.resetInput();
      }
      this.vm.stack = context.pathStack;
      if (param?.sheetParams) {
        this.vm.sheetParams = param.sheetParams;
      }
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
    .layoutWeight(1)
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
      Text(this.vm.anonymousPhone)
        .fontSize($r('sys.float.Title_L'))
        .fontColor($r('sys.color.font_primary'))
        .fontWeight(FontWeight.Bold)
        .margin({
          top: Constants.PADDING_40,
        })
      Text('华为账号绑定号码')
        .fontSize($r('sys.float.Body_S'))
        .fontColor($r('sys.color.font_secondary'))
        .margin({
          top: CommonConstants.PADDING_XS,
        })
      Column() {
        LoginWithHuaweiIDButton({
          params: {
            style: loginComponentManager.Style.BUTTON_CUSTOM,
            extraStyle: {
              buttonStyle: new loginComponentManager.ButtonStyle().loadingStyle({
                show: true,
              }).backgroundColor($r('sys.color.icon_emphasize')),
            },
            loginType: loginComponentManager.LoginType.QUICK_LOGIN,
            supportDarkMode: false,
          },
          controller: this.vm.controller,
        }).id('login_with_huaweiId_button')
      }
      .height(Constants.BTN_HEIGHT)
      .margin({
        top: Constants.PADDING_40 + CommonConstants.PADDING_S,
      })

      Button('其他方式登录')
        .width(CommonConstants.FULL_PERCENT)
        .height(Constants.BTN_HEIGHT)
        .fontSize($r('sys.float.Body_L'))
        .fontColor($r('sys.color.font_primary'))
        .fontWeight(FontWeight.Medium)
        .backgroundColor($r('sys.color.comp_background_tertiary'))
        .margin({
          top: CommonConstants.PADDING_M,
          bottom: CommonConstants.PADDING_S,
        })
        .onClick(() => {
          this.vm.jumpOtherLogin();
        })
    }
  }
}