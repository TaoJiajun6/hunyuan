import { MusicPlayMode } from './MusicData';
import { SongItem } from './SongItem';


@ObservedV2
export class MusicModel {
  @Trace windowsMode: number = 1
  @Trace isVip: boolean = false;
  @Trace isLogin: boolean = false;
  @Trace isPlay: boolean = false; //是否播放
  @Trace songList: SongItem[] = [] // 播放歌曲列表
  @Trace currentSong: SongItem | undefined = undefined; //当前播放歌曲
  @Trace totalTime: string = ''; // 总时长
  @Trace progressMax: number = 0; // 进度条最大值
  @Trace progress: number = 0; // 进度
  @Trace selectIndex: number = 0; // 选中歌曲索引
  @Trace currentTime: string = '00:00'; // 当前播放时长
  @Trace playMode: MusicPlayMode = MusicPlayMode.ORDER; // 播放模式
  // 收藏列表
  @Trace collectList: SongItem[] = [];
  // 私有静态实例变量
  private static instance: MusicModel | null = null;
  //定时停止播放时间点
  @Trace stopTime: number = 0;
  // 全局播放页开关
  @Trace isShowPlay: boolean = false;
  @Trace themeColor: string = '#FF1949'
  // 青少年模式
  @Trace teenagersSwitch: boolean = false;
  // 开始登录时间
  @Trace startLoginTime: number = 0
  // 下载品质
  @Trace qualitySwitch: number = 0;
  // 通过map 方式记录所有歌曲被收藏量
  @Trace collectMap: Map<string, number> = new Map();
  // 通过map 方式记录所有歌曲被加入歌单 数量
  @Trace gedanMap: Map<string, number> = new Map();
  // 通过map 方式记录所有歌曲被下载量
  @Trace downloadMap: Map<string, number> = new Map();
  // 通过map 方式记录所有歌曲被分享 数量
  @Trace shareMap: Map<string, number> = new Map();
  // 是否切换歌曲
  @Trace updateSongInfo: boolean = false;

  @Monitor('currentSong')
  toggleSongs() {
    if (this.currentSong) {
      this.updateToggle()
    }
  }

  /**
   * 获取单例实例
   */
  public static getInstance(): MusicModel {
    if (!MusicModel.instance) {
      MusicModel.instance = new MusicModel();
    }
    return MusicModel.instance;
  }

  /**
   * 设置歌曲列表
   */
  public setSongList(value: SongItem[]) {
    this.songList = value
  }

  /**
   * 设置当前播放歌曲
   */
  public setCurrentSong(value: SongItem | undefined) {
    if (value) {
      this.currentSong = value
    }
  }

  // 获取歌曲列表
  public getSongList(): SongItem[] {
    return this.songList
  }

  // 加入收藏列表
  public addCollect(value: SongItem) {
    this.collectList.push(value)

    if (!this.collectMap.get(value?.id ?? '')) {
      this.collectMap.set(value?.id ?? '', value?.collectedCount ?? 0)
    }
    let collectedCount = this.collectMap.get(value?.id ?? '') ?? 0
    collectedCount++

    if (this.currentSong?.id === (value.id + '')) {
      value.isCollected = true
      this.currentSong = value
      this.currentSong.collectedCount = collectedCount
    }
    this.collectMap.set(this.currentSong?.id ?? '', collectedCount)
    // 更新播放列表中该歌曲收藏状态
    this.updateCollectStatus(value)
  }

  // 移除收藏列表
  public removeCollect(value: SongItem) {
    // 从收藏列表中移除该歌曲
    this.collectList = this.collectList.filter((item) => item.id !== value.id)

    if (!this.collectMap.get(value?.id ?? '')) {
      this.collectMap.set(value?.id ?? '', value?.collectedCount ?? 0)
    }
    let collectedCount = this.collectMap.get(value?.id ?? '') ?? 0
    collectedCount--

    if (this.currentSong?.id === (value.id + '')) {
      value.isCollected = false
      this.currentSong = value
      this.currentSong.collectedCount = collectedCount
    }
    this.collectMap.set(this.currentSong?.id ?? '', collectedCount)
    this.updateCollectStatus(value)
  }

  // 获取收藏列表
  public getCollectList(): SongItem[] {
    if (!this.collectList) {
      this.collectList = []
    }
    return this.collectList
  }

  // 添加歌单刷新数量
  public upataGedanNum(value: object, type: string) {
    let songItem = value as SongItem
    // 判断songItem是否为当前播放歌曲，如果是的是用当前播放歌曲替换
    if (this.currentSong?.id === songItem.id) {
      songItem = this.currentSong
    }
    let playlistCount = getMusicModel().gedanMap.get(songItem.id) as number;
    if (!playlistCount) {
      playlistCount = songItem.playlistCount
    }
    if (type === 'add') {
      playlistCount++
    } else {
      playlistCount--
    }

    getMusicModel().gedanMap.set(songItem.id, playlistCount)
    // 如何被加入的歌曲是当前播放歌曲
    if (this.currentSong?.id === songItem.id) {
      // this.currentSong.playlistCount = playlistCount
      songItem.playlistCount = playlistCount
      this.currentSong = songItem
    }
    this.updateToggle()
  }

  // 更新播放列表中歌曲收藏状态
  public updateCollectStatus(value: SongItem) {
    this.songList.forEach((item) => {
      if (item.id === value.id) {
        item.isCollected = value.isCollected
      }
    })
  }

  // 根据歌曲id从播放列表中移除
  public removeSongById(id: string) {
    this.songList = this.songList.filter((item) => item.id !== id)
  }

  // 清空播放列表
  public clearSongList() {
    this.songList = []
    this.currentSong = undefined
    this.selectIndex = -1
    this.progress = 0
    this.currentTime = '00:00'
    this.totalTime = '00:00'
    this.progressMax = 0
    this.isPlay = false
  }

  // 向播放列表表头增加一条歌曲
  public unshiftSong(value: SongItem) {
    this.songList.unshift(value)
  }

  /**
   * 判断歌单是为喜欢的歌曲
   */
  public isLikeSong(value: string): boolean {
    return this.collectList.some((item) => item.id === value);
  }

  /**
   * 更新歌曲下载数量
   */
  public updateDownloadNum(value: object) {
    let songData = value as SongItem
    if (!this.downloadMap.get(songData?.id ?? '')) {
      this.downloadMap.set(songData?.id ?? '', songData?.downloadCount ?? 0)
    }
    let downloadCount = this.downloadMap.get(songData?.id ?? '') ?? 0
    downloadCount++
    this.downloadMap.set(songData?.id ?? '', downloadCount)
    if (this.currentSong?.id === (songData.id + '')) {
      songData.downloadCount = downloadCount
      this.currentSong = songData
      this.updateToggle()
    }
  }

  /**
   * 更新歌曲分享数量
   */
  public updateShareNum(value: object) {
    let songData = value as SongItem
    if (!this.shareMap.get(songData?.id ?? '')) {
      this.shareMap.set(songData?.id ?? '', songData?.shareCount ?? 0)
    }
    let shareCount = this.shareMap.get(songData?.id ?? '') ?? 0
    shareCount++
    this.shareMap.set(songData?.id ?? '', shareCount)
    if (this.currentSong?.id === (songData.id + '')) {
      songData.shareCount = shareCount
      this.currentSong = songData
      this.updateToggle()
    }
  }

  //更新randomnum值
  public updateToggle() {
    this.updateSongInfo = !this.updateSongInfo
  }
}

export function getMusicModel(): MusicModel {
  return MusicModel.getInstance();
}
