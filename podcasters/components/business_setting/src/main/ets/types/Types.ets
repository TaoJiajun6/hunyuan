import { RouterMap } from 'lib_common';

export interface ISelectOption {
  id: number;
  label: string;
  value?: number;
}

export interface ISettingItem {
  icon?: ResourceStr;
  label: ResourceStr;
  subLabel?: ResourceStr;
  routerName?: RouterMap;
  routerParams?: Object;
  typeSwitch?: boolean;
  typeSelect?: boolean;
  switchV?: boolean;
  selectV?: number;
  selectOptions?: ISelectOption[];
  selectTitle?: string;
  extraLabel?: ResourceStr;
  onClick?: (param?: Object) => void;
  onSelect?: (param?: Object) => void;
}

/**
 * 设置ListItem类型
 */
@ObservedV2
export class SettingItem implements ISettingItem {
  @Trace icon?: ResourceStr = '';
  @Trace label: ResourceStr = '';
  @Trace subLabel?: ResourceStr = '';
  @Trace routerName?: RouterMap;
  @Trace routerParams?: Object;
  @Trace typeSwitch?: boolean = false;
  @Trace typeSelect?: boolean = false;
  @Trace switchV?: boolean;
  @Trace selectV?: number;
  @Trace selectOptions?: ISelectOption[];
  @Trace selectTitle?: string;
  @Trace extraLabel?: ResourceStr;
  @Trace onClick?: (param?: Object) => void;
  @Trace onSelect?: (param?: Object) => void;

  constructor(item?: ISettingItem) {
    if (!item) {
      return;
    }
    this.icon = item.icon;
    this.label = item.label;
    this.subLabel = item.subLabel;
    this.routerName = item.routerName;
    this.routerParams = item.routerParams;
    this.typeSwitch = item.typeSwitch;
    this.typeSelect = item.typeSelect;
    this.switchV = item.switchV;
    this.selectV = item.selectV;
    this.selectOptions = item.selectOptions;
    this.selectTitle = item.selectTitle;
    this.extraLabel = item.extraLabel;
    this.onClick = item.onClick;
    this.onSelect = item.onSelect;
  }
}