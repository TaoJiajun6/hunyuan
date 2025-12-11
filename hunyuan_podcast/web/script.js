// 全局状态
let currentPage = 'create';
let currentPodcastType = 'multi';
let charCount = 0;
let currentCategory = 'all';

// 页面切换
function switchPage(page) {
  currentPage = page;
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  
  const pageElement = document.getElementById(`page-${page}`);
  if (pageElement) {
    pageElement.classList.add('active');
  }
  
  const navItem = event?.target?.closest('.nav-item');
  if (navItem) {
    navItem.classList.add('active');
  }
  
  if (page === 'explore') {
    loadHistory();
  }
}

// 播客类型切换
function switchPodcastType(type) {
  currentPodcastType = type;
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  event.target.classList.add('active');
  
  updateDynamicConfig();
  updateVoiceSelectors();
}

// 更新动态配置区域
function updateDynamicConfig() {
  const configArea = document.getElementById('dynamic-config');
  configArea.innerHTML = '';
  
  if (currentPodcastType === 'multi') {
    configArea.innerHTML = `
      <div class="config-item">
        <label>角色1 名称</label>
        <input type="text" id="role1" value="角色A" />
      </div>
      <div class="config-item">
        <label>角色2 名称</label>
        <input type="text" id="role2" value="角色B" />
      </div>
      <div class="config-row">
        <div class="config-item">
          <label>静音间隔 (毫秒)</label>
          <input type="number" id="silence" value="800" min="200" max="1500" />
        </div>
        <div class="config-item">
          <label>背景音乐</label>
          <input type="text" value="自动选择" disabled style="opacity: 0.6;" />
        </div>
      </div>
    `;
  } else if (currentPodcastType === 'character') {
    configArea.innerHTML = `
      <div class="config-item">
        <label>播客主题（可选）</label>
        <input type="text" id="char-topic" placeholder="例如：人工智能的未来" />
      </div>
      <div class="config-item">
        <label>角色配置</label>
        <div id="characters-list"></div>
        <button class="btn-secondary" onclick="addCharacter()" style="margin-top: 12px;">+ 添加角色</button>
      </div>
      <div class="config-item">
        <label>静音间隔 (毫秒)</label>
        <input type="number" id="char-silence" value="800" min="200" max="1500" />
      </div>
    `;
    // 初始化两个默认角色
    if (document.getElementById('characters-list').children.length === 0) {
      addCharacter();
      addCharacter();
    }
  } else if (currentPodcastType === 'deep') {
    configArea.innerHTML = `
      <div class="config-row">
        <div class="config-item">
          <label>角色数量</label>
          <select id="deep-num-chars" onchange="updateDeepVoices()">
            <option value="1">1个角色</option>
            <option value="2" selected>2个角色</option>
            <option value="3">3个角色</option>
          </select>
        </div>
        <div class="config-item">
          <label>深度级别</label>
          <select id="deep-level">
            <option value="浅层">浅层</option>
            <option value="中等">中等</option>
            <option value="深度" selected>深度</option>
          </select>
        </div>
      </div>
      <div class="config-item">
        <label>角色音色</label>
        <div id="deep-voices"></div>
      </div>
      <div class="config-item">
        <label>静音间隔 (毫秒)</label>
        <input type="number" id="deep-silence" value="800" min="200" max="1500" />
      </div>
    `;
    updateDeepVoices();
  }
}

// 更新音色选择器
function updateVoiceSelectors() {
  const voiceSelectors = document.getElementById('voice-selectors');
  let numVoices = 2;
  
  if (currentPodcastType === 'multi') {
    numVoices = 2;
  } else if (currentPodcastType === 'character') {
    numVoices = 2; // 默认2个，可以添加更多
  } else if (currentPodcastType === 'deep') {
    numVoices = parseInt(document.getElementById('deep-num-chars')?.value || '2');
  }
  
  voiceSelectors.innerHTML = '';
  for (let i = 1; i <= numVoices; i++) {
    const selector = document.createElement('div');
    selector.className = 'voice-selector';
    selector.innerHTML = `
      <select id="voice${i}" class="select-input" onchange="updateVoiceSelection(${i}, event)">
        <option value="">请选择音色</option>
        ${VOICE_OPTIONS.map(voice => 
          `<option value="${voice.id}">${voice.name}${voice.description ? ' - ' + voice.description : ''}</option>`
        ).join('')}
      </select>
    `;
    voiceSelectors.appendChild(selector);
  }
}

