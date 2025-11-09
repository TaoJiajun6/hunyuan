import { Constants, ISettingItem } from '../common/Constants';

@ComponentV2
export struct SettingList {
  @Param list: ISettingItem[] = [];
  @Param fontSizeRatio: number = 1;
  @Consumer() stack: NavPathStack = new NavPathStack();

  build() {
    List({ space: Constants.SPACE_12 }) {
      ForEach(this.list, (v: ISettingItem) => {
        ListItem() {
          Row() {
            Row({ space: Constants.SPACE_8 }) {
              Text(v.label)
                .fontSize(16 * this.fontSizeRatio)
                .fontColor($r('sys.color.font_primary'))
                .fontWeight(FontWeight.Medium)
                .layoutWeight(1)
                .textAlign(TextAlign.Start)
              Image($r('app.media.ic_right'))
                .width($r('app.float.arrow_right_w'))
                .draggable(false)
            }
            .padding({
              left: Constants.PADDING_S,
              right: Constants.PADDING_S,
              top: Constants.PADDING_M,
              bottom: Constants.PADDING_M,
            })
            .borderRadius(Constants.RADIUS_16)
            .stateStyles({
              normal: this.normalStyles,
              pressed: this.pressedStyles,
            })
          }
          .width(Constants.FULL_PERCENT)
          .padding(Constants.PADDING_XS)
          .borderRadius(Constants.RADIUS_16)
          .backgroundColor($r('sys.color.comp_background_primary'))
        }
        .onClick(() => {
          if (v.routerName) {
            this.stack.pushPathByName(v.routerName, null);
          }
        })
      }, (v: ISettingItem) => v.label)
    }
    .width(Constants.FULL_PERCENT)
    .height(Constants.FULL_PERCENT)
    .scrollBar(BarState.Off)
  }

  @Styles
  normalStyles() {
    .backgroundColor($r('sys.color.comp_background_primary'))
  }

  @Styles
  pressedStyles(): void {
    .backgroundColor($r('sys.color.interactive_pressed'))
  }
}
