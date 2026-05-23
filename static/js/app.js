// ---- Utils ----
const $ = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];
const fmt = n => n >= 10000 ? (n/10000).toFixed(1)+'万' : n >= 1000 ? (n/1000).toFixed(1)+'K' : String(n??0);
const GENRE_LABEL = { food:'ご飯', beauty:'美容', fashion:'ファッション' };
const GENRE_ALL = ['food','beauty','fashion'];

async function api(path, opts={}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'エラーが発生しました');
  }
  return res.json();
}

// ---- Router ----
let currentPage = 'dashboard';
function navigate(page) {
  currentPage = page;
  $$('.nav-item').forEach(el => el.classList.toggle('active', el.dataset.page === page));
  render(page);
}

$$('.nav-item').forEach(el => el.addEventListener('click', e => {
  e.preventDefault();
  navigate(el.dataset.page);
}));

function render(page) {
  const main = $('#main');
  main.innerHTML = '<div class="spinner">読み込み中...</div>';
  const pages = { dashboard: renderDashboard, posts: renderPosts, influencers: renderInfluencers, database: renderDatabase, accounts: renderAccounts };
  (pages[page] || renderDashboard)(main);
}

// ---- Dashboard ----
async function renderDashboard(main) {
  const [accounts, posts, influencers, topPosts] = await Promise.all([
    api('/api/accounts'),
    api('/api/posts?status=scheduled'),
    api('/api/influencers'),
    api('/api/influencers/database?sort=score&limit=5'),
  ]);

  const totalFollowers = accounts.reduce((s,a) => s+a.followers, 0);
  const totalDbPosts = influencers.reduce((s,i) => s+i.post_count, 0);

  main.innerHTML = `
    <div class="top-bar">
      <h1 class="page-title">ダッシュボード</h1>
    </div>
    <div class="grid-4" style="margin-bottom:24px">
      <div class="stat-card"><div class="val">${accounts.length}</div><div class="label">運用アカウント</div></div>
      <div class="stat-card"><div class="val">${fmt(totalFollowers)}</div><div class="label">総フォロワー</div></div>
      <div class="stat-card"><div class="val">${posts.length}</div><div class="label">予約投稿</div></div>
      <div class="stat-card"><div class="val">${totalDbPosts}</div><div class="label">DB投稿数</div></div>
    </div>
    <div class="grid-2">
      <div>
        <div class="card-title">運用アカウント</div>
        ${accounts.slice(0,5).map(a => `
          <div class="account-card">
            ${a.profile_image_url ? `<img src="${a.profile_image_url.replace('_normal','_bigger')}" />` : '<div style="width:44px;height:44px;border-radius:50%;background:#333"></div>'}
            <div class="info">
              <div class="name">${a.display_name || a.username} <span class="badge badge-${a.genre}">${GENRE_LABEL[a.genre]}</span></div>
              <div class="handle">@${a.username}</div>
            </div>
            <div class="stats"><span>フォロワー <b>${fmt(a.followers)}</b></span></div>
          </div>`).join('') || '<p class="text-muted">アカウント未登録</p>'}
      </div>
      <div>
        <div class="card-title">DB バズ投稿 TOP5</div>
        ${topPosts.map((p,i) => `
          <div class="trend-card" style="cursor:default">
            <div class="author">
              <span class="rank-badge ${i<3?'top':''}">${i+1}</span>
              ${p.influencer_image ? `<img src="${p.influencer_image}" />` : ''}
              <span style="font-size:0.85rem;font-weight:600">@${p.influencer_username}</span>
              <span class="badge badge-${p.genre}">${GENRE_LABEL[p.genre]||''}</span>
            </div>
            <div class="text">${p.text.slice(0,80)}${p.text.length>80?'...':''}</div>
            <div class="metrics">
              <span>いいね <b>${fmt(p.likes)}</b></span>
              <span>RT <b>${fmt(p.retweets)}</b></span>
            </div>
          </div>`).join('') || '<p class="text-muted">インフルエンサーを登録するとここに表示されます</p>'}
      </div>
    </div>`;
}

// ---- (Trends removed) ----

