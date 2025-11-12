import { SongItem } from './SongItem';

@ObservedV2
export class PlayModel {
  @Trace isPlay: boolean = false;
  @Trace currentSong: SongItem | undefined = undefined;
  @Trace isShowPlay: boolean = false;
}