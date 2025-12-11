let charCount = 0;

function switchTab(tab) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  event.target.classList.add('active');
  document.getElementById('tab-' + tab).classList.add('active');
}

function addCharacter() {
  charCount++;
  const div = document.createElement('div');
  div.className = 'char-item';
  div.id = 'char-' + charCount;
  div.innerHTML = `
    <h4>角色 ${charCount}</h4>
    <label>角色名称</label>
    <input type="text" class="char-name" placeholder="角色名称" />
    <label>身份/职业（可选）</label>
    <input type="text" class="char-identity" placeholder="例如：AI研究员" />
    <label>性格特点（可选）</label>
    <input type="text" class="char-personality" placeholder="例如：严谨、理性" />
    <label>说话风格（可选）</label>
    <input type="text" class="char-style" placeholder="例如：简洁明了" />
    <label>音色文件</label>
    <input type="file" class="char-voice" accept=".wav,.mp3,.flac,.m4a" />
    <button class="btn-remove" onclick="removeCharacter('char-${charCount}')">删除角色</button>
  `;
  document.getElementById('characters-list').appendChild(div);
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
      <label>${roles[i]} 音色文件</label>
      <input type="file" class="deep-voice" data-role="${roles[i]}" accept=".wav,.mp3,.flac,.m4a" />
    `;
    container.appendChild(div);
  }
}

// 将文件转换为 base64
function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      // 移除 data:audio/...;base64, 前缀，只保留 base64 字符串
      const base64 = reader.result.split(',')[1];
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

async function generateMultiRole(event) {
  console.log('generateMultiRole 函数被调用');
  
  // 获取按钮元素
  const btn = event ? event.target : document.querySelector('#tab-multi button[onclick*="generateMultiRole"]');
  
  try {
    const text = document.getElementById('text').value.trim();
    const role1 = document.getElementById('role1').value.trim() || '角色A';
    const role2 = document.getElementById('role2').value.trim() || '角色B';
    const silence = parseInt(document.getElementById('silence').value.trim() || '800');
    const voice1 = document.getElementById('voice1').files[0];
    const voice2 = document.getElementById('voice2').files[0];
    
    console.log('输入验证:', { text: text ? '有文本' : '无文本', voice1: !!voice1, voice2: !!voice2 });
    
    if (!text) { 
      log('multi', '请输入文本'); 
      return; 
    }
    if (!voice1 || !voice2) { 
      log('multi', '请上传两个角色的音色文件'); 
      return; 
    }
    
    if (btn) {
      btn.disabled = true;
    }
    log('multi', '正在处理文件，请稍候...');
    showProgress('multi', 5);
    // 将音色文件转换为 base64
    log('multi', '正在转换音色文件...');
    const [voice1Base64, voice2Base64] = await Promise.all([
      fileToBase64(voice1),
      fileToBase64(voice2)
    ]);
    
    // 生成 job_id
    const jobId = 'job_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    
    // 构建请求体
    const requestBody = {
      text: text,
      role_voices: {
        [role1]: voice1Base64,
        [role2]: voice2Base64
      },
      silence_interval: silence,
      job_id: jobId
    };
    
    log('multi', '提交中，请稍候...');
    showProgress('multi', 10);
    
    // 发送请求（增加超时时间，因为生成可能需要较长时间）
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30秒超时（仅用于提交）
    
    let resp;
    try {
      resp = await fetch('/api/v1/podcast/multi_role', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody),
        signal: controller.signal
      });
      clearTimeout(timeoutId);
    } catch (e) {
      clearTimeout(timeoutId);
      if (e.name === 'AbortError') {
        // 提交超时，但任务可能已经在后端开始处理，尝试轮询
        log('multi', '提交请求超时，但任务可能已开始处理，正在检查进度...');
        // 继续执行轮询逻辑
      } else {
        throw new Error(`网络错误: ${e.message}`);
      }
    }
    
    // 如果请求成功，获取响应数据
    let submitData = null;
    if (resp && resp.ok) {
      submitData = await resp.json();
      if (!submitData.success) {
        throw new Error(submitData.message || '提交失败');
      }
      log('multi', '任务已提交，正在生成中...');
    } else if (resp && !resp.ok) {
      const errorText = await resp.text();
      throw new Error(`HTTP ${resp.status}: ${errorText}`);
    } else {
      // 请求超时，但继续尝试轮询
      log('multi', '正在检查任务状态...');
    }
    
    showProgress('multi', 15);
    
    // 轮询获取进度
    const pollInterval = 2000; // 2秒轮询一次
    const maxPollTime = 600000; // 最大等待10分钟
    const startTime = Date.now();
    
    const pollProgress = async () => {
      let lastProgress = 0;
      while (Date.now() - startTime < maxPollTime) {
        try {
          const progressResp = await fetch(`/api/v1/podcast/progress/${jobId}`);
          if (!progressResp.ok) {
            // 如果是 404，可能是任务还没创建，继续等待
            if (progressResp.status === 404) {
              await new Promise(resolve => setTimeout(resolve, pollInterval));
              continue;
            }
            throw new Error(`获取进度失败: HTTP ${progressResp.status}`);
          }
          
          const progressData = await progressResp.json();
          
          // 检查是否是未知状态（任务不存在）
          if (progressData.phase === 'unknown') {
            // 任务可能还没创建，继续等待
            await new Promise(resolve => setTimeout(resolve, pollInterval));
            continue;
          }
          
          // 更新进度
          if (progressData.percent !== undefined && progressData.percent !== lastProgress) {
            showProgress('multi', progressData.percent);
            lastProgress = progressData.percent;
          }
          if (progressData.message) {
            log('multi', progressData.message);
          }
          
          // 检查是否完成
          if (progressData.done) {
            if (progressData.error) {
              throw new Error(progressData.error);
            }
            
            // 任务完成，获取最终结果
            log('multi', '生成完成！正在获取音频...');
            showProgress('multi', 100);
            
            // 如果有 audio_url，直接使用
            if (progressData.audio_url) {
              const player = document.getElementById('player-multi');
              player.src = progressData.audio_url;
              player.style.display = 'block';
              player.load();
              log('multi', '音频已加载！');
              return;
            }
            
            // 如果没有 audio_url，等待一下再检查（后端可能还在处理）
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            // 再次检查进度，看是否有 audio_url
            const finalProgressResp = await fetch(`/api/v1/podcast/progress/${jobId}`);
            if (finalProgressResp.ok) {
              const finalProgressData = await finalProgressResp.json();
              if (finalProgressData.audio_url) {
                const player = document.getElementById('player-multi');
                player.src = finalProgressData.audio_url;
                player.style.display = 'block';
                player.load();
                log('multi', '音频已加载！');
                return;
              }
            }
            
            // 如果还是没有，尝试从提交响应中获取（后端可能已经返回了）
            if (submitData.data) {
              const player = document.getElementById('player-multi');
              if (submitData.data.audio_base64) {
                player.src = 'data:audio/wav;base64,' + submitData.data.audio_base64;
              } else if (submitData.data.audio_url) {
                player.src = submitData.data.audio_url;
              } else {
                throw new Error('未找到音频数据，请检查后端日志');
              }
              player.style.display = 'block';
              player.load();
              log('multi', '音频已加载！');
              return;
            }
            
            throw new Error('未找到音频数据，请检查后端是否成功生成');
          }
          
          // 等待后继续轮询
          await new Promise(resolve => setTimeout(resolve, pollInterval));
        } catch (e) {
          if (e.message.includes('获取进度失败') || e.message.includes('未找到音频数据')) {
            throw e;
          }
          // 其他错误继续轮询
          await new Promise(resolve => setTimeout(resolve, pollInterval));
        }
      }
      
      throw new Error('生成超时，请稍后重试');
    };
    
    await pollProgress();
  } catch (e) {
    log('multi', '错误：' + e.message);
    showProgress('multi', 0);
    console.error('生成播客失败:', e);
  } finally {
    // 确保按钮重新启用
    if (btn) {
      btn.disabled = false;
    }
  }
}

async function generateCharacter() {
  const text = document.getElementById('char-text').value.trim();
  const topic = document.getElementById('char-topic').value.trim();
  const silence = document.getElementById('char-silence').value.trim() || '800';
  const chars = [];
  document.querySelectorAll('.char-item').forEach(item => {
    const name = item.querySelector('.char-name').value.trim();
    const voice = item.querySelector('.char-voice').files[0];
    if (!name || !voice) return;
    chars.push({
      name,
      identity: item.querySelector('.char-identity').value.trim(),
      personality: item.querySelector('.char-personality').value.trim(),
      speaking_style: item.querySelector('.char-style').value.trim(),
      voice
    });
  });
  if (!text) { log('character', '请输入文本素材'); return; }
  if (chars.length < 2) { log('character', '至少需要2个角色'); return; }
  const fd = new FormData();
  fd.append('text', text);
  if (topic) fd.append('topic', topic);
  fd.append('silence_interval', silence);
  chars.forEach((char, i) => {
    fd.append(`char${i}_name`, char.name);
    if (char.identity) fd.append(`char${i}_identity`, char.identity);
    if (char.personality) fd.append(`char${i}_personality`, char.personality);
    if (char.speaking_style) fd.append(`char${i}_style`, char.speaking_style);
    fd.append(`char${i}_voice`, char.voice);
  });
  const btn = event.target;
  btn.disabled = true;
  log('character', '提交中，请稍候...');
  showProgress('character', 10);
  try {
    const resp = await fetch('/web/api/character', { method: 'POST', body: fd });
    const data = await resp.json();
    if (!data.success) throw new Error(data.message || '生成失败');
    log('character', '生成完成！');
    showProgress('character', 100);
    const player = document.getElementById('player-character');
    player.src = data.data.audio_url;
    player.style.display = 'block';
    player.load();
  } catch (e) {
    log('character', '错误：' + e.message);
    showProgress('character', 0);
  } finally {
    btn.disabled = false;
  }
}

async function generateDeep() {
  const topic = document.getElementById('deep-topic').value.trim();
  const numChars = parseInt(document.getElementById('deep-num-chars').value);
  const depthLevel = document.getElementById('deep-level').value;
  const silence = document.getElementById('deep-silence').value.trim() || '800';
  if (!topic) { log('deep', '请输入播客主题'); return; }
  const voices = {};
  let hasAll = true;
  document.querySelectorAll('.deep-voice').forEach(input => {
    const role = input.dataset.role;
    const file = input.files[0];
    if (!file) hasAll = false;
    else voices[role] = file;
  });
  if (!hasAll) { log('deep', '请上传所有角色的音色文件'); return; }
  const fd = new FormData();
  fd.append('topic', topic);
  fd.append('num_characters', numChars);
  fd.append('depth_level', depthLevel);
  fd.append('silence_interval', silence);
  Object.keys(voices).forEach(role => {
    fd.append(`voice_${role}`, voices[role]);
  });
  const btn = event.target;
  btn.disabled = true;
  log('deep', '提交中，请稍候...');
  showProgress('deep', 10);
  try {
    const resp = await fetch('/web/api/deep', { method: 'POST', body: fd });
    const data = await resp.json();
    if (!data.success) throw new Error(data.message || '生成失败');
    log('deep', '生成完成！');
    showProgress('deep', 100);
    const player = document.getElementById('player-deep');
    player.src = data.data.audio_url;
    player.style.display = 'block';
    player.load();
  } catch (e) {
    log('deep', '错误：' + e.message);
    showProgress('deep', 0);
  } finally {
    btn.disabled = false;
  }
}

async function analyzeText() {
  const text = document.getElementById('analyze-text').value.trim();
  if (!text) { log('analyze', '请输入文本素材'); return; }
  const btn = event.target;
  btn.disabled = true;
  log('analyze', '分析中，请稍候...');
  try {
    const resp = await fetch('/api/v1/podcast/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
    const data = await resp.json();
    if (!data.success) throw new Error(data.message || '分析失败');
    const result = data.data;
    const resultDiv = document.getElementById('analyze-result');
    resultDiv.innerHTML = `
      <h4>分析结果</h4>
      <p><strong>播客名称：</strong>${result.podcast_name || '未识别'}</p>
      <p><strong>本期主题：</strong>${result.topic || '未识别'}</p>
      <p><strong>角色设定：</strong></p>
      <ul>
        ${(result.characters || []).map(c => `<li><strong>${c.name}</strong> - ${c.personality || ''} (${c.speaking_style || ''})</li>`).join('')}
      </ul>
      <p><strong>互动场景：</strong>${(result.scene_types || []).join('、') || '未识别'}</p>
    `;
    resultDiv.style.display = 'block';
    log('analyze', '分析完成！');
  } catch (e) {
    log('analyze', '错误：' + e.message);
  } finally {
    btn.disabled = false;
  }
}

function log(tab, msg) {
  document.getElementById('log-' + tab).textContent = msg;
}

function showProgress(tab, percent) {
  const bar = document.getElementById('progress-bar-' + tab);
  const container = document.getElementById('progress-' + tab);
  if (percent > 0) {
    bar.style.width = percent + '%';
    container.style.display = 'block';
  } else {
    container.style.display = 'none';
  }
}

// 初始化：添加两个默认角色
document.addEventListener('DOMContentLoaded', function() {
  document.getElementById('deep-num-chars').onchange = updateDeepVoices;
  updateDeepVoices();
  addCharacter();
  addCharacter();
});

