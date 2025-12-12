/**
 * 音色配置（从API动态加载）
 */
let VOICE_OPTIONS = [];
let VOICES_LOADED = false;

/**
 * 从API获取音色列表
 */
async function loadVoicesFromAPI() {
  if (VOICES_LOADED) {
    return VOICE_OPTIONS;
  }
  
  try {
    const apiBaseUrl = window.API_BASE_URL || 'http://localhost:8000';
    const response = await fetch(`${apiBaseUrl}/api/v1/podcast/voices`);
    
    if (!response.ok) {
      throw new Error(`获取音色列表失败: HTTP ${response.status}`);
    }
    
    const result = await response.json();
    
    if (result.success && result.data && result.data.voices) {
      // 转换API返回的格式为前端需要的格式
      VOICE_OPTIONS = result.data.voices.map(voice => ({
        id: voice.id,
        name: voice.name,
        description: voice.description,
        file: voice.url || voice.cloud_path, // 使用云存储URL
        url: voice.url, // 保存完整URL
        cloud_path: voice.cloud_path,
        gender: voice.gender,
        style: voice.style,
      }));
      
      VOICES_LOADED = true;
      console.log(`✓ 从API加载了 ${VOICE_OPTIONS.length} 个音色文件`);
      return VOICE_OPTIONS;
    } else {
      console.warn('API返回的音色列表为空，使用默认音色');
      // 如果API返回空列表，使用默认音色（向后兼容）
      return getDefaultVoices();
    }
  } catch (error) {
    console.error('从API加载音色列表失败:', error);
    console.warn('使用默认音色配置');
    // 如果API调用失败，使用默认音色（向后兼容）
    return getDefaultVoices();
  }
}

/**
 * 获取默认音色配置（向后兼容）
 */
function getDefaultVoices() {
  return [
    {
      id: 'voice_male_01',
      name: '男声-沉稳',
      description: '沉稳大气的男声',
      file: '/voices/male_01.wav',
      gender: 'male',
      style: '沉稳',
    },
    {
      id: 'voice_female_01',
      name: '女声-温柔',
      description: '温柔甜美的女声',
      file: '/voices/female_01.wav',
      gender: 'female',
      style: '温柔',
    },
  ];
}

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
    // 优先使用云存储URL，如果没有则使用file字段
    const voiceUrl = voice.url || voice.file;
    
    // 如果是云存储URL（包含agcstorage.link），需要通过代理接口
    let fetchUrl = voiceUrl;
    if (voiceUrl && (voiceUrl.includes('agcstorage.link') || voiceUrl.includes('ops-server'))) {
      // 使用代理接口下载云存储文件
      const apiBaseUrl = window.API_BASE_URL || 'http://localhost:8000';
      fetchUrl = `${apiBaseUrl}/api/v1/podcast/proxy_audio?url=${encodeURIComponent(voiceUrl)}`;
    }
    
    const response = await fetch(fetchUrl);
    if (!response.ok) {
      throw new Error(`无法加载音色文件: ${voiceUrl}`);
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