function updateVoiceSelection(index, event) {
  const voiceId = event.target.value;
  if (voiceId) {
    const voice = getVoiceById(voiceId);
    if (voice) {
      event.target.style.color = 'var(--text-primary)';
    }
  } else {
    event.target.style.color = 'var(--text-secondary)';
  }
}

// 文件上传处理
function handleFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;
  
  const reader = new FileReader();
  reader.onload = function(e) {
    if (file.type === 'text/plain' || file.name.endsWith('.txt')) {
      document.getElementById('podcast-input').value = e.target.result;
    } else {
      log('create', '暂不支持此文件类型，请上传 .txt 文件');
    }
  };
  reader.readAsText(file);
}

// 添加角色
function addCharacter() {
  charCount++;
  const list = document.getElementById('characters-list');
  const div = document.createElement('div');
  div.className = 'char-item';
  div.id = `char-${charCount}`;
  div.innerHTML = `
    <h4>角色 ${charCount}</h4>
    <div class="config-row">
      <div class="config-item">
        <label>角色名称</label>
        <input type="text" class="char-name" placeholder="角色名称" />
      </div>
      <div class="config-item">
        <label>身份/职业（可选）</label>
        <input type="text" class="char-identity" placeholder="例如：AI研究员" />
      </div>
    </div>
    <div class="config-row">
      <div class="config-item">
        <label>性格特点（可选）</label>
        <input type="text" class="char-personality" placeholder="例如：严谨、理性" />
      </div>
      <div class="config-item">
        <label>说话风格（可选）</label>
        <input type="text" class="char-style" placeholder="例如：简洁明了" />
      </div>
    </div>
    <div class="config-item">
      <label>音色</label>
      <select class="char-voice select-input">
        <option value="">请选择音色</option>
        ${VOICE_OPTIONS.map(voice => 
          `<option value="${voice.id}">${voice.name}${voice.description ? ' - ' + voice.description : ''}</option>`
        ).join('')}
      </select>
    </div>
    <button class="btn-secondary" onclick="removeCharacter('char-${charCount}')" style="margin-top: 12px;">删除角色</button>
  `;
  list.appendChild(div);
}

function removeCharacter(id) {
  document.getElementById(id).remove();
}

function updateDeepVoices() {
  const num = parseInt(document.getElementById('deep-num-chars').value);
  const container = document.getElementById('deep-voices');
  container.innerHTML = '';
  const roles = ['角色A', '角色B', '角色C'];
  for (let i = 0; i < num; i++) {
    const div = document.createElement('div');
    div.style.marginBottom = '12px';
    div.innerHTML = `
      <label>${roles[i]} 音色</label>
      <select class="deep-voice select-input" data-role="${roles[i]}">
        <option value="">请选择音色</option>
        ${VOICE_OPTIONS.map(voice => 
          `<option value="${voice.id}">${voice.name}${voice.description ? ' - ' + voice.description : ''}</option>`
        ).join('')}
      </select>
    `;
    container.appendChild(div);
  }
  updateVoiceSelectors();
}

// 将文件转换为 base64
function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const base64 = reader.result.split(',')[1];
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

// 上传音色文件到云存储，返回URL
async function uploadVoiceFile(base64Data) {
  try {
    const resp = await fetch('/api/v1/podcast/upload_voice', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ base64_data: base64Data })
    });
    
    if (!resp.ok) {
      const error = await resp.json();
      throw new Error(error.message || '上传失败');
    }
    
    const result = await resp.json();
    if (result.success && result.data && result.data.url) {
      return result.data.url;
    } else {
      throw new Error(result.message || '上传失败');
    }
  } catch (e) {
    console.error('上传音色文件失败:', e);
    throw e;
  }
}

// 生成播客（统一入口）
async function generatePodcast(event) {
  const btn = event.target;
  btn.disabled = true;
  
  try {
    if (currentPodcastType === 'multi') {
      await generateMultiRole();
    } else if (currentPodcastType === 'character') {
      await generateCharacter();
    } else if (currentPodcastType === 'deep') {
      await generateDeep();
    }
  } finally {
    btn.disabled = false;
  }
}

