const API = '/api/v1';
let selectedFile = null;
let knownBrandId = null;
let toastTimer;

const $ = (selector) => document.querySelector(selector);
function toast(message) {
  const el = $('#toast'); el.textContent = message; el.classList.add('show');
  clearTimeout(toastTimer); toastTimer = setTimeout(() => el.classList.remove('show'), 3200);
}
async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, options);
  let data = {};
  try { data = await response.json(); } catch {}
  if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
  return data;
}
function esc(value = '') {
  return String(value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
}
function setMode(mode) {
  document.querySelectorAll('.mode').forEach(button => button.classList.toggle('active', button.dataset.mode === mode));
  $('#recording-pane').classList.toggle('hidden', mode !== 'recording');
  $('#topic-pane').classList.toggle('hidden', mode !== 'topic');
}
document.querySelectorAll('.mode').forEach(button => button.addEventListener('click', () => setMode(button.dataset.mode)));
document.querySelectorAll('.chip').forEach(button => button.addEventListener('click', () => { $('#topic-input').value = button.dataset.topic; $('#topic-input').focus(); }));
$('#docs-link').addEventListener('click', () => window.open('/docs', '_blank'));

const fileInput = $('#video-file');
fileInput.addEventListener('change', () => {
  selectedFile = fileInput.files[0] || null;
  $('#file-label').textContent = selectedFile ? selectedFile.name : 'Drop a class recording here';
  $('#file-picked').textContent = selectedFile ? `${(selectedFile.size / 1024 / 1024).toFixed(1)} MB · ready to upload` : '';
});
const drop = $('#dropzone');
drop.addEventListener('dragover', event => { event.preventDefault(); drop.classList.add('dragover'); });
drop.addEventListener('dragleave', () => drop.classList.remove('dragover'));
drop.addEventListener('drop', event => { event.preventDefault(); drop.classList.remove('dragover'); const file = event.dataTransfer.files[0]; if (file) { selectedFile = file; $('#file-label').textContent = file.name; $('#file-picked').textContent = `${(file.size / 1024 / 1024).toFixed(1)} MB · ready to upload`; } });

$('#make-recording').addEventListener('click', async event => {
  if (!selectedFile) return toast('Choose a class recording first.');
  const button = event.currentTarget; button.disabled = true; button.textContent = 'Uploading recording…';
  try {
    const form = new FormData(); form.append('file', selectedFile);
    const asset = await request('/assets', { method: 'POST', body: form });
    const vocabulary = $('#vocabulary').value.split(',').map(word => word.trim()).filter(Boolean);
    const job = await request('/jobs/recording', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({asset_id:asset.id,language:$('#language').value,target_clip_seconds:Number($('#clip-length').value),technical_vocabulary:vocabulary,brand_id:knownBrandId}) });
    toast('Recording added. Your demo highlight is ready to explore.'); await loadJobs(); openJob(job.id);
  } catch (error) { toast(error.message); }
  finally { button.disabled = false; button.innerHTML = 'Find my best moments <span>→</span>'; }
});

$('#make-topic').addEventListener('click', async event => {
  const topic = $('#topic-input').value.trim(); if (topic.length < 2) return toast('Add a topic for your explainer.');
  const button = event.currentTarget; button.disabled = true; button.textContent = 'Building your preview…';
  try {
    const job = await request('/jobs/explainer', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({topic,audience:$('#audience').value,duration_seconds:Number($('#explainer-length').value),language:$('#explainer-language').value,brand_id:knownBrandId}) });
    toast('Your sample storyboard is ready.'); await loadJobs(); openJob(job.id);
  } catch (error) { toast(error.message); }
  finally { button.disabled = false; button.innerHTML = 'Create my explainer <span>→</span>'; }
});

async function loadJobs() {
  const host = $('#jobs-list');
  try {
    const jobs = await request('/jobs?limit=20'); $('#job-count').textContent = jobs.length;
    if (!jobs.length) { host.innerHTML = '<div class="empty-state"><span>◷</span><b>Your next great reel starts here</b><p>Start with a recording or a topic above.</p></div>'; return; }
    host.innerHTML = jobs.map(job => {
      const title = job.input_json?.topic || job.input_json?.source_filename || (job.kind === 'recording_highlights' ? 'Class recording highlights' : job.kind.replaceAll('_',' '));
      const icon = job.kind === 'topic_explainer' ? '✳' : job.kind === 'clip_render' ? '▶' : '◉';
      const date = new Date(job.created_at).toLocaleString([], {month:'short',day:'numeric',hour:'numeric',minute:'2-digit'});
      return `<article class="job-card" data-job="${esc(job.id)}"><div class="job-thumb">${icon}</div><div class="job-info"><b>${esc(title)}</b><small>${esc(job.kind.replaceAll('_',' '))} · ${date}${job.error ? ` · ${esc(job.error)}` : ''}</small></div><span class="status ${esc(job.status)}">${esc(job.status)}</span><span class="job-arrow">→</span></article>`;
    }).join('');
    host.querySelectorAll('.job-card').forEach(card => card.addEventListener('click', () => openJob(card.dataset.job)));
  } catch (error) { host.innerHTML = `<div class="empty-state"><b>Couldn’t reach the API</b><p>${esc(error.message)} · Start the backend server and refresh.</p></div>`; }
}
$('#refresh-jobs').addEventListener('click', loadJobs);

