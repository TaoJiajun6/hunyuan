import { SelectDialog } from '@kit.ArkUI';
import { CommonConstants, GridRowColSetting, PopViewUtils } from 'lib_common';
import { SettingItem } from '../types/Types';

@Builder
export function SettingSelectDialog(v: SettingItem) {
  Column() {
    Column() {
      SelectDialog({
        title: v.selectTitle,
        selectedIndex: v.selectV,
        confirm: {
          value: '取消',
          action: () => {
            PopViewUtils.closePopView();
          },
        },
        radioContent: v.selectOptions?.map(item => {
          return {
            title: item.label,
            action: () => {
              if (v.onSelect) {
                v.onSelect(item);
                PopViewUtils.closePopView();
              }
            },
          } as SheetInfo;
        })
      })
    }
    .width(CommonConstants.FULL_PERCENT)
    .borderRadius($r('app.float.xxl_radius'))
    .backgroundColor($r('sys.color.comp_background_primary'))
    .constraintSize({ maxWidth: GridRowColSetting.DIALOG_MAX_WIDTH })
  }
  .width(CommonConstants.FULL_PERCENT)
  .padding({
    left: CommonConstants.PADDING_L,
    right: CommonConstants.PADDING_L,
  })
}