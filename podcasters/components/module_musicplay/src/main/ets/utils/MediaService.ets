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

import { media } from '@kit.MediaKit';
import { common, wantAgent } from '@kit.AbilityKit';
import { avSession } from '@kit.AVSessionKit';
import { BusinessError } from '@kit.BasicServicesKit';
import { SongItem } from '../viewmodel/SongItem';
import { Logger } from './Logger';
import { AudioPlayerState, MusicPlayMode } from '../viewmodel/MusicData';
import { MediaTools } from './MediaTools';
import { CollectAction, PlayActionType } from '../viewmodel/FormCardConstant';
import { BackgroundUtil } from './BackgroundUtil';
import SongItemBuilder from './SongItemBuilder';
import { getMusicModel, MusicModel } from '../viewmodel/MusicModel';
import { promptAction } from '@kit.ArkUI';
import { Constants } from '../constants/Constants';
import { audio } from '@kit.AudioKit';
import fs from '@ohos.file.fs';
import { cryptoFramework } from '@kit.CryptoArchitectureKit';
import { util } from '@kit.ArkTS';

const TAG = 'MediaService';

export class SongChangedData {
  isPlay: boolean = false;
  totalTime: string = '';
  progressMax: number = 0;
  selectIndex: number = 0;
  songItem: SongItem = new SongItem();
}

export enum AudioQuality {
  LOW = 'low', // 低音质
  MEDIUM = 'medium', // 中音质
  HIGH = 'high', // 高音质
  LOSSLESS = 'lossless' // 无损音质
}

