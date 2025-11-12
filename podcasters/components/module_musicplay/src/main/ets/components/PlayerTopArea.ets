/*
 * Copyright (c) 2024 Huawei Device Co., Ltd.
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
import { promptAction } from '@kit.ArkUI';
import { MediaService } from '../utils/MediaService';
import { getMusicModel } from '../viewmodel/MusicModel';

@ComponentV2
export struct PlayerTopArea {
  @Event changenShowPlay: (value: boolean) => void = (value: boolean) => {
  };

  build() {
    Row() {
      Image($r('app.media.ic_back_down'))
        .width(24)
        .height(24)
        .onClick(() => {
          this.changenShowPlay(false);
        })

      Image($r('app.media.ic_mv'))
        .width(38)
        .height(38)
        .onClick(() => {
          if (!getMusicModel().currentSong?.mvUrl) {
            promptAction.showToast({ message: '无MV文件' });
            return
          }
          MediaService.getInstance().pause()
          this.changenShowPlay(false);
          if (getMusicModel().currentSong && getMusicModel().currentSong?.mvUrl) {
            MediaService.getInstance().playMv(getMusicModel().currentSong?.mvUrl ?? '')
          }
        })
    }
    .height(48)
    .width('100%')
    .justifyContent(FlexAlign.SpaceBetween)
    .padding({
      left: 24,
      right: 24
    })
  }
}