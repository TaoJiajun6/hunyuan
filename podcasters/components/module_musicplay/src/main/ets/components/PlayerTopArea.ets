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
import { promptAction, window } from '@kit.ArkUI';
import { MediaService } from '../utils/MediaService';
import { getMusicModel } from '../viewmodel/MusicModel';

@ComponentV2
export struct PlayerTopArea {
  @Event changenShowPlay: (value: boolean) => void = (value: boolean) => {
  };
  @Local statusBarHeight: number = 0;

  aboutToAppear(): void {
    // 优先从 AppStorage 获取，如果没有则从 window 直接获取
    let storedHeight = AppStorage.get('statusBarHeight') as number;
    if (storedHeight && storedHeight > 0) {
      this.statusBarHeight = storedHeight;
    } else {
      // 如果 AppStorage 中没有，尝试从 window 直接获取
      try {
        let windowStage = AppStorage.get('windowStage') as window.WindowStage;
        if (windowStage) {
          let windowClass = windowStage.getMainWindowSync();
          let avoidArea = windowClass.getWindowAvoidArea(window.AvoidAreaType.TYPE_SYSTEM);
          this.statusBarHeight = px2vp(avoidArea.topRect.height);
        } else {
          // 默认值
          this.statusBarHeight = 40;
        }
      } catch (error) {
        // 如果获取失败，使用默认值
        this.statusBarHeight = 40;
      }
    }
  }

  build() {
    Row() {
      Image($r('app.media.ic_back_down'))
        .width(24)
        .height(24)
        .onClick(() => {
          this.changenShowPlay(false);
        })
    }
    .height(48)
    .width('100%')
    .justifyContent(FlexAlign.SpaceBetween)
    .padding({
      left: 20,
      right: 20,
      top: this.statusBarHeight + 10
    })
  }
}