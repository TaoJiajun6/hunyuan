import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Plus, X } from 'lucide-react';
import { podcastService, CharacterRequest, CharacterInfo, ProgressStatus } from '../../services/PodcastService';
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

export default function CharacterPage() {
  const navigate = useNavigate();
  const [text, setText] = useState('');
  const [category, setCategory] = useState('');
  const [characters, setCharacters] = useState<CharacterInfo[]>([
    { name: '角色A', voice_url: '' },
    { name: '角色B', voice_url: '' },
  ]);
  const [characterVoiceIds, setCharacterVoiceIds] = useState<Record<number, string>>({}); // 角色索引 -> 音色ID
  const [isLoading, setIsLoading] = useState(false);
  const [progressPercent, setProgressPercent] = useState(0);
  const [progressMessage, setProgressMessage] = useState('');

  const addCharacter = () => {
    if (characters.length >= 4) {
      alert('最多只能添加4个角色');
      return;
    }
    const newCharacterName = `角色${String.fromCharCode(65 + characters.length)}`;
    setCharacters([...characters, { name: newCharacterName, voice_url: '' }]);
  };

  const removeCharacter = (index: number) => {
    if (characters.length <= 2) {
      alert('至少需要保留2个角色');
      return;
    }
    setCharacters(characters.filter((_, i) => i !== index));
  };

  const updateCharacter = (index: number, updates: Partial<CharacterInfo>) => {
    const newCharacters = [...characters];
    newCharacters[index] = { ...newCharacters[index], ...updates };
    setCharacters(newCharacters);
  };

  const handleSelectVoice = (index: number, voiceBase64: string, voiceId: string) => {
    updateCharacter(index, { voice_base64: voiceBase64 });
    setCharacterVoiceIds((prev) => ({ ...prev, [index]: voiceId }));
  };

  const handleGenerate = async () => {
    if (!text.trim()) {
      alert('请输入文本素材');
      return;
    }

    if (characters.length < 2) {
      alert('至少需要2个角色');
      return;
    }

    for (const char of characters) {
      if (!char.name || (!char.voice_base64 && !char.voice_url)) {
        alert(`角色 ${char.name || '未知'} 的信息不完整（缺少音色数据）`);
        return;
      }
    }

    setIsLoading(true);
    setProgressPercent(0);
    setProgressMessage('正在生成播客...');

    try {
      const jobId = `job_${Date.now()}`;
      const request: CharacterRequest = {
        characters,
        text,
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

      const result = await podcastService.generateCharacterPodcast(request, (progress) => {
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
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">自定义角色播客</h1>
      </div>

      {/* 滚动内容区域 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* 文本素材 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            文本素材（必需）
          </label>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={8}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white resize-none"
            placeholder="请输入文本素材..."
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

        {/* 角色配置 */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              角色配置（至少2个，最多4个）
            </label>
            <button
              onClick={addCharacter}
              disabled={characters.length >= 4}
              className="flex items-center gap-1 px-3 py-1 text-sm text-primary-600 dark:text-primary-400 hover:bg-primary-50 dark:hover:bg-primary-900/20 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Plus className="w-4 h-4" />
              <span>添加角色</span>
            </button>
          </div>

          {characters.map((character, index) => (
            <div key={index} className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  {character.name}
                </span>
                {characters.length > 2 && (
                  <button
                    onClick={() => removeCharacter(index)}
                    className="p-1 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>

              <div>
                <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1">角色名称</label>
                <input
                  type="text"
                  value={character.name}
                  onChange={(e) => updateCharacter(index, { name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
                  placeholder="请输入角色名称"
                />
              </div>

              <div>
                <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1">身份</label>
                <input
                  type="text"
                  value={character.identity || ''}
                  onChange={(e) => updateCharacter(index, { identity: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
                  placeholder="请输入角色身份（可选）"
                />
              </div>

              <div>
                <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1">性格特点</label>
                <input
                  type="text"
                  value={character.personality || ''}
                  onChange={(e) => updateCharacter(index, { personality: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
                  placeholder="请输入性格特点（可选）"
                />
              </div>

              <div>
                <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1">说话风格</label>
                <input
                  type="text"
                  value={character.speaking_style || ''}
                  onChange={(e) => updateCharacter(index, { speaking_style: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
                  placeholder="请输入说话风格（可选）"
                />
              </div>

              <div>
                <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1">音色文件（必需）</label>
                <VoiceSelector
                  roleName={character.name}
                  selectedVoiceUrl={character.voice_base64 || character.voice_url}
                  selectedVoiceId={characterVoiceIds[index]}
                  onSelect={(voiceBase64, voiceId) => handleSelectVoice(index, voiceBase64, voiceId)}
                  disabled={isLoading}
                />
              </div>
            </div>
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

