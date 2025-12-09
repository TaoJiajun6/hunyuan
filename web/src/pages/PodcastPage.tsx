import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, MoreVertical, Music, Upload, Download } from 'lucide-react';
import { podcastService, PodcastResult } from '../services/PodcastService';

interface RecentPodcast {
  id: string;
  title: string;
  singer?: string;
  date: string;
  audioUrl?: string;
}

export default function PodcastPage() {
  const navigate = useNavigate();
  const [recentPodcasts, setRecentPodcasts] = useState<RecentPodcast[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    loadRecentPodcasts();
  }, []);

  const loadRecentPodcasts = async () => {
    // TODO: 从API获取最近播客列表
    // 这里暂时使用空列表
    setRecentPodcasts([]);
  };

  const handlePlayPodcast = (podcast: RecentPodcast) => {
    if (podcast.audioUrl) {
      // TODO: 实现音频播放
      console.log('播放播客:', podcast);
    }
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
                {recentPodcasts.map((podcast) => (
                  <button
                    key={podcast.id}
                    onClick={() => handlePlayPodcast(podcast)}
                    className="w-full p-3 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 hover:border-primary-300 dark:hover:border-primary-600 transition-all flex items-center gap-3"
                  >
                    <div className="flex-shrink-0 w-12 h-12 bg-primary-50 dark:bg-primary-900/20 rounded-lg flex items-center justify-center">
                      <Music className="w-6 h-6 text-primary-600 dark:text-primary-400" />
                    </div>
                    <div className="flex-1 min-w-0 text-left">
                      <h3 className="text-base font-medium text-gray-900 dark:text-white truncate">
                        {podcast.title || '未知播客'}
                      </h3>
                      {podcast.singer && (
                        <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
                          {podcast.singer}
                        </p>
                      )}
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded">
                          播客
                        </span>
                      </div>
                    </div>
                    <div className="flex-shrink-0 text-sm text-gray-500 dark:text-gray-400">
                      {podcast.date}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