async function generatePost() {
  const btn = $('#generateBtn');
  const result = $('#generateResult');
  btn.disabled = true;
  result.innerHTML = '<div class="spinner">生成中...</div>';
  try {
    const data = await api('/api/posts/generate', {
      method: 'POST',
      body: {
        genre: 'food',
        inspiration_texts: [],
        instruction: '',
      },
    });
    result.innerHTML = `
      <div class="generate-panel">
        <div class="card-title">生成結果</div>
        <textarea class="form-control" id="generatedText" style="min-height:80px">${data.content}</textarea>
        <div class="flex gap-2 mt-2">
          <button class="btn btn-primary btn-sm" onclick="openPostModal()">投稿・予約する</button>
        </div>
      </div>`;
  } catch(e) {
    result.innerHTML = `<p class="text-muted">${e.message}</p>`;
  }
  btn.disabled = false;
}

// ---- Posts ----
async function renderPosts(main) {
  const [posts, accounts] = await Promise.all([
    api('/api/posts'),
    api('/api/accounts'),
  ]);

  main.innerHTML = `
    <div class="top-bar">
      <h1 class="page-title">投稿管理</h1>
      <div class="flex gap-2">
        <button class="btn btn-secondary" onclick="openCaptionModal()">画像からキャプション生成</button>
        <button class="btn btn-primary" onclick="openPostModal()">+ 新規投稿</button>
      </div>
    </div>
    <div class="genre-tabs">
      <button class="genre-tab active" data-status="all">すべて</button>
      <button class="genre-tab" data-status="scheduled">予約済み</button>
      <button class="genre-tab" data-status="published">公開済み</button>
      <button class="genre-tab" data-status="draft">下書き</button>
    </div>
    <div id="postList">
      ${renderPostList(posts)}
    </div>
    <div id="postModal"></div>`;

  $$('.genre-tab').forEach(tab => tab.addEventListener('click', async () => {
    $$('.genre-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    const status = tab.dataset.status;
    const url = status === 'all' ? '/api/posts' : `/api/posts?status=${status}`;
    const filtered = await api(url);
    $('#postList').innerHTML = renderPostList(filtered);
  }));

  window._postAccounts = accounts;
}

function renderPostList(posts) {
  if (!posts.length) return '<p class="text-muted">投稿なし</p>';
  return posts.map(p => `
    <div class="post-row">
      <div class="content">
        <div>${p.content}</div>
        <div class="meta">
          @${p.account_username || '?'} &nbsp;·&nbsp;
          ${p.scheduled_at ? '予約: '+new Date(p.scheduled_at).toLocaleString('ja-JP') : ''}
          ${p.published_at ? '公開: '+new Date(p.published_at).toLocaleString('ja-JP') : ''}
        </div>
      </div>
      <div class="actions">
        <span class="badge badge-${p.status}">${statusLabel(p.status)}</span>
        ${p.status !== 'published' ? `<button class="btn btn-danger btn-sm" onclick="deletePost(${p.id})">削除</button>` : ''}
      </div>
    </div>`).join('');
}

function statusLabel(s) {
  return { draft:'下書き', scheduled:'予約', published:'公開済み', failed:'失敗' }[s] || s;
}

function openCaptionModal() {
  const modal = document.createElement('div');
  modal.className = 'modal-overlay';
  modal.innerHTML = `
    <div class="modal" style="width:600px">
      <div class="modal-title">画像からキャプション生成</div>
      <div class="form-group">
        <label>ジャンル</label>
        <select class="form-control" id="capGenre">
          ${GENRE_ALL.map(g => `<option value="${g}">${GENRE_LABEL[g]}</option>`).join('')}
        </select>
      </div>
      <div class="form-group">
        <label>画像（任意）</label>
        <input type="file" class="form-control" id="capImage" accept="image/*" />
        <div id="capPreview" style="margin-top:8px"></div>
      </div>
      <div class="form-group">
        <label>画像の詳細・メモ</label>
        <textarea class="form-control" id="capDescription" placeholder="例：渋谷の人気カフェで食べたフルーツパフェ。見た目が華やかで映える。価格は1800円。" style="min-height:80px"></textarea>
      </div>
      <div class="form-group">
        <label>テイスト</label>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px" id="tasteGrid">
          ${[
            ['buzz',    'バズ狙い', 'いいね・保存されやすい、インパクト重視'],
            ['empathy', '共感型',   'あるある・日常感、フォロワーが反応しやすい'],
            ['elegant', '上品・洗練', 'ハイブランド感、シンプルで洗練された文体'],
            ['casual',  '親しみやすい', 'カジュアル・フレンドリー、会話口調'],
            ['info',    '情報提供型', '詳細・スペック・使い方を伝える'],
          ].map(([val, label, desc]) => `
            <label style="background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:12px;cursor:pointer;display:flex;gap:10px;align-items:flex-start">
              <input type="radio" name="capTaste" value="${val}" ${val==='buzz'?'checked':''} style="margin-top:3px;flex-shrink:0" />
              <div>
                <div style="font-weight:600;font-size:0.9rem">${label}</div>
                <div style="font-size:0.78rem;color:var(--muted)">${desc}</div>
              </div>
            </label>`).join('')}
        </div>
      </div>
      <div id="capResult"></div>
      <div class="modal-footer">
        <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()">閉じる</button>
        <button class="btn btn-primary" id="capGenBtn" onclick="submitCaption()">生成</button>
      </div>
    </div>`;
  document.body.appendChild(modal);
  modal.addEventListener('click', e => { if (e.target === modal) modal.remove(); });

  $('#capImage').addEventListener('change', e => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = ev => {
      $('#capPreview').innerHTML = `<img src="${ev.target.result}" style="max-width:100%;max-height:200px;border-radius:8px;object-fit:contain" />`;
    };
    reader.readAsDataURL(file);
  });
}

