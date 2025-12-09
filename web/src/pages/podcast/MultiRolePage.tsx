import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, FileText, Download, Play } from 'lucide-react';
import { podcastService, MultiRoleRequest, ProgressStatus } from '../../services/PodcastService';
import VoiceSelector from '../../components/VoiceSelector';
import AudioPlayer from '../../components/AudioPlayer';
import { saveRecentPodcast } from '../../services/RecentPodcastService';

const INPUT_TYPE_OPTIONS = [
  '文字',
  '文字+指令',
  '公众号',
  '公众号+指令',
  '网页',
  '网页+指令',
  '文件',
  '文件+指令',
  '文字+英文指令',
];

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

export default function MultiRolePage() {
  const navigate = useNavigate();
  const [text, setText] = useState('');
  const [textFileNames, setTextFileNames] = useState<string[]>([]); // 仅用于显示文件名
  const [inputType, setInputType] = useState('文字');
  const [inputUrl, setInputUrl] = useState('');
  const [instruction, setInstruction] = useState('');
  const [category, setCategory] = useState('');
  const [roleVoices, setRoleVoices] = useState<Record<string, string>>({}); // base64编码的音色数据
  const [roleVoiceIds, setRoleVoiceIds] = useState<Record<string, string>>({}); // 音色ID，用于显示选中状态
  const [roleNames] = useState(['角色A', '角色B']);
  const [isLoading, setIsLoading] = useState(false);
  const [progressPercent, setProgressPercent] = useState(0);
  const [progressMessage, setProgressMessage] = useState('');
  const [generatedAudioUrl, setGeneratedAudioUrl] = useState<string | null>(null);
  const [generatedAudioTitle, setGeneratedAudioTitle] = useState<string>('');

  const handleSelectTextFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setIsLoading(true);
    try {
      const filePromises = Array.from(files).map(async (file) => {
        // 读取文件内容
        const text = await file.text();
        return { content: text, fileName: file.name };
      });

      const results = await Promise.all(filePromises);
      
      if (results.length > 0) {
        // 合并所有文件内容到text字段
        const combinedText = results.map(r => r.content).join('\n\n');
        setText(combinedText);
        setTextFileNames(results.map((r) => r.fileName));
        alert(`已读取${results.length}个文件内容`);
      }
    } catch (error) {
      console.error('文件读取失败:', error);
      alert('文件读取失败，请重试');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectVoice = (roleName: string, voiceBase64: string, voiceId: string) => {
    setRoleVoices((prev) => ({ ...prev, [roleName]: voiceBase64 }));
    setRoleVoiceIds((prev) => ({ ...prev, [roleName]: voiceId }));
  };

  const handleGenerate = async () => {
    const hasText = text.trim().length > 0;
    const hasTextFile = textFileNames.length > 0; // 文本文件内容已合并到text字段
    const hasInputUrl = inputUrl.trim().length > 0;

    if (!hasText && !hasTextFile && !hasInputUrl) {
      alert('请提供文本内容、上传文本文件或输入URL');
      return;
    }

    if (Object.keys(roleVoices).length === 0) {
      alert('请至少选择一个角色的音色');
      return;
    }

    setIsLoading(true);
    setProgressPercent(0);
    setProgressMessage('正在生成播客...');

    try {
      const jobId = `job_${Date.now()}`;
      const request: MultiRoleRequest = {
        text: hasText ? text : undefined,
        // 文本文件内容已合并到text字段，不需要text_file_url
        input_type: inputType,
        input_url: hasInputUrl ? inputUrl : undefined,
        instruction: instruction.trim() || undefined,
        role_voices: roleVoices, // 使用base64编码的音色数据
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
            // 处理音频数据
            if (progress.audio_base64) {
              // 将base64转换为可播放的URL
              const audioUrl = `data:audio/wav;base64,${progress.audio_base64}`;
              setGeneratedAudioUrl(audioUrl);
              setGeneratedAudioTitle('生成的播客');
              
              // 保存到最近播客列表
              console.log('保存播客到最近列表，音频数据长度:', progress.audio_base64?.length || 0);
              saveRecentPodcast({
                title: '多角色互动播客',
                type: 'multi-role',
                audioBase64: progress.audio_base64,
                script: progress.script,
                roles: progress.roles,
              });
            } else if (progress.audio_url) {
              setGeneratedAudioUrl(progress.audio_url);
              setGeneratedAudioTitle('生成的播客');
              
              // 保存到最近播客列表
              saveRecentPodcast({
                title: '多角色互动播客',
                type: 'multi-role',
                audioUrl: progress.audio_url,
                script: progress.script,
                roles: progress.roles,
              });
            }
          }
        }
      });

      const result = await podcastService.generateMultiRolePodcast(request, (progress) => {
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
        // 如果API立即返回成功，停止轮询
        stopPolling();
        
        // 处理音频数据
        if (result.data.audio_base64) {
          const audioUrl = `data:audio/wav;base64,${result.data.audio_base64}`;
          setGeneratedAudioUrl(audioUrl);
          setGeneratedAudioTitle('生成的播客');
          
          // 保存到最近播客列表
          saveRecentPodcast({
            title: '多角色互动播客',
            type: 'multi-role',
            audioBase64: result.data.audio_base64,
            script: result.data.script,
            roles: result.data.roles,
            fileSizeMb: result.data.file_size_mb,
          });
        } else if (result.data.audio_url) {
          setGeneratedAudioUrl(result.data.audio_url);
          setGeneratedAudioTitle('生成的播客');
          
          // 保存到最近播客列表
          saveRecentPodcast({
            title: '多角色互动播客',
            type: 'multi-role',
            audioUrl: result.data.audio_url,
            script: result.data.script,
            roles: result.data.roles,
            fileSizeMb: result.data.file_size_mb,
          });
        }
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
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">多角色互动播客</h1>
      </div>

      {/* 滚动内容区域 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* 输入类型选择 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            输入类型
          </label>
          <select
            value={inputType}
            onChange={(e) => setInputType(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
          >
            {INPUT_TYPE_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </div>

        {/* 文本输入 */}
        {['文字', '文字+指令', '文字+英文指令'].includes(inputType) && (
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              播客文本
            </label>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={8}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white resize-none"
              placeholder="请输入播客文本内容..."
            />
          </div>
        )}

        {/* 文件上传 */}
        {['文件', '文件+指令'].includes(inputType) && (
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              文本文件
            </label>
            <div className="flex items-center gap-2">
              <label className="flex items-center gap-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                <FileText className="w-5 h-5" />
                <span>选择文件</span>
                <input
                  type="file"
                  multiple
                  accept=".txt,.doc,.docx,.pdf"
                  onChange={handleSelectTextFile}
                  className="hidden"
                />
              </label>
              {textFileNames.length > 0 && (
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  已选择 {textFileNames.length} 个文件
                </span>
              )}
            </div>
            {textFileNames.length > 0 && (
              <div className="mt-2 space-y-1">
                {textFileNames.map((name, index) => (
                  <div key={index} className="text-sm text-gray-600 dark:text-gray-400">
                    • {name}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* URL输入 */}
        {['公众号', '公众号+指令', '网页', '网页+指令'].includes(inputType) && (
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              输入URL
            </label>
            <input
              type="url"
              value={inputUrl}
              onChange={(e) => setInputUrl(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              placeholder="请输入URL..."
            />
          </div>
        )}

        {/* 指令输入 */}
        {inputType.includes('指令') && (
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              指令内容
            </label>
            <textarea
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              rows={4}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white resize-none"
              placeholder="请输入指令内容..."
            />
          </div>
        )}

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

        {/* 角色音色选择 */}
        <div className="space-y-4">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            角色音色（必需）
          </label>
          {roleNames.map((roleName) => (
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

      {/* 音频播放器 */}
      {generatedAudioUrl && (
        <AudioPlayer
          src={generatedAudioUrl}
          title={generatedAudioTitle}
          onClose={() => {
            setGeneratedAudioUrl(null);
            setGeneratedAudioTitle('');
          }}
          onDownload={() => {
            // 从data URL下载
            const link = document.createElement('a');
            link.href = generatedAudioUrl;
            link.download = `${generatedAudioTitle || 'podcast'}.wav`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
          }}
        />
      )}
    </div>
  );
}