async function openJob(id) {
  try {
    const job = await request(`/jobs/${encodeURIComponent(id)}`);
    const detail = $('#job-detail');
    let content = `<div class="detail-kicker">${esc(job.kind.replaceAll('_',' '))} · ${esc(job.status)}</div><h3 class="detail-title">${esc(job.input_json?.topic || (job.kind === 'recording_highlights' ? 'Class recording highlights' : 'Render preview'))}</h3><div class="detail-meta">${job.progress}% complete · ${new Date(job.created_at).toLocaleString()}</div>`;
    if (job.error) content += `<div class="detail-callout">${esc(job.error)}</div>`;
    if (job.result_json?.demo) {
      content += `<div class="detail-callout"><b>DEMO OUTPUT</b><br>${esc(job.result_json.message || 'This is sample content generated for the interface preview.')}</div>`;
      if (job.result_json.script) content += `<div class="detail-callout"><b>Sample script</b><br>${esc(job.result_json.script)}</div>`;
      if (job.result_json.scenes) content += job.result_json.scenes.map(scene => `<div class="scene"><time>${Number(scene.at_seconds).toString().padStart(2,'0')}s</time><div><b>${esc(scene.text)}</b>${scene.code ? `<code>${esc(scene.code)}</code>` : ''}</div></div>`).join('');
      if (job.kind === 'recording_highlights') {
        const clips = await request(`/jobs/${encodeURIComponent(id)}/clips`);
        content += clips.map(clip => `<div class="detail-callout"><b>${esc(clip.title)}</b><br>${Number(clip.start_seconds).toFixed(1)}s — ${Number(clip.end_seconds).toFixed(1)}s<br>${esc(clip.transcript || '')}</div><div class="clip-edit"><label>Start (s)<input id="clip-start" type="number" min="0" step="0.1" value="${clip.start_seconds}"></label><label>End (s)<input id="clip-end" type="number" min="0" step="0.1" value="${clip.end_seconds}"></label><button id="save-clip" data-clip="${esc(clip.id)}">Save edit</button></div>`).join('');
      }
    }
    detail.innerHTML = content; $('#job-dialog').showModal();
    const save = $('#save-clip');
    if (save) save.addEventListener('click', async () => {
      try { await request(`/clips/${encodeURIComponent(save.dataset.clip)}`, {method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({start_seconds:Number($('#clip-start').value),end_seconds:Number($('#clip-end').value)})}); toast('Clip boundaries saved.'); }
      catch (error) { toast(error.message); }
    });
  } catch (error) { toast(error.message); }
}
$('dialog form').addEventListener('submit', () => $('#job-dialog').close());

$('#brand-name').addEventListener('input', () => { $('#brand-preview-name').textContent = $('#brand-name').value || 'Your brand'; $('#brand-preview-logo').textContent = ($('#brand-name').value.trim()[0] || 'R').toUpperCase(); });
$('#brand-color').addEventListener('input', event => { document.documentElement.style.setProperty('--lime', event.target.value); $('#brand-colors').textContent = `${event.target.value.toUpperCase()}   #101512`; });
$('#save-brand').addEventListener('click', async () => {
  const name = $('#brand-name').value.trim(); if (!name) return toast('Add a brand name.');
  const color = $('#brand-color').value;
  const body = {name,colors:{primary:color,background:'#101512'},fonts:{heading:'Manrope',body:'DM Sans'},caption_style:{accent:color}};
  try {
    const saved = knownBrandId ? await request(`/brands/${encodeURIComponent(knownBrandId)}`, {method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}) : await request('/brands', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    knownBrandId = saved.id; toast('Brand kit saved to the backend.');
  } catch (error) { toast(error.message); }
});

loadJobs();
request('/brands').then(brands => {
  if (!brands.length) return;
  const brand = brands[0]; knownBrandId = brand.id; $('#brand-name').value = brand.name; $('#brand-preview-name').textContent = brand.name;
  $('#brand-preview-logo').textContent = (brand.name[0] || 'R').toUpperCase();
  const color = brand.colors?.primary || '#b9f66a'; $('#brand-color').value = color; $('#brand-colors').textContent = `${color.toUpperCase()}   #101512`; document.documentElement.style.setProperty('--lime', color);
}).catch(() => {});
setInterval(loadJobs, 12000);
