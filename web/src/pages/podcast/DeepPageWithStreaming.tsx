/**
 * 主题深度播客页面 - 带流式播放功能
 * 
 * 这个示例展示了如何集成 StreamingTTSPlayer 实现边生成边播放
 */
import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Play, Pause } from 'lucide-react';
import { podcastService, DeepPodcastRequest, ProgressStatus } from '../../services/PodcastService';
import VoiceSelector from '../../components/VoiceSelector';
import { saveRecentPodcast } from '../../services/RecentPodcastService';
import { StreamingTTSPlayer } from '../../utils/StreamingTTSPlayer';

const CATEGORY_OPTIONS = [
  '社会文化与历史',
  '音乐',
  '影视',
  '书',
  '喜剧/脱口秀',
  '艺术',
  '宗教与灵修',
  '科学与科技',
  '时尚与美妆',
  '健康、健身与养身',
  '育儿与家庭',
  '情感',
  '生活',
  '体育运动',
  '休闲娱乐与爱好',
  '商业与财经',
  '新闻',
  '职场万象',
  '自我成长与自愈',
  '学术研究',
];

const DEPTH_LEVELS = ['深度', '中等', '浅层'];
const ROLE_NAMES = ['角色A', '角色B', '角色C'];

export default function DeepPageWithStreaming() {
  const navigate = useNavigate();
  const [topic, setTopic] = useState('');
  const [category, setCategory] = useState('');
  const [roleVoices, setRoleVoices] = useState<Record<string, string>>({});
  const [roleVoiceIds, setRoleVoiceIds] = useState<Record<string, string>>({});
  const [numCharacters, setNumCharacters] = useState(2);
  const [depthLevel, setDepthLevel] = useState('深度');
  const [isLoading, setIsLoading] = useState(false);
  const [progressPercent, setProgressPercent] = useState(0);
  const [progressMessage, setProgressMessage] = useState('');
  
  // 流式播放相关状态
  const [isStreaming, setIsStreaming] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  
  // 使用 ref 保存播放器实例和停止函数
  const playerRef = useRef<StreamingTTSPlayer | null>(null);
  const stopStreamingRef = useRef<(() => void) | null>(null);

  // 清理函数
  useEffect(() => {
    return () => {
      // 组件卸载时清理资源
      if (playerRef.current) {
        playerRef.current.destroy();
        playerRef.current = null;
      }
      if (stopStreamingRef.current) {
        stopStreamingRef.current();
        stopStreamingRef.current = null;
      }
    };
  }, []);

  const handleSelectVoice = (roleName: string, voiceBase64: string, voiceId: string) => {
    setRoleVoices((prev) => ({ ...prev, [roleName]: voiceBase64 }));
    setRoleVoiceIds((prev) => ({ ...prev, [roleName]: voiceId }));
  };

  const handleGenerate = async () => {
    if (!topic.trim()) {
      alert('请输入播客主题');
      return;
    }

    const roleNames = ROLE_NAMES.slice(0, numCharacters);
    if (Object.keys(roleVoices).length !== numCharacters) {
      alert(`请为所有${numCharacters}个角色选择音色`);
      return;
    }

    for (const roleName of roleNames) {
      if (!roleVoices[roleName]) {
        alert(`缺少角色 ${roleName} 的音色数据`);
        return;
      }
    }

    setIsLoading(true);
    setIsStreaming(true);
    setProgressPercent(0);
    setProgressMessage('正在生成播客...');

    try {
      // 创建流式播放器
      const player = new StreamingTTSPlayer({
        onEvent: (event, data) => {
          console.log('播放器事件:', event, data);
          
          if (event === 'ready') {
            console.log('播放器已就绪');
          } else if (event === 'play') {
            setIsPlaying(true);
          } else if (event === 'pause') {
            setIsPlaying(false);
          } else if (event === 'timeupdate') {
            if (data) {
              setCurrentTime(data.currentTime || 0);
              setDuration(data.duration || 0);
            }
          } else if (event === 'ended') {
            setIsPlaying(false);
            setIsStreaming(false);
          } else if (event === 'error') {
            console.error('播放器错误:', data);
            alert('播放出错，请重试');
          }
        }
      });
      
      playerRef.current = player;

      const jobId = `job_${Date.now()}`;
      const request: DeepPodcastRequest = {
        topic,
        role_voices: roleVoices,
        num_characters: numCharacters,
        depth_level: depthLevel,
        category: category || undefined,
        job_id: jobId,
      };

      // 启动流式进度监听（支持音频块接收）
      const stopStreaming = podcastService.startStreamingProgress(
        jobId,
        (progress: ProgressStatus) => {
          // 处理普通进度更新
          setProgressPercent(progress.percent);
          setProgressMessage(progress.message);
          
          if (progress.done) {
            setIsLoading(false);
            
            if (progress.error) {
              alert(`生成失败: ${progress.error}`);
              setIsStreaming(false);
              if (playerRef.current) {
                playerRef.current.destroy();
                playerRef.current = null;
              }
            } else {
              // 生成完成，等待最后一个音频块
              console.log('生成完成，等待最后一个音频块...');
            }
          }
        },
        (chunk) => {
          // 处理音频块
          console.log(`收到音频块 ${chunk.chunk_index}, 是否最后: ${chunk.is_last}`);
          
          if (playerRef.current) {
            // 将音频块发送给播放器
            // 注意：如果后端发送的是 WAV 格式，需要确保 base64 数据包含正确的 data URL 前缀
            const audioBase64 = chunk.audio_base64.startsWith('data:') 
              ? chunk.audio_base64 
              : `data:audio/wav;base64,${chunk.audio_base64}`;
            
            playerRef.current.receiveBase64(audioBase64, true); // 自动播放
            
            // 如果是最后一个块，结束流
            if (chunk.is_last) {
              console.log('收到最后一个音频块，结束流');
              setTimeout(() => {
                if (playerRef.current) {
                  playerRef.current.endOfStream();
                }
                setIsStreaming(false);
                
                // 保存到最近播客列表（使用完整音频）
                // 注意：流式播放时，完整音频会在生成完成后通过 progress.audio_base64 返回
                // 这里可以保存播放器中的音频，或者等待完整音频返回
              }, 1000);
            }
          }
        }
      );
      
      stopStreamingRef.current = stopStreaming;

      // 发送生成请求
      const result = await podcastService.generateDeepPodcast(request, (progress) => {
        setProgressPercent(progress.percent);
        setProgressMessage(progress.message);
      });

      // 如果API调用失败，停止流式监听
      if (!result.success) {
        stopStreaming();
        setIsLoading(false);
        setIsStreaming(false);
        if (playerRef.current) {
          playerRef.current.destroy();
          playerRef.current = null;
        }
        
        const errorMsg = result.error || result.message || '未知错误';
        if (errorMsg.includes('Network Error') || errorMsg.includes('ERR_CONNECTION_REFUSED') || errorMsg.includes('网络')) {
          alert(`无法连接到服务器: ${errorMsg}\n\n请检查网络连接或联系管理员`);
        } else {
          alert(`生成失败: ${errorMsg}`);
        }
        return;
      }

      // 如果API立即返回了完整音频（非流式模式），保存并导航
      if (result.success && result.data && result.data.audio_base64) {
        stopStreaming();
        setIsLoading(false);
        setIsStreaming(false);
        
        // 保存到最近播客列表
        saveRecentPodcast({
          title: result.data.topic || '主题深度播客',
          type: 'deep',
          audioBase64: result.data.audio_base64,
          script: result.data.script,
          topic: result.data.topic,
          fileSizeMb: result.data.file_size_mb,
        });
        
        // 可以选择导航到播客列表，或者继续在当前页面播放
        // navigate('/podcast');
      }
    } catch (error) {
      console.error('生成失败:', error);
      alert('生成失败，请重试');
      setIsLoading(false);
      setIsStreaming(false);
      if (playerRef.current) {
        playerRef.current.destroy();
        playerRef.current = null;
      }
      if (stopStreamingRef.current) {
        stopStreamingRef.current();
        stopStreamingRef.current = null;
      }
    }
  };

  const handleTogglePlay = () => {
    if (playerRef.current) {
      if (isPlaying) {
        playerRef.current.pause();
      } else {
        playerRef.current.play();
      }
    }
  };

  const handleStop = () => {
    if (playerRef.current) {
      playerRef.current.stop();
      setIsPlaying(false);
      setIsStreaming(false);
    }
    if (stopStreamingRef.current) {
      stopStreamingRef.current();
      stopStreamingRef.current = null;
    }
  };

  const formatTime = (seconds: number) => {
    if (isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const currentRoleNames = ROLE_NAMES.slice(0, numCharacters);

  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-900">
      {/* 顶部标题栏 */}
      <div className="flex items-center gap-4 px-4 py-3 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <button
          onClick={() => navigate('/podcast')}
          className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        >
          <ArrowLeft className="w-5 h-5 text-gray-600 dark:text-gray-400" />
        </button>
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">主题深度播客（流式播放）</h1>
      </div>

      {/* 滚动内容区域 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* 播客主题 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            播客主题（必需）
          </label>
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
            placeholder="请输入播客主题..."
          />
        </div>

        {/* 播客分类 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            播客分类（可选）
          </label>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
          >
            <option value="">请选择分类</option>
            {CATEGORY_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </div>

        {/* 角色数量 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            角色数量（1-3个）
          </label>
          <select
            value={numCharacters}
            onChange={(e) => {
              const newNum = parseInt(e.target.value);
              setNumCharacters(newNum);
              const newRoleNames = ROLE_NAMES.slice(0, newNum);
              const newRoleVoices: Record<string, string> = {};
              const newRoleVoiceIds: Record<string, string> = {};
              newRoleNames.forEach((name) => {
                if (roleVoices[name]) {
                  newRoleVoices[name] = roleVoices[name];
                  newRoleVoiceIds[name] = roleVoiceIds[name];
                }
              });
              setRoleVoices(newRoleVoices);
              setRoleVoiceIds(newRoleVoiceIds);
            }}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
          >
            <option value={1}>1个角色</option>
            <option value={2}>2个角色</option>
            <option value={3}>3个角色</option>
          </select>
        </div>

        {/* 深度级别 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            深度级别
          </label>
          <div className="flex gap-2">
            {DEPTH_LEVELS.map((level) => (
              <button
                key={level}
                onClick={() => setDepthLevel(level)}
                className={`flex-1 px-4 py-2 rounded-lg border transition-colors ${
                  depthLevel === level
                    ? 'bg-primary-600 text-white border-primary-600'
                    : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:border-primary-300 dark:hover:border-primary-600'
                }`}
              >
                {level}
              </button>
            ))}
          </div>
        </div>

        {/* 角色音色选择 */}
        <div className="space-y-4">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            角色音色（必需）
          </label>
          {currentRoleNames.map((roleName) => (
            <VoiceSelector
              key={roleName}
              roleName={roleName}
              selectedVoiceUrl={roleVoices[roleName]}
              selectedVoiceId={roleVoiceIds[roleName]}
              onSelect={(voiceBase64, voiceId) => handleSelectVoice(roleName, voiceBase64, voiceId)}
              disabled={isLoading}
            />
          ))}
        </div>

        {/* 进度显示 */}
        {isLoading && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600 dark:text-gray-400">{progressMessage}</span>
              <span className="text-gray-600 dark:text-gray-400">{progressPercent}%</span>
            </div>
            <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-primary-600 transition-all duration-300"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>
        )}

        {/* 流式播放控制 */}
        {isStreaming && (
          <div className="p-4 bg-primary-50 dark:bg-primary-900/20 rounded-lg border border-primary-200 dark:border-primary-800">
            <div className="flex items-center gap-4">
              <button
                onClick={handleTogglePlay}
                className="p-3 rounded-full bg-primary-600 text-white hover:bg-primary-700 transition-colors"
              >
                {isPlaying ? (
                  <Pause className="w-5 h-5" />
                ) : (
                  <Play className="w-5 h-5" />
                )}
              </button>
              <div className="flex-1">
                <div className="text-sm font-medium text-gray-900 dark:text-white mb-1">
                  正在流式播放...
                </div>
                <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                  <span>{formatTime(currentTime)}</span>
                  <span>/</span>
                  <span>{formatTime(duration) || '--:--'}</span>
                </div>
              </div>
              <button
                onClick={handleStop}
                className="px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
              >
                停止
              </button>
            </div>
          </div>
        )}

        {/* 生成按钮 */}
        <button
          onClick={handleGenerate}
          disabled={isLoading || isStreaming}
          className="w-full px-4 py-3 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isLoading ? '生成中...' : isStreaming ? '正在播放...' : '生成播客'}
        </button>
      </div>
    </div>
  );
}