// 多角色播客生成
async function generateMultiRole() {
  const text = document.getElementById('podcast-input').value.trim();
  const role1 = document.getElementById('role1').value.trim() || '角色A';
  const role2 = document.getElementById('role2').value.trim() || '角色B';
  const silence = parseInt(document.getElementById('silence').value || '800');
  const voice1Id = document.getElementById('voice1')?.value;
  const voice2Id = document.getElementById('voice2')?.value;
  
  if (!text) {
    log('create', '请输入文本');
    return;
  }
  if (!voice1Id || !voice2Id) {
    log('create', '请为两个角色选择音色');
    return;
  }
  
  log('create', '正在上传音色文件，请稍候...');
  showProgress(5);
  
  try {
    // 先上传音色文件到云存储，获取URL
    const [voice1Base64, voice2Base64] = await Promise.all([
      loadVoiceFileAsBase64(voice1Id),
      loadVoiceFileAsBase64(voice2Id)
    ]);
    
    log('create', '正在上传音色文件到云存储...');
    showProgress(8);
    
    const [voice1Url, voice2Url] = await Promise.all([
      uploadVoiceFile(voice1Base64),
      uploadVoiceFile(voice2Base64)
    ]);
    
    const jobId = 'job_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    
    const requestBody = {
      text: text,
      role_voice_urls: {
        [role1]: voice1Url,
        [role2]: voice2Url
      },
      silence_interval: silence,
      job_id: jobId
    };
    
    log('create', '提交中，请稍候...');
    showProgress(10);
    
    await submitAndPoll(jobId, requestBody, '/api/v1/podcast/multi_role');
  } catch (e) {
    log('create', '错误：' + e.message);
    showProgress(0);
    console.error('生成播客失败:', e);
  }
}

// 自定义角色播客生成
async function generateCharacter() {
  const text = document.getElementById('podcast-input').value.trim();
  const topic = document.getElementById('char-topic')?.value.trim();
  const silence = parseInt(document.getElementById('char-silence')?.value || '800');
  const chars = [];
  
  document.querySelectorAll('.char-item').forEach(item => {
    const name = item.querySelector('.char-name').value.trim();
    const voiceId = item.querySelector('.char-voice').value;
    if (!name || !voiceId) return;
    chars.push({
      name,
      identity: item.querySelector('.char-identity').value.trim(),
      personality: item.querySelector('.char-personality').value.trim(),
      speaking_style: item.querySelector('.char-style').value.trim(),
      voiceId
    });
  });
  
  if (!text) {
    log('create', '请输入文本素材');
    return;
  }
  if (chars.length < 2) {
    log('create', '至少需要2个角色');
    return;
  }
  
  log('create', '正在上传音色文件，请稍候...');
  showProgress(5);
  
  try {
    // 先加载并上传所有音色文件
    const voiceBase64List = await Promise.all(
      chars.map(char => loadVoiceFileAsBase64(char.voiceId))
    );
    
    log('create', '正在上传音色文件到云存储...');
    showProgress(8);
    
    const voiceUrlList = await Promise.all(
      voiceBase64List.map(base64 => uploadVoiceFile(base64))
    );
    
    // 构建characters数组，使用voice_url而不是voice
    const characters = chars.map((char, index) => ({
        name: char.name,
        identity: char.identity || undefined,
        personality: char.personality || undefined,
        speaking_style: char.speaking_style || undefined,
      voice_url: voiceUrlList[index]
    }));
    
    const jobId = 'job_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    
    const requestBody = {
      text: text,
      characters: characters,
      silence_interval: silence,
      job_id: jobId
    };
    
    if (topic) {
      requestBody.topic = topic;
    }
    
    log('create', '提交中，请稍候...');
    showProgress(10);
    
    await submitAndPoll(jobId, requestBody, '/api/v1/podcast/character');
  } catch (e) {
    log('create', '错误：' + e.message);
    showProgress(0);
    console.error('生成播客失败:', e);
  }
}

