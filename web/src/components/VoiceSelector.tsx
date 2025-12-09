import { useState, useEffect } from 'react';
import { Music, Play, Check } from 'lucide-react';
import { VoiceOption, getVoiceFileUrl, VOICE_OPTIONS } from '../config/voices';
import { podcastService } from '../services/PodcastService';

interface VoiceSelectorProps {
  roleName: string;
  selectedVoiceUrl?: string; // base64数据或音色ID
  selectedVoiceId?: string; // 选中的音色ID（用于显示）
  onSelect: (voiceBase64: string, voiceId: string) => void; // 同时返回base64和ID
  disabled?: boolean;
}

export default function VoiceSelector({
  roleName,
  selectedVoiceUrl,
  selectedVoiceId,
  onSelect,
  disabled = false,
}: VoiceSelectorProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [playingId, setPlayingId] = useState<string | null>(null);
  const [audioElement, setAudioElement] = useState<HTMLAudioElement | null>(null);

  // 找到当前选中的音色（优先使用selectedVoiceId，如果没有则尝试从base64推断）
  const selectedVoice = selectedVoiceId 
    ? VOICE_OPTIONS.find((voice) => voice.id === selectedVoiceId)
    : selectedVoiceUrl 
      ? VOICE_OPTIONS[0] // 如果没有ID，暂时显示第一个（兼容旧数据）
      : undefined;

  const handleSelectVoice = async (voice: VoiceOption) => {
    if (disabled || isLoading) return;

    setIsLoading(true);
    try {
      // 获取音色文件的完整路径（从public目录）
      const voiceFileUrl = getVoiceFileUrl(voice);
      
      // 从public目录读取文件并转换为base64
      const response = await fetch(voiceFileUrl);
      if (!response.ok) {
        throw new Error(`无法加载音色文件: ${voiceFileUrl}`);
      }

      const blob = await response.blob();
      
      // 转换为base64
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64String = reader.result as string;
        // 移除data URI前缀（如果有）
        const base64 = base64String.includes(',') 
          ? base64String.split(',')[1] 
          : base64String;
        // 同时传递base64数据和音色ID
        onSelect(base64, voice.id);
        setIsLoading(false);
      };
      reader.onerror = () => {
        throw new Error('读取音色文件失败');
      };
      reader.readAsDataURL(blob);
    } catch (error) {
      console.error('选择音色失败:', error);
      alert(`选择音色失败: ${error instanceof Error ? error.message : '请重试'}`);
      setIsLoading(false);
    }
  };

  const handlePreview = (voice: VoiceOption) => {
    if (playingId === voice.id) {
      // 停止播放
      if (audioElement) {
        audioElement.pause();
        audioElement.currentTime = 0;
        setAudioElement(null);
      }
      setPlayingId(null);
    } else {
      // 播放新音色
      if (audioElement) {
        audioElement.pause();
      }

      const audio = new Audio(getVoiceFileUrl(voice));
      audio.play().catch((error) => {
        console.error('播放失败:', error);
      });

      audio.addEventListener('ended', () => {
        setPlayingId(null);
        setAudioElement(null);
      });

      setAudioElement(audio);
      setPlayingId(voice.id);
    }
  };

  useEffect(() => {
    // 组件卸载时清理音频
    return () => {
      if (audioElement) {
        audioElement.pause();
        audioElement.currentTime = 0;
      }
    };
  }, [audioElement]);

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{roleName}</span>
        {selectedVoice && (
          <span className="text-xs px-2 py-0.5 bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded">
            已选择: {selectedVoice.name}
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 gap-2">
        {VOICE_OPTIONS.map((voice) => {
          const isSelected = selectedVoice?.id === voice.id;
          const isPlaying = playingId === voice.id;

          return (
            <div
              key={voice.id}
              className={`flex items-center gap-3 p-3 border rounded-lg transition-all relative ${
                isSelected
                  ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                  : 'border-gray-200 dark:border-gray-700 hover:border-primary-300 dark:hover:border-primary-600'
              } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
              onClick={() => !disabled && handleSelectVoice(voice)}
              style={{ pointerEvents: disabled ? 'none' : 'auto' }}
            >
              <div className="flex-shrink-0 w-10 h-10 bg-primary-100 dark:bg-primary-900/30 rounded-lg flex items-center justify-center pointer-events-none">
                <Music className="w-5 h-5 text-primary-600 dark:text-primary-400" />
              </div>

              <div className="flex-1 min-w-0 pointer-events-none">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-900 dark:text-white">
                    {voice.name}
                  </span>
                  {voice.style && (
                    <span className="text-xs px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded">
                      {voice.style}
                    </span>
                  )}
                </div>
                {voice.description && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    {voice.description}
                  </p>
                )}
              </div>

              <div className="flex items-center gap-2" style={{ pointerEvents: 'auto' }}>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (!disabled) {
                      handlePreview(voice);
                    }
                  }}
                  disabled={disabled}
                  className={`p-1.5 rounded-lg transition-colors ${
                    isPlaying
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'
                  } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                >
                  <Play className="w-4 h-4" />
                </button>

                {isSelected && (
                  <div className="w-5 h-5 bg-primary-600 rounded-full flex items-center justify-center pointer-events-none">
                    <Check className="w-3 h-3 text-white" />
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {isLoading && (
        <div className="text-xs text-gray-500 dark:text-gray-400 text-center py-2">
          正在加载音色文件...
        </div>
      )}
    </div>
  );
}

