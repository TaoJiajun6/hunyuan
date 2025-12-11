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

async function generateMultiRole() {
  const text = document.getElementById('text').value.trim();
  const role1 = document.getElementById('role1').value.trim() || '角色A';
  const role2 = document.getElementById('role2').value.trim() || '角色B';
  const silence = document.getElementById('silence').value.trim() || '800';
  const voice1 = document.getElementById('voice1').files[0];
  const voice2 = document.getElementById('voice2').files[0];
  const bg = document.getElementById('bg').files[0];
  if (!text) { log('multi', '请输入文本'); return; }
  if (!voice1 || !voice2) { log('multi', '请上传两个角色的音色文件'); return; }
  const fd = new FormData();
  fd.append('text', text);
  fd.append('role1', role1);
  fd.append('role2', role2);
  fd.append('silence_interval', silence);
  fd.append('voice1', voice1);
  fd.append('voice2', voice2);
  if (bg) fd.append('background', bg);
  const btn = event.target;
  btn.disabled = true;
  log('multi', '提交中，请稍候...');
  showProgress('multi', 10);
  try {
    const resp = await fetch('/web/api/generate', { method: 'POST', body: fd });
    const data = await resp.json();
    if (!data.success) throw new Error(data.message || '生成失败');
    log('multi', '生成完成！');
    showProgress('multi', 100);
    const player = document.getElementById('player-multi');
    player.src = data.data.audio_url;
    player.style.display = 'block';
    player.load();
  } catch (e) {
    log('multi', '错误：' + e.message);
    showProgress('multi', 0);
  } finally {
    btn.disabled = false;
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