export class MediaService {
  private static instance: MediaService;
  private context: common.UIAbilityContext = AppStorage.get('context') as common.UIAbilityContext;
  public avPlayer?: media.AVPlayer;
  private session?: avSession.AVSession;
  private songItemBuilder: SongItemBuilder = new SongItemBuilder(this.context);
  private state: AudioPlayerState = AudioPlayerState.IDLE;
  private isFirstLoadAsset: boolean = true;
  private isPrepared: boolean = false;
  private musicIndex: number = 0;
  private changedData: MusicModel = getMusicModel();
  private timerId: number | null = null;
  // 播放音质
  public currentQuality: AudioQuality = AudioQuality.MEDIUM;
  private songChangedBack?: Function;
  private timeUpdateCallBack?: Function;
  //声明收藏回调
  private collectCallBack?: Function;
  //声明播放mv回调
  private playMvCallBack?: Function;
  // 声明下载歌曲回调
  private downloadCallBack?: Function;
  //加入歌单回调
  private addPalyListCallBack?: Function;
  // 弹出登录回调
  private openLoginCallBack?: Function;
  // 判断下载歌曲在沙箱内是否存在回调
  private downloadSongExistCallBack: Function = (filePath: string): Promise<boolean> => {
    return new Promise((resolve) => {
      fs.access(filePath).then(() => {
        Logger.info(TAG, `filePath ${filePath} exists`);
        resolve(true);
      }).catch(() => {
        Logger.info(TAG, `filePath ${filePath} not exists`);
        resolve(false);
      });
    });
  };
  private avPlayerSeekDoneCall = (seekDoneTime: number) => {
    Logger.info(TAG, `avPlayerSeekDoneCall seek succeeded, seek time is ${seekDoneTime}`);
    this.setAVSessionPlayState({
      position: {
        elapsedTime: this.getCurrentTime(),
        updateTime: new Date().getTime()
      }
    });
  };
  private avPlayerErrorCall = (error: BusinessError) => {
    Logger.error(TAG, `avPlayerErrorCall error, code is ${error.code}, message is ${error.message}`);
    this.reset();
  };
  private avPlayerTimeUpdateCall = (updateTime: number) => {
    Logger.info(TAG, `avPlayerTimeUpdateCall updateTime is ${updateTime}`);
    this.changedData.progress = updateTime;
    this.changedData.currentTime = MediaTools.msToCountdownTime(updateTime);
    if (this.timeUpdateCallBack) {
      this.timeUpdateCallBack(updateTime, MediaTools.msToCountdownTime(updateTime));
    }
  };
  private avPlayerStateChangeCall = async (state: string) => {
    switch (state) {
      case 'idle':
        Logger.info(TAG, 'avPlayerStateChangeCall AVPlayer state idle called.');
        // 首次播放，设置源并准备
        this.state = AudioPlayerState.IDLE;
        this.isPrepared = false;
        this.loadAsset();
        break;
      case 'initialized':
        Logger.info(TAG, 'avPlayerStateChangeCall AVPlayer state initialized called.');
        this.state = AudioPlayerState.INITIALIZED;
        this.prepare();
        break;
      case 'prepared':
        Logger.info(TAG, 'avPlayerStateChangeCall AVPlayer state prepared called.');
        this.state = AudioPlayerState.PREPARED;
        this.isPrepared = true;
        if (!this.isFirstLoadAsset) {
          this.play();
          this.setAVMetadata();
        }
        Logger.info(TAG, 'avPlayerStateChangeCall AVPlayer prepared succeeded.');
        break;
      case 'playing':
        Logger.info(TAG, 'avPlayerStateChangeCall AVPlayer state playing called.');
        if (this.isFirstLoadAsset) {
          BackgroundUtil.startContinuousTask(this.context);
          this.isFirstLoadAsset = false;
        }
        this.state = AudioPlayerState.PLAY;
        this.setCallBackData(true);
        this.updateSessionPlayState(true);
        break;
      case 'paused':
        Logger.info(TAG, 'avPlayerStateChangeCall AVPlayer state paused called.');
        this.state = AudioPlayerState.PAUSE;
        this.setCallBackData(false);
        this.updateSessionPlayState(false);
        break;
      case 'completed':
        Logger.info(TAG, 'avPlayerStateChangeCall AVPlayer state completed called.');
        this.state = AudioPlayerState.COMPLETED;
        this.exportDownload()
        this.playCompleteAuto();
        break;
      case 'stopped':
        Logger.info(TAG, 'avPlayerStateChangeCall AVPlayer state stopped called.');
        this.state = AudioPlayerState.STOP;
        this.reset();
        break;
      case 'error':
        Logger.info(TAG, 'avPlayerStateChangeCall AVPlayer state error called.');
        this.state = AudioPlayerState.ERROR;
        break;
      case 'released':
        Logger.info(TAG, 'avPlayerStateChangeCall AVPlayer state released called.');
        this.state = AudioPlayerState.RELEASED;
        break;
      default:
        Logger.info(TAG, 'avPlayerStateChangeCall AVPlayer state unknown called.');
        this.state = AudioPlayerState.UNKNOWN;
        break;
    }
  };
  private avSessionPlayCall = () => {
    Logger.info(TAG, 'avSessionPlayCall on play , do play task');
    this.play();
  };
  private avSessionPauseCall = () => {
    Logger.info(TAG, 'avSessionPauseCall on pause , do pause task');
    this.pause();
  };
  private avSessionPlayNextCall = () => {
    Logger.info(TAG, 'avSessionPlayNextCall on playNext , do playNext task');
    this.playNext();
  };
  private avSessionPlayPreviousCall = () => {
    Logger.info(TAG, 'avSessionPlayPreviousCall on playPrevious , do playPrevious task');
    this.playPrevious();
  };
  private avSessionLoopModeCall: (loopMode: avSession.LoopMode) => void = (loopMode: avSession.LoopMode) => {
    Logger.info(TAG, 'on loopMode , do loopMode task');
    let playMode: MusicPlayMode = MusicPlayMode.ORDER;
    let loopModeNew: avSession.LoopMode = avSession.LoopMode.LOOP_MODE_LIST;
    switch (loopMode.valueOf()) {
      case avSession.LoopMode.LOOP_MODE_SINGLE: //单曲循环
        playMode = MusicPlayMode.ORDER //列表循环
        loopModeNew = avSession.LoopMode.LOOP_MODE_LIST;
        break;
      case avSession.LoopMode.LOOP_MODE_SHUFFLE: // 随机播放
        playMode = MusicPlayMode.SINGLE_CYCLE; //单曲循环
        loopModeNew = avSession.LoopMode.LOOP_MODE_SINGLE;
        break;
      case avSession.LoopMode.LOOP_MODE_LIST: //顺序播放
      case avSession.LoopMode.LOOP_MODE_SEQUENCE:
        playMode = MusicPlayMode.RANDOM; //随机播放
        loopModeNew = avSession.LoopMode.LOOP_MODE_SHUFFLE;
        break;
      default:
        playMode = MusicPlayMode.ORDER;
        break;
    }

    //将播放默认同步到avSession中
    this.setAVSessionPlayState({
      loopMode: loopModeNew,
    });
    this.changedData.playMode = playMode;
  }
  // 设置收藏状态
  private avSessionFavoriteState: (assetId: string) => void = (assetId: string) => {
    Logger.info(TAG, 'avSessionFavoriteState assetId.' + assetId);

    if (this.changedData.currentSong === null) {
      return;
    }

    //判断是否登录
    if (!this.changedData.isLogin) {
      return
    }

    if (this.changedData.currentSong?.isCollected) {
      this.unCollect(this.changedData.currentSong.id);
    } else {
      if (this.changedData && this.changedData.currentSong && this.changedData.currentSong.id) {
        this.collect(this.changedData.currentSong.id);
      }
    }
  }

