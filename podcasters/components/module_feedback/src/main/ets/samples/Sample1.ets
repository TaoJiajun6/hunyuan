import { RouterMap } from '../common/Constants';
import { FeedbackModel } from '../common/FeedbackModel';

@Entry
@ComponentV2
struct Sample1 {
  stack: NavPathStack = new NavPathStack()

  build() {
    Navigation(this.stack) {
      Column({ space: 10 }) {
        Text('意见反馈').fontSize(20).fontWeight(FontWeight.Bold)
        Button('跳转').width('100%').onClick(() => {
          this.stack.pushPath({
            name: RouterMap.FEEDBACK_PAGE,
            param: {
              windowTopPadding: 0,
              windowBottomPadding: 0,
              fontSizeRatio: 1,
            } as FeedbackModel,
          })
        })
      }
      .padding({
        left: 16,
        right: 16,
      })
    }
    .hideTitleBar(true)
    .mode(NavigationMode.Stack)
  }
}