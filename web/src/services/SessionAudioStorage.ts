/**
 * 会话音频存储服务
 * 使用sessionStorage临时存储当前会话的音频数据
 * sessionStorage在标签页关闭后会自动清除，不会占用太多空间
 */

const SESSION_STORAGE_KEY = 'session_audio_data';

export interface SessionAudioData {
  [podcastId: string]: string; // podcastId -> audioBase64
}

/**
 * 保存音频数据到sessionStorage
 */
export function saveSessionAudio(podcastId: string, audioBase64: string): void {
  try {
    const existing = getSessionAudios();
    existing[podcastId] = audioBase64;
    
    // 限制sessionStorage中的数据量（最多保存最近10个）
    const keys = Object.keys(existing);
    if (keys.length > 10) {
      // 删除最旧的
      const oldestKey = keys[0];
      delete existing[oldestKey];
    }
    
    sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(existing));
  } catch (error) {
    console.error('保存会话音频失败:', error);
  }
}

/**
 * 从sessionStorage获取音频数据
 */
export function getSessionAudio(podcastId: string): string | null {
  try {
    const audios = getSessionAudios();
    return audios[podcastId] || null;
  } catch (error) {
    console.error('获取会话音频失败:', error);
    return null;
  }
}

/**
 * 获取所有会话音频数据
 */
function getSessionAudios(): SessionAudioData {
  try {
    const stored = sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (!stored) return {};
    return JSON.parse(stored) as SessionAudioData;
  } catch (error) {
    console.error('读取会话音频失败:', error);
    return {};
  }
}

/**
 * 清除会话音频数据
 */
export function clearSessionAudios(): void {
  try {
    sessionStorage.removeItem(SESSION_STORAGE_KEY);
  } catch (error) {
    console.error('清除会话音频失败:', error);
  }
}





