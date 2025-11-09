import { AppStorageV2 } from '@kit.ArkUI';
import { CommonConstants, NetworkModel } from 'lib_common'

@ComponentV2
export struct NetworkExceptionView {
  @Param textFontColor: ResourceColor = '#E5FFFFFF';
  @Param btnFontColor: ResourceColor = Color.White;
  @Param btnBorderColor: ResourceColor = '#99ffffff'
  @Event refreshNetwork: () => void = () => {}
  @Local networkModel: NetworkModel = AppStorageV2.connect(NetworkModel, () => NetworkModel.getInstance())!;

  build() {
    Column({ space: CommonConstants.SPACE_L }) {
      Image($r('app.media.ic_net_exception'))
        .width(120)

      Text('网络不给力，请重试')
        .fontSize(14)
        .lineHeight(19)
        .fontColor(this.textFontColor)

      Row() {
        Text('点击重试')
          .fontColor(this.btnFontColor)
          .fontSize(14).fontWeight(500)
      }
      .padding({ left: 10, top: 8, bottom: 8, right: 10 })
      .border({ width: 1, color: this.btnBorderColor, style: BorderStyle.Solid, radius: 30 })
      .margin({ top: 40 })
      .onClick(() => {
        this.refreshNetwork && this.refreshNetwork()
      })
    }
    .width(CommonConstants.FULL_PERCENT)
    .height(CommonConstants.FULL_PERCENT)
    .justifyContent(FlexAlign.Center)
    .alignItems(HorizontalAlign.Center)
  }
}