  // 更新AVSession中isFavorite
  private updateSessionFavoriteState(isFavorite: boolean): void {
    this.setAVSessionPlayState({
      isFavorite: isFavorite,
    });
  }


  public setOnPlayStateCall(callBak: Function): void {
    this.songChangedBack = callBak;
  }

  public setTimeUpdateCall(callBak: Function): void {
    this.timeUpdateCallBack = callBak;
  }

  private setCallBackData(isPlay: boolean): void {
    this.changedData.currentSong = this.changedData.songList[this.musicIndex];
    this.changedData.isPlay = isPlay;
    this.changedData.selectIndex = this.musicIndex;
    this.changedData.totalTime = MediaTools.msToCountdownTime(this.getDuration());
    this.changedData.progressMax = this.getDuration();
    if (this.songChangedBack) {
      this.songChangedBack(this.changedData);
    }
  }

  public static getInstance(): MediaService {
    if (!MediaService.instance) {
      MediaService.instance = new MediaService();
    }
    return MediaService.instance;
  }

  public initAudioPlayer(songList: Array<SongItem>, currentSong: SongItem): void {
    Logger.info(TAG, 'initAudioPlayer');
    this.changedData.songList = songList;
    media.createAVPlayer().then(async avPlayer => {
      if (avPlayer) {
        this.avPlayer = avPlayer;
        this.loadAsset(currentSong);
        this.setAVPlayerCallback();
        this.createSession();
        this.manageAudioInputDevice();

        Logger.info(TAG, 'initAudioPlayer success');
      }
    }).catch((error: BusinessError) => {
      Logger.error(TAG, `initAudioPlayer error, code is ${error.code}, message is ${error.message}`);
    })
  }

  private setAVPlayerCallback(): void {
    if (this.avPlayer) {
      this.avPlayer.on('seekDone', this.avPlayerSeekDoneCall);
      this.avPlayer.on('error', this.avPlayerErrorCall);
      this.avPlayer.on('timeUpdate', this.avPlayerTimeUpdateCall);
      this.avPlayer.on('stateChange', this.avPlayerStateChangeCall)
    }
  }

  /**
   * 创建session
   */
  private async createSession(): Promise<void> {
    this.session = await avSession.createAVSession(this.context, 'SESSION_NAME', 'audio');
    this.session.activate();
    Logger.info(TAG, `session create done : sessionId : ${this.session.sessionId}`);
    this.setAVMetadata();
    let wantAgentInfo: wantAgent.WantAgentInfo = {
      wants: [
        {
          bundleName: this.context.abilityInfo.bundleName,
          abilityName: this.context.abilityInfo.name
        }
      ],
      actionType: wantAgent.OperationType.START_ABILITIES,
      requestCode: 0,
      wantAgentFlags: [wantAgent.WantAgentFlags.UPDATE_PRESENT_FLAG]
    }
    wantAgent.getWantAgent(wantAgentInfo).then((agent) => {
      this.session?.setLaunchAbility(agent);
    })
    this.setListenerForMesFromController();
  }

  private setListenerForMesFromController(): void {
    if (this.session) {
      this.session.on('play', this.avSessionPlayCall);
      this.session.on('pause', this.avSessionPauseCall);
      this.session.on('playNext', this.avSessionPlayNextCall);
      this.session.on('playPrevious', this.avSessionPlayPreviousCall);
      this.session.on('setLoopMode', this.avSessionLoopModeCall);
      this.session.on('toggleFavorite', this.avSessionFavoriteState);
    }
  }

  private unregisterSessionListener(): void {
    if (this.session) {
      this.session.off('play');
      this.session.off('pause');
      this.session.off('playNext');
      this.session.off('playPrevious');
      this.session.off('setLoopMode');
      this.session.off('toggleFavorite');
    }
  }

