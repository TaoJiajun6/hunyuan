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
import { MediaService } from '../utils/MediaService';
import { getMusicModel, MusicModel } from '../viewmodel/MusicModel';
import { promptAction } from '@kit.ArkUI';
import { PlayList } from './PlayList';
import { MusicPlayMode } from '../viewmodel/MusicData';
import { Share } from 'module_share';
import { singleClick } from '../utils/AntiShakeUtil';
import { FormatCountUtil } from '../utils/FormatCountUtil';
import { DownloadFileUtil } from '../utils/DownloadFileUtil';
import { common } from '@kit.AbilityKit';

/**
 * 播放器控制区域
 */
@ComponentV2
export struct PlayerControlArea {
  @Local musicModel: MusicModel = getMusicModel();
  @Local isShowSheet: boolean = false; //是否展示播放列表
  @Local playmodeImg: Resource = $r('sys.symbol.repeat');
  @Local isCollected: boolean = false;
  //收藏数量
  @Local collectedCount: number = this.musicModel.currentSong?.collectedCount ?? 0;
  //下载次数
  @Local downloadCount: number = 2;
  // 分享次数
  @Local shareCount: number = 5;
  // 歌单数量
  @Local playlistCount: number = 0;

  aboutToAppear(): void {
    this.playModeBuilder()
    this.changeSong()
  }

  // 监听当前播放歌曲
  @Monitor('musicModel.currentSong.id, musicModel.updateSongInfo')
  changeSong() {
    this.isCollected = this.musicModel.currentSong?.isCollected ?? false;
    const currentSongId = this.musicModel.currentSong?.id ?? '';
    // 歌单数量
    const playlistCount = this.musicModel.gedanMap.get(currentSongId) ?? 0;
    if (playlistCount) {
      this.musicModel.currentSong!.playlistCount = playlistCount;
    }
    this.playlistCount = this.musicModel.currentSong?.playlistCount ?? 0;

    // 分享数量
    const shareCount = this.musicModel.shareMap.get(currentSongId) ?? 0;
    if (shareCount) {
      this.musicModel.currentSong!.shareCount = shareCount;
    }
    this.shareCount = this.musicModel.currentSong?.shareCount ?? 0;

    // 下载数量
    const downloadCount = this.musicModel.downloadMap.get(currentSongId) ?? 0;
    if (downloadCount) {
      this.musicModel.currentSong!.downloadCount = downloadCount;
    }
    this.downloadCount = this.musicModel.currentSong?.downloadCount ?? 0;
  }

  // 监听当前播放歌曲收藏状态
  @Monitor('musicModel.currentSong.isCollected')
  changeCollected() {
    this.isCollected = this.musicModel.currentSong?.isCollected ?? false;
  }

  // 监听播放模式
  @Monitor('musicModel.playMode')
  playModeBuilder() {
    switch (this.musicModel.playMode) {
      case MusicPlayMode.ORDER:
        this.playmodeImg = $r('sys.symbol.repeat');
        break;
      case MusicPlayMode.RANDOM:
        this.playmodeImg = $r('sys.symbol.shuffle');
        break;
      case MusicPlayMode.SINGLE_CYCLE:
        this.playmodeImg = $r('sys.symbol.repeat_1');
        break;
    }
  }

  // 收藏
  async collected() {
    if (!this.musicModel.currentSong) {
      return
    }

    if (this.isCollected) {
      this.musicModel.currentSong.isCollected = false;
      MediaService.getInstance().unCollect(this.musicModel.currentSong?.id);
      this.isCollected = false;
      promptAction.showToast({ message: '已取消我喜欢' });
    } else {
      this.musicModel.currentSong.isCollected = true;
      MediaService.getInstance().collect(this.musicModel.currentSong?.id ?? '');
      this.isCollected = true;
      //提示收藏成功
      promptAction.showToast({ message: '已添加到我喜欢' });
    }
  }

  // 播放模式
  playMode() {
    let playMode: MusicPlayMode;
    let msg: string = ''
    switch (this.musicModel.playMode) {
      case MusicPlayMode.ORDER:
        playMode = MusicPlayMode.RANDOM
        msg = '随机播放'
        break;
      case MusicPlayMode.RANDOM:
        playMode = MusicPlayMode.SINGLE_CYCLE;
        msg = '单曲循环'
        break;
      case MusicPlayMode.SINGLE_CYCLE:
        playMode = MusicPlayMode.ORDER;
        msg = '列表循环'
        break;
    }
    MediaService.getInstance().setPlayModel(playMode);
    promptAction.showToast({ message: msg });
  }

