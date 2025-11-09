import { AlertDialog } from '@kit.ArkUI';
import { CommonConstants } from '../constants/CommonConstants';
import { GridRowColSetting } from '../constants/GridRowColSetting';
import { PopViewUtils } from '../utils/PopViewUtils';

export interface ITipDialogParams {
  primaryTitle?: ResourceStr;
  secondaryTitle?: ResourceStr;
  content: ResourceStr;
  priBtnV?: ResourceStr;
  confirm?: () => void;
}

class TipDialogParams implements ITipDialogParams {
  primaryTitle: ResourceStr = '';
  secondaryTitle: ResourceStr = '';
  content: ResourceStr = '';
  priBtnV: ResourceStr = '取消';
  confirm: () => void = () => {
  };

  constructor(item: ITipDialogParams) {
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
    if (item.confirm) {
      this.confirm = item.confirm;
    }
  }
}

@Builder
function commonTipView(params: TipDialogParams) {
  Column() {
    Column() {
      AlertDialog({
        primaryTitle: params.primaryTitle,
        secondaryTitle: params.secondaryTitle,
        content: params.content,
        primaryButton: {
          value: params.priBtnV,
          fontColor: $r('app.color.app_theme'),
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
 * 通用通知弹窗
 */
export class CommonTipDialog {
  /**
   * 打开弹窗
   * @param param
   */
  public static show(param: ITipDialogParams) {
    PopViewUtils.showPopView<TipDialogParams>(wrapBuilder(commonTipView), {}, new TipDialogParams(param));
  }
}