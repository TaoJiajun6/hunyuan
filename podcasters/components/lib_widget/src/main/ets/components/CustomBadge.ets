import { CircleShape } from '@kit.ArkUI';

@ComponentV2
export struct CustomBadge {
  @Param count: number = 1;
  @Param maxCount: number = 99;
  @Param badgeH: number = 16;
  @BuilderParam bodyBuilder: () => void;

  build() {
    RelativeContainer() {
      Row() {
        this.bodyBuilder()
      }
      .id('body_id')

      Row() {
        if (this.showCircleBadge) {
          this.circleBadge()
        } else if (this.showCapsuleBadge) {
          this.capsuleBadge()
        }
      }
      .alignRules({
        right: { anchor: 'body_id', align: HorizontalAlign.End },
        top: { anchor: 'body_id', align: VerticalAlign.Top }
      })
    }
    .width('auto')
    .height('auto')
  }

  @Builder
  circleBadge() {
    Text(this.count.toString())
      .width(this.badgeH)
      .height(this.badgeH)
      .clipShape(new CircleShape({ width: this.badgeH, height: this.badgeH }))
      .fontSize($r('sys.float.Caption_M'))
      .fontColor($r('sys.color.font_on_primary'))
      .backgroundColor($r('sys.color.warning'))
      .textAlign(TextAlign.Center)
  }

  @Builder
  capsuleBadge() {
    Text(this.count > this.maxCount ? `${this.maxCount}+` : this.count.toString())
      .height(this.badgeH)
      .fontSize($r('sys.float.Caption_M'))
      .fontColor($r('sys.color.font_on_primary'))
      .borderRadius($r('app.float.small_radius'))
      .backgroundColor($r('sys.color.warning'))
      .textAlign(TextAlign.Center)
      .padding({
        top: 1,
        bottom: 1,
        left: 6,
        right: 6,
      })
  }

  @Computed
  get showCircleBadge() {
    return this.count > 0 && this.count < 10;
  }

  @Computed
  get showCapsuleBadge() {
    return this.count >= 10;
  }
}