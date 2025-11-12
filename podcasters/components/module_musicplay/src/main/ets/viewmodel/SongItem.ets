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

/**
 * Music information entity class.
 */
@ObservedV2
export class SongItem {
  /**
   * Primary key ID.
   */
  @Trace id: string = '';
  /**
   * Music name.
   */
  @Trace title: string = '';
  /**
   * Music author name.
   */
  @Trace singer: string = '';
  /**
   * Music logo information. 1:vip 2:sq
   */
  @Trace mark: string = '1';
  /**
   * Music avatar information.
   */
  @Trace label: string | Resource = $r('app.media.ic_music_icon');
  /**
   * 为不同音质歌曲 URL  src默认为LOW音质
   */
  @Trace src: string = '';
  /**
   * 为不同音质歌曲 URL  srcMedium 音质为MEDIUM
   */
  @Trace srcMedium?: string = '';
  /**
   * 为不同音质歌曲 URL  srcHigh 音质为HIGH
   */
  @Trace srcHigh?: string = '';
  /**
   * 为不同音质歌曲 URL  srcLossless 音质为LOSSLESS
   */
  @Trace srcLossless?: string = '';
  /**
   * Lyric file path information.
   */
  @Trace lyric: string = '';
  /**
   * is collected 1:collected 0:uncollected
   */
  @Trace isCollected: boolean = false;
  /**
   * 是否本地歌曲
   */
  @Trace isLocal: boolean = false;
  /**
   * MV url
   */
  @Trace mvUrl: string = '';
  @Trace isVip: boolean = false;
  //收藏数量
  @Trace collectedCount: number = 1;
  //加入歌单 数量
  @Trace playlistCount: number = 10;
  //下载次数
  @Trace downloadCount: number = 2;
  // 分享次数
  @Trace shareCount: number = 5;
}
