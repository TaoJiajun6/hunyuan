import { AlertDialog } from '@kit.ArkUI';
import { CommonConstants } from '../constants/CommonConstants';
import { GridRowColSetting } from '../constants/GridRowColSetting';
import { PopViewUtils } from '../utils/PopViewUtils';

export interface IConfirmDialogParams {
  primaryTitle?: ResourceStr;
  secondaryTitle?: ResourceStr;
  content: ResourceStr;
  priBtnV?: ResourceStr;
  secBtnV?: ResourceStr;
  priBtnFg?: ResourceColor;
  secBtnFg?: ResourceColor;
  confirm?: () => void;
  cancel?: () => void;
}

class ConfirmDialogParams implements IConfirmDialogParams {
  primaryTitle: ResourceStr = '';
  secondaryTitle: ResourceStr = '';
  content: ResourceStr = '';
  priBtnV: ResourceStr = '取消';
  secBtnV: ResourceStr = '确定';
  priBtnFg: ResourceColor = $r('app.color.app_theme');
  secBtnFg: ResourceColor = $r('app.color.app_theme');
  confirm: () => void = () => {
  };
  cancel: () => void = () => {
  };

  constructor(item: IConfirmDialogParams) {
    this.content = item.content;
    if (item.primaryTitle) {
      this.primaryTitle = item.primaryTitle;
    }
    if (item.secondaryTitle) {
      this.secondaryTitle = item.secondaryTitle;
    }
    if (item.priBtnV) {
      this.priBtnV = item.priBtnV;
    }
    if (item.secBtnV) {
      this.secBtnV = item.secBtnV;
    }
    if (item.priBtnFg) {
      this.priBtnFg = item.priBtnFg;
    }
    if (item.secBtnFg) {
      this.secBtnFg = item.secBtnFg;
    }
    if (item.confirm) {
      this.confirm = item.confirm;
    }
    if (item.cancel) {
      this.cancel = item.cancel;
    }
  }
}

@Builder
function confirmDialogView(params: ConfirmDialogParams) {
  Column() {
    Column() {
      AlertDialog({
        primaryTitle: params.primaryTitle,
        secondaryTitle: params.secondaryTitle,
        content: params.content,
        primaryButton: {
          value: params.priBtnV,
          fontColor: params.priBtnFg || $r('app.color.app_theme'),
          background: Color.Transparent,
          action: () => {
            PopViewUtils.closePopView();
            params.cancel();
          },
        },
        secondaryButton: {
          value: params.secBtnV,
          fontColor: params.secBtnFg || $r('app.color.app_theme'),
          background: Color.Transparent,
          action: () => {
            PopViewUtils.closePopView();
            params.confirm();
          },
        },
      })
    }
    .width(CommonConstants.FULL_PERCENT)
    .borderRadius($r('app.float.xxl_radius'))
    .backgroundColor($r('sys.color.comp_background_primary'))
    .constraintSize({ maxWidth: GridRowColSetting.DIALOG_MAX_WIDTH })
  }
  .width(CommonConstants.FULL_PERCENT)
  .padding({
    left: CommonConstants.PADDING_L,
    right: CommonConstants.PADDING_L,
  })
}

/**
 * 通用确认弹窗
 */
export class CommonConfirmDialog {
  /**
   * 打开弹窗
   * @param param
   */
  public static show(param: IConfirmDialogParams) {
    PopViewUtils.showPopView<ConfirmDialogParams>(wrapBuilder(confirmDialogView), {}, new ConfirmDialogParams(param));
  }
}