  private async setAVMetadata(): Promise<void> {
    try {
      //判断label是网络图还是资源图片
      let mediaImage =
        await MediaTools.getPixelMapBylabel(this.context, this.changedData.songList[this.musicIndex].label as Resource);
      Logger.info(TAG, 'getPixelMapFromResource success' + JSON.stringify(mediaImage));
      let metadata: avSession.AVMetadata = {
        assetId: this.changedData.songList[this.musicIndex].id,
        title: this.changedData.songList[this.musicIndex].title,
        artist: this.changedData.songList[this.musicIndex].singer,
        mediaImage: mediaImage,
        duration: this.getDuration()
      };
      this.session?.setAVMetadata(metadata).then(() => {
        Logger.info(TAG, 'SetAVMetadata successfully');
      }).catch((error: BusinessError) => {
        Logger.error(TAG, `SetAVMetadata BusinessError: code: ${error.code}, message: ${error.message}`);
      });
    } catch (error) {
      Logger.error(TAG, `SetAVMetadata err, code: ${JSON.stringify(error)}`);
    }
  }

  // 管理全局音频输入设备
  private manageAudioInputDevice() {
    let audioManager = audio.getAudioManager(); // 需要先创建AudioManager实例。
    let audioRoutingManager = audioManager.getRoutingManager();
    // 监听音频设备状态变化。
    audioRoutingManager.on('deviceChange', audio.DeviceFlag.INPUT_DEVICES_FLAG,
      (deviceChanged: audio.DeviceChangeAction) => {
        Logger.info('device change type : ' + deviceChanged.type); // 设备连接状态变化，0为连接，1为断开连接。
        Logger.info('device descriptor size : ' + deviceChanged.deviceDescriptors.length);
        Logger.info('device change descriptor : ' + deviceChanged.deviceDescriptors[0].deviceRole); // 设备角色。
        Logger.info('device change descriptor : ' + deviceChanged.deviceDescriptors[0].deviceType); // 设备类型。
        // 设备断开连接暂停播放
        if (deviceChanged.type === 1) {
          MediaService.getInstance().pause()
        }
      });
  }

  /**
   * 指定索引控制播放
   * @param musicIndex
   */
  public controlPlay(musicIndex: number): void {
    this.isFirstLoadAsset = false;
    this.playByIndex(musicIndex);
  }

  public setPlayModel(playMode: MusicPlayMode): void {
    this.changedData.playMode = playMode;
    Logger.info(TAG, 'setPlayModel mode: ' + this.changedData.playMode);
    let loopModeNew: avSession.LoopMode = avSession.LoopMode.LOOP_MODE_LIST;
    switch (playMode) {
      case MusicPlayMode.SINGLE_CYCLE: //单曲循环
        loopModeNew = avSession.LoopMode.LOOP_MODE_SINGLE;
        break;
      case MusicPlayMode.RANDOM: // 随机播放
        loopModeNew = avSession.LoopMode.LOOP_MODE_SHUFFLE;
        break;
      case MusicPlayMode.ORDER: //顺序播放
        loopModeNew = avSession.LoopMode.LOOP_MODE_LIST;
        break;
      default:
        loopModeNew = avSession.LoopMode.LOOP_MODE_LIST;
        break;
    }
    this.setAVSessionPlayState({
      loopMode: loopModeNew,
    });
  }

  public seek(ms: number): void {
    if (this.isPrepared && this.state !== AudioPlayerState.ERROR && this.avPlayer) {
      let seekMode = this.getCurrentTime() < ms ? 0 : 1;
      let realTime = (ms <= 0 ? 0 : (ms >= this.getDuration() ? this.getDuration() : ms));
      this.avPlayer.seek(realTime, seekMode);
    }
  }

  public play(): void {
    if (!this.isPrepared) {
      this.prepare();
    } else {
      if (!MediaService.getInstance().checkPlayTime()) {
        promptAction.showToast({ message: '未成年模式，当天限播10分钟。' })
        MediaService.getInstance().pause()
        MediaService.getInstance().changedData.isPlay = false
        return
      }
      this.avPlayer?.play().then(() => {
        Logger.info(TAG, 'AVPlayer play successfully');
      }).catch((error: BusinessError) => {
        Logger.error(TAG, `AVPlayer play failed, code is ${error.code}, message is ${error.message}`);
      })
    }
  }

