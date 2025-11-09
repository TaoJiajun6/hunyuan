@ComponentV2
export struct Empty {
  @Param text: string = '暂无记录';
  @Param fontSizeRatio: number = 1;

  build() {
    Column({ space: 12 }) {
      Image($r('app.media.empty'))
        .width(200)
        .draggable(false)
      Text(this.text)
        .fontSize(14 * this.fontSizeRatio)
        .fontColor($r('sys.color.font_secondary'))
    }
  }
}