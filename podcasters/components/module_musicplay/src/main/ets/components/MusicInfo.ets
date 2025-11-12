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


import { PlayerControlArea } from './PlayerControlArea';
import { getMusicModel, MusicModel } from '../viewmodel/MusicModel';
import { QualityList } from './QualityList';
import { MediaService } from '../utils/MediaService';
import ImageUtils from '../utils/ImageUtils';

/**
 * 曲信息页面
 */
@ComponentV2
export struct MusicInfo {
  @Local naviIndicatorHeight: number = 0;
  // 歌曲信息
  @Local musicModel: MusicModel = getMusicModel();
  // 是否展示音质选择页面
  @Local isShowSheet: boolean = false;
  @Local maxWidth: number = 350;

  aboutToAppear(): void {
    this.naviIndicatorHeight = AppStorage.get('naviIndicatorHeight') as number;
    this.updateSongCoverMaxWidth()
  }

  @Monitor('musicModel.windowsMode')
  updateSongCoverMaxWidth() {
    if (this.musicModel.windowsMode === 4) {
      this.maxWidth = 200
    } else {
      this.maxWidth = 350
    }
  }

  build() {
    Column() {
      this.coverInfo() //歌曲封面信息
      this.musicInfo() //歌曲信息
      PlayerControlArea() //播放控制区域
    }
    .height('100%')
    .width('100%')
    .clip(false)
    .margin({
      top: $r('app.float.music_component_top'),
      bottom: $r('app.float.music_component_bottom')
    })
    .padding({
      left: $r('app.float.common_padding'),
      right: $r('app.float.common_padding')
    })
  }

  @Builder
  coverInfo() {
    Row() {
      Image(ImageUtils.getPic(this.musicModel.currentSong?.label ?? 'ic_dream'))
        .width('100%')
        .aspectRatio(1)
        .borderRadius($r('app.float.cover_radius_label'))
        .constraintSize({
          maxWidth: this.maxWidth
        })
        .shadow({
          radius: $r('app.float.shadow_radius'),
          color: $r('app.color.shadow_color'),
          offsetX: 0,
          offsetY: 6
        })
        .margin($r('app.float.lyric_margin_right_sm'))
    }
  }

  @Builder
  musicInfo() {
    Column() {
      Flex({ justifyContent: FlexAlign.SpaceBetween, alignItems: ItemAlign.Center }) {
        Row() {
          Text(this.musicModel.currentSong?.title)
            .fontSize($r('app.float.title_font_play'))
            .fontColor(Color.White)
            .opacity(0.86)
            .fontWeight(FontWeight.Bold)
            .margin({ right: 8 })
            .width(200)
            .maxLines(1)
            .textOverflow({ overflow: TextOverflow.Ellipsis })
        }
        .layoutWeight(1)

        Row({ space: 8 }) {
          Text(`音质：${MediaService.getInstance().getCurrentQuality()}`)
            .textAlign(TextAlign.Start)
            .fontSize($r('app.float.font_fourteen'))
            .fontColor($r('app.color.slider_select'))
            .margin({ top: $r('app.float.music_text_margin_top') })
            .fontWeight(FontWeight.Regular)
            .bindSheet($$this.isShowSheet, this.qualityListSheet(), {
              height: '50%',
              dragBar: true,
              showClose: true,
              title: { title: '音质选择' }
            })
          SymbolGlyph($r('sys.symbol.arrowtriangle_down_fill'))
            .fontSize(18)
            .symbolEffect(new ReplaceSymbolEffect(EffectScope.WHOLE), true)
            .fontColor([$r('app.color.slider_select')])
        }
        .width('fit-content')
        .height(32)
        .padding({
          left: 12,
          right: 8,
          top: 0,
          bottom: 0
        })
        .backgroundColor('#11ffffff')
        .borderRadius(16) // 椭圆形框 (高度的一半)
        .onClick(() => {
          this.isShowSheet = !this.isShowSheet;
        })
      }
      .width('100%')

      Row({ space: 5 }) {
        Image($r('app.media.ic_local'))
          .width(25)
          .height(16)
          .fillColor($r('app.color.slider_select'))
          .visibility(this.musicModel.currentSong?.isLocal ? Visibility.Visible : Visibility.None)
        Image($r('app.media.ic_vip'))
          .width(25)
          .height(16)
          .fillColor($r('app.color.slider_select'))
          .visibility(this.musicModel.currentSong?.isVip ? Visibility.Visible : Visibility.None)
        Text(this.musicModel.currentSong?.singer)
          .textAlign(TextAlign.Start)
          .fontSize($r('app.float.font_fourteen'))
          .fontColor($r('app.color.play_text_color'))
          .margin({ top: $r('app.float.music_text_margin_top') })
          .width('100%')
          .fontWeight(FontWeight.Regular)
      }
    }
    .margin({ top: $r('app.float.music_info_margin_top') })

    Blank()
  }

  @Builder
  qualityListSheet() {
    QualityList({
      onChange: (quality) => {
        this.isShowSheet = false;
      }
    })
      .width('100%')
      .height('100%')
      .padding({ bottom: this.naviIndicatorHeight })
  }
}