async function submitCaption() {
  const btn = $('#capGenBtn');
  const result = $('#capResult');
  btn.disabled = true;
  btn.textContent = '生成中...';
  result.innerHTML = '<div class="spinner">DBを参照してキャプションを生成中...</div>';

  try {
    const form = new FormData();
    form.append('genre', $('#capGenre').value);
    form.append('taste', document.querySelector('input[name="capTaste"]:checked').value);
    form.append('description', $('#capDescription').value);
    const imageFile = $('#capImage').files[0];
    if (imageFile) form.append('image', imageFile);

    const res = await fetch('/api/posts/generate-caption', { method: 'POST', body: form });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail); }
    const data = await res.json();

    result.innerHTML = `
      <div class="generate-panel" style="margin-top:0">
        <div class="card-title">生成結果</div>
        <textarea class="form-control" id="capGenerated" style="min-height:90px">${data.content}</textarea>
        <div style="font-size:0.78rem;color:var(--muted);margin-top:4px" id="capCharCount">${data.content.length} / 140文字</div>
        <div class="flex gap-2 mt-2">
          <button class="btn btn-secondary btn-sm" onclick="submitCaption()">再生成</button>
          <button class="btn btn-primary btn-sm" onclick="useCaption()">投稿・予約する</button>
        </div>
      </div>`;

    const ta = $('#capGenerated');
    ta.addEventListener('input', () => {
      $('#capCharCount').textContent = `${ta.value.length} / 140文字`;
    });
  } catch(e) {
    result.innerHTML = `<p class="text-muted">${e.message}</p>`;
  }
  btn.disabled = false;
  btn.textContent = '再生成';
}

async function useCaption() {
  const text = $('#capGenerated').value;
  document.querySelector('.modal-overlay')?.remove();
  const accounts = await api('/api/accounts');
  window._postAccounts = accounts;
  openPostModal(text);
}

async function deletePost(id) {
  if (!confirm('削除しますか？')) return;
  await api(`/api/posts/${id}`, { method:'DELETE' });
  navigate('posts');
}

