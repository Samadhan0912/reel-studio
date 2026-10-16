const API = '/api/v1';
let selectedFile = null;
let knownBrandId = null;
let brandAssetIds = {logo_asset_id:null,intro_asset_id:null,outro_asset_id:null};
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
    toast('Recording uploaded. Local transcription is starting.'); await loadJobs(); openJob(job.id);
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
    if (['queued','processing'].includes(job.status)) content += `<button class="cancel-job" data-job="${esc(job.id)}" type="button">Cancel processing</button>`;
    if (job.error) content += `<div class="detail-callout">${esc(job.error)}</div>`;
    const result = job.result_json || {};
    if (Object.keys(result).length) {
      content += `<div class="detail-callout"><b>${result.demo ? 'SAMPLE OUTPUT' : 'GENERATED OUTPUT'}</b><br>${esc(result.message || '')}</div>`;
      if (result.audio_note) content += `<div class="detail-callout">${esc(result.audio_note)}</div>`;
      if (result.transcript_text) content += `<details class="transcript-view"><summary>View local transcript</summary><pre>${esc(result.transcript_text)}</pre></details>`;
      if (result.script) content += `<div class="detail-callout"><b>Generated script</b><br>${esc(result.script)}</div>`;
      if (result.scenes) content += result.scenes.map(scene => `<div class="scene"><time>${Number(scene.at_seconds).toString().padStart(2,'0')}s</time><div><b>${esc(scene.text)}</b>${scene.code ? `<code>${esc(scene.code)}</code>` : ''}</div></div>`).join('');
      if (result.output_path) content += `<video controls playsinline style="width:100%;max-height:55vh;margin-top:16px;border-radius:10px;background:#090c0a" src="${API}/jobs/${encodeURIComponent(id)}/download"></video><a class="secondary-button" style="display:inline-flex;align-items:center;text-decoration:none;margin-top:10px" href="${API}/jobs/${encodeURIComponent(id)}/download" download>Download MP4</a>`;
    }
    if (job.kind === 'recording_highlights' && job.status === 'completed') {
      const clips = await request(`/jobs/${encodeURIComponent(id)}/clips`);
      if (!clips.length) content += '<div class="detail-callout">No usable 30–60 second highlights were found. Try another recording or check the recording length.</div>';
      content += clips.map(clip => `<div class="detail-callout"><b>${esc(clip.title)}</b><br>${Number(clip.start_seconds).toFixed(1)}s – ${Number(clip.end_seconds).toFixed(1)}s<br>${esc(clip.transcript || '')}</div><div class="clip-edit"><label>Start (s)<input class="clip-start" data-clip="${esc(clip.id)}" type="number" min="0" step="0.1" value="${clip.start_seconds}"></label><label>End (s)<input class="clip-end" data-clip="${esc(clip.id)}" type="number" min="0" step="0.1" value="${clip.end_seconds}"></label><button class="save-clip" data-clip="${esc(clip.id)}">Save edit</button><button class="render-clip" data-clip="${esc(clip.id)}">Render MP4</button></div>`).join('');
    }
    detail.innerHTML = content; if (!$('#job-dialog').open) $('#job-dialog').showModal();
    detail.querySelector('.cancel-job')?.addEventListener('click', async event => {
      const button = event.currentTarget; button.disabled = true; button.textContent = 'Cancelling…';
      try { await request(`/jobs/${encodeURIComponent(button.dataset.job)}/cancel`, {method:'POST'}); toast('Processing cancelled.'); await loadJobs(); openJob(button.dataset.job); }
      catch (error) { toast(error.message); button.disabled = false; button.textContent = 'Cancel processing'; }
    });
    if (['queued','processing'].includes(job.status)) setTimeout(() => { if ($('#job-dialog').open) openJob(id); }, 2200);
    detail.querySelectorAll('.save-clip').forEach(save => save.addEventListener('click', async () => {
      const clipId = save.dataset.clip;
      try { await request(`/clips/${encodeURIComponent(clipId)}`, {method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({start_seconds:Number(detail.querySelector(`.clip-start[data-clip="${clipId}"]`).value),end_seconds:Number(detail.querySelector(`.clip-end[data-clip="${clipId}"]`).value)})}); toast('Clip boundaries saved.'); }
      catch (error) { toast(error.message); }
    }));
    detail.querySelectorAll('.render-clip').forEach(button => button.addEventListener('click', async () => {
      button.disabled = true; button.textContent = 'Rendering…';
      try {
        const render = await request(`/clips/${encodeURIComponent(button.dataset.clip)}/render`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({aspect_ratio:'9:16',resolution:'720x1280',brand_id:knownBrandId})});
        toast('Rendering your vertical MP4…');
        let finished = render;
        for (let attempt = 0; attempt < 180 && ['queued','processing'].includes(finished.status); attempt++) {
          await new Promise(resolve => setTimeout(resolve, 2000));
          finished = await request(`/jobs/${encodeURIComponent(render.id)}`);
        }
        if (finished.status === 'failed') throw new Error(finished.error || 'Video render failed.');
        if (finished.status !== 'completed') throw new Error('Render is still processing. Refresh your projects in a moment.');
        toast('Vertical MP4 is ready.');
        await loadJobs();
        openJob(render.id);
      } catch (error) { toast(error.message); }
      finally { button.disabled = false; button.textContent = 'Render MP4'; }
    }));
  } catch (error) { toast(error.message); }
}
$('dialog form').addEventListener('submit', () => $('#job-dialog').close());

