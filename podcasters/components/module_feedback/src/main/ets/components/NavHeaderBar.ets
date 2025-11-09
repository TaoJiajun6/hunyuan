import { AppStorageV2 } from '@kit.ArkUI';
import { CommonUtils } from '../common/CommonUtils';
import { Constants } from '../common/Constants';
import { FeedbackModel } from '../common/FeedbackModel';

@ComponentV2
export struct NavHeaderBar {
  @Param title: ResourceStr = '';
  @Param showBackBtn: boolean = true;
  @Param hasBgColor: boolean = false;
  @Param isSubTitle: boolean = true;
  @Param breakpoint: string = 'sm';
  @Local feedbackModel: FeedbackModel = AppStorageV2.connect(FeedbackModel, () => new FeedbackModel())!;
  @Consumer() stack: NavPathStack = new NavPathStack();

  build() {
    Column() {
      Row() {
        Button() {
          SymbolGlyph($r('sys.symbol.chevron_backward'))
            .fontColor([$r('sys.color.font_primary')])
            .fontWeight(FontWeight.Normal)
            .fontSize(24)
        }
        .width(40)
        .aspectRatio(1)
        .borderRadius(Constants.HALF_PERCENT)
        .backgroundColor($r('sys.color.comp_background_tertiary'))
        .accessibilityText('返回')
        .onClick(() => {
          this.stack.pop();
        })

        if (this.title) {
          Text(this.title)
            .fontSize(this.isSubTitle ? $r('sys.float.Title_S') : $r('sys.float.Title_M'))
            .fontColor($r('sys.color.font_primary'))
            .fontWeight(FontWeight.Bold)
            .margin({ left: Constants.SPACE_8 })
        }
      }
      .height(56)
      .width(Constants.FULL_PERCENT)
    }
    .padding({
      left: CommonUtils.getPageMargin(this.breakpoint),
      right: CommonUtils.getPageMargin(this.breakpoint),
      top: this.feedbackModel.windowTopPadding,
    })
    .width(Constants.FULL_PERCENT)
    .backgroundColor(this.hasBgColor ? $r('sys.color.background_primary') : '#00000000')
  }
}