function openPostModal(prefillContent='') {
  const content = prefillContent || ($('#generatedText')?.value ?? '');
  const accounts = window._postAccounts || [];
  const modal = document.createElement('div');
  modal.className = 'modal-overlay';
  modal.innerHTML = `
    <div class="modal">
      <div class="modal-title">投稿を作成</div>
      <div class="form-group">
        <label>アカウント</label>
        <select class="form-control" id="postAccount">
          <option value="">選択してください</option>
          ${accounts.map(a => `<option value="${a.id}">@${a.username} (${GENRE_LABEL[a.genre]})</option>`).join('')}
        </select>
      </div>
      <div class="form-group">
        <label>本文</label>
        <textarea class="form-control" id="postContent" style="min-height:120px">${content}</textarea>
        <div class="text-muted mt-1" id="charCount">0 / 140文字</div>
      </div>
      <div class="form-group">
        <label>予約日時（空欄=下書き）</label>
        <input type="datetime-local" class="form-control" id="postSchedule" />
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()">キャンセル</button>
        <button class="btn btn-primary" onclick="submitPost()">保存</button>
      </div>
    </div>`;
  document.body.appendChild(modal);
  modal.addEventListener('click', e => { if (e.target === modal) modal.remove(); });
  const ta = $('#postContent');
  const cc = $('#charCount');
  ta.addEventListener('input', () => {
    const len = ta.value.length;
    cc.textContent = `${len} / 140文字`;
    cc.style.color = len > 140 ? 'var(--red)' : 'var(--muted)';
  });
  if (content) ta.dispatchEvent(new Event('input'));
}

async function submitPost() {
  const accountId = parseInt($('#postAccount').value);
  const content = $('#postContent').value.trim();
  const scheduleVal = $('#postSchedule').value;
  if (!accountId) { alert('アカウントを選択してください'); return; }
  if (!content) { alert('本文を入力してください'); return; }
  try {
    await api('/api/posts', {
      method: 'POST',
      body: {
        account_id: accountId,
        content,
        scheduled_at: scheduleVal ? new Date(scheduleVal).toISOString() : null,
      },
    });
    document.querySelector('.modal-overlay')?.remove();
    navigate('posts');
  } catch(e) { alert(e.message); }
}

// ---- Database ----
let dbGenre = '';
let dbInfluencerId = '';
let dbSort = 'score';
let dbInfluencers = [];

