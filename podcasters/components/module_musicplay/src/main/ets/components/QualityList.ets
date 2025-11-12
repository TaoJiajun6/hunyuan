import { Constants } from '../constants/Constants'
import { AudioQuality, MediaService } from '../utils/MediaService'


@ComponentV2
export struct QualityList {
  @Event onChange: (value: string) => void;

  build() {
    Column({ space: 15 }) {
      List() {
        this.radioItem(Constants.QUALITY_LOW, AudioQuality.LOW, 'radioGroup')
        this.radioItem(Constants.QUALITY_MEDIUM, AudioQuality.MEDIUM, 'radioGroup')
        this.radioItem(Constants.QUALITY_HIGH, AudioQuality.HIGH, 'radioGroup')
        this.radioItem(Constants.QUALITY_LOSSLESS, AudioQuality.LOSSLESS, 'radioGroup')
      }
      .width('100%')
      .cachedCount(3)
      .layoutWeight(1)
      .divider({
        strokeWidth: 1,
        color: '#E8E8E8',
        startMargin: 16,
        endMargin: 16
      })
    }
    .margin({ top: $r('app.float.common_padding') })
  }

  //单个左文字右单选按钮组件
  @Builder
  radioItem(text: string, quality: AudioQuality, value: string) {
    Row() {
      Text(text)
        .layoutWeight(1)

      Radio({ value: value, group: 'radioGroup' })
        .checked(quality === MediaService.getInstance().currentQuality ? true : false)
        .height(25)
        .width(25)
        .onChange((isChecked: boolean) => {
          if (isChecked) {
            MediaService.getInstance().currentQuality = quality
            this.onChange(text)
          }
        })
    }
    .padding({
      left: $r('app.float.common_padding'),
      right: $r('app.float.common_padding'),
      top: $r('app.float.lyric_margin_top'),
    })
    .alignItems(VerticalAlign.Center)
    .justifyContent(FlexAlign.SpaceBetween)
  }
}