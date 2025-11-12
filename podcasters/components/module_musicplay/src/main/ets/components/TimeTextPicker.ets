import { Logger } from '../utils/Logger'
import { Operation } from './Operation'

@ComponentV2
export struct TimeTextPicker {
  /**
   * 弹窗标题
   */
  @Param title: string = ''
  /**
   * 当前传入的绑定列表
   */
  @Require @Param textList: string[] = []
  /**
   * 传入默认选择值
   */
  @Param selected: number = 1
  /**
   * 当前选择值
   */
  @Local select: number = 1
  /**
   * 切换回调
   */
  @Event textPickerChange: (value: number) => void = () => {
  }
  /**
   * 取消回调
   */
  @Event cancel: () => void = () => {
  }
  /**
   * 确认回调
   */
  @Event confirm: (value: number) => void = () => {
  }

  aboutToAppear(): void {
    this.select = this.selected
  }

  build() {
    Column() {
      Operation({
        isShowTitle: true,
        currentDate: this.title,
        confirm: () => {
          this.confirm(this.select)
        },
        cancel: () => {
          this.cancel()
        }
      })

      TextPicker({ range: this.textList, selected: this.select })
        .onChange((value: string | string[], index: number | number[]) => {
          this.select = index as number
          this.textPickerChange(this.select)
        })
        .onScrollStop((value: string | string[], index: number | number[]) => {
          Logger.info('Picker scroll stopped, value: ' + value + ', index: ' + index)
        })
        .height(240)
    }
    .justifyContent(FlexAlign.End)
    .height('100%')
    .width('100%')
    .transition(TransitionEffect.translate({ y: 500 }))
  }
}