// 主题深度播客生成
async function generateDeep() {
  const topic = document.getElementById('podcast-input').value.trim();
  if (!topic) {
    log('create', '请输入播客主题');
    return;
  }
  
  const numChars = parseInt(document.getElementById('deep-num-chars').value);
  const depthLevel = document.getElementById('deep-level').value;
  const silence = parseInt(document.getElementById('deep-silence').value || '800');
  
  const voices = {};
  let hasAll = true;
  document.querySelectorAll('.deep-voice').forEach(select => {
    const role = select.dataset.role;
    const voiceId = select.value;
    if (!voiceId) hasAll = false;
    else voices[role] = voiceId;
  });
  
  if (!hasAll) {
    log('create', '请为所有角色选择音色');
    return;
  }
  
  log('create', '正在上传音色文件，请稍候...');
  showProgress(5);
  
  try {
    // 先加载所有音色文件
    const voiceBase64Map = {};
    await Promise.all(Object.keys(voices).map(async (role) => {
      voiceBase64Map[role] = await loadVoiceFileAsBase64(voices[role]);
    }));
    
    log('create', '正在上传音色文件到云存储...');
    showProgress(8);
    
    // 上传所有音色文件，获取URL
    const roleVoiceUrls = {};
    await Promise.all(Object.keys(voiceBase64Map).map(async (role) => {
      roleVoiceUrls[role] = await uploadVoiceFile(voiceBase64Map[role]);
    }));
    
    const jobId = 'job_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    
    const requestBody = {
      topic: topic,
      role_voice_urls: roleVoiceUrls,
      num_characters: numChars,
      depth_level: depthLevel,
      silence_interval: silence,
      job_id: jobId
    };
    
    log('create', '提交中，请稍候...');
    showProgress(10);
    
    await submitAndPoll(jobId, requestBody, '/api/v1/podcast/deep');
  } catch (e) {
    log('create', '错误：' + e.message);
    showProgress(0);
    console.error('生成播客失败:', e);
  }
}

// 提交并轮询进度
async function submitAndPoll(jobId, requestBody, endpoint) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 10000);
  
  let resp;
  try {
    resp = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody),
      signal: controller.signal
    });
    clearTimeout(timeoutId);
  } catch (e) {
    clearTimeout(timeoutId);
    if (e.name === 'AbortError') {
      log('create', '提交请求超时，但任务可能已开始处理，正在检查进度...');
    } else {
      throw new Error(`网络错误: ${e.message}`);
    }
  }
  
  let submitData = null;
  if (resp && resp.ok) {
    submitData = await resp.json();
    if (!submitData.success) {
      throw new Error(submitData.message || '提交失败');
    }
    log('create', '任务已提交，正在生成中...');
  } else if (resp && !resp.ok) {
    const errorText = await resp.text();
    throw new Error(`HTTP ${resp.status}: ${errorText}`);
  }
  
  showProgress(15);
  
  // 轮询进度
  const pollInterval = 2000;
  const maxPollTime = 600000;
  const startTime = Date.now();
  let lastProgress = 0;
  
  while (Date.now() - startTime < maxPollTime) {
    try {
      const progressResp = await fetch(`/api/v1/podcast/progress/${jobId}`);
      if (!progressResp.ok) {
        if (progressResp.status === 404) {
          await new Promise(resolve => setTimeout(resolve, pollInterval));
          continue;
        }
        throw new Error(`获取进度失败: HTTP ${progressResp.status}`);
      }
      
      const progressData = await progressResp.json();
      
      if (progressData.phase === 'unknown') {
        await new Promise(resolve => setTimeout(resolve, pollInterval));
        continue;
      }
      
      if (progressData.percent !== undefined && progressData.percent !== lastProgress) {
        showProgress(progressData.percent);
        lastProgress = progressData.percent;
      }
      if (progressData.message) {
        log('create', progressData.message);
      }
      
      if (progressData.done) {
        if (progressData.error) {
          throw new Error(progressData.error);
        }
        
        log('create', '生成完成！正在获取音频...');
        showProgress(100);
        
        if (progressData.audio_url) {
          loadAudio(progressData.audio_url);
          return;
        }
        
        // 重试获取 audio_url
        for (let retry = 0; retry < 10; retry++) {
          await new Promise(resolve => setTimeout(resolve, 2000));
          const finalProgressResp = await fetch(`/api/v1/podcast/progress/${jobId}`);
          if (finalProgressResp.ok) {
            const finalProgressData = await finalProgressResp.json();
            if (finalProgressData.audio_url) {
              loadAudio(finalProgressData.audio_url);
              return;
            }
          }
        }
        
        // 尝试从提交响应获取
        if (submitData?.data) {
          if (submitData.data.audio_base64) {
            loadAudio('data:audio/wav;base64,' + submitData.data.audio_base64);
            return;
          } else if (submitData.data.audio_url) {
            loadAudio(submitData.data.audio_url);
            return;
          }
        }
        
        throw new Error('未找到音频数据');
      }
      
      await new Promise(resolve => setTimeout(resolve, pollInterval));
    } catch (e) {
      if (e.message.includes('获取进度失败') || e.message.includes('未找到音频数据')) {
        throw e;
      }
      await new Promise(resolve => setTimeout(resolve, pollInterval));
    }
  }
  
  throw new Error('生成超时，请稍后重试');
}

