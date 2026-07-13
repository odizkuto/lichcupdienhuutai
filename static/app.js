const pushStatusEl = document.getElementById('pushStatus');
const btnSubscribe  = document.getElementById('btnSubscribe');
const resultsAllEl  = document.getElementById('resultsAll');
const resultsMineEl = document.getElementById('resultsMine');
const badgeAll      = document.getElementById('badgeAll');
const badgeMine     = document.getElementById('badgeMine');

// Tự động tải cả 2 cột khi mở trang
loadAll();
loadMine();

async function loadAll() {
  resultsAllEl.innerHTML = '<div class="empty">Đang tải...</div>';
  try {
    const res  = await fetch('/api/check-all');
    const data = await res.json();
    const entries = data.entries || [];
    badgeAll.textContent = entries.length;
    renderEntries(resultsAllEl, entries, false);
  } catch {
    resultsAllEl.innerHTML = '<div class="empty">Có lỗi, thử lại sau.</div>';
    badgeAll.textContent = '!';
  }
}

async function loadMine() {
  resultsMineEl.innerHTML = '<div class="empty">Đang tải...</div>';
  try {
    const res  = await fetch('/api/check');
    const data = await res.json();
    const entries = data.entries || [];
    badgeMine.textContent = entries.length;
    renderEntries(resultsMineEl, entries, true);
  } catch {
    resultsMineEl.innerHTML = '<div class="empty">Có lỗi, thử lại sau.</div>';
    badgeMine.textContent = '!';
  }
}

function renderEntries(container, entries, showCountdown) {
  if (entries.length === 0) {
    container.innerHTML = '<div class="empty">Không có lịch cúp điện nào.</div>';
    return;
  }
  container.innerHTML = entries.map((e) => {
    let countdown = '';
    if (showCountdown && e.hours_left != null) {
      countdown = e.hours_left < 1
        ? `<div class="countdown">⏰ Còn ${Math.round(e.hours_left * 60)} phút nữa</div>`
        : `<div class="countdown">⏰ Còn khoảng ${e.hours_left} tiếng nữa</div>`;
    }
    return `
      <div class="entry">
        <div><b>${e.ngay}</b> — ${e.thoi_gian}</div>
        <div>${e.khu_vuc}</div>
        <div style="color:#94a3b8;font-size:0.78rem">${e.dien_luc} • ${e.trang_thai}</div>
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
