import { PodcastResult } from 'lib_api';
import { SongItem } from 'module_musicplay';
import { CloudStorageMusicUtils } from './CloudStorageMusicUtils';
import fs from '@ohos.file.fs';
import { Logger } from 'lib_common';
import { GlobalContext } from './GlobalContext';
import { FileUtils } from '../utils/FileUtils';

const TAG = 'PodcastMusicUtils';

/**
 * 播客音频工具类
 * 用于将播客结果转换为播放器所需的 SongItem
 */
export class PodcastMusicUtils {
  /**
   * 将播客结果转换为 SongItem
   * @param result 播客结果
   * @param pageTitle 页面标题，用作歌曲名称
   * @returns SongItem 对象
   */
  static async convertToSongItem(result: PodcastResult, pageTitle: string = '播客音频'): Promise<SongItem> {
    const songItem = new SongItem();

    // 生成唯一ID
    songItem.id = `podcast_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    // 设置标题和歌手
    songItem.title = pageTitle;
    songItem.singer = 'AI播客';

    let localPath: string = '';

    try {
      // 优先使用 audio_path
      if (result.audio_path && result.audio_path.length > 0) {
        const fileName = CloudStorageMusicUtils.getFileName(result.audio_path, 'podcast');
        localPath = await CloudStorageMusicUtils.downloadFile(result.audio_path, fileName, true);
      } else if (result.audio_url && result.audio_url.length > 0) {
        // 尝试从 URL 提取云侧路径
        const cloudPath = CloudStorageMusicUtils.extractCloudPath(result.audio_url);
        if (cloudPath) {
          const fileName = CloudStorageMusicUtils.getFileName(cloudPath, 'podcast');
          localPath = await CloudStorageMusicUtils.downloadFile(cloudPath, fileName, true);
        }
      }

      // 如果没有从云侧下载成功，但存在 base64，则写入本地文件
      if (!localPath && result.audio_base64) {
        const fileName = `podcast_${Date.now()}.wav`;
        localPath = await PodcastMusicUtils.saveBase64Audio(result.audio_base64, fileName);
      }
    } catch (error) {
      Logger.error(TAG, `保存音频到本地失败: ${error}`);
    }

    if (localPath && localPath.length > 0) {
      songItem.src = localPath;
      songItem.isLocal = true;
    } else if (result.audio_url) {
      // 无法保存到本地时，回退使用原始URL
      songItem.src = result.audio_url;
      songItem.isLocal = false;
    } else {
      songItem.src = '';
    }

    // 设置其他属性
    songItem.mark = '1';
    songItem.label = $r('app.media.ic_music_icon'); // 使用默认图标
    songItem.lyric = '';
    songItem.isCollected = false;
    songItem.mvUrl = '';
    songItem.isVip = false;
    songItem.collectedCount = 0;
    songItem.playlistCount = 0;
    songItem.downloadCount = 0;
    songItem.shareCount = 0;

    return songItem;
  }

  private static async saveBase64Audio(base64Data: string, fileName: string): Promise<string> {
    const context = GlobalContext.getContext();
    if (!context) {
      throw new Error('无法获取上下文，请确保GlobalContext已初始化');
    }

    const uint8Array = FileUtils.base64ToUint8Array(base64Data);
    const filePath = `${context.cacheDir}/${fileName}`;

    let file: fs.File | null = null;
    try {
      file = fs.openSync(filePath, fs.OpenMode.CREATE | fs.OpenMode.WRITE_ONLY | fs.OpenMode.TRUNC);
      fs.writeSync(file.fd, uint8Array);
    } finally {
      if (file) {
        fs.closeSync(file.fd);
      }
    }

    return filePath;
  }

  /**
   * 检查播客结果是否包含可播放的音频
   * @param result 播客结果
   * @returns 是否包含音频
   */
  static hasAudio(result?: PodcastResult): boolean {
    return !!(result?.audio_url || result?.audio_base64 || result?.audio_path);
  }

  /**
   * 向后兼容：是否有可用的播放源
   */
  static hasPlayableUrl(result?: PodcastResult): boolean {
    return PodcastMusicUtils.hasAudio(result);
  }
}




