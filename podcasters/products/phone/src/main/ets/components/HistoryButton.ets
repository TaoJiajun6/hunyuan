@ComponentV2
export struct HistoryButton {
  @Event onEvent?: () => void;
  @Param isBtnHidden: boolean = false;

  build() {
    SymbolGlyph($r('sys.symbol.exercise_records'))
      .fontSize($r('sys.float.Title_M'))
      .fontColor([$r('sys.color.icon_primary')])
      .padding(8)
      .borderRadius(40)
      .backgroundColor($r('sys.color.comp_background_tertiary'))
      .onClick(() => {
        this.onEvent?.();
      })
      .visibility(this.isBtnHidden ? Visibility.None : Visibility.Visible)
  }
}