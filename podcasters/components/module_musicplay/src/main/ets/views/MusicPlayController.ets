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
    // 卡片样式的播放器
    Row() {
      if (!this.musicModel.currentSong) {
        this.NoSong()
      } else {
        // 卡片内容
        Row() {
          // 左侧：缩略图
          this.ThumbnailBuilder()

          // 中间：歌曲信息
          Column() {
            this.SongInfoBuild()
          }
          .layoutWeight(1)
          .alignItems(HorizontalAlign.Start)
          .justifyContent(FlexAlign.Center)

          // 右侧：控制按钮
          Row() {
            // 播放/暂停按钮
            this.PlayPauseButton()
            
            // 播放列表按钮
            this.PlayListButton()
          }
          .alignItems(VerticalAlign.Center)
        }
        .width('100%')
      }
    }
    .width('100%')
    .height(55)
    .linearGradient({
      angle: 90,
      colors: [
        ['#ffb3e0', 0.0],
        ['#c085f5', 0.5],
        ['#a0e5ff', 1.0]
      ]
    })
    .borderRadius(14)
    .shadow({
      radius: 14,
      color: '#1F000000',
      offsetX: 0,
      offsetY: 20
    })
    .bindContentCover($$this.musicModel.isShowPlay, this.MusicPlayBuilder(), {
      transition: TransitionEffect.translate({ y: this.windowHeight })
        .animation({
          duration: 300,
          curve: Curve.Smooth
        })
    })
    .padding({
      left: 10,
      right: 10,
      top: 8,
      bottom: 8
    })
  }

  /**
   * 无播放歌曲
   */
  @Builder
  NoSong() {
    Row() {
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
        .fontColor('#88000000')
    }
    .layoutWeight(1)
    .alignItems(VerticalAlign.Center)
    .justifyContent(FlexAlign.Start)
    .padding(12)
  }

  /**
   * 缩略图构建器
   */
  @Builder
  ThumbnailBuilder() {
    Stack({ alignContent: Alignment.BottomStart }) {
      // 圆形唱片作为缩略图
      RotatingCover()
      
      // 标签（本地/云存储）- 位于左下角
      if (this.musicModel.currentSong?.isLocal) {
        Row() {
          Text('本地')
            .fontSize(10)
            .fontColor(Color.White)
            .fontWeight(FontWeight.Medium)
        }
        .padding({ left: 6, right: 6, top: 2, bottom: 2 })
        .borderRadius(4)
        .backgroundColor('#FF1949')
        .margin({ left: 2, bottom: 2 })
      } else {
        Row() {
          Text('云存储音频')
            .fontSize(10)
            .fontColor(Color.White)
            .fontWeight(FontWeight.Medium)
        }
        .padding({ left: 6, right: 6, top: 2, bottom: 2 })
        .borderRadius(4)
        .backgroundColor('#FF1949')
        .margin({ left: 2, bottom: 2 })
      }
    }
    .width(56)
    .height(56)
    .onClick(() => {
      // 点击缩略图打开播放页面
      if (this.musicModel.songList.length <= 0) {
        promptAction.showToast({ message: '请选择歌曲播放' })
        return
      }
      this.musicModel.isShowPlay = true;
    })
  }

  /**
   * 歌单信息
   */
  @Builder
  SongInfoBuild() {
    Column({ space: 4 }) {
      // 标题
      Text(this.musicModel.currentSong?.title || '未知播客')// 歌名
        .fontSize(14)
        .fontWeight(FontWeight.Bold)
        .fontColor('#000000')
        .maxLines(1)
        .textOverflow({ overflow: TextOverflow.Ellipsis })
        .width('100%')
      
      // 作者和标签
      Row({ space: 6 }) {
        if (this.musicModel.currentSong?.singer) {
          Text(this.musicModel.currentSong.singer)//作者
            .fontSize(12)
            .fontColor('#000000')
            .maxLines(1)
            .textOverflow({ overflow: TextOverflow.Ellipsis })
        }
        
        // 类型标签
        Image(this.getSongType())//VIP 标签
          .height(14)
          .width(20)
          .fillColor(this.themeColor)
          .visibility((!this.musicModel.currentSong?.isVip && !this.musicModel.currentSong?.isLocal) ?
          Visibility.None : Visibility.Visible)
      }
      .width('100%')
      .alignItems(VerticalAlign.Center)
    }
    .width('100%')
    .onClick(() => {
      // 点击信息区域打开播放页面
      if (this.musicModel.songList.length <= 0) {
        promptAction.showToast({ message: '请选择歌曲播放' })
        return
      }
      this.musicModel.isShowPlay = true;
    })
  }

  /**
   * 播放/暂停按钮
   */
  @Builder
  PlayPauseButton() {
    Button() {
      Image(this.musicModel.isPlay ? $r('app.media.ic_pause') : $r('app.media.ic_play'))// 播放|暂停
        .width(24)
        .height(24)
        .fillColor(Color.White)
    }
    .width(40)
    .height(40)
    .borderRadius(20)
    .backgroundColor(Color.Transparent)
    .onClick(singleClick(() => {
      MediaService.getInstance().playAndPause();
    }, 1000))
  }

  // 播放列表按钮
  @Builder
  PlayListButton() {
    Button() {
      Image($r('app.media.ic_music_list'))// 当前播放列表入口
        .width(20)
        .height(20)
        .fillColor(Color.White)
    }
    .width(40)
    .height(40)
    .borderRadius(20)
    .backgroundColor(Color.Transparent)
    .bindSheet($$this.isShowSheet, this.PlayListSheet(), {
      height: '68%',
      dragBar: true,
      showClose: true,
      title: { title: $r('app.string.current_play_list', this.musicModel.songList.length) }
    })
    .onClick(singleClick(() => {
      this.isShowSheet = !this.isShowSheet;
    }, 1000))
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