  public getPic(value: string | Resource): Resource | string {
    if (value === '') {
      return ''
    }
    if (typeof value === 'string' && value.startsWith('http')) {
      return value
    }
    return getContext().resourceManager.getMediaBase64ByNameSync(value as string)
  }

  build() {
    Column() {
      Row() {
        //收藏
        this.collectedBuilder()

        // 加歌单
        this.playlistBuilder()

        // 下载
        this.downloadBuilder()

        // 分享
        this.shareBuilder()
      }
      .width('100%')
      .justifyContent(FlexAlign.SpaceBetween)
      .visibility(this.musicModel.currentSong?.isLocal ? Visibility.Hidden : Visibility.Visible)

      // 进度条
      Column() {
        Slider({
          min: 0,
          max: this.musicModel.progressMax,
          step: 1,
          value: this.musicModel.progress
        })
          .blockColor($r('app.color.slider_block'))
          .selectedColor($r('app.color.slider_select'))
          .trackColor($r('app.color.slider_track'))
          .blockSize({
            width: $r('app.float.slider_block'),
            height: $r('app.float.slider_block')
          })
          .onChange((value: number, mode: SliderChangeMode) => {
            if (mode === SliderChangeMode.End || mode === SliderChangeMode.Begin) {
              MediaService.getInstance().seek(value);
            }
          })
          .height($r('app.float.slider_height'))
          .margin({
            left: -4,
            right: -4
          })

        Row() {
          Text(this.musicModel.currentTime)
            .fontColor($r('app.color.play_text_color'))
            .fontSize($r('app.float.singer_title_sm'))
            .lineHeight('14vp')
          Text(this.musicModel.totalTime)
            .fontColor($r('app.color.play_text_color'))
            .fontSize($r('app.float.singer_title_sm'))
            .lineHeight('14vp')
        }
        .width('100%')
        .justifyContent(FlexAlign.SpaceBetween)
      }
      .hitTestBehavior(HitTestMode.None)
      .margin({
        top: $r('app.float.slider_margin_top'),
        bottom: 16
      })

      // 播放控制
      Row({ space: 18 }) {
        // 播放模式
        SymbolGlyph(this.playmodeImg)
          .fontSize(28)
          .symbolEffect(new ReplaceSymbolEffect(EffectScope.WHOLE), true)
          .fontColor([$r('app.color.slider_select')])
          .onClick(singleClick(() => {
            this.playMode()
          }, 1000))

        // 上一曲
        Image($r('app.media.ic_public_forward'))
          .controlImageBuilder()
          .width(32)
          .onClick(singleClick(() => {
            MediaService.getInstance().playPrevious();
          }, 1000))

        // 播放
        Image(this.musicModel.isPlay ? $r('app.media.ic_public_pause') : $r('app.media.ic_public_play'))
          .controlImageBuilder()
          .width(72)
          .onClick(singleClick(() => {
            MediaService.getInstance().playAndPause();
          }, 1000))

        // 下一曲
        Image($r('app.media.ic_public_next'))
          .controlImageBuilder()
          .width(32)
          .onClick(singleClick(() => {
            MediaService.getInstance().playNext();
          }, 1000))

        // 播放列表
        Image($r('app.media.ic_music_list'))// 当前播放列表入口
          .fillColor($r('app.color.slider_select'))
          .controlImageBuilder()
          .width(28)
          .bindSheet($$this.isShowSheet, this.playListSheet(), {
            height: '65%',
            dragBar: true,
            showClose: true,
            title: { title: $r('app.string.current_play_list', this.musicModel.songList.length) }
          })
          .onClick(() => {
            this.isShowSheet = !this.isShowSheet;
          })
      }
      .width('100%')
      .justifyContent(FlexAlign.SpaceBetween)
      .padding({
        left: $r('app.float.control_padding'),
        right: $r('app.float.control_padding')
      })
    }
  }

  @Builder
  shareCommentBuilder() {
    Column({ space: 5 }) {
      SymbolGlyph($r('sys.symbol.share'))
        .fontSize(28)
        .symbolEffect(new ReplaceSymbolEffect(EffectScope.WHOLE), true)
        .fontColor([Color.White])
      Text(FormatCountUtil.formatToK(this.shareCount))
        .fontSize(10).fontColor(Color.White)
    }
  }

