/**
 * 预设音色配置
 * 音色文件路径相对于 web/public/voices/ 目录
 */
const VOICE_OPTIONS = [
  {
    id: 'voice_male_01',
    name: '男声-沉稳',
    description: '沉稳大气的男声',
    file: '/voices/male_01.wav',
    gender: 'male',
    style: '沉稳',
  },
  {
    id: 'voice_male_02',
    name: '男声-活泼',
    description: '活泼开朗的男声',
    file: '/voices/male_02.wav',
    gender: 'male',
    style: '活泼',
  },
  {
    id: 'voice_female_01',
    name: '女声-温柔',
    description: '温柔甜美的女声',
    file: '/voices/female_01.wav',
    gender: 'female',
    style: '温柔',
  },
  {
    id: 'voice_female_02',
    name: '女声-知性',
    description: '知性优雅的女声',
    file: '/voices/female_02.wav',
    gender: 'female',
    style: '知性',
  },
  {
    id: 'voice_neutral_01',
    name: '中性-自然',
    description: '自然流畅的中性声音',
    file: '/voices/neutral_01.wav',
    gender: 'neutral',
    style: '自然',
  },
];

/**
 * 根据ID获取音色选项
 */
function getVoiceById(id) {
  return VOICE_OPTIONS.find((voice) => voice.id === id);
}

/**
 * 从URL加载音色文件并转换为base64
 */
async function loadVoiceFileAsBase64(voiceId) {
  const voice = getVoiceById(voiceId);
  if (!voice) {
    throw new Error(`音色 ${voiceId} 不存在`);
  }
  
  try {
    const response = await fetch(voice.file);
    if (!response.ok) {
      throw new Error(`无法加载音色文件: ${voice.file}`);
    }
    
    const blob = await response.blob();
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64String = reader.result;
        // 移除data URI前缀
        const base64 = base64String.includes(',') 
          ? base64String.split(',')[1] 
          : base64String;
        resolve(base64);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  } catch (error) {
    console.error('加载音色文件失败:', error);
    throw error;
  }
}