async function renderDatabase(main) {
  dbInfluencers = await api('/api/influencers');

  main.innerHTML = `
    <div class="top-bar">
      <h1 class="page-title">データベース</h1>
      <div class="flex gap-2">
        <select class="form-control" id="dbInfluencerFilter" style="width:180px">
          <option value="">全インフルエンサー</option>
          ${dbInfluencers.map(inf => `<option value="${inf.id}">@${inf.username}</option>`).join('')}
        </select>
        <select class="form-control" id="dbSortFilter" style="width:140px">
          <option value="score">スコア順</option>
          <option value="likes">いいね順</option>
          <option value="retweets">RT順</option>
          <option value="recent">新しい順</option>
        </select>
      </div>
    </div>
    <div class="genre-tabs" style="margin-bottom:20px">
      <button class="genre-tab active" data-genre="">すべて</button>
      ${GENRE_ALL.map(g => `<button class="genre-tab" data-genre="${g}">${GENRE_LABEL[g]}</button>`).join('')}
    </div>
    <div id="dbList"><div class="spinner">読み込み中...</div></div>`;

  $$('.genre-tab').forEach(tab => tab.addEventListener('click', () => {
    $$('.genre-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    dbGenre = tab.dataset.genre;
    loadDatabase();
  }));

  $('#dbInfluencerFilter').addEventListener('change', e => { dbInfluencerId = e.target.value; loadDatabase(); });
  $('#dbSortFilter').addEventListener('change', e => { dbSort = e.target.value; loadDatabase(); });

  loadDatabase();
}

async function loadDatabase() {
  const list = $('#dbList');
  if (!list) return;
  list.innerHTML = '<div class="spinner">読み込み中...</div>';

  const params = new URLSearchParams({ sort: dbSort, limit: 50 });
  if (dbGenre) params.set('genre', dbGenre);
  if (dbInfluencerId) params.set('influencer_id', dbInfluencerId);

  try {
    const posts = await api(`/api/influencers/database?${params}`);
    if (!posts.length) {
      list.innerHTML = '<p class="text-muted">データなし。インフルエンサーを登録して投稿を取得してください。</p>';
      return;
    }
    list.innerHTML = posts.map(p => `
      <div class="trend-card" data-text="${encodeURIComponent(p.text)}" onclick="toggleDbInspiration(this)">
        <div class="author">
          ${p.influencer_image ? `<img src="${p.influencer_image}" />` : ''}
          <div>
            <div class="name">${p.influencer_name || p.influencer_username} <span class="badge badge-${p.genre||''}">${GENRE_LABEL[p.genre]||''}</span></div>
            <div class="handle">@${p.influencer_username} · ${p.posted_at ? new Date(p.posted_at).toLocaleDateString('ja-JP') : ''}</div>
          </div>
        </div>
        <div class="text">${p.text}</div>
        <div class="metrics">
          <span>いいね <b>${fmt(p.likes)}</b></span>
          <span>RT <b>${fmt(p.retweets)}</b></span>
          <span>リプライ <b>${fmt(p.replies)}</b></span>
        </div>
      </div>`).join('');
  } catch(e) {
    list.innerHTML = `<p class="text-muted">${e.message}</p>`;
  }
}

let dbSelectedTexts = [];

function toggleDbInspiration(card) {
  const text = decodeURIComponent(card.dataset.text);
  const idx = dbSelectedTexts.indexOf(text);
  if (idx >= 0) {
    dbSelectedTexts.splice(idx, 1);
    card.classList.remove('selected');
  } else if (dbSelectedTexts.length < 3) {
    dbSelectedTexts.push(text);
    card.classList.add('selected');
  }
  updateDbGenerateBar();
}

function updateDbGenerateBar() {
  let bar = $('#dbGenerateBar');
  if (!bar) {
    bar = document.createElement('div');
    bar.id = 'dbGenerateBar';
    bar.style.cssText = 'position:fixed;bottom:0;left:220px;right:0;background:var(--surface);border-top:1px solid var(--border);padding:16px 32px;display:flex;align-items:center;gap:12px;z-index:50';
    document.body.appendChild(bar);
  }
  if (!dbSelectedTexts.length) { bar.remove(); return; }

  const genre = dbGenre || (dbInfluencers.find(i => i.id == dbInfluencerId)?.genre) || 'food';
  bar.innerHTML = `
    <span class="text-muted" style="font-size:0.85rem">${dbSelectedTexts.length}件選択中</span>
    <input class="form-control" id="dbInstruction" placeholder="追加指示（任意）" style="flex:1;max-width:300px" />
    <button class="btn btn-primary" onclick="generateFromDb('${genre}')">AIで生成</button>
    <button class="btn btn-secondary" onclick="dbSelectedTexts=[];$$('.trend-card').forEach(c=>c.classList.remove('selected'));updateDbGenerateBar()">クリア</button>`;
}

async function generateFromDb(genre) {
  const btn = $('#dbGenerateBar .btn-primary');
  btn.disabled = true;
  btn.textContent = '生成中...';
  try {
    const data = await api('/api/posts/generate', {
      method: 'POST',
      body: { genre, inspiration_texts: dbSelectedTexts, instruction: $('#dbInstruction')?.value || '' },
    });
    // 生成結果をモーダルで表示
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
      <div class="modal">
        <div class="modal-title">AI 生成結果</div>
        <textarea class="form-control" id="dbGeneratedText" style="min-height:100px">${data.content}</textarea>
        <div class="modal-footer">
          <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()">閉じる</button>
          <button class="btn btn-primary" onclick="openPostModalWithText($('#dbGeneratedText').value)">投稿・予約する</button>
        </div>
      </div>`;
    document.body.appendChild(modal);
    modal.addEventListener('click', e => { if (e.target === modal) modal.remove(); });
  } catch(e) { alert(e.message); }
  btn.disabled = false;
  btn.textContent = 'AIで生成';
}

async function openPostModalWithText(text) {
  document.querySelector('.modal-overlay')?.remove();
  const accounts = await api('/api/accounts');
  window._postAccounts = accounts;
  openPostModal(text);
}

// ---- Influencers ----
async function renderInfluencers(main) {
  const influencers = await api('/api/influencers');
  main.innerHTML = `
    <div class="top-bar">
      <h1 class="page-title">インフルエンサー</h1>
      <button class="btn btn-primary" onclick="openAddInfluencer()">+ 追加</button>
    </div>
    <div class="grid-2" id="influencerGrid">
      ${influencers.length ? influencers.map(inf => renderInfluencerCard(inf)).join('') : '<p class="text-muted">未登録</p>'}
    </div>
    <div id="influencerModal"></div>`;
}

function renderInfluencerCard(inf) {
  return `
    <div class="card" id="inf-${inf.id}">
      <div class="account-card" style="border:none;padding:0;margin-bottom:12px">
        ${inf.profile_image_url ? `<img src="${inf.profile_image_url.replace('_normal','_bigger')}" />` : '<div style="width:44px;height:44px;border-radius:50%;background:#333"></div>'}
        <div class="info">
          <div class="name">${inf.display_name || inf.username} ${inf.genre ? `<span class="badge badge-${inf.genre}">${GENRE_LABEL[inf.genre]}</span>` : ''}</div>
          <div class="handle">@${inf.username}</div>
          <div class="text-muted" style="font-size:0.8rem">フォロワー ${fmt(inf.followers)} · 取得済み ${inf.post_count}件 · 最高いいね ${fmt(inf.top_likes)}</div>
        </div>
        <div class="flex gap-2">
          <button class="btn btn-secondary btn-sm" onclick="refreshInfluencer(${inf.id})">更新</button>
          <button class="btn btn-danger btn-sm" onclick="deleteInfluencer(${inf.id})">削除</button>
        </div>
      </div>
      <div id="posts-${inf.id}">
        <button class="btn btn-secondary btn-sm" style="width:100%" onclick="loadInfluencerPosts(${inf.id})">ポストを見る</button>
      </div>
    </div>`;
}

async function loadInfluencerPosts(id) {
  const container = $(`#posts-${id}`);
  container.innerHTML = '<div class="spinner">読み込み中...</div>';
  try {
    const posts = await api(`/api/influencers/${id}/posts`);
    container.innerHTML = posts.length
      ? posts.map(p => `
        <div class="trend-card" style="cursor:default;margin-bottom:8px" data-text="${encodeURIComponent(p.text)}">
          <div class="text">${p.text}</div>
          <div class="metrics">
            <span>いいね <b>${fmt(p.likes)}</b></span>
            <span>RT <b>${fmt(p.retweets)}</b></span>
            <span>リプライ <b>${fmt(p.replies)}</b></span>
            ${p.posted_at ? `<span>${new Date(p.posted_at).toLocaleDateString('ja-JP')}</span>` : ''}
          </div>
        </div>`).join('')
      : '<p class="text-muted">投稿なし</p>';
  } catch(e) {
    container.innerHTML = `<p class="text-muted">${e.message}</p>`;
  }
}

async function refreshInfluencer(id) {
  try {
    const res = await api(`/api/influencers/${id}/refresh`, { method: 'POST' });
    alert(`更新完了: ${res.added}件追加`);
    await loadInfluencerPosts(id);
  } catch(e) { alert(e.message); }
}

async function deleteInfluencer(id) {
  if (!confirm('削除しますか？')) return;
  await api(`/api/influencers/${id}`, { method: 'DELETE' });
  navigate('influencers');
}

function openAddInfluencer() {
  const modal = document.createElement('div');
  modal.className = 'modal-overlay';
  modal.innerHTML = `
    <div class="modal">
      <div class="modal-title">インフルエンサー追加</div>
      <div class="form-group">
        <label>ユーザー名（@ なし）</label>
        <input class="form-control" id="infUsername" placeholder="例: yamada_taro" />
      </div>
      <div class="form-group">
        <label>ジャンル（任意）</label>
        <select class="form-control" id="infGenre">
          <option value="">指定なし</option>
          ${GENRE_ALL.map(g => `<option value="${g}">${GENRE_LABEL[g]}</option>`).join('')}
        </select>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()">キャンセル</button>
        <button class="btn btn-primary" onclick="submitInfluencer()">追加</button>
      </div>
    </div>`;
  document.body.appendChild(modal);
  modal.addEventListener('click', e => { if (e.target === modal) modal.remove(); });
}

async function submitInfluencer() {
  const username = $('#infUsername').value.trim().replace(/^@/, '');
  const genre = $('#infGenre').value || null;
  if (!username) { alert('ユーザー名を入力してください'); return; }
  try {
    await api('/api/influencers', { method: 'POST', body: { username, genre } });
    document.querySelector('.modal-overlay')?.remove();
    navigate('influencers');
  } catch(e) { alert(e.message); }
}

// ---- Accounts ----
async function renderAccounts(main) {
  const accounts = await api('/api/accounts');
  main.innerHTML = `
    <div class="top-bar">
      <h1 class="page-title">アカウント管理</h1>
      <button class="btn btn-primary" onclick="openAddAccount()">+ アカウント追加</button>
    </div>
    ${accounts.map(a => `
      <div class="account-card">
        ${a.profile_image_url ? `<img src="${a.profile_image_url.replace('_normal','_bigger')}" />` : '<div style="width:44px;height:44px;border-radius:50%;background:#333"></div>'}
        <div class="info">
          <div class="name">${a.display_name || a.username} <span class="badge badge-${a.genre}">${GENRE_LABEL[a.genre]}</span> ${a.has_token ? '<span class="badge badge-published">投稿可</span>' : '<span class="badge badge-draft">読み取りのみ</span>'}</div>
          <div class="handle">@${a.username}</div>
        </div>
        <div class="stats">
          <span>フォロワー <b>${fmt(a.followers)}</b></span>
          <span>フォロー中 <b>${fmt(a.following)}</b></span>
          <span>ツイート <b>${fmt(a.tweet_count)}</b></span>
        </div>
        <button class="btn btn-danger btn-sm" onclick="deleteAccount(${a.id})">削除</button>
      </div>`).join('') || '<p class="text-muted">アカウント未登録</p>'}
    <div id="accountModal"></div>`;
}

function openAddAccount() {
  const modal = document.createElement('div');
  modal.className = 'modal-overlay';
  modal.innerHTML = `
    <div class="modal">
      <div class="modal-title">アカウント追加</div>
      <div class="form-group">
        <label>ユーザー名（@ なし）</label>
        <input class="form-control" id="newUsername" placeholder="例: nakayuu_x" />
      </div>
      <div class="form-group">
        <label>ジャンル</label>
        <select class="form-control" id="newGenre">
          ${GENRE_ALL.map(g => `<option value="${g}">${GENRE_LABEL[g]}</option>`).join('')}
        </select>
      </div>
      <div class="form-group">
        <label>Access Token（投稿する場合）</label>
        <input class="form-control" id="newAccessToken" placeholder="OAuth 1.0a Access Token" />
      </div>
      <div class="form-group">
        <label>Access Token Secret（投稿する場合）</label>
        <input class="form-control" id="newAccessTokenSecret" placeholder="OAuth 1.0a Access Token Secret" />
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()">キャンセル</button>
        <button class="btn btn-primary" onclick="submitAccount()">追加</button>
      </div>
    </div>`;
  document.body.appendChild(modal);
  modal.addEventListener('click', e => { if (e.target === modal) modal.remove(); });
}

async function submitAccount() {
  const username = $('#newUsername').value.trim().replace(/^@/,'');
  const genre = $('#newGenre').value;
  const access_token = $('#newAccessToken').value.trim() || null;
  const access_token_secret = $('#newAccessTokenSecret').value.trim() || null;
  if (!username) { alert('ユーザー名を入力してください'); return; }
  try {
    await api('/api/accounts', { method:'POST', body:{ username, genre, access_token, access_token_secret } });
    document.querySelector('.modal-overlay')?.remove();
    navigate('accounts');
  } catch(e) { alert(e.message); }
}

async function deleteAccount(id) {
  if (!confirm('削除しますか？')) return;
  await api(`/api/accounts/${id}`, { method:'DELETE' });
  navigate('accounts');
}

// Boot
navigate('dashboard');