  public pause(): void {
    if (this.isPrepared && this.state === AudioPlayerState.PLAY && this.avPlayer) {
      this.avPlayer.pause().then(() => {
        Logger.info(TAG, 'AVPlayer pause successfully');
      }).catch((error: BusinessError) => {
        Logger.error(TAG, `AVPlayer pause failed, code is ${error.code}, message is ${error.message}`);
      });
    }
  }

  public playNext(): void {
    this.isFirstLoadAsset = false;
    Logger.info(TAG, `playNext Index: ${this.musicIndex}, songList length: ${this.changedData.songList.length}`);
    switch (this.changedData.playMode) {
      case MusicPlayMode.RANDOM: //随机播放
        this.playRandom();
        break;
      case MusicPlayMode.ORDER: //顺序播放
      case MusicPlayMode.SINGLE_CYCLE: //单曲循环
        if (this.musicIndex === this.changedData.songList.length - 1) {
          this.playByIndex(0);
        } else {
          this.playByIndex(this.musicIndex + 1);
        }
        break;
      default:
        break;
    }
  }

  public playPrevious(): void {
    this.isFirstLoadAsset = false;
    Logger.info(TAG, `playPrevious Index: ${this.musicIndex}, songList length: ${this.changedData.songList.length}`);
    switch (this.changedData.playMode) {
      case MusicPlayMode.RANDOM:
        this.playRandom();
        break;
      case MusicPlayMode.ORDER:
      case MusicPlayMode.SINGLE_CYCLE:
        if (this.musicIndex === 0) {
          this.playByIndex(this.changedData.songList.length - 1);
        } else {
          this.playByIndex(this.musicIndex - 1);
        }
        break;
      default:
        break;
    }
  }

  public playByAction(action: PlayActionType): void {
    switch (action) {
      case PlayActionType.PAUSE:
        this.pause();
        break;
      case PlayActionType.PLAY:
        this.isFirstLoadAsset = false;
        this.play();
        break;
      case PlayActionType.PREVIOUS:
        this.playPrevious();
        break;
      case PlayActionType.NEXT:
        this.playNext();
        break;
      default:
        break;
    }
  }

  public async playByIndex(musicIndex: number): Promise<void> {
    if (musicIndex >= this.changedData.songList.length) {
      Logger.error(TAG,
        `playByIndex error, index is ${musicIndex} out of songList length ${this.changedData.songList.length}`);
      return;
    }
    this.updateMusicIndex(musicIndex);
    await this.stop();
  }

  public async release(): Promise<void> {
    if (this.avPlayer && this.session && this.context) {
      this.avPlayer.release();
      this.songItemBuilder.release();
      BackgroundUtil.stopContinuousTask(this.context);
      this.unregisterSessionListener();
      this.session.destroy();
      this.timerId = null;
    }
  }

  private async loadAsset(currentSong?: SongItem): Promise<void> {
    if (currentSong) {
      this.musicIndex = Number.parseInt(currentSong.id) - 1;
      Logger.info(`loadAsset musicIndex: ${this.musicIndex}`);
    }

    // 播放歌曲
    currentSong = this.changedData.songList[this.musicIndex];

    if (currentSong.src.startsWith('http')) {
      // 根据歌曲地址判断是否网络歌曲
      this.loadAssetHttp(currentSong)
    } else if (currentSong.src.startsWith('/')) {
      // 沙箱文件路径判断 - 以 '/' 开头的绝对路径视为沙箱文件
      this.loadAssetSandbox(currentSong);
    } else {
      await this.songItemBuilder.build(this.changedData.songList[this.musicIndex]);
      let url = this.songItemBuilder.getRealUrl();
      if (url) {
        if (this.avPlayer) {
          // 加载Rawfile歌曲
          let avFileDescriptor: media.AVFileDescriptor = { fd: url.fd, offset: url.offset, length: url.length };
          this.avPlayer.fdSrc = avFileDescriptor;
          Logger.info(TAG, `loadAsset avPlayer url: ${this.avPlayer.fdSrc}}`);
        }
      } else {
        // 沙箱歌曲处理
        this.loadAssetSandbox(currentSong)
      }
    }
  }


  /**
   * 加载网络歌曲
   * @param currentSong
   */
  loadAssetHttp(currentSong: SongItem) {
    // 根据音质获取对应 URL
    let qualityUrl = this.getUrlByQuality(currentSong)
    qualityUrl = qualityUrl === '' ? currentSong.src : qualityUrl;
    // 网络歌曲处理
    if (this.avPlayer) {
      this.avPlayer.url = qualityUrl;
    }
  }

