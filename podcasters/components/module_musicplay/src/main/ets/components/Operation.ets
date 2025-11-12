@ComponentV2
export struct Operation {
  @Param currentDate: string = ''
  @Param isShowTitle: boolean = false
  @Param isBottom: boolean = false
  @Event confirm: () => void = () => {
  }
  @Event cancel: () => void = () => {
  }

  build() {
    Row() {
      Row() {
        Text('取消')
          .fontSize($r('sys.float.Body_L'))
          .fontColor($r('sys.color.font_primary'))
          .fontWeight(FontWeight.Bold)
      }
      .onClick(() => {
        this.cancel()
      })

      Row() {
        Text(this.currentDate).fontWeight(FontWeight.Bold)
          .fontSize(20)
      }
      .visibility(this.isShowTitle ? Visibility.Visible : Visibility.None)

      Row() {
        Text('确认')
          .fontWeight(FontWeight.Bold)
          .fontColor('#FFE94949')
          .fontSize($r('sys.float.Body_L'))
      }
      .onClick(() => {
        this.confirm()
      })
    }
    .width('100%')
    .padding({
      top: 10,
      left: 20,
      right: 20,
      bottom: 10
    })
    .justifyContent(FlexAlign.SpaceBetween)
    .backgroundColor(Color.White)
    .padding({
      left: 32,
      right: 32,
      bottom: this.isBottom ? 24 : 16,
      top: this.isBottom ? 24 : 16
    })
  }
}