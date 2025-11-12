import { displaySync } from '@kit.ArkGraphics2D';
import ImageUtils from '../utils/ImageUtils';
import { getMusicModel, MusicModel } from '../viewmodel/MusicModel';

/**
 * 圆形唱片
 */
@ComponentV2
export struct RotatingCover {
  @Local musicModel: MusicModel = getMusicModel();
  @Local imageRotate: number = 0;
  private backDisplaySyncSlow: displaySync.DisplaySync | undefined = undefined;
  private drawFrame = () => {
    if (this.imageRotate >= 360) {
      this.imageRotate = 0;
    }
    this.imageRotate += 1;
  };

  /**
   * 播放状态监听
   */
  @Monitor('musicModel.isPlay')
  animationFun() {
    if (this.musicModel.isPlay) {
      this.backDisplaySyncSlow?.start();
    } else {
      this.backDisplaySyncSlow?.stop();
    }
  }

  aboutToAppear() {
    let range: ExpectedFrameRateRange = {
      expected: 30,
      min: 0,
      max: 30
    };

    this.backDisplaySyncSlow = displaySync.create();
    this.backDisplaySyncSlow.setExpectedFrameRateRange(range);
    this.backDisplaySyncSlow.on('frame', this.drawFrame);
  }

  aboutToDisappear(): void {
    this.backDisplaySyncSlow?.off('frame', this.drawFrame);
  }

  build() {
    Column() {
      Image(ImageUtils.getPic(this.musicModel.currentSong?.label ?? 'default'))
        .height(32)
        .width(32)
        .borderRadius(16)
        .margin({ right: 12 })
        .rotate({ angle: this.imageRotate })
        .onAppear(() => {
          this.animationFun();
        })
    }
  }
}