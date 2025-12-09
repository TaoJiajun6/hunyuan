import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, FileText, Copy, Check, Download } from 'lucide-react';
import { podcastService, StreamingScriptRequest } from '../../services/PodcastService';

export default function StreamingScriptPage() {
  const navigate = useNavigate();
  const [textMaterial, setTextMaterial] = useState('');
  const [instruction, setInstruction] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [generatedScript, setGeneratedScript] = useState<string | null>(null);
  const [copySuccess, setCopySuccess] = useState(false);

  const handleSelectTextFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setIsLoading(true);
    try {
      const filePromises = Array.from(files).map(async (file) => {
        const text = await file.text();
        return text;
      });

      const results = await Promise.all(filePromises);
      
      if (results.length > 0) {
        const combinedText = results.join('\n\n');
        setTextMaterial(combinedText);
        alert(`已读取${results.length}个文件内容`);
      }
    } catch (error) {
      console.error('文件读取失败:', error);
      alert('文件读取失败，请重试');
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerate = async () => {
    if (!textMaterial.trim()) {
      alert('请输入内容（报告、文章、访谈稿、数据手册、故事素材等）');
      return;
    }

    setIsLoading(true);
    setGeneratedScript(null);

    try {
      const request: StreamingScriptRequest = {
        text_material: textMaterial,
        instruction: instruction.trim() || undefined,
      };

      const result = await podcastService.generateStreamingScript(request);

      if (result.success && result.data) {
        setGeneratedScript(result.data.script);
      } else {
        const errorMsg = result.error || result.message || '未知错误';
        
        // 检查是否是网络错误
        if (errorMsg.includes('Network Error') || errorMsg.includes('ERR_CONNECTION_REFUSED') || errorMsg.includes('网络')) {
          alert(`无法连接到服务器: ${errorMsg}\n\n请检查网络连接或联系管理员`);
        } else {
          alert(`生成失败: ${errorMsg}`);
        }
      }
    } catch (error) {
      console.error('生成失败:', error);
      alert('生成失败，请重试');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopyScript = async () => {
    if (generatedScript) {
      try {
        await navigator.clipboard.writeText(generatedScript);
        setCopySuccess(true);
        setTimeout(() => setCopySuccess(false), 2000);
      } catch (error) {
        console.error('复制失败:', error);
        alert('复制失败，请手动复制');
      }
    }
  };

  const handleDownloadScript = () => {
    if (generatedScript) {
      const blob = new Blob([generatedScript], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `流式播客脚本_${new Date().getTime()}.txt`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
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
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">流式播客脚本生成</h1>
      </div>

      {/* 滚动内容区域 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* 功能说明 */}
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <h3 className="text-sm font-medium text-blue-900 dark:text-blue-300 mb-2">
            💡 功能说明
          </h3>
          <p className="text-sm text-blue-800 dark:text-blue-400">
            基于任意输入内容（报告、文章、访谈稿、数据手册、故事素材等），生成适配音频流式播放的专业播客脚本。
            脚本特点：信息精准、语言口语化、节奏适配碎片化收听。
          </p>
        </div>

        {/* 输入内容 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            输入内容 <span className="text-red-500">*</span>
          </label>
          <div className="flex items-center gap-2 mb-2">
            <label className="flex items-center gap-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors text-sm">
              <FileText className="w-4 h-4" />
              <span>选择文件</span>
              <input
                type="file"
                multiple
                accept=".txt,.doc,.docx,.pdf"
                onChange={handleSelectTextFile}
                className="hidden"
                disabled={isLoading}
              />
            </label>
          </div>
          <textarea
            value={textMaterial}
            onChange={(e) => setTextMaterial(e.target.value)}
            rows={12}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white resize-none font-mono text-sm"
            placeholder="请输入内容（报告、文章、访谈稿、数据手册、故事素材等）..."
            disabled={isLoading}
          />
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            支持直接粘贴文本或上传文件（.txt、.doc、.docx、.pdf）
          </p>
        </div>

        {/* 可选指令 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            可选指令
          </label>
          <textarea
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white resize-none"
            placeholder="例如：生成3分钟播客、使用轻松风格等..."
            disabled={isLoading}
          />
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            可选：用于控制生成过程，如时长要求、风格要求等
          </p>
        </div>

        {/* 生成按钮 */}
        <button
          onClick={handleGenerate}
          disabled={isLoading || !textMaterial.trim()}
          className="w-full px-4 py-3 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isLoading ? '生成中...' : '生成播客脚本'}
        </button>

        {/* 生成的脚本显示 */}
        {generatedScript && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                生成的脚本
              </h3>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleCopyScript}
                  className="flex items-center gap-2 px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                  title="复制脚本"
                >
                  {copySuccess ? (
                    <>
                      <Check className="w-4 h-4" />
                      <span>已复制</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-4 h-4" />
                      <span>复制</span>
                    </>
                  )}
                </button>
                <button
                  onClick={handleDownloadScript}
                  className="flex items-center gap-2 px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                  title="下载脚本"
                >
                  <Download className="w-4 h-4" />
                  <span>下载</span>
                </button>
              </div>
            </div>
            <div className="border border-gray-300 dark:border-gray-600 rounded-lg p-4 bg-gray-50 dark:bg-gray-800">
              <pre className="whitespace-pre-wrap text-sm text-gray-900 dark:text-gray-100 font-mono leading-relaxed">
                {generatedScript}
              </pre>
            </div>
            <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-3">
              <p className="text-sm text-green-800 dark:text-green-400">
                ✅ 脚本生成完成！你可以复制或下载脚本，然后使用其他播客功能将其转换为音频。
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

