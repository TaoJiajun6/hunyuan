import { PlayerView } from '../components/PlayerView';
import { PlayList } from '../components/PlayList';
import { RotatingCover } from '../components/RotatingCover';
import { MediaService } from '../utils/MediaService';
import { getMusicModel, MusicModel } from '../viewmodel/MusicModel';
import { singleClick } from '../utils/AntiShakeUtil';
import { promptAction, window } from '@kit.ArkUI';

/**
 * 应用内播放条
 */
@ComponentV2
export struct MusicPlayController {
  // 是否默认皮肤
  @Param isDefaultTheme: boolean = true;
  // 主题色
  @Param themeColor?: string = '#FF1949'
  // 播放条背景色
  @Param playBarBgColor?: string = '#FFFFFF'
  // 标题颜色
  @Param titleFontColor?: string = '#88000000';
  // 歌手颜色
  @Param singerFontColor?: string = '#4D000000';
  // 屏幕高度
  @Local windowHeight: number = 0;
  // 音乐模型
  @Local musicModel: MusicModel = getMusicModel();
  // 播放条位移
  @Local translateY: number = 0;
  // 是否展示播放列表
  @Local isShowSheet: boolean = false;
  private panOption: PanGestureOptions = new PanGestureOptions({ direction: PanDirection.Vertical }); //垂直手势
  @Event onPlayerViewClose: () => void = () => {
  };

  aboutToAppear(): void {
    this.windowHeight = AppStorage.get('windowHeight') as number;
    this.playDefaultSong()
  }

  /**
   * 监听主题色
   */
  @Monitor('themeColor')
  onchangeThemeColor() {
    this.musicModel.themeColor = this.themeColor ?? '';
  }

  //播放默认歌曲
  playDefaultSong() {
    if (!this.musicModel.currentSong && this.musicModel.songList.length > 0) {
      this.musicModel.setCurrentSong(this.musicModel.songList[0]);
      MediaService.getInstance().addToSongList(this.musicModel.currentSong)
    }
  }

  /**
   * 获取当前歌曲类型
   * @returns
   */
  getSongType(): ResourceStr {
    // 判断是否位本地歌曲
    if (this.musicModel.currentSong?.isLocal) {
      return $r('app.media.ic_local')
    }
    if (this.musicModel.currentSong?.isVip) {
      return $r('app.media.ic_vip');
    }
    return '';
  }

  build() {
    Row() {
      if (!this.musicModel.currentSong) {
        this.NoSong()
      } else {
        // 左侧：当前歌曲信息
        this.SongInfoBuild()

        //中间：播放操作按钮
        this.PlayButton()
      }

      // 右侧：播放列表按钮
      this.PlayListButton()
    }
    .width('100%')
    .height(48)
    .justifyContent(FlexAlign.Center)
    .backgroundColor(this.isDefaultTheme ? $r('app.color.start_window_background') : this.playBarBgColor)
    .bindContentCover($$this.musicModel.isShowPlay, this.MusicPlayBuilder(), {
      transition: TransitionEffect.translate({ y: this.windowHeight })
        .animation({
          duration: 300,
          curve: Curve.Smooth
        })
    })
    .padding({
      left: 16,
      right: 16
    })
  }

  /**
   * 无播放歌曲
   */
  @Builder
  NoSong() {
    Row({ space: 16 }) {
      Row() {
        SymbolGlyph($r('sys.symbol.music_fill'))
          .fontSize(28)
          .symbolEffect(new ReplaceSymbolEffect(EffectScope.WHOLE), true)
          .fontColor(['#33000000'])
      }
      .height(38)
      .width(38)
      .borderRadius(50)
      .backgroundColor('#0D000000')
      .alignItems(VerticalAlign.Center)
      .justifyContent(FlexAlign.Center)

      Text('暂无播放')
        .fontSize(14)
        .fontWeight(500)
        .fontColor(this.titleFontColor)
    }
    .layoutWeight(1)
    .alignItems(VerticalAlign.Center)
    .justifyContent(FlexAlign.Start)
  }

