import { NavHeaderBar } from '../components/NavHeaderBar';
import { Constants } from '../common/Constants';
import { RecordListVM } from '../viewmodels/RecordListVM';
import { FeedbackResponseParams } from '../services/ResponseModel';
import { RecordCard } from '../components/RecordCard';
import { Empty } from '../components/Empty';
import { CommonUtils } from '../common/CommonUtils';

@Builder
export function RecordListPageBuilder() {
  RecordListPage()
}

@ComponentV2
export struct RecordListPage {
  @Provider() stack: NavPathStack = new NavPathStack();
  @Local vm: RecordListVM = new RecordListVM();

  build() {
    NavDestination() {
      Column() {
        NavHeaderBar({
          title: '反馈记录',
          breakpoint: this.vm.breakpoint,
        })
        GridRow(Constants.GRID_ROW_OPTIONS) {
          GridCol({
            span: Constants.FULL_COL_SPAN,
          }) {
            Scroll() {
              if (this.vm.loading) {
                Column() {
                  LoadingProgress()
                    .width(72)
                    .height(72)
                }
                .height(Constants.FULL_PERCENT)
                .justifyContent(FlexAlign.Center)
              } else if (this.vm.list.length) {
                Column({ space: Constants.SPACE_12 }) {
                  ForEach(this.vm.list, (v: FeedbackResponseParams) => {
                    RecordCard({
                      record: v,
                      fontSizeRatio: this.vm.feedbackModel.fontSizeRatio,
                      gridCount: this.vm.gridCount,
                    })
                  }, (v: FeedbackResponseParams) => v.id)
                }
              } else {
                Column() {
                  Empty({
                    fontSizeRatio: this.vm.feedbackModel.fontSizeRatio,
                  })
                }
                .height(Constants.FULL_PERCENT)
                .justifyContent(FlexAlign.Center)
              }
            }
            .width(Constants.FULL_PERCENT)
            .layoutWeight(1)
            .align(Alignment.Top)
            .scrollBar(BarState.Off)
            .edgeEffect(EdgeEffect.Spring)
            .backgroundColor($r('sys.color.background_secondary'))
            .padding({
              left: CommonUtils.getPageMargin(this.vm.breakpoint),
              right: CommonUtils.getPageMargin(this.vm.breakpoint),
              top: Constants.PADDING_M,
              bottom: this.vm.feedbackModel.windowBottomPadding,
            })
          }
        }
        .layoutWeight(1)
        .onBreakpointChange((bp: string) => {
          this.vm.onBreakpointChange(bp);
        })
      }
    }
    .hideTitleBar(true)
    .onReady((context) => {
      this.stack = context.pathStack;
    })
  }
}