  //加载沙箱歌曲
  async loadAssetSandbox(currentSong: SongItem) {
    let file: fs.File | null = null;
    try {
      // 本地歌曲处理
      let fdPath = 'fd://';
      file = await fs.openSync(currentSong.src);
      fdPath = fdPath + '' + file.fd;
      if (this.avPlayer) {
        this.avPlayer.url = fdPath;
      }
    } catch (error) {
      let err: BusinessError = error as BusinessError;
      Logger.error(TAG, 'loadAsset', ` err: ${err.code}, ${err.message}`);
    } finally {
      if (file) {
        setTimeout(() => {
          fs.closeSync(file);
        }, 300)
      }
    }
  }

  public updateSessionPlayState(isPlay: boolean): void {
    Logger.info(TAG, `updateIsPlay isPlay: ${isPlay}`);
    this.setAVSessionPlayState({
      state: isPlay ? avSession.PlaybackState.PLAYBACK_STATE_PLAY : avSession.PlaybackState.PLAYBACK_STATE_PAUSE,
      position: {
        elapsedTime: this.getCurrentTime(),
        updateTime: new Date().getTime(),
      },
    });
  }

  private getCurrentTime(): number {
    if (this.isPrepared && this.avPlayer) {
      return this.avPlayer.currentTime;
    }
    return 0;
  }

  private getDuration(): number {
    if (this.isPrepared && this.avPlayer) {
      return this.avPlayer.duration;
    }
    return 0;
  }

  private reset(): void {
    this.avPlayer?.reset().then(() => {
      Logger.info(TAG, 'AVPlayer reset successfully');
    }).catch((error: BusinessError) => {
      Logger.error(TAG, `AVPlayer reset failed, code is ${error.code}, message is ${error.message}`);
    });
  }

  private prepare() {
    this.avPlayer?.prepare().then(() => {
      Logger.info(TAG, 'AVPlayer prepare successfully');
    }).catch((error: BusinessError) => {
      Logger.error(TAG, `AVPlayer prepare failed, code is ${error.code}, message is ${error.message}`);
    });
  }

  private playCompleteAuto(): void {
    switch (this.changedData.playMode) {
      case MusicPlayMode.SINGLE_CYCLE:
        this.play();
        break;
      case MusicPlayMode.ORDER:
        this.playNext();
        break;
      case MusicPlayMode.RANDOM:
        this.playRandom();
        break;
      default:
        break;
    }
  }

  private playRandom(): void {
    let num = this.getRandomIndex((this.changedData.songList.length - 1));
    if (this.musicIndex === num) {
      this.playRandom();
    } else {
      this.playByIndex(num);
    }
  }

  private async stop(): Promise<void> {
    if (this.isPrepared && this.avPlayer) {
      this.state = AudioPlayerState.PAUSE;
      this.avPlayer.stop().then(() => {
        Logger.info(TAG, 'AVPlayer stop succeeded.');
      }).catch((error: BusinessError) => {
        Logger.error(TAG, `AVPlayer stop failed, code is ${error.code}, message is ${error.message}`);
      });
    }
  }

  private updateMusicIndex(musicIndex: number): void {
    Logger.info(TAG, `updateMusicIndex: ${musicIndex}`);
    this.musicIndex = musicIndex;
  }

  private setAVSessionPlayState(playbackState: avSession.AVPlaybackState): void {
    this.session?.setAVPlaybackState(playbackState).then(() => {
      Logger.info(TAG, 'SetAVPlaybackState successfully');
    }).catch((error: BusinessError) => {
      Logger.info(TAG, `SetAVPlaybackState BusinessError: code: ${error.code}, message: ${error.message}`);
    });
  }

  // 设置收藏回调
  public setCollectCallback(callback: Function): void {
    this.collectCallBack = callback;
  }

  // 收藏
  public collect(id: string): void {
    if (this.collectCallBack) {
      this.collectCallBack({ songId: id, state: CollectAction.COLLECTED });
      if (this.changedData.currentSong?.id === id) {
        this.updateSessionFavoriteState(true)
      }
    }
  }

  // 取消收藏歌曲
  public unCollect(id: string): void {
    if (this.collectCallBack) {
      this.collectCallBack({ songId: id, state: CollectAction.UNCOLLECTED });
      if (this.changedData.currentSong?.id === id) {
        this.updateSessionFavoriteState(false)
      }
    }
  }

