import { BaseViewModel } from 'lib_common';
import { ISelectOption, SettingItem } from '../types/Types';

@ObservedV2
export class SettingNetworkVM extends BaseViewModel {
  @Trace item1: SettingItem = new SettingItem({
    typeSelect: true,
    label: '非WLAN网络流量',
    selectTitle: '非WLAN网络流量',
    selectOptions: [
      {
        id: 0,
        label: '最佳效果（下载大图）',
      },
      {
        id: 1,
        label: '较省流量（智能下载）',
      },
      {
        id: 2,
        label: '极省流量（不下载图）',
      },
    ],
    selectV: this.settingInfo.network.downloadWithoutWlan,
    onSelect: (option) => {
      this.settingInfo.network.downloadWithoutWlan = (option as ISelectOption).id;
      this.item1.selectV = this.settingInfo.network.downloadWithoutWlan;
    },
  });
  @Trace item2: SettingItem = new SettingItem({
    typeSelect: true,
    label: '非WLAN网络播放提醒',
    selectTitle: '非WLAN网络播放提醒',
    selectOptions: [
      {
        id: 0,
        label: '提醒一次',
      },
      {
        id: 1,
        label: '每次提醒',
      },
    ],
    selectV: this.settingInfo.network.remindWithoutWlan,
    onSelect: (option) => {
      this.settingInfo.network.remindWithoutWlan = (option as ISelectOption).id;
      this.item2.selectV = this.settingInfo.network.remindWithoutWlan;
    },
  });
  @Trace item4: SettingItem = new SettingItem({
    typeSwitch: true,
    label: '使用移动网络改善内容浏览体验',
    subLabel: '如Wi-Fi网络质量差，将使用移动网络改善',
    switchV: this.settingInfo.network.optimizeWith4G,
    onClick: (isOn) => {
      this.item4.switchV = isOn as boolean;
      this.settingInfo.network.optimizeWith4G = isOn as boolean;
    },
  });
  @Trace item5: SettingItem = new SettingItem({
    typeSwitch: true,
    label: '视频自动下滑',
    subLabel: '视频观看结束将自动下滑至下一个视频',
    switchV: this.settingInfo.network.autoPlayNext,
    onClick: (isOn) => {
      this.item5.switchV = isOn as boolean;
      this.settingInfo.network.autoPlayNext = isOn as boolean;
    },
  });
  @Trace item6: SettingItem = new SettingItem({
    typeSwitch: true,
    label: '推荐频道自动播放视频',
    switchV: this.settingInfo.network.autoPlayTabRecommend,
    onClick: (isOn) => {
      this.item6.switchV = isOn as boolean;
      this.settingInfo.network.autoPlayTabRecommend = isOn as boolean;
    },
  });
  @Trace list1: SettingItem[] = [
    this.item1,
    this.item2,
    this.item4,
  ];
  @Trace list2: SettingItem[] = [
    this.item5,
    this.item6,
  ];
}