  /**
   * 歌单信息
   */
  @Builder
  SongInfoBuild() {
    Row() {
      // 圆形唱片
      RotatingCover()
      Column() {
        Text(this.musicModel.currentSong?.title)// 歌名
          .fontSize(14)
          .fontWeight(500)
          .fontColor(this.titleFontColor)
        Row() {
          Image(this.getSongType())//VIP 标签
            .height(16)
            .width(25)
            .margin({ right: 4 })
            .fillColor(this.themeColor)
            .visibility((!this.musicModel.currentSong?.isVip && !this.musicModel.currentSong?.isLocal) ?
            Visibility.None : Visibility.Visible)
          Text(this.musicModel.currentSong?.singer)//作者
            .fontSize(10)
            .fontColor(this.singerFontColor)
        }
      }
      .alignItems(HorizontalAlign.Start)
    }
    .layoutWeight(1)
    .onClick(() => {
      // 播放列表为空提示
      if (this.musicModel.songList.length <= 0) {
        promptAction.showToast({ message: '请选择歌曲播放' })
        return
      }
      this.musicModel.isShowPlay = true;
    })
  }

  /**
   * 播放操作按钮
   */
  @Builder
  PlayButton() {
    Row() {
      Image($r('app.media.ic_previous'))// 上一首
        .height(24)
        .width(24)
        .margin({ right: 16 })
        .displayPriority(2)
        .fillColor(this.themeColor)
        .onClick(singleClick(() => {
          MediaService.getInstance().playPrevious();
        }, 1000))


      Image(this.musicModel.isPlay ? $r('app.media.ic_play') : $r('app.media.ic_pause'))// 播放|暂停
        .height(23)
        .width(23)
        .displayPriority(3)
        .borderRadius(50)
        .fillColor(this.themeColor)
        .onClick(singleClick(() => {
          MediaService.getInstance().playAndPause();
        }, 1000))

      Image($r('app.media.ic_next'))// 下一首
        .height(24)
        .width(24)
        .margin({
          right: 16,
          left: 16
        })
        .displayPriority(2)
        .fillColor(this.themeColor)
        .onClick(singleClick(() => {
          MediaService.getInstance().playNext();
        }, 1000))
    }
  }

  // 播放列表按钮
  @Builder
  PlayListButton() {
    Image($r('app.media.ic_music_list'))// 当前播放列表入口
      .height(24)
      .width(24)
      .displayPriority(1)
      .bindSheet($$this.isShowSheet, this.PlayListSheet(), {
        height: '68%',
        dragBar: true,
        showClose: true,
        title: { title: $r('app.string.current_play_list', this.musicModel.songList.length) }
      })
      .fillColor(this.themeColor)
      .onClick(singleClick(() => {
        this.isShowSheet = !this.isShowSheet;
      }))
  }

  /**
   * 播放列表
   */
  @Builder
  PlayListSheet() {
    PlayList()
      .width('100%')
  }

  /**
   * 播放页面
   */
  @Builder
  MusicPlayBuilder() {
    PlayerView()
      .height('100%')
      .width('100%')
      .onDisAppear(() => {
        this.translateY = 0;
      })
      .translate({ y: this.translateY })
      .gesture(
        PanGesture(this.panOption)
          .onActionUpdate((event?: GestureEvent) => {
            if (event) {
              this.translateY = event.offsetY;
              if (this.translateY < 0) {
                this.translateY = 0;
                return;
              }
            }
          })
          .onActionEnd(() => {
            if (this.translateY > this.windowHeight / 2) {
              this.musicModel.isShowPlay = false;
            } else {
              this.getUIContext().animateTo({
                duration: 300,
                curve: Curve.Smooth
              }, () => {
                this.translateY = 0;
              })
            }
          })
      )
  }
}