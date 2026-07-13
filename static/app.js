const pushStatusEl  = document.getElementById('pushStatus');
const btnSubscribe  = document.getElementById('btnSubscribe');
const resultsAllEl  = document.getElementById('resultsAll');
const resultsMineEl = document.getElementById('resultsMine');
const badgeAll      = document.getElementById('badgeAll');
const badgeMine     = document.getElementById('badgeMine');
const lastUpdatedEl = document.getElementById('lastUpdated');
const btnShare      = document.getElementById('btnShare');

// Tự động tải cả 2 cột khi mở trang
loadAll();
loadMine();

async function loadAll() {
  resultsAllEl.innerHTML = getSkeletonHtml(4);
  try {
    const res  = await fetch('/api/check-all');
    const data = await res.json();
    const entries = data.entries || [];
    badgeAll.textContent = entries.length;
    renderEntries(resultsAllEl, entries, true);
    if (data.last_updated) showLastUpdated(data.last_updated);
  } catch {
    resultsAllEl.innerHTML = '<div class="empty">Có lỗi, thử lại sau.</div>';
    badgeAll.textContent = '!';
  }
}

async function loadMine() {
  resultsMineEl.innerHTML = getSkeletonHtml(3);
  try {
    const res  = await fetch('/api/check');
    const data = await res.json();
    const entries = data.entries || [];
    badgeMine.textContent = entries.length;
    renderEntries(resultsMineEl, entries, true, true);
    if (data.last_updated) showLastUpdated(data.last_updated);
  } catch {
    resultsMineEl.innerHTML = '<div class="empty">Có lỗi, thử lại sau.</div>';
    badgeMine.textContent = '!';
  }
}

function showLastUpdated(timeStr) {
  if (lastUpdatedEl) lastUpdatedEl.textContent = `⏱ Cập nhật lúc ${timeStr}`;
}

// Nút chia sẻ
btnShare.addEventListener('click', async () => {
  const url = window.location.href;
  const text = '⚡ Theo dõi lịch cúp điện Huyện Phú Tân - An Giang tại đây:';
  if (navigator.share) {
    try {
      await navigator.share({ title: 'Power Notify - Lịch Cúp Điện', text, url });
    } catch {}
  } else {
    await navigator.clipboard.writeText(url);
    btnShare.textContent = '✅ Đã sao chép link!';
    setTimeout(() => (btnShare.textContent = '🔗 Chia sẻ trang này'), 2000);
  }
});

// ---------- Đếm ngược (tính trực tiếp trên trình duyệt) ----------

// Parse "13 tháng 7 năm 2026" + "Từ 08:00 đến 09:10" -> thời điểm bắt đầu (giờ VN, UTC+7)
function getStartTime(entry) {
  const d = /(\d{1,2})\s*tháng\s*(\d{1,2})\s*năm\s*(\d{4})/.exec(entry.ngay || '');
  const t = /(\d{1,2}):(\d{2})/.exec(entry.thoi_gian || '');
  if (!d || !t) return null;
  const [, day, month, year] = d.map(Number);
  const [, hour, min] = t.map(Number);
  return new Date(Date.UTC(year, month - 1, day, hour - 7, min));
}

function getSkeletonHtml(count) {
  let html = '';
  for (let i = 0; i < count; i++) {
    html += `
      <div class="skeleton">
        <div class="skeleton-line w-60"></div>
        <div class="skeleton-line w-90"></div>
        <div class="skeleton-line w-40"></div>
      </div>`;
  }
  return html;
}

function getStatusBadgeHtml(trangThai) {
  if (!trangThai) return '';
  const t = trangThai.trim();
  let cls = 'status-badge';
  if (t === 'Đã thực hiện') cls += ' status-done';
  else if (t === 'Đã duyệt') cls += ' status-approved';
  return `<span class="${cls}">${t}</span>`;
}

