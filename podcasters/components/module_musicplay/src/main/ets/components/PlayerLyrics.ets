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

import { common } from '@kit.AbilityKit';
import { util } from '@kit.ArkTS';
import { PlayerControlArea } from './PlayerControlArea';
import LrcView from '../lyric/LrcView';
import { LyricFile, LyricScrollEffect, LyricTopPosition } from '../lyric/LyricConst';
import { LrcEntry } from '../lyric/LrcEntry';
import { parseKrcLyric, parseLrcLyric } from '../lyric/LrcUtils';
import { getMusicModel, MusicModel } from '../viewmodel/MusicModel';

/**
 * 歌词页面
 */
@ComponentV2
export struct PlayerLyrics {
  @Local time: number = 0;
  @Local isPlay: boolean = false;
  @Local musicModel: MusicModel = getMusicModel();
  @Local progressText: string = '';
  @Local lyricScrollEffect: LyricScrollEffect = LyricScrollEffect.Line;
  @Local mLrcEntryList: LrcEntry[] = [];
  private context: common.UIAbilityContext | undefined = AppStorage.get('context');

  aboutToAppear() {
    this.getLrcEntryList();
  }

  @Monitor('currentSong')
  getLrcEntryList() {
    this.mLrcEntryList = [];
    if (!this.context || !this.musicModel.currentSong) {
      return;
    }
    this.context.resourceManager.getRawFileContent(this.musicModel.currentSong?.lyric)
      .then((value: Uint8Array) => {
        let textDecoder = util.TextDecoder.create('utf-8', { ignoreBOM: true });
        let stringData = textDecoder.decodeToString(value, { stream: false });
        if (this.musicModel.currentSong?.lyric.endsWith(LyricFile.KRC)) {
          this.mLrcEntryList = parseKrcLyric(stringData);
        } else if (this.musicModel.currentSong?.lyric.endsWith(LyricFile.LRC)) {
          this.mLrcEntryList = parseLrcLyric(stringData);
        }
      })
  }

  build() {
    Column() {
      Row() {
        Image(this.musicModel.currentSong?.label)
          .width($r('app.float.label_width_sm'))
          .borderRadius($r('app.float.label_border'))
          .aspectRatio(1)
          .margin({
            right: $r('app.float.label_margin_right')
          })

        Column() {
          Text(this.musicModel.currentSong?.title)
            .fontSize(16)
            .fontColor(Color.White)
            .fontWeight(700)
          Text(this.musicModel.currentSong?.singer)
            .fontSize(12)
            .fontColor($r('sys.color.ohos_id_color_text_hint_contrary'))
            .fontWeight(500)
            .margin({
              top: $r('app.float.singer_margin_top')
            })
        }
        .alignItems(HorizontalAlign.Start)
      }
      .width('100%')
      .justifyContent(FlexAlign.Start)
      .margin({
        top: 48,
        bottom: $r('app.float.info_margin_bottom')
      })

      LrcView({
        lyricMilliSecondsTime: this.musicModel.progress,
        mLrcEntryList: this.mLrcEntryList,
        lyricScrollEffect: this.lyricScrollEffect,
        lyricTopPosition: LyricTopPosition.Middle
      })
        .layoutWeight(1)

      Row() {
        Image($r('app.media.ic_lyrics_button'))
          .width(24)
          .aspectRatio(1)
          .opacity(0.86)
      }
      .width('100%')
      .height($r('app.float.control_icon_height'))
      .justifyContent(FlexAlign.End)
      .margin({
        top: $r('app.float.lyric_margin_top'),
        bottom: 8,
        right: 3
      })

      PlayerControlArea()
        .margin({
          top: $r('app.float.control_lyric_margin'),
          bottom: $r('app.float.music_component_bottom')
        })
    }
    .margin({
      top: $r('app.float.margin_lyric')
    })
    .padding({
      left: $r('app.float.common_padding'),
      right: $r('app.float.common_padding')
    })
  }
}