  //根据歌曲id从播放列表中移除
  public removeSongById(id: string): void {
    this.changedData.removeSongById(id);
    //判断要删除的歌曲是否为当前播放歌曲
    if (this.changedData.currentSong?.id === id) {
      this.pause();
    }
    // 重新设置当前播放歌曲
    this.changedData.setCurrentSong(this.changedData.songList[this.musicIndex >= this.changedData.songList.length?0:
    this.musicIndex]);
    // 判断播放列表是否被清空
    if (this.changedData.songList.length === 0) {
      this.clearPlayList()
    }
  }

  // 清空播放列表
  public clearPlayList(): void {
    this.changedData.clearSongList();
    // 清空播放列表
    this.changedData.setCurrentSong(undefined);
    // 停止播放
    this.pause();
  }

  //设置关闭时间
  public setStopTime(time: number): void {
    this.changedData.stopTime = time;
    this.executeAtTimestamp(time);
  }

  private executeAtTimestamp(targetTimestamp: number) {
    // 计算当前时间与目标时间的差值
    const now = Date.now();
    const delay = targetTimestamp - now;

    // 检查目标时间是否在未来
    if (delay <= 0) {
      return;
    }

    // 设置定时器，在延迟时间后执行
    this.timerId = setTimeout(() => {
      MediaService.getInstance().pause()
      this.timerId = null // 执行后重置ID
      this.changedData.stopTime = 0;
    }, delay);
  }

  // 设置播放mv回调
  public setPlayMvCallback(callback: Function): void {
    this.playMvCallBack = callback;
  }

  // 播放mv
  public playMv(mvUrl: string): void {
    if (this.playMvCallBack) {
      this.playMvCallBack(mvUrl);
    }
  }

  // 设置下载歌曲回调
  public setDownloadSongCallback(callback: Function): void {
    this.downloadCallBack = callback;
  }

  // 下载歌曲
  public downloadSong(src: string): void {
    if (this.downloadCallBack) {
      this.downloadCallBack(src);
    }
  }

  // 加入歌单回调
  public setAddPalyListCallback(callback: Function): void {
    this.addPalyListCallBack = callback;
  }

  // 加入歌单
  public addPalyList(songId: string): void {
    if (this.addPalyListCallBack) {
      this.addPalyListCallBack(songId);
    }
  }

  // 打开登录回调
  public setOpenLoginCallback(callback: Function): void {
    this.openLoginCallBack = callback;
  }

  // 打开登录
  public openLogin(): void {
    if (this.openLoginCallBack) {
      this.openLoginCallBack();
    }
  }


  // 根据当前时间和当天第一次登录时间判断，是否可以播放歌曲，要求离当天第一次登录时间间隔超过10分钟不允许播放歌曲
  public checkPlayTime(): boolean {
    // 判断是否未成年模式
    if (!this.changedData.teenagersSwitch) {
      return true
    }
    // todo:自行调整使用总时间
    const useNumTime: number = 60000 * 10;
    return (this.changedData.startLoginTime + useNumTime) > Date.now()
  }

  // 设置音质
  public setAudioQuality(quality: AudioQuality): void {
    this.currentQuality = quality;
    Logger.info(TAG, `Audio quality set to: ${quality}`);

    // 如果正在播放，则重新加载当前歌曲
    if (this.state === AudioPlayerState.PLAY ||
      this.state === AudioPlayerState.PAUSE ||
      this.state === AudioPlayerState.PREPARED) {
      this.reloadCurrentSong();
    }
  }

  // 获取当前音质
  public getCurrentQuality(): string {
    //根据音质返回对应的中文名称
    switch (this.currentQuality) {
      case AudioQuality.LOW:
        return Constants.QUALITY_LOW;
      case AudioQuality.MEDIUM:
        return Constants.QUALITY_MEDIUM;
      case AudioQuality.HIGH:
        return Constants.QUALITY_HIGH;
      case AudioQuality.LOSSLESS:
        return Constants.QUALITY_LOSSLESS;
      default:
        return Constants.QUALITY_LOW;
    }
  }

  // 重新加载当前歌曲（切换音质时使用）
  private async reloadCurrentSong(): Promise<void> {
    if (this.avPlayer && this.changedData.songList.length > 0) {
      // 暂停当前播放
      if (this.state === AudioPlayerState.PLAY) {
        await this.avPlayer.pause();
      }

      // 重置播放器
      await this.avPlayer.reset();

      // 重新加载资源
      this.loadAsset();
    }
  }

