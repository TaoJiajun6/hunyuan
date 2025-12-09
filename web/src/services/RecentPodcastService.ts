/**
 * 最近播客管理服务
 * 使用localStorage存储最近生成的播客
 */

export interface RecentPodcast {
  id: string;
  title: string;
  type: 'multi-role' | 'character' | 'deep';
  audioBase64?: string;
  audioUrl?: string;
  script?: string;
  roles?: string[];
  characters?: string[];
  topic?: string;
  date: string;
  fileSizeMb?: number;
}

const STORAGE_KEY = 'recent_podcasts';
const MAX_RECENT_PODCASTS = 50; // 最多保存50个播客

/**
 * 获取所有最近播客
 */
export function getRecentPodcasts(): RecentPodcast[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return [];
    const podcasts = JSON.parse(stored) as RecentPodcast[];
    // 按日期倒序排列（最新的在前）
    return podcasts.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
  } catch (error) {
    console.error('读取最近播客失败:', error);
    return [];
  }
}

/**
 * 保存播客到最近播客列表
 * 注意：为了节省localStorage空间，base64音频数据不会被保存到localStorage
 * 但会保存到sessionStorage中，供当前会话使用
 */
export function saveRecentPodcast(podcast: Omit<RecentPodcast, 'id' | 'date'>): RecentPodcast {
  // 生成播客ID（在保存前生成，确保IndexedDB和localStorage使用同一个ID）
  const podcastId = `podcast_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  
  // 如果有base64数据，保存到IndexedDB（支持大文件，持久化存储）
  if (podcast.audioBase64) {
    import('./AudioStorage').then(({ saveAudioToIndexedDB, cleanOldAudioData }) => {
      saveAudioToIndexedDB(podcastId, podcast.audioBase64!)
        .then(() => {
          console.log('音频数据已保存到 IndexedDB，播客ID:', podcastId);
          // 清理旧数据，保持数据库大小合理
          cleanOldAudioData(50).catch(err => {
            console.warn('清理旧音频数据失败:', err);
          });
        })
        .catch(err => {
          console.error('保存音频到 IndexedDB 失败:', err);
        });
    }).catch(err => {
      console.warn('无法加载 AudioStorage 模块:', err);
    });
  }

  // 不保存base64音频数据到localStorage（数据太大，会超出限制）
  // 只保存元数据和URL（如果有）
  const podcastToSave: Omit<RecentPodcast, 'id' | 'date'> = {
    ...podcast,
    audioBase64: undefined, // 不保存base64到localStorage，避免超出限制
    // 保留audioUrl（如果有），因为URL字符串很小
  };

  const newPodcast: RecentPodcast = {
    ...podcastToSave,
    id: podcastId, // 使用上面生成的ID
    date: new Date().toISOString(),
  };

  // 检查是否有音频数据（URL或base64）
  const hasAudio = !!(podcast.audioBase64 || podcast.audioUrl);
  if (!hasAudio) {
    console.warn('保存播客时没有音频数据:', newPodcast);
  }

  try {
    const existing = getRecentPodcasts();
    // 清理现有播客的base64数据（如果存在），释放空间
    const cleanedExisting = existing.map(p => ({
      ...p,
      audioBase64: undefined, // 清理旧的base64数据
    }));
    
    // 添加新播客到列表开头
    const updated = [newPodcast, ...cleanedExisting];
    // 限制数量
    const limited = updated.slice(0, MAX_RECENT_PODCASTS);
    
    // 尝试保存数据
    const jsonString = JSON.stringify(limited);
    const sizeInMB = new Blob([jsonString]).size / (1024 * 1024);
    
    console.log('保存播客元数据，大小:', sizeInMB.toFixed(2), 'MB');
    
    localStorage.setItem(STORAGE_KEY, jsonString);
    
    // 验证保存是否成功
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const parsed = JSON.parse(saved);
      const savedPodcast = parsed.find((p: RecentPodcast) => p.id === newPodcast.id);
      if (savedPodcast) {
        console.log('播客元数据保存成功，ID:', newPodcast.id);
        // 注意：base64数据不会被保存，这是预期的行为
        if (podcast.audioBase64) {
          console.log('注意：base64音频数据未保存到localStorage（数据过大），仅在当前会话中可用');
        }
      }
    }
    
    // 触发自定义事件，通知其他组件更新
    window.dispatchEvent(new CustomEvent('podcastSaved'));
    
    // 返回播客对象（不包含base64，已保存到sessionStorage）
    return newPodcast;
  } catch (error: any) {
    console.error('保存最近播客失败:', error);
    
    // 检查是否是QuotaExceededError（存储空间不足）
    if (error.name === 'QuotaExceededError' || error.code === 22) {
      console.error('localStorage存储空间不足，清理所有旧数据');
      // 清理所有旧数据，只保存最新的播客
      try {
        const { audioBase64, ...basicInfo } = newPodcast;
        const minimalPodcast = { ...basicInfo, audioBase64: undefined };
        localStorage.setItem(STORAGE_KEY, JSON.stringify([minimalPodcast]));
        console.warn('已清理所有旧数据，只保留最新播客');
      } catch (e) {
        console.error('清理后保存也失败:', e);
        // 如果还是失败，清空所有数据
        try {
          localStorage.removeItem(STORAGE_KEY);
          console.warn('已清空所有播客数据');
        } catch (clearError) {
          console.error('清空数据也失败:', clearError);
        }
      }
    } else {
      // 其他错误
      console.error('保存失败，错误类型:', error.name, error.message);
    }
    
    // 即使保存失败，也返回播客对象
    return newPodcast;
  }
}

/**
 * 删除播客
 */
export function deleteRecentPodcast(id: string): void {
  try {
    const existing = getRecentPodcasts();
    const updated = existing.filter(p => p.id !== id);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
    
    // 同时从 IndexedDB 删除音频数据
    import('./AudioStorage').then(({ deleteAudioFromIndexedDB }) => {
      deleteAudioFromIndexedDB(id).catch(err => {
        console.warn('从 IndexedDB 删除音频失败:', err);
      });
    }).catch(err => {
      // AudioStorage 模块不可用，忽略
    });
  } catch (error) {
    console.error('删除最近播客失败:', error);
  }
}

/**
 * 清空所有最近播客
 */
export function clearRecentPodcasts(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
    
    // 同时清空 IndexedDB 中的音频数据
    import('./AudioStorage').then(({ cleanOldAudioData }) => {
      // 保留0个，即清空所有
      cleanOldAudioData(0).catch(err => {
        console.warn('清空 IndexedDB 音频数据失败:', err);
      });
    }).catch(err => {
      // AudioStorage 模块不可用，忽略
    });
  } catch (error) {
    console.error('清空最近播客失败:', error);
  }
}

/**
 * 获取播客的音频URL（用于播放）
 * 同步版本：优先检查localStorage和URL
 */
export function getPodcastAudioUrl(podcast: RecentPodcast): string | null {
  // 优先使用localStorage中的base64（如果有，向后兼容）
  if (podcast.audioBase64) {
    return `data:audio/wav;base64,${podcast.audioBase64}`;
  }
  
  // 尝试使用URL
  if (podcast.audioUrl) {
    return podcast.audioUrl;
  }
  
  return null;
}

/**
 * 获取播客的音频URL（异步版本，会从IndexedDB获取）
 */
export async function getPodcastAudioUrlAsync(podcast: RecentPodcast): Promise<string | null> {
  // 优先使用localStorage中的base64（如果有，向后兼容）
  if (podcast.audioBase64) {
    return `data:audio/wav;base64,${podcast.audioBase64}`;
  }
  
  // 如果没有，尝试从IndexedDB获取（持久化存储）
  try {
    const { getAudioFromIndexedDB } = await import('./AudioStorage');
    const audioBase64 = await getAudioFromIndexedDB(podcast.id);
    if (audioBase64) {
      return `data:audio/wav;base64,${audioBase64}`;
    }
  } catch (err) {
    console.warn('从 IndexedDB 获取音频失败:', err);
  }
  
  // 最后尝试使用URL
  if (podcast.audioUrl) {
    return podcast.audioUrl;
  }
  
  return null;
}

/**
 * 下载播客音频文件
 */
export async function downloadPodcastAudio(podcast: RecentPodcast): Promise<void> {
  // 先尝试同步获取
  let audioBase64: string | null = podcast.audioBase64 || null;
  
  // 如果没有，尝试从IndexedDB获取
  if (!audioBase64) {
    try {
      const { getAudioFromIndexedDB } = await import('./AudioStorage');
      audioBase64 = await getAudioFromIndexedDB(podcast.id);
    } catch (err) {
      console.warn('从 IndexedDB 获取音频失败:', err);
    }
  }
  
  const title = getPodcastTitle(podcast);
  const fileName = `${title}_${new Date(podcast.date).toISOString().split('T')[0]}.wav`;

  if (audioBase64) {
    // 从base64下载
    try {
      // 将base64转换为blob
      const byteCharacters = atob(audioBase64);
      const byteNumbers = new Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
      }
      const byteArray = new Uint8Array(byteNumbers);
      const blob = new Blob([byteArray], { type: 'audio/wav' });

      // 创建下载链接
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      // 清理URL对象
      setTimeout(() => URL.revokeObjectURL(url), 100);
    } catch (error) {
      console.error('下载失败:', error);
      alert('下载失败，请重试');
    }
  } else if (podcast.audioUrl) {
    // 从URL下载
    const link = document.createElement('a');
    link.href = podcast.audioUrl;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  } else {
    alert('无法下载：播客音频数据不可用');
  }
}

/**
 * 格式化日期显示
 */
export function formatPodcastDate(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) {
    return '刚刚';
  } else if (minutes < 60) {
    return `${minutes}分钟前`;
  } else if (hours < 24) {
    return `${hours}小时前`;
  } else if (days < 7) {
    return `${days}天前`;
  } else {
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
  }
}

/**
 * 获取播客标题
 */
export function getPodcastTitle(podcast: RecentPodcast): string {
  if (podcast.title) {
    return podcast.title;
  }
  
  switch (podcast.type) {
    case 'multi-role':
      return podcast.roles && podcast.roles.length > 0
        ? `${podcast.roles.join('、')}互动播客`
        : '多角色互动播客';
    case 'character':
      return podcast.characters && podcast.characters.length > 0
        ? `${podcast.characters.join('、')}角色播客`
        : '自定义角色播客';
    case 'deep':
      return podcast.topic || '主题深度播客';
    default:
      return '生成的播客';
  }
}

