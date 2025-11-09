import { DownloadWithoutWlanEnum, NetworkModel } from 'lib_common';

@ComponentV2
export struct BaseImage {
  @Param url: string = '';
  @Param fit: ImageFit = ImageFit.Cover
  @Param imgRadius: number = 8;
  @Param @Once downloadWithoutWlan: number = 0;
  @Local imageUrl: ResourceStr = ''

  aboutToAppear() {
    let network = NetworkModel.getInstance();
    let isCellular = network.isNetworkAvailable && network.isCellular;
    let isDisabled = this.downloadWithoutWlan === DownloadWithoutWlanEnum.downloadDisable;
    this.imageUrl = isCellular && isDisabled ? $r('app.media.ic_default_bg') : this.url;
  }

  build() {
    Image(this.imageUrl)
      .objectFit(this.fit)
      .backgroundColor($r('sys.color.comp_background_tertiary'))
      .borderRadius(this.imgRadius)
      .draggable(false)
  }
}