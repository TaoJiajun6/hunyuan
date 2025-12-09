import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { podcastService, DeepPodcastRequest, ProgressStatus } from '../../services/PodcastService';
import VoiceSelector from '../../components/VoiceSelector';

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

export default function DeepPage() {
  const navigate = useNavigate();
  const [topic, setTopic] = useState('');
  const [category, setCategory] = useState('');
  const [roleVoices, setRoleVoices] = useState<Record<string, string>>({}); // base64编码的音色数据
  const [roleVoiceIds, setRoleVoiceIds] = useState<Record<string, string>>({}); // 音色ID，用于显示选中状态
  const [numCharacters, setNumCharacters] = useState(2);
  const [depthLevel, setDepthLevel] = useState('深度');
  const [isLoading, setIsLoading] = useState(false);
  const [progressPercent, setProgressPercent] = useState(0);
  const [progressMessage, setProgressMessage] = useState('');

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
    setProgressPercent(0);
    setProgressMessage('正在生成播客...');

    try {
      const jobId = `job_${Date.now()}`;
      const request: DeepPodcastRequest = {
        topic,
        role_voices: roleVoices, // 使用base64编码的音色数据
        num_characters: numCharacters,
        depth_level: depthLevel,
        category: category || undefined,
        job_id: jobId,
      };

      const stopPolling = podcastService.startProgressPolling(jobId, (progress: ProgressStatus) => {
        setProgressPercent(progress.percent);
        setProgressMessage(progress.message);
        if (progress.done) {
          setIsLoading(false);
          stopPolling(); // 停止轮询
          if (progress.error) {
            alert(`生成失败: ${progress.error}`);
          } else if (progress.audio_url || progress.audio_base64) {
            alert('播客生成成功！');
          }
        }
      });

      const result = await podcastService.generateDeepPodcast(request, (progress) => {
        setProgressPercent(progress.percent);
        setProgressMessage(progress.message);
      });

      // 如果API调用失败，停止轮询
      if (!result.success) {
        stopPolling();
        setIsLoading(false);
        const errorMsg = result.error || result.message || '未知错误';
        
        // 检查是否是网络错误
        if (errorMsg.includes('Network Error') || errorMsg.includes('ERR_CONNECTION_REFUSED') || errorMsg.includes('网络')) {
          alert(`无法连接到服务器: ${errorMsg}\n\n请检查网络连接或联系管理员`);
        } else {
          alert(`生成失败: ${errorMsg}`);
        }
        return;
      }

      if (result.success && result.data) {
        stopPolling();
        alert('播客生成成功！');
        navigate('/podcast');
      }
    } catch (error) {
      console.error('生成失败:', error);
      alert('生成失败，请重试');
    } finally {
      setIsLoading(false);
    }
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
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">主题深度播客</h1>
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
              // 清理多余角色的音色URL
              const newRoleNames = ROLE_NAMES.slice(0, newNum);
              const newRoleVoiceUrls: Record<string, string> = {};
              newRoleNames.forEach((name) => {
                if (roleVoiceUrls[name]) {
                  newRoleVoiceUrls[name] = roleVoiceUrls[name];
                }
              });
              setRoleVoiceUrls(newRoleVoiceUrls);
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
              selectedVoiceUrl={roleVoices[roleName]} // base64数据
              selectedVoiceId={roleVoiceIds[roleName]} // 音色ID，用于显示选中状态
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

        {/* 生成按钮 */}
        <button
          onClick={handleGenerate}
          disabled={isLoading}
          className="w-full px-4 py-3 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isLoading ? '生成中...' : '生成播客'}
        </button>
      </div>
    </div>
  );
}

