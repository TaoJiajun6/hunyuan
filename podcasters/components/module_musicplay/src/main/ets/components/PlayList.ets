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

import { getMusicModel, MusicModel } from '../viewmodel/MusicModel';
import { SongItem } from '../viewmodel/SongItem';
import { SongListItem } from './SongListItem';
import { promptAction } from '@kit.ArkUI';
import { MusicPlayMode } from '../viewmodel/MusicData';
import { MediaService } from '../utils/MediaService';
import { MediaTools } from '../utils/MediaTools';
import { TimeTextPicker } from './TimeTextPicker';


/**
 * 播放列表
 */
@ComponentV2
export struct PlayList {
  @Local naviIndicatorHeight: number = 0;
  @Local musicModel: MusicModel = getMusicModel();
  @Local playmodeImg: Resource = $r('sys.symbol.repeat');
  @Local playmodeTitle: string = '列表循环';
  @Local isShowSheet: boolean = false; //是否展示播放列表
  @Local futureTimeMs: number = 0;
  @Local stopTimeStr: string = '';
  @Local intervalTimer: number = 0;
  @Local textList: string[] = ['不启用', '10分钟', '20分钟', '30分钟', '40分钟', '50分钟', '60分钟']
  @Local select: number = 0

  aboutToAppear(): void {
    this.naviIndicatorHeight = AppStorage.get('naviIndicatorHeight') as number + 50;
    this.initStopTime();
    this.playModeBuilder();
    // 初始化定时关闭选择项
    this.select = this.getSelectedIndexFromStopTime();
  }

  initStopTime() {
    if (this.musicModel.stopTime > 0) {
      //更新倒计时
      this.intervalTimer = setInterval(() => {
        if (this.musicModel.stopTime > 0) {
          this.stopTimeStr = MediaTools.getRemainingTimeMMSS(this.musicModel.stopTime);
          if (this.stopTimeStr === '00:00') {
            clearInterval(this.intervalTimer);
          }
        } else {
          this.musicModel.stopTime = 0;
          clearInterval(this.intervalTimer);
        }
      }, 1000);
    }
  }

  aboutToDisappear(): void {
    this.intervalTimer = 0
    clearInterval(this.intervalTimer);
  }

  /**
   * 监听播放模式切换
   */
  @Monitor('musicModel.playMode')
  playModeBuilder() {
    switch (this.musicModel.playMode) {
      case MusicPlayMode.ORDER:
        this.playmodeImg = $r('sys.symbol.repeat');
        this.playmodeTitle = '列表循环';
        break;
      case MusicPlayMode.RANDOM:
        this.playmodeImg = $r('sys.symbol.shuffle');
        this.playmodeTitle = '随机播放';
        break;
      case MusicPlayMode.SINGLE_CYCLE:
        this.playmodeImg = $r('sys.symbol.repeat_1');
        this.playmodeTitle = '单曲循环';
        break;
    }
  }

  getStopTime(): number {
    // 遍历textList解析数字值
    const numericValues: number[] = this.textList.map(item => {
      const match = item.match(/\d+/);
      return match ? parseInt(match[0], 10) : 0;
    });
    return numericValues[this.select];
  }

  // 在 PlayList 组件中添加以下方法
  private getSelectedIndexFromStopTime(): number {
    if (this.musicModel.stopTime <= 0) {
      return 0; // 默认"不启用"
    }

    const remainingMinutes = Math.ceil((this.musicModel.stopTime - Date.now()) / (1000 * 60));

    // 查找最接近的预设值
    for (let i = 1; i < this.textList.length; i++) {
      const match = this.textList[i].match(/\d+/);
      const presetMinute = match ? parseInt(match[0], 10) : 0;

      if (Math.abs(presetMinute - remainingMinutes) < 1) { // 容忍1分钟误差
        return i;
      }
    }

    return 0; // 如果没有匹配项，默认为"不启用"
  }

