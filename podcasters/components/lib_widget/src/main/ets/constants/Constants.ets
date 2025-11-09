/**
 * Common constants for common component.
 */
export class Constants {
  // Space
  static readonly SM_SPACE: number = 4;
  static readonly MD_SPACE: number = 8;
  static readonly LG_SPACE: number = 12;
  // Percent
  static readonly FULL_PERCENT: string = '100%';
  static readonly PADDING_S: number = 8;
  static readonly PADDING_L: number = 16;
  // 空白图标宽度
  public static readonly EMPTY_IMG_W: number = 120;
}

export interface IButtonItem {
  id: string;
  label: string;
}