$('#brand-name').addEventListener('input', () => { $('#brand-preview-name').textContent = $('#brand-name').value || 'Your brand'; $('#brand-preview-logo').textContent = ($('#brand-name').value.trim()[0] || 'R').toUpperCase(); });
$('#brand-color').addEventListener('input', event => { document.documentElement.style.setProperty('--lime', event.target.value); $('#brand-colors').textContent = `${event.target.value.toUpperCase()}   #101512`; });
async function saveBrand(showToast = true) {
  const name = $('#brand-name').value.trim(); if (!name) return toast('Add a brand name.');
  const color = $('#brand-color').value;
  const body = {name,colors:{primary:color,background:'#101512'},fonts:{heading:'Manrope',body:'DM Sans'},caption_style:{accent:color},...brandAssetIds};
  try {
    const saved = knownBrandId ? await request(`/brands/${encodeURIComponent(knownBrandId)}`, {method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}) : await request('/brands', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    knownBrandId = saved.id; if (showToast) toast('Brand kit saved to the backend.');
  } catch (error) { toast(error.message); }
}
$('#save-brand').addEventListener('click', () => saveBrand());
[['brand-logo-file','logo_asset_id','brand-logo-name'],['brand-intro-file','intro_asset_id','brand-intro-name'],['brand-outro-file','outro_asset_id','brand-outro-name']].forEach(([inputId,assetKey,nameId]) => {
  $(`#${inputId}`).addEventListener('change', async event => {
    const file = event.target.files[0]; if (!file) return;
    const form = new FormData(); form.append('file',file);
    try {
      const asset = await request('/assets',{method:'POST',body:form});
      brandAssetIds[assetKey] = asset.id; $(`#${nameId}`).textContent = file.name;
      await saveBrand(false); toast('Brand asset uploaded and saved.');
    } catch (error) { toast(error.message); }
  });
});

loadJobs();
const initialJob = new URLSearchParams(location.search).get('job');
if (initialJob) setTimeout(() => openJob(initialJob), 350);
request('/capabilities').then(capabilities => {
  const isDemo = capabilities.demo_mode;
  const features = capabilities.features || {};
  const ready = !isDemo && features.local_transcription && features.gemini_configured && features.mp4_rendering;
  document.querySelector('.demo-pill').innerHTML = `<i></i> ${isDemo ? 'DEMO MODE' : ready ? 'STUDIO READY' : 'SETUP NEEDED'}`;
  const notice = document.querySelector('.notice');
  if (isDemo) notice.querySelector('span:nth-child(2)').innerHTML = '<b>Demo mode is active.</b> Configure GEMINI_API_KEY and install backend requirements to process real recordings and generate explainers.';
  else if (ready) notice.querySelector('span:nth-child(2)').innerHTML = '<b>Your studio is ready.</b> Video audio is transcribed on this machine; Gemini receives only the transcript to choose highlights.';
  else {
    const missing = [];
    if (!features.local_transcription) missing.push('install the backend requirements for local transcription');
    if (!features.gemini_configured) missing.push('add GEMINI_API_KEY to backend/.env');
    if (!features.mp4_rendering) missing.push('install FFmpeg rendering support');
    notice.querySelector('span:nth-child(2)').innerHTML = `<b>Setup needed.</b> ${esc(missing.join('; ') || 'Check backend settings')} then restart the server. Video is not sent to Gemini.`;
  }
}).catch(() => {});
request('/brands').then(brands => {
  if (!brands.length) return;
  const brand = brands[0]; knownBrandId = brand.id; $('#brand-name').value = brand.name; $('#brand-preview-name').textContent = brand.name;
  brandAssetIds = {logo_asset_id:brand.logo_asset_id || null,intro_asset_id:brand.intro_asset_id || null,outro_asset_id:brand.outro_asset_id || null};
  $('#brand-preview-logo').textContent = (brand.name[0] || 'R').toUpperCase();
  const color = brand.colors?.primary || '#b9f66a'; $('#brand-color').value = color; $('#brand-colors').textContent = `${color.toUpperCase()}   #101512`; document.documentElement.style.setProperty('--lime', color);
}).catch(() => {});
setInterval(loadJobs, 12000);
