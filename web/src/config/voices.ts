/**
 * 音色配置文件
 * 定义可用的音色列表
 */

export interface VoiceOption {
  id: string;
  name: string;
  description?: string;
  file: string; // 相对于 public/voices 的路径
  gender?: 'male' | 'female' | 'neutral';
  style?: string; // 风格描述，如：温柔、活泼、沉稳等
}

/**
 * 预设音色列表
 * 音色文件应放在 public/voices/ 目录下
 */
export const VOICE_OPTIONS: VoiceOption[] = [
  {
    id: 'voice_male_01',
    name: '男声-沉稳',
    description: '沉稳大气的男声',
    file: 'male_01.wav',
    gender: 'male',
    style: '沉稳',
  },
  {
    id: 'voice_male_02',
    name: '男声-活泼',
    description: '活泼开朗的男声',
    file: 'male_02.wav',
    gender: 'male',
    style: '活泼',
  },
  {
    id: 'voice_female_01',
    name: '女声-温柔',
    description: '温柔甜美的女声',
    file: 'female_01.wav',
    gender: 'female',
    style: '温柔',
  },
  {
    id: 'voice_female_02',
    name: '女声-知性',
    description: '知性优雅的女声',
    file: 'female_02.wav',
    gender: 'female',
    style: '知性',
  },
  {
    id: 'voice_neutral_01',
    name: '中性-自然',
    description: '自然流畅的中性声音',
    file: 'neutral_01.wav',
    gender: 'neutral',
    style: '自然',
  },
];

/**
 * 根据ID获取音色选项
 */
export function getVoiceById(id: string): VoiceOption | undefined {
  return VOICE_OPTIONS.find((voice) => voice.id === id);
}

/**
 * 根据性别筛选音色
 */
export function getVoicesByGender(gender?: 'male' | 'female' | 'neutral'): VoiceOption[] {
  if (!gender) return VOICE_OPTIONS;
  return VOICE_OPTIONS.filter((voice) => voice.gender === gender);
}

/**
 * 获取音色文件的完整URL
 */
export function getVoiceFileUrl(voice: VoiceOption): string {
  return `/voices/${voice.file}`;
}

