const resultsEl = document.getElementById('results');
const pushStatusEl = document.getElementById('pushStatus');
const btnSubscribe = document.getElementById('btnSubscribe');

// Tự động quét ngay khi mở trang
runCheck();

async function runCheck() {
  resultsEl.innerHTML = '<div class="empty">Đang tải dữ liệu...</div>';
  try {
    const res = await fetch('/api/check');
    const data = await res.json();
    renderResults(data.entries || []);
  } catch (err) {
    resultsEl.innerHTML = '<div class="empty">Có lỗi xảy ra, thử lại sau.</div>';
  }
}

function renderResults(entries) {
  if (entries.length === 0) {
    resultsEl.innerHTML = '<div class="empty">Không có lịch cúp điện nào khớp khu vực của bạn.</div>';
    return;
  }
  resultsEl.innerHTML = entries
    .map((e) => {
      const countdown =
        e.hours_left != null
          ? e.hours_left < 1
            ? `<div style="color:#facc15; font-size:0.8rem;">⏰ Còn ${Math.round(e.hours_left * 60)} phút nữa</div>`
            : `<div style="color:#facc15; font-size:0.8rem;">⏰ Còn khoảng ${e.hours_left} tiếng nữa</div>`
          : '';
      return `
    <div class="entry">
      <div><b>${e.ngay}</b> — ${e.thoi_gian}</div>
      <div>${e.khu_vuc}</div>
      <div style="color:#94a3b8; font-size:0.8rem;">${e.dien_luc} • ${e.trang_thai}</div>
      ${countdown}
    </div>`;
    })
    .join('');
}

// ---------- Đăng ký push notification ----------
function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = atob(base64);
  return Uint8Array.from([...rawData].map((c) => c.charCodeAt(0)));
}

async function subscribeToPush() {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    pushStatusEl.textContent = 'Trình duyệt của bạn không hỗ trợ thông báo đẩy.';
    pushStatusEl.className = 'status off';
    return;
  }

  const permission = await Notification.requestPermission();
  if (permission !== 'granted') {
    pushStatusEl.textContent = 'Bạn chưa cho phép nhận thông báo.';
    pushStatusEl.className = 'status off';
    return;
  }

  const reg = await navigator.serviceWorker.register('/sw.js');
  const { publicKey } = await fetch('/api/vapid-public-key').then((r) => r.json());

  const sub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(publicKey),
  });

  await fetch('/api/subscribe', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(sub),
  });

  pushStatusEl.textContent = '✅ Đã bật thông báo! Bạn sẽ nhận cảnh báo khi có lịch cúp điện trùng khu vực.';
  pushStatusEl.className = 'status on';
  btnSubscribe.textContent = '🔔 Đã bật thông báo';
  btnSubscribe.disabled = true;
}

btnSubscribe.addEventListener('click', () => {
  subscribeToPush().catch((err) => {
    console.error(err);
    pushStatusEl.textContent = 'Có lỗi khi đăng ký thông báo.';
    pushStatusEl.className = 'status off';
  });
});

// Kiểm tra trạng thái đăng ký hiện có khi tải trang
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
