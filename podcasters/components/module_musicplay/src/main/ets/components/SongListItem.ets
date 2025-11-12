/*
 * Copyright (c) 2024 Huawei Device Co., Ltd.
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */


import { MediaService } from '../utils/MediaService';
import { getMusicModel, MusicModel } from '../viewmodel/MusicModel';
import { SongItem } from '../viewmodel/SongItem';
import { promptAction } from '@kit.ArkUI';

@ComponentV2
export struct SongListItem {
  @Local musicModel: MusicModel = getMusicModel();
  @Param @Require item: SongItem;
  @Param @Require index: number = 0;
  private isCanPlay: boolean = true;
  @Local isCollected: boolean = false

  aboutToAppear(): void {
    this.isCollected = this.item.isCollected;
  }

  /**
   * 收藏监听
   * @param value
   */
  @Monitor('item.isCollected')
  collectedMonitor(value: boolean) {
    this.isCollected = value;
  }

  /**
   * 收藏
   */
  async collected() {
    if (this.item.isCollected) {
      this.item.isCollected = false;
      this.isCollected = false;
      MediaService.getInstance().unCollect(this.item.id);
      promptAction.showToast({ message: '取消收藏' });
    } else {
      this.item.isCollected = true;
      this.isCollected = true;
      MediaService.getInstance().collect(this.item.id);
      //提示收藏成功
      promptAction.showToast({ message: '收藏成功' });
    }
  }

  /**
   *  获取歌曲类型
   */
  getSongType(song: SongItem): ResourceStr {
    // 判断是否位本地歌曲
    if (song?.isLocal) {
      return $r('app.media.ic_local')
    }
    if (song?.isVip) {
      return $r('app.media.ic_vip');
    }
    return '';
  }

  getColor(): ResourceColor {
    let themeColor = getMusicModel().themeColor;
    if (themeColor === '#FFFFFFFF') {
      themeColor = '#FF1949';
    }
    return this.item.id === getMusicModel().currentSong?.id ? themeColor :
    $r('sys.color.ohos_id_color_text_primary');
  }

  build() {
    Row() {
      Column() {
        Text(this.item.title)
          .fontWeight(500)
          .fontColor(this.getColor())
          .fontSize(16)
          .margin({ bottom: 4 })
        Row({ space: 4 }) {
          Image($r('app.media.zhibozhong'))
            .width(16)
            .height(16)
            .fillColor(this.getColor())
            .visibility((this.item.id === getMusicModel().currentSong?.id ?? '') ? Visibility.Visible : Visibility.None)
          Image(this.getSongType(this.item))
            .width(25)
            .height(16)
            .visibility((!this.item?.isVip && !this.item?.isLocal) ? Visibility.None : Visibility.Visible)
          Text(this.item.singer)
            .fontSize(12)
            .fontWeight(400)
            .fontColor(this.getColor())
        }
      }
      .alignItems(HorizontalAlign.Start)

      SymbolGlyph($r('sys.symbol.xmark'))
        .fontSize(23)
        .symbolEffect(new ReplaceSymbolEffect(EffectScope.WHOLE), true)
        .fontColor([Color.Black])
        .onClick(() => {
          MediaService.getInstance().removeSongById(this.item.id)
        })
    }
    .justifyContent(FlexAlign.SpaceBetween)
    .padding({
      left: 16,
      right: 16,
      top: 12,
      bottom: 12
    })
    .onClick(() => {
      if (this.isCanPlay && !(this.item.id === this.musicModel.currentSong?.id)) {
        MediaService.getInstance().controlPlay(this.index);
      }
    })
    .width('100%')
  }
}


