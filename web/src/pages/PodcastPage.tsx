import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, MoreVertical, Music, Upload, Download, Play, Trash2 } from 'lucide-react';
import { podcastService, PodcastResult } from '../services/PodcastService';
import {
  getRecentPodcasts,
  deleteRecentPodcast,
  getPodcastAudioUrl,
  getPodcastAudioUrlAsync,
  formatPodcastDate,
  getPodcastTitle,
  downloadPodcastAudio,
  type RecentPodcast as RecentPodcastType,
} from '../services/RecentPodcastService';
import AudioPlayer from '../components/AudioPlayer';

export default function PodcastPage() {
  const navigate = useNavigate();
  const [recentPodcasts, setRecentPodcasts] = useState<RecentPodcastType[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [playingPodcast, setPlayingPodcast] = useState<RecentPodcastType | null>(null);
  const [playingAudioUrl, setPlayingAudioUrl] = useState<string | null>(null);

  useEffect(() => {
    loadRecentPodcasts();
    // 监听storage事件，当其他标签页保存播客时更新列表
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'recent_podcasts') {
        loadRecentPodcasts();
      }
    };
    window.addEventListener('storage', handleStorageChange);
    
    // 监听自定义事件，当当前页面保存播客时也更新列表
    const handleCustomStorage = () => {
      loadRecentPodcasts();
    };
    window.addEventListener('podcastSaved', handleCustomStorage);
    
    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('podcastSaved', handleCustomStorage);
    };
  }, []);

  const loadRecentPodcasts = () => {
    const podcasts = getRecentPodcasts();
    // 注意：从localStorage加载的播客不包含base64数据（为了节省空间）
    // 只有通过URL或重新生成才能播放
    setRecentPodcasts(podcasts);
  };

  const handlePlayPodcast = async (podcast: RecentPodcastType) => {
    // 先尝试同步获取（localStorage中的base64或URL）
    let audioUrl = getPodcastAudioUrl(podcast);
    
    // 如果没有，尝试从IndexedDB异步获取
    if (!audioUrl) {
      try {
        console.log('从 IndexedDB 获取音频，播客ID:', podcast.id);
        audioUrl = await getPodcastAudioUrlAsync(podcast);
        if (audioUrl) {
          console.log('成功从 IndexedDB 获取音频');
        } else {
          console.warn('IndexedDB 中未找到音频数据，播客ID:', podcast.id);
        }
      } catch (error) {
        console.error('获取音频数据失败:', error);
      }
    }
    
    if (audioUrl) {
      setPlayingPodcast(podcast);
      setPlayingAudioUrl(audioUrl);
    } else {
      alert('无法播放：播客音频数据不可用。\n\n提示：如果这是刚生成的播客，请返回生成页面播放。');
    }
  };

  const handleDeletePodcast = (e: React.MouseEvent, podcast: RecentPodcastType) => {
    e.stopPropagation(); // 阻止触发播放
    if (confirm(`确定要删除播客"${getPodcastTitle(podcast)}"吗？`)) {
      deleteRecentPodcast(podcast.id);
      loadRecentPodcasts();
      // 如果正在播放被删除的播客，停止播放
      if (playingPodcast?.id === podcast.id) {
        setPlayingPodcast(null);
        setPlayingAudioUrl(null);
      }
    }
  };

  const handleDownloadPodcast = async (e: React.MouseEvent, podcast: RecentPodcastType) => {
    e.stopPropagation(); // 阻止触发播放
    await downloadPodcastAudio(podcast);
  };

  const handleUploadMusic = () => {
    // 本地模式：背景音乐功能已移除（不再需要上传到云存储）
    alert('本地模式下，背景音乐由系统自动选择，无需手动上传');
  };

  const handleImportAudio = async () => {
    // 本地模式：音频直接通过API返回，无需从云存储导入
    alert('本地模式下，生成的播客音频会直接返回，无需导入');
  };

  const podcastFunctions = [
    {
      title: '多角色互动播客',
      description: '将文本素材转化为多角色自然互动的播客音频',
      onClick: () => navigate('/podcast/multi-role'),
    },
    {
      title: '自定义角色播客',
      description: '根据用户自定义的角色人设和音色生成契合风格的播客音频',
      onClick: () => navigate('/podcast/character'),
    },
    {
      title: '主题深度播客',
      description: '基于指定主题生成有深度、引发思考的播客音频',
      onClick: () => navigate('/podcast/deep'),
    },
    {
      title: '流式播客脚本',
      description: '生成适配流式播放的单人播客脚本（信息精准、口语化）',
      onClick: () => navigate('/podcast/streaming-script'),
    },
    {
      title: '背景音乐',
      description: '系统会根据播客分类自动选择背景音乐',
      onClick: handleUploadMusic,
    },
    {
      title: '音频管理',
      description: '生成的播客音频会直接返回，支持下载和播放',
      onClick: handleImportAudio,
      loading: isLoading,
    },
  ];

  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-900">
      {/* 顶部标题栏 */}
      <div className="flex items-center justify-between px-4 py-3 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">AI播客</h1>
        <div className="flex items-center gap-2">
          <button className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
            <Search className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          </button>
          <button className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
            <MoreVertical className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          </button>
        </div>
      </div>

      {/* 滚动内容区域 */}
      <div className="flex-1 overflow-y-auto">
        <div className="space-y-5 p-4">
          {/* 播客功能卡片区域 */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-gray-900 dark:text-white">播客功能</h2>
              <button className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300">
                更多&gt;
              </button>
            </div>
            <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide">
              {podcastFunctions.map((func, index) => (
                <button
                  key={index}
                  onClick={func.onClick}
                  disabled={func.loading}
                  className="flex-shrink-0 w-36 p-3 bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 hover:border-primary-300 dark:hover:border-primary-600 transition-all disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  <div className="flex items-center justify-center w-12 h-12 mb-2 bg-primary-50 dark:bg-primary-900/20 rounded-xl">
                    <Music className="w-6 h-6 text-primary-600 dark:text-primary-400" />
                  </div>
                  <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-1 text-center line-clamp-1">
                    {func.title}
                  </h3>
                  <p className="text-xs text-gray-500 dark:text-gray-400 text-center line-clamp-2">
                    {func.description}
                  </p>
                </button>
              ))}
            </div>
          </div>

          {/* 最近播客列表区域 */}
          <div className="space-y-3">
            <h2 className="text-lg font-bold text-gray-900 dark:text-white">最近播客</h2>
            {recentPodcasts.length === 0 ? (
              <div className="flex items-center justify-center py-12 text-gray-500 dark:text-gray-400">
                <span>暂无播客内容</span>
              </div>
            ) : (
              <div className="space-y-2">
                {recentPodcasts.map((podcast) => {
                  const title = getPodcastTitle(podcast);
                  const dateStr = formatPodcastDate(podcast.date);
                  // 检查是否有音频（URL、localStorage中的base64，或可能在IndexedDB中）
                  // 注意：即使没有base64，也可能在IndexedDB中，所以假设所有播客都有音频
                  const hasAudio = true; // IndexedDB中可能有音频，所以始终显示按钮
                  
                  return (
                    <div
                      key={podcast.id}
                      className="w-full p-3 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 hover:border-primary-300 dark:hover:border-primary-600 transition-all flex items-center gap-3"
                    >
                      <div className="flex-shrink-0 w-12 h-12 bg-primary-50 dark:bg-primary-900/20 rounded-lg flex items-center justify-center">
                        <Music className="w-6 h-6 text-primary-600 dark:text-primary-400" />
                      </div>
                      <div className="flex-1 min-w-0 text-left">
                        <h3 className="text-base font-medium text-gray-900 dark:text-white truncate">
                          {title}
                        </h3>
                        {(podcast.roles || podcast.characters) && (
                          <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
                            {podcast.roles?.join('、') || podcast.characters?.join('、')}
                          </p>
                        )}
                        {podcast.topic && (
                          <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
                            {podcast.topic}
                          </p>
                        )}
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-xs px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded">
                            {podcast.type === 'multi-role' ? '多角色' : podcast.type === 'character' ? '自定义角色' : '深度播客'}
                          </span>
                          {podcast.fileSizeMb && (
                            <span className="text-xs text-gray-500 dark:text-gray-400">
                              {podcast.fileSizeMb.toFixed(1)}MB
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-1 flex-shrink-0">
                        <div className="text-xs text-gray-500 dark:text-gray-400 mr-1">
                          {dateStr}
                        </div>
                        <button
                          onClick={() => handlePlayPodcast(podcast)}
                          className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors cursor-pointer"
                          title="播放"
                        >
                          <Play className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                        </button>
                        <button
                          onClick={(e) => handleDownloadPodcast(e, podcast)}
                          className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors cursor-pointer"
                          title="下载"
                        >
                          <Download className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                        </button>
                        <button
                          onClick={(e) => handleDeletePodcast(e, podcast)}
                          className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                          title="删除"
                        >
                          <Trash2 className="w-5 h-5 text-red-500 dark:text-red-400" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 音频播放器 */}
      {playingPodcast && playingAudioUrl && (
        <AudioPlayer
          src={playingAudioUrl}
          title={getPodcastTitle(playingPodcast)}
          onClose={() => {
            setPlayingPodcast(null);
            setPlayingAudioUrl(null);
          }}
          onDownload={() => {
            if (playingPodcast) {
              downloadPodcastAudio(playingPodcast);
            }
          }}
        />
      )}
    </div>
  );
}

