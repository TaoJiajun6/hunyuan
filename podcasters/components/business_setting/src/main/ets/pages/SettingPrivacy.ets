import { CommonConstants, GridRowColSetting } from 'lib_common';
import { NavHeaderBar } from 'lib_widget';
import { SettingCard } from '../components/SettingCard';
import { SettingPrivacyVM } from '../viewmodels/SettingPrivacyVM'

@Builder
export function SettingPrivacyBuilder() {
  SettingPrivacy()
}

@ComponentV2
struct SettingPrivacy {
  @Local vm: SettingPrivacyVM = new SettingPrivacyVM();

  build() {
    NavDestination() {
      Column() {
        NavHeaderBar({
          title: '隐私设置',
        })
        GridRow(GridRowColSetting.DEFAULT_GRID_ROW_OPTIONS) {
          GridCol({
            span: GridRowColSetting.DEFAULT_CENTER_COL_SPAN,
            offset: GridRowColSetting.DEFAULT_CENTER_COL_OFFSET,
          }) {
            Scroll() {
              Column({ space: CommonConstants.SPACE_M }) {
                SettingCard({ list: this.vm.list1 })
                SettingCard({ list: this.vm.list2 })
              }
              .padding({
                left: this.vm.breakPointModel.pagePadding,
                right: this.vm.breakPointModel.pagePadding,
                top: CommonConstants.PADDING_M,
                bottom: this.vm.windowModel.windowBottomPadding,
              })
            }
            .layoutWeight(1)
            .scrollBar(BarState.Off)
            .align(Alignment.Top)
            .edgeEffect(EdgeEffect.Spring)
          }
        }
        .layoutWeight(1)
      }
      .width(CommonConstants.FULL_PERCENT)
      .height(CommonConstants.FULL_PERCENT)
    }
    .hideTitleBar(true)
    .backgroundColor($r('sys.color.background_secondary'))
  }
}