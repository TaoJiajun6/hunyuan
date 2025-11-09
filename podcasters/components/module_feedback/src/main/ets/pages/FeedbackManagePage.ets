import { AppStorageV2 } from '@kit.ArkUI';
import { FeedbackModel } from '../common/FeedbackModel';
import { NavHeaderBar } from '../components/NavHeaderBar';
import { Constants, LIST_INFO } from '../common/Constants';
import { SettingList } from '../components/SettingList';
import { CommonUtils } from '../common/CommonUtils';

@Builder
export function FeedbackManagePageBuilder() {
  FeedbackManagePage()
}

@ComponentV2
export struct FeedbackManagePage {
  @Provider() stack: NavPathStack = new NavPathStack();
  @Local feedbackModel: FeedbackModel = AppStorageV2.connect(FeedbackModel, () => new FeedbackModel())!;
  @Local breakpoint: string = 'sm';

  build() {
    NavDestination() {
      Column({ space: Constants.SPACE_12 }) {
        NavHeaderBar({
          title: '意见反馈',
          breakpoint: this.breakpoint,
        })
        GridRow(Constants.GRID_ROW_OPTIONS) {
          GridCol({
            span: Constants.CENTER_COL_SPAN,
            offset: Constants.CENTER_COL_OFFSET,
          }) {
            Scroll() {
              Column() {
                SettingList({
                  list: LIST_INFO,
                  fontSizeRatio: this.feedbackModel.fontSizeRatio,
                })
              }
              .padding({
                left: CommonUtils.getPageMargin(this.breakpoint),
                right: CommonUtils.getPageMargin(this.breakpoint),
              })
            }
            .layoutWeight(1)
            .scrollBar(BarState.Off)
            .align(Alignment.Top)
            .edgeEffect(EdgeEffect.Spring)
          }
        }
        .onBreakpointChange((bp: string) => {
          this.breakpoint = bp;
        })
      }
    }
    .hideTitleBar(true)
    .backgroundColor($r('sys.color.background_secondary'))
    .onReady((context) => {
      this.stack = context.pathStack;
      if (context?.pathInfo?.param) {
        const params = context.pathInfo.param as FeedbackModel;
        this.feedbackModel.windowTopPadding = params.windowTopPadding;
        this.feedbackModel.windowBottomPadding = params.windowBottomPadding;
        this.feedbackModel.fontSizeRatio = params.fontSizeRatio;
      }
    })
  }
}