  /**
   * 根据音质获取歌曲的url
   * @param song 歌曲对象
   * @returns 歌曲的url
   */
  getUrlByQuality(song: SongItem): string {
    switch (this.currentQuality) {
      case AudioQuality.LOW:
        return song.src;
      case AudioQuality.MEDIUM:
        return song.srcMedium ?? song.src;
      case AudioQuality.HIGH:
        return song.srcHigh ?? song.src;
      case AudioQuality.LOSSLESS:
        return song.srcLossless ?? song.src;
      default:
        return song.src; // 默认返回LOW音质
    }
  }

  /**
   * 播放歌曲
   * @param song 歌曲对象
   * @param isShowPlayPage true 显示播放页面 默认不显示播放页面
   */
  public playSong(song: ESObject, isShowPlayPage: boolean = false): void {
    // 判断歌曲是否为空
    if (!song) {
      return;
    }
    let songList: SongItem[] = [];
    songList = songList.concat(this.changedData.songList)
    if (songList.length === 0) {
      songList = [song];
    } else {
      if (song.id === '') {
        song.id = this.getUniqueId()
      }

      if (songList.findIndex((item) => item.title === song.title) !== -1) {
        songList.splice(songList.findIndex((item) => item.title === song.title), 1);
      }

      songList.unshift(song);
    }

    this.changedData.setSongList(songList);
    this.controlPlay(0);
    if (isShowPlayPage) {
      this.changedData.isShowPlay = true;
    }
  }

  /**
   * 替换当前播放列表并从第一首开始播放（顺序播放）
   */
  public playAllSongs(songList: Array<SongItem>, isShowPlayPage: boolean = false): void {
    if (!songList || songList.length === 0) {
      return;
    }
    this.changedData.setSongList(songList);
    // 设置为顺序播放
    this.setPlayModel(MusicPlayMode.ORDER);
    // 从第一首开始播放
    this.isFirstLoadAsset = false;
    this.controlPlay(0);
    if (isShowPlayPage) {
      this.changedData.isShowPlay = true;
    }
  }

  /**
   * 添加到播放列表（不立即播放）
   * @param song
   */
  addToSongList(song?: SongItem): boolean {
    if (!song) {
      return false;
    }
    // 去重：若已存在则不重复添加
    const list = this.changedData.getSongList();
    const newList: SongItem[] = list.slice();
    const existsIndex = newList.findIndex((item: SongItem) => item.id === song.id);
    if (existsIndex !== -1) {
      newList.splice(existsIndex, 1);
    }
    newList.unshift(song);
    this.changedData.setSongList(newList);
    this.updateCrrentSongIndex();
    return true;
  }

  //切换播放和停止播放
  public async playAndPause() {
    if (this.changedData.isPlay) {
      // 暂停播放
      this.pause()
    } else {
      // 播放
      this.play()
    }
  }

  /**
   * 加入新歌曲后，更新当前播放歌曲的索引
   */
  private updateCrrentSongIndex(): void {
    Logger.info(TAG, `playSong 变更前 Index: ${this.musicIndex}`);
    this.musicIndex = this.changedData.songList.findIndex((item) => item.title === this.changedData.currentSong?.title);
    this.changedData.selectIndex = this.musicIndex;
    Logger.info(TAG, `playSong 变更后 Index: ${this.musicIndex}, songList length: ${this.changedData.songList.length}`);
  }

  /**
   * 导出下载歌曲
   */
  async exportDownload() {
    if (this.changedData.currentSong && this.changedData.isVip) {
      const url: string = this.getUrlByQuality(this.changedData.currentSong)
      this.downloadSong(url)
    }
  }

  /**
   * 获取随机数(符合安全随机数)
   * @param leng 长度
   * @returns
   */
  getRandomIndex(leng: number) {
    let rand = cryptoFramework.createRandom();
    // 设置生成随机数的字节长度为1
    let randData = rand.generateRandomSync(1);
    // 自定义范围(0-10之内)
    let num: number = randData.data[0] * leng / 255;
    num = Math.floor(num);
    return num;
  }

  // 获取唯一ID
  getUniqueId() {
    return util.generateRandomUUID().replace(/-/g, '').substring(2, 10)
  }
}