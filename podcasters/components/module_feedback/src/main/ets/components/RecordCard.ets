import { ImagePreview, PreviewVerticalAlign } from 'module_imagepreview';
import { CommonUtils } from '../common/CommonUtils';
import { Constants } from '../common/Constants';
import { FeedbackResponseParams } from '../services/ResponseModel'

@ComponentV2
export struct RecordCard {
  @Require @Param record: FeedbackResponseParams;
  @Param fontSizeRatio: number = 1;
  @Param gridCount: number = 3;

  build() {
    Column() {
      Text(CommonUtils.handleDateTime(this.record.createTime))
        .fontSize(12 * this.fontSizeRatio)
        .fontColor($r('sys.color.font_primary'))
        .fontWeight(FontWeight.Medium)
      Text('问题描述')
        .fontSize(16 * this.fontSizeRatio)
        .fontColor($r('sys.color.font_primary'))
        .fontWeight(FontWeight.Medium)
        .margin({
          top: 12,
        })
      Text(this.record.problemDesc)
        .fontSize(12 * this.fontSizeRatio)
        .fontColor($r('sys.color.font_secondary'))
        .margin({
          top: 8,
        })
      Text('问题截图')
        .fontSize(16 * this.fontSizeRatio)
        .fontColor($r('sys.color.font_primary'))
        .fontWeight(FontWeight.Medium)
        .margin({
          top: 12,
          bottom: 8,
        })
        .visibility(this.record?.screenShots?.length ? Visibility.Visible : Visibility.None)
      Grid() {
        if (this.record?.screenShots?.length) {
          ForEach(this.record.screenShots, (item: string, index: number) => {
            GridItem() {
              Image(item)
                .width(Constants.FULL_PERCENT)
                .aspectRatio(1)
                .borderRadius(16)
                .clip(true)
                .onClick(() => {
                  ImagePreview.show(this.record.screenShots, {
                    startIndex: index,
                    showIndex: true,
                    loop: false,
                    isBasicMode: true,
                    indexPosition: PreviewVerticalAlign.Top,
                  })
                })
            }
          }, (v: string) => v)
        }
      }
      .columnsTemplate(this.getColumnsTemplate)
      .columnsGap(12)
      .rowsGap(8)
      .maxCount(Constants.MAX_IMG_COUNT)
      .scrollBar(BarState.Off)
    }
    .width(Constants.FULL_PERCENT)
    .backgroundColor($r('sys.color.comp_background_primary'))
    .borderRadius(Constants.RADIUS_16)
    .padding(Constants.PADDING_M)
    .alignItems(HorizontalAlign.Start)
  }

  @Computed
  get getColumnsTemplate() {
    return Array(this.gridCount).fill('1fr').join(' ');
  }
}