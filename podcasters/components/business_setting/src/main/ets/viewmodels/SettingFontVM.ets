import { promptAction } from '@kit.ArkUI';
import { BaseViewModel } from 'lib_common';

@ObservedV2
export class SettingFontViewModel extends BaseViewModel {
  @Trace currentRatio: number = this.settingInfo.fontSizeRatio;

  confirm(ratio: number) {
    this.currentRatio = ratio;
    this.settingInfo.fontSizeRatio = ratio;
    promptAction.showToast({ message: '字号设置已成功' });
  }
}