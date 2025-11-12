/*
 * Copyright (c) 2024 Huawei Device Co., Ltd.
 * Licensed under the Apache License, Version 2.0 (the 'License');
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an 'AS IS' BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
import ImageUtils from '../utils/ImageUtils';
import { SongItem } from '../viewmodel/SongItem';
import { window } from '@kit.ArkUI';
import { MusicInfo } from './MusicInfo';
import { PlayerLyrics } from './PlayerLyrics';
import { PlayerTopArea } from './PlayerTopArea';
import { getMusicModel, MusicModel } from '../viewmodel/MusicModel';

/**
 * 播放器页面
 */
@ComponentV2
export struct PlayerView {
  // 播放器页面
  @Local naviIndicatorHeight: number = 0;
  // 状态栏高度
  @Local statusBarHeight: number = 0;
  // 音乐模型
  @Local musicModel: MusicModel = getMusicModel();
  // 背景颜色
  @Local imageColor: string = 'rgba(0, 0, 2, 1.00)';
  // 背景图片
  @Local imageLabel: PixelMap | undefined = undefined;

  aboutToAppear(): void {
    this.naviIndicatorHeight = AppStorage.get('naviIndicatorHeight') as number;
    this.statusBarHeight = AppStorage.get('statusBarHeight') as number;
    this.getImageColor();
  }

  /**
   * 获取图片颜色
   */
  @Monitor('musicModel.currentSong')
  getImageColor() {
    let currentSong: SongItem = getMusicModel().currentSong as SongItem;
    ImageUtils.getImageDealData(getContext(this), currentSong?.label as Resource).then((data) => {
      this.imageColor = data.imageColor;
      this.imageLabel = data.blurPixelMap;
    })
  }

  /**
   * 设置状态栏颜色
   * @param color
   */
  setStatusbarContentColor(color: string) {
    let windowStage: window.WindowStage = AppStorage.get('windowStage') as window.WindowStage;
    let mainWindow = windowStage.getMainWindowSync();
    let systemBarProperties: window.SystemBarProperties = {
      statusBarContentColor: color
    };
    mainWindow.setWindowSystemBarProperties(systemBarProperties);
  }

  build() {
    Stack() {
      Image(this.imageLabel)
        .size({ height: '120%' })
        .aspectRatio(1)
        .objectFit(ImageFit.Cover)
        .opacity(0.5)

      Row() {
        Stack({ alignContent: Alignment.TopStart }) {
          Swiper() {
            MusicInfo() //歌曲信息
            PlayerLyrics() //歌词
          }
          .height('100%')
          .indicator(
            new DotIndicator()
              .top(10)
              .selectedColor(Color.White)
              .color($r('sys.color.comp_background_secondary'))
          )
          .clip(false)
          .loop(false)

          // 顶部区域
          PlayerTopArea({
            changenShowPlay: (value: boolean) => {
              this.musicModel.isShowPlay = value;
            }
          })
        }
        .height('100%')
      }
      .padding({
        bottom: this.naviIndicatorHeight,
        top: this.statusBarHeight
      })
    }
    .onAppear(() => {
      // 设置状态栏颜色
      this.setStatusbarContentColor('#FFFFFF');
    })
    .onDisAppear(() => {
      // 恢复状态栏颜色
      this.setStatusbarContentColor('#000000');
    })
    .height('100%')
    .width('100%')
    .backgroundColor(this.imageColor)
  }
}