  @Builder
  shareBuilder() {
    Column({ space: 5 }) {
      Share({
        qrCodeInfo: {
          id: this.musicModel.currentSong?.id ?? '',
          type: 2,
          articleFrom: this.musicModel.currentSong?.singer ?? '',
          title: this.musicModel.currentSong?.title ?? '',
          createTime: '2025-8-4 10:26',
          isVideo: false,
          coverUrl: this.getPic(this.musicModel.currentSong?.label ?? '') as string,
        },
        onShareResult: () => {
          if (this.musicModel.currentSong) {
            this.musicModel.updateShareNum(this.musicModel.currentSong)
          }
          promptAction.showToast({ message: '分享成功' });
        },
      })
      Text(FormatCountUtil.formatToK(this.shareCount))
        .fontSize(10).fontColor(Color.White)
    }
  }

  @Builder
  collectedBuilder() {
    Column({ space: 5 }) {
      SymbolGlyph(this.isCollected ? $r('sys.symbol.heart_fill') : $r('sys.symbol.heart'))
        .fontSize(28)
        .symbolEffect(new ReplaceSymbolEffect(EffectScope.WHOLE), true)
        .fontColor([Color.White])
      Text(FormatCountUtil.formatToK(this.musicModel.currentSong?.collectedCount ?? 0))
        .fontSize(10).fontColor(Color.White)
    }
    .onClick(() => {
      //判断是否登录
      if (!this.musicModel.isLogin) {
        MediaService.getInstance().openLogin()
        return
      }
      this.collected()
    })
  }

  @Builder
  playlistBuilder() {
    Column({ space: 5 }) {
      SymbolGlyph($r('sys.symbol.plus_square'))
        .fontSize(28)
        .symbolEffect(new ReplaceSymbolEffect(EffectScope.WHOLE), true)
        .fontColor([Color.White])
      Text(FormatCountUtil.formatToK(this.playlistCount ?? 0))
        .fontSize(10).fontColor(Color.White)
    }
    .onClick(() => {
      if (!this.musicModel.isLogin) {
        MediaService.getInstance().openLogin()
        return
      }
      MediaService.getInstance().addPalyList(this.musicModel.currentSong?.id ?? '')
    })
  }

  @Builder
  downloadBuilder() {
    Column({ space: 5 }) {
      Image($r('app.media.ic_sequence'))
        .controlImageBuilder()
        .width(28)
      Text(FormatCountUtil.formatToK(this.downloadCount))
        .fontSize(10).fontColor(Color.White)
    }
    .onClick(() => {
      if (!this.musicModel.isLogin) {
        MediaService.getInstance().openLogin()
        return
      }
      if (!this.musicModel.isVip) {
        promptAction.showToast({ message: '请先开通会员' })
        return
      }

      //根据下载品质获取下载地址
      let downUrl: string = ''
      switch (this.musicModel.qualitySwitch) {
        case 1:
          downUrl = this.musicModel.currentSong?.srcMedium ?? '';
          break;
        case 2:
          downUrl = this.musicModel.currentSong?.srcHigh ?? '';
          break;
        case 3:
          downUrl = this.musicModel.currentSong?.srcLossless ?? '';
          break;
        default:
          downUrl = this.musicModel.currentSong?.src ?? '';
          break;
      }
      if (downUrl === '') {
        downUrl = this.musicModel.currentSong?.src ?? '';
      }
      if (!downUrl.startsWith('http')) {
        promptAction.showToast({ message: '不是在线歌曲不能下载' })
        return
      }

      DownloadFileUtil.isFileExist(downUrl, getContext(this) as common.UIAbilityContext).then((exist) => {
        if (exist) {
          promptAction.showToast({ message: '本地已存在该歌曲' })
          return
        } else {
          promptAction.showToast({ message: '下载歌曲' })
          MediaService.getInstance().downloadSong(downUrl)
          this.downloadCount++
          if (this.musicModel.currentSong) {
            this.musicModel.updateDownloadNum(this.musicModel.currentSong)
          }
        }
      })
    })
  }

  @Builder
  playListSheet() {
    PlayList()
      .width('100%')
      .height('100%')
  }
}

@Extend(Image)
function controlImageBuilder() {
  .aspectRatio(1)
  .opacity(0.86)
  .objectFit(ImageFit.Contain)
}
