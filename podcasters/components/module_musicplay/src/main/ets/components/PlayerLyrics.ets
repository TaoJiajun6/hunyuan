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
import { MediaService } from '../utils/MediaService';

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
      // 顶部区域：标题、作者信息、播放按钮
      Column({ space: 12 }) {
        // 图标和标题
        Row({ space: 12 }) {
          // 图标
          Image(this.musicModel.currentSong?.label)
            .width(60)
            .height(60)
            .borderRadius(12)
            .aspectRatio(1)
            .objectFit(ImageFit.Cover)

          // 标题和作者信息
          Column({ space: 4 }) {
            Text(this.musicModel.currentSong?.title ?? '未知播客')
              .fontSize(18)
              .fontColor(Color.White)
              .fontWeight(FontWeight.Bold)
              .maxLines(2)
              .textOverflow({ overflow: TextOverflow.Ellipsis })
              .width('100%')
              .textAlign(TextAlign.Start)

            Row({ space: 8 }) {
              // 作者信息
              Row({ space: 4 }) {
                SymbolGlyph($r('sys.symbol.person'))
                  .fontSize(14)
                  .fontColor([Color.White])
                  .opacity(0.6)
                Text(this.musicModel.currentSong?.singer ?? '未知作者')
                  .fontSize(12)
                  .fontColor(Color.White)
                  .opacity(0.6)
              }

              // 播放次数
              Row({ space: 4 }) {
                SymbolGlyph($r('sys.symbol.headphones'))
                  .fontSize(14)
                  .fontColor([Color.White])
                  .opacity(0.6)
                Text('39')
                  .fontSize(12)
                  .fontColor(Color.White)
                  .opacity(0.6)
              }

              // 日期
              Text('12-11')
                .fontSize(12)
                .fontColor(Color.White)
                .opacity(0.6)
            }
            .width('100%')
            .margin({ top: 4 })
          }
          .layoutWeight(1)
          .alignItems(HorizontalAlign.Start)
        }
        .width('100%')
        .alignItems(VerticalAlign.Center)

        // 播放按钮
        Row() {
          Button() {
            Row({ space: 8 }) {
              SymbolGlyph(this.musicModel.isPlay ? $r('sys.symbol.pause_fill') : $r('sys.symbol.play_fill'))
                .fontSize(20)
                .fontColor([Color.White])
              Text(this.musicModel.totalTime || '8分钟')
                .fontSize(14)
                .fontColor(Color.White)
            }
          }
          .type(ButtonType.Normal)
          .backgroundColor('#33FFFFFF')
          .borderRadius(24)
          .height(48)
          .padding({ left: 24, right: 24 })
          .onClick(() => {
            MediaService.getInstance().playAndPause();
          })
        }
        .width('100%')
        .justifyContent(FlexAlign.Center)
        .margin({ top: 8 })
      }
      .width('100%')
      .margin({
        top: 100,
        bottom: 24
      })

      // 脚本内容区域（可滚动）
      if (this.musicModel.currentSong?.script && this.musicModel.currentSong.script.trim().length > 0) {
        Scroll() {
          Text(this.musicModel.currentSong.script)
            .fontSize(15)
            .fontColor(Color.White)
            .opacity(0.9)
            .lineHeight(26)
            .textAlign(TextAlign.Start)
            .padding({
              left: 16,
              right: 16,
              top: 20,
              bottom: 20
            })
            .width('100%')
        }
        .layoutWeight(1)
        .width('100%')
        .borderRadius(16)
        .backgroundColor('#1AFFFFFF')
        .margin({ bottom: 16 })
      } else if (this.mLrcEntryList.length > 0) {
        // 如果没有脚本，显示歌词
        LrcView({
          lyricMilliSecondsTime: this.musicModel.progress,
          mLrcEntryList: this.mLrcEntryList,
          lyricScrollEffect: this.lyricScrollEffect,
          lyricTopPosition: LyricTopPosition.Middle
        })
          .layoutWeight(1)
      } else {
        Blank()
          .layoutWeight(1)
      }

      // 底部播放控制区域
      PlayerControlArea()
        .margin({
          top: 16,
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