// 加载音频
function loadAudio(url) {
  const player = document.getElementById('audio-player');
  console.log('设置音频源:', url);
  player.src = url;
  player.style.display = 'block';
  
  player.onerror = function(e) {
    console.error('音频加载失败:', e);
    log('create', '音频加载失败，请检查 URL 是否正确');
  };
  
  player.onloadeddata = function() {
    console.log('音频数据已加载');
    log('create', '音频已加载！');
  };
  
  player.load();
}

// 日志和进度
function log(page, msg) {
  const logArea = document.getElementById('log-area');
  if (logArea) {
    logArea.textContent = msg;
  }
}

function showProgress(percent) {
  const bar = document.getElementById('progress-bar');
  const container = document.getElementById('progress-area');
  if (percent > 0) {
    bar.style.width = percent + '%';
    container.style.display = 'block';
  } else {
    container.style.display = 'none';
  }
}

// 加载历史播客
async function loadHistory() {
  const listElement = document.getElementById('explore-list');
  if (!listElement) return;
  
  listElement.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--text-secondary);">加载中...</div>';
  
  try {
    const resp = await fetch(`/api/v1/podcast/history?limit=50${currentCategory !== 'all' ? '&category=' + currentCategory : ''}`);
    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`);
    }
    
    const data = await resp.json();
    if (!data.success) {
      throw new Error(data.message || '获取历史播客失败');
    }
    
    const podcasts = data.data.podcasts || [];
    
    if (podcasts.length === 0) {
      listElement.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--text-secondary);">暂无历史播客</div>';
      return;
    }
    
    listElement.innerHTML = '';
    podcasts.forEach(podcast => {
      const card = createPodcastCard(podcast);
      listElement.appendChild(card);
    });
  } catch (e) {
    console.error('加载历史播客失败:', e);
    listElement.innerHTML = `<div style="text-align: center; padding: 40px; color: var(--text-muted);">加载失败: ${e.message}</div>`;
  }
}

// 创建播客卡片
function createPodcastCard(podcast) {
  const card = document.createElement('div');
  card.className = 'podcast-card';
  
  // 处理时间：created_at可能是秒级或毫秒级时间戳
  let created_at = podcast.created_at;
  if (created_at) {
    // 如果是毫秒级时间戳（大于10位数），需要转换为秒
    if (created_at > 10000000000) {
      created_at = Math.floor(created_at / 1000);
    }
    const date = new Date(created_at * 1000);
    var dateStr = date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    }) + ' ' + date.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit'
    });
  } else {
    var dateStr = '未知';
  }
  
  // 格式化时长（如果有）
  let durationStr = '未知';
  if (podcast.duration) {
    // duration是秒数
    const totalSeconds = parseInt(podcast.duration);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    if (minutes > 0) {
      durationStr = seconds > 0 ? `${minutes}分${seconds}秒` : `${minutes}分钟`;
    } else {
      durationStr = `${seconds}秒`;
    }
  } else if (podcast.file_size_mb) {
    // 根据文件大小估算时长（粗略估算：1MB ≈ 1分钟）
    const estimatedMinutes = Math.round(podcast.file_size_mb);
    durationStr = `${estimatedMinutes} 分钟（估算）`;
  }
  
  // 获取内容预览
  const content = podcast.content || podcast.script || '';
  const contentPreview = content.length > 100 ? content.substring(0, 100) + '...' : content;
  
  card.innerHTML = `
    <div class="podcast-thumbnail"></div>
    <div class="podcast-card-content">
      <div class="podcast-title">${podcast.title || '未命名播客'}</div>
      <div class="podcast-author">${dateStr}</div>
      ${contentPreview ? `<div style="font-size: 13px; color: var(--text-muted); margin: 8px 0; line-height: 1.4;">${contentPreview}</div>` : ''}
      <div class="podcast-meta">
        <div class="podcast-meta-item">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 1 L7 7 L11 9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            <circle cx="7" cy="7" r="6" stroke="currentColor" stroke-width="1.5" fill="none"/>
          </svg>
          <span>${durationStr}</span>
        </div>
      </div>
      <div class="podcast-actions">
        <button class="play-btn" onclick="playPodcast('${podcast.audio_url || ''}', '${podcast.id}', event)" title="${podcast.audio_url ? '播放' : '暂无音频'}" ${!podcast.audio_url ? 'disabled style="opacity: 0.5; cursor: not-allowed;"' : ''}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M6 4 L12 8 L6 12 Z"/>
          </svg>
        </button>
        <button class="delete-btn" onclick="deletePodcast('${podcast.id}', event)" title="删除">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M4 4 L12 12 M12 4 L4 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </button>
      </div>
    </div>
  `;
  
  return card;
}

// 播放播客
function playPodcast(audioUrl, podcastId, event) {
  event.stopPropagation();
  
  if (!audioUrl || audioUrl === 'null' || audioUrl === 'undefined' || audioUrl.trim() === '') {
    alert('该播客暂无音频文件');
    return;
  }
  
  // 可以打开一个播放器或者直接播放
  const player = document.getElementById('audio-player');
  if (player) {
    // 检测是否是云存储URL（需要代理）
    let finalUrl = audioUrl;
    if (audioUrl.includes('agcstorage.link') || audioUrl.includes('ops-server')) {
      // 使用代理接口
      finalUrl = `/api/v1/podcast/proxy_audio?url=${encodeURIComponent(audioUrl)}`;
      console.log('检测到云存储URL，使用代理接口:', finalUrl);
    }
    
    console.log('播放播客:', podcastId, '原始URL:', audioUrl, '最终URL:', finalUrl);
    player.src = finalUrl;
    player.style.display = 'block';
    
    // 添加错误处理
    player.onerror = function(e) {
      console.error('音频播放失败:', e);
      console.error('失败的URL:', finalUrl);
      alert('音频加载失败，请检查URL是否正确或网络连接');
      player.style.display = 'none';
    };
    
    // 添加加载成功处理
    player.onloadeddata = function() {
      console.log('音频加载成功，开始播放');
      player.play().catch(err => {
        console.error('播放失败:', err);
        alert('播放失败: ' + err.message);
      });
    };
    
    // 尝试播放
    player.load();
  } else {
    alert('找不到音频播放器');
  }
}

// 删除播客
async function deletePodcast(podcastId, event) {
  event.stopPropagation();
  
  // 确认删除
  if (!confirm('确定要删除这个播客吗？此操作不可恢复。')) {
    return;
  }
  
  try {
    const resp = await fetch(`/api/v1/podcast/${podcastId}`, {
      method: 'DELETE'
    });
    
    if (!resp.ok) {
      const errorData = await resp.json();
      throw new Error(errorData.detail || `HTTP ${resp.status}`);
    }
    
    const data = await resp.json();
    if (data.success) {
      // 从页面中移除该卡片
      const card = event.target.closest('.podcast-card');
      if (card) {
        card.style.opacity = '0.5';
        card.style.transition = 'opacity 0.3s';
        setTimeout(() => {
          card.remove();
          // 重新加载列表
          loadHistory();
        }, 300);
      }
      alert('播客已删除');
    } else {
      throw new Error(data.message || '删除失败');
    }
  } catch (e) {
    console.error('删除播客失败:', e);
    alert('删除失败: ' + e.message);
  }
}

// 分类筛选
function filterByCategory(category) {
  currentCategory = category;
  document.querySelectorAll('.category-btn').forEach(btn => btn.classList.remove('active'));
  event.target.classList.add('active');
  loadHistory();
}

// 初始化
document.addEventListener('DOMContentLoaded', function() {
  updateDynamicConfig();
  updateVoiceSelectors();
  
  // 如果当前在探索页面，加载数据
  if (currentPage === 'explore') {
    loadHistory();
  }
});