function getCountdownHtml(entry) {
  const start = getStartTime(entry);
  if (!start) return '';
  const diffMs = start - Date.now();
  if (diffMs <= 0) return '';
  const totalMin = Math.round(diffMs / 60000);
  const hours = Math.floor(totalMin / 60);
  return hours < 1
    ? `<div class="countdown">⏰ Còn ${totalMin} phút nữa</div>`
    : `<div class="countdown">⏰ Còn khoảng ${hours} tiếng nữa</div>`;
}

function getEmptyMineHtml() {
  return `
    <div class="empty-safe">
      <svg class="empty-safe-icon" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M8 30L32 10L56 30" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M14 26V52C14 53.1 14.9 54 16 54H48C49.1 54 50 53.1 50 52V26" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
        <circle cx="41" cy="45" r="11" fill="#0f1729" stroke="currentColor" stroke-width="3"/>
        <path d="M36 45L39.5 48.5L46.5 41" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <div class="empty-safe-text">An toàn. Không có lịch cúp điện nào cho khu vực của bạn.</div>
    </div>`;
}

function renderEntries(container, entries, showCountdown, isMine) {
  if (entries.length === 0) {
    container.innerHTML = isMine ? getEmptyMineHtml() : '<div class="empty">Không có lịch cúp điện nào.</div>';
    return;
  }
  container.innerHTML = entries.map((e, i) => {
    const countdown = showCountdown ? getCountdownHtml(e) : '';
    // delay tăng dần tạo hiệu ứng sóng (mỗi ô cách nhau 60ms)
    const delay = `animation-delay: ${i * 60}ms`;
    return `
      <div class="entry" style="${delay}">
        <div><b>${e.ngay}</b> — ${e.thoi_gian}</div>
        <div>${e.khu_vuc}</div>
        <div class="entry-meta">
          <span style="color:#94a3b8;font-size:0.78rem">${e.dien_luc}</span>
          ${getStatusBadgeHtml(e.trang_thai)}
        </div>
        ${countdown}
      </div>`;
  }).join('');
}

// ---------- Push notification ----------
function urlBase64ToUint8Array(b64) {
  const pad = '='.repeat((4 - b64.length % 4) % 4);
  const raw = atob((b64 + pad).replace(/-/g, '+').replace(/_/g, '/'));
  return Uint8Array.from([...raw].map(c => c.charCodeAt(0)));
}

async function subscribeToPush() {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    pushStatusEl.textContent = 'Trình duyệt không hỗ trợ thông báo đẩy.';
    pushStatusEl.className = 'status off'; return;
  }
  const perm = await Notification.requestPermission();
  if (perm !== 'granted') {
    pushStatusEl.textContent = 'Bạn chưa cho phép nhận thông báo.';
    pushStatusEl.className = 'status off'; return;
  }
  const reg = await navigator.serviceWorker.register('/sw.js');
  const { publicKey } = await fetch('/api/vapid-public-key').then(r => r.json());
  const sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: urlBase64ToUint8Array(publicKey) });
  await fetch('/api/subscribe', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(sub) });
  pushStatusEl.textContent = '✅ Đã bật thông báo! Sẽ nhận cảnh báo khi có lịch cúp điện trùng khu vực.';
  pushStatusEl.className = 'status on';
  btnSubscribe.textContent = '🔔 Đã bật thông báo';
  btnSubscribe.disabled = true;
}

btnSubscribe.addEventListener('click', () =>
  subscribeToPush().catch(err => {
    console.error(err);
    pushStatusEl.textContent = 'Có lỗi khi đăng ký thông báo.';
    pushStatusEl.className = 'status off';
  })
);

(async () => {
  if ('serviceWorker' in navigator) {
    const reg = await navigator.serviceWorker.getRegistration();
    if (reg) {
      const existing = await reg.pushManager.getSubscription();
      if (existing) {
        btnSubscribe.textContent = '🔔 Đã bật thông báo';
        btnSubscribe.disabled = true;
        pushStatusEl.textContent = '✅ Thông báo đang bật trên thiết bị này.';
        pushStatusEl.className = 'status on';
      }
    }
  }
})();