  build() {
    Column() {
      Row() {
        Row() {
          SymbolGlyph(this.playmodeImg)
            .fontSize(23)
            .symbolEffect(new ReplaceSymbolEffect(EffectScope.WHOLE), true)
            .fontColor([Color.Black])

          Text(this.playmodeTitle)
            .fontSize(14)
            .fontWeight(400)
            .fontColor(Color.Black)
            .margin({ left: 16 })
            .textAlign(TextAlign.Start)
        }
        .layoutWeight(1)
        .onClick(() => {
          let playMode: MusicPlayMode;
          switch (this.musicModel.playMode) {
            case MusicPlayMode.ORDER:
              playMode = MusicPlayMode.RANDOM
              break;
            case MusicPlayMode.RANDOM:
              playMode = MusicPlayMode.SINGLE_CYCLE;
              break;
            case MusicPlayMode.SINGLE_CYCLE:
              playMode = MusicPlayMode.ORDER;
              break;
          }
          MediaService.getInstance().setPlayModel(playMode);
          this.playModeBuilder();
          promptAction.showToast({ message: this.playmodeTitle });
        })

        Row() {
          Text(`倒计时：${this.stopTimeStr}`)
            .fontSize(14)
            .fontWeight(400)
            .fontColor('#4D000000')
            .margin({ left: 16 })
            .textAlign(TextAlign.Start)
            .visibility(this.musicModel.stopTime > 0 ? Visibility.Visible : Visibility.None)
          SymbolGlyph($r('sys.symbol.alarm'))
            .fontSize(23)
            .symbolEffect(new ReplaceSymbolEffect(EffectScope.WHOLE), true)
            .fontColor([Color.Black])
            .bindSheet($$this.isShowSheet, this.TimedControlSheet(), {
              height: '45%',
              dragBar: false,
              showClose: false,
              maskColor: '#10000000',
            })
            .margin({ left: 16 })
            .onClick(() => {
              this.isShowSheet = !this.isShowSheet;
            })

          SymbolGlyph($r('sys.symbol.trash'))
            .fontSize(23)
            .symbolEffect(new ReplaceSymbolEffect(EffectScope.WHOLE), true)
            .fontColor([Color.Black])
            .margin({ left: 16 })
            .onClick(() => {
              // 弹框确认是否删除
              promptAction.showDialog({
                title: '提示',
                message: '确定要删除全部吗？',
                buttons: [
                  {
                    text: '取消',
                    color: '#000'
                  },
                  {
                    text: '确定',
                    color: '#000'
                  }
                ]

              }).then((data) => {
                if (data.index === 1) {
                  MediaService.getInstance().clearPlayList()
                }
              })
            })
        }
      }
      .justifyContent(FlexAlign.SpaceBetween)
      .padding({
        left: 16,
        right: 16,
        top: 12,
        bottom: 12
      })
      .width('100%')

      List() {
        ForEach(this.musicModel.songList, (item: SongItem, index: number) => {
          ListItem() {
            SongListItem({
              item: item,
              index: index
            })
          }
        }, (item: SongItem) => item.id)
      }
      .width('100%')
      .cachedCount(3)
      .padding({
        bottom: this.naviIndicatorHeight
      })
      .divider({
        strokeWidth: 1,
        color: '#E8E8E8',
        startMargin: 16,
        endMargin: 16
      })
      .scrollBar(BarState.Off)
    }
    .width('100%')
    .height('100%')

  }

  @Builder
  TimedControlSheet() {
    Column() {
      TimeTextPicker({
        textList: this.textList,
        title: '定时关闭',
        selected: this.select,
        confirm: (value: number) => {
          this.select = value;
          this.isShowSheet = false;

          if (value === 0) {
            // 选择"不启用"时清除定时器
            this.musicModel.stopTime = 0;
            this.stopTimeStr = '';
            clearInterval(this.intervalTimer);
            MediaService.getInstance().setStopTime(0);
          } else {
            this.futureTimeMs = MediaTools.getFutureTimeMs(0, this.getStopTime());
            this.musicModel.stopTime = this.futureTimeMs;
            this.stopTimeStr = MediaTools.getRemainingTimeMMSS(this.futureTimeMs);
            this.initStopTime();
            MediaService.getInstance().setStopTime(this.futureTimeMs);
          }
        },
        cancel: () => {
          this.isShowSheet = false
        }
      })
    }
    .padding({ bottom: this.naviIndicatorHeight })
  }
}