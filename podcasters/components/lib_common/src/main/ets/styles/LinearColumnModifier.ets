import { PersistenceV2 } from '@kit.ArkUI'
import { SettingModel } from '../models/SettingModel'

@ObservedV2
export class LinearColumnModifier implements AttributeModifier<ColumnAttribute> {
  @Trace settingInfo: SettingModel = PersistenceV2.connect(SettingModel, () => new SettingModel())!
  color: ResourceStr = '#FFFFFF'

  constructor(color: ResourceStr) {
    this.color = color
  }

  applyNormalAttribute(instance: ColumnAttribute): void {
    if (!this.settingInfo.darkSwitch) {
      instance.linearGradient({
        angle: 180,
        colors: [
          [$r('app.color.gradient_start'), 0.05],
          [this.color, 0.12],
        ],
      })
    }
  }
}