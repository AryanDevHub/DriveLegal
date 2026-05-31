/* ═══════════════════════════════════════════════════════════
   DriveLegal — app.js
   Global utilities shared across all pages
   ═══════════════════════════════════════════════════════════ */

  const API_BASE = '';

/* ─────────────────────────────────────────────────────────
   1. STATE MANAGEMENT
   ───────────────────────────────────────────────────────── */

// FIX: All values must be 2-letter state codes, not full names
const STATE_MAP = {
  'Madhya Pradesh': 'MP',
  'Maharashtra':    'MH',
  'Delhi':          'DL',
  'Karnataka':      'KA',
  'Tamil Nadu':     'TN',
  'Uttar Pradesh':  'UP',
  'Gujarat':        'GJ',
  'Rajasthan':      'RJ',
  'Andhra Pradesh': 'AP',
  'Telangana':      'TS'
};

const STATE_NAMES = {
  'MP': 'Madhya Pradesh',
  'MH': 'Maharashtra',
  'DL': 'Delhi',
  'KA': 'Karnataka',
  'TN': 'Tamil Nadu',
  'UP': 'Uttar Pradesh',
  'GJ': 'Gujarat',
  'RJ': 'Rajasthan',
  'AP': 'Andhra Pradesh',
  'TS': 'Telangana'
};

/**
 * Get currently selected state code (e.g. "MP")
 */
function getState() {
  const sel = document.getElementById('stateSelector');
  return sel ? sel.value : (localStorage.getItem('dl_state') || 'MP');
}

/**
 * Save state to localStorage and update all state selectors on page
 */
function saveState(code) {
  const val = code || getState();
  localStorage.setItem('dl_state', val);
  // Update all state selectors on the page
  document.querySelectorAll('.state-selector, #stateSelector').forEach(el => {
    el.value = val;
  });
  // Update any state labels
  document.querySelectorAll('#stateLabel, .state-label').forEach(el => {
    el.textContent = STATE_NAMES[val] || val;
  });
}

/**
 * Auto-detect user's state using browser GPS + Nominatim reverse geocoding
 */
async function detectLocation() {
  const statusEl = document.getElementById('locationStatus');

  if (!navigator.geolocation) {
    if (statusEl) statusEl.textContent = 'Location unavailable';
    return;
  }

  navigator.geolocation.getCurrentPosition(
    async (pos) => {
      try {
        const { latitude: lat, longitude: lon } = pos.coords;
        const res = await fetch(
          `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json`
        );
        const data = await res.json();
        const stateName = data.address?.state || '';
        const code = STATE_MAP[stateName];

        if (code) {
          saveState(code);
          if (statusEl) statusEl.textContent = `📍 ${stateName}`;
        } else {
          if (statusEl) statusEl.textContent = '📍 Location detected';
        }
      } catch {
        if (statusEl) statusEl.textContent = 'Select state above';
      }
    },
    () => {
      if (statusEl) statusEl.textContent = 'Select state above';
    },
    { timeout: 6000, maximumAge: 300000 }
  );
}

/**
 * Init state selector on any page
 * — loads saved state from localStorage
 * — falls back to GPS detection if none saved
 */
function initStateSelector() {
  const saved = localStorage.getItem('dl_state');
  const sel   = document.getElementById('stateSelector');

  if (saved && sel) {
    sel.value = saved;
    const label = document.getElementById('stateLabel');
    if (label) label.textContent = STATE_NAMES[saved] || saved;
  } else {
    detectLocation();
  }
}


/* ─────────────────────────────────────────────────────────
   2. API HELPERS
   ───────────────────────────────────────────────────────── */

/**
 * Generic API call wrapper with error handling
 * @param {string} endpoint  - e.g. '/chat'
 * @param {object} body      - request body
 * @returns {object|null}
 */
async function apiPost(endpoint, body) {
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(body)
    });

    if (!res.ok) {
      console.error(`API error ${res.status} on ${endpoint}`);
      return null;
    }

    return await res.json();
  } catch (err) {
    console.error(`Network error on ${endpoint}:`, err);
    return null;
  }
}

/**
 * Quick health check — is backend running?
 * @returns {boolean}
 */
async function checkBackend() {
  try {
    const res = await fetch(`${API_BASE}/`, { method: 'GET' });
    return res.ok;
  } catch {
    return false;
  }
}


/* ─────────────────────────────────────────────────────────
   3. UI UTILITIES
   ───────────────────────────────────────────────────────── */

/**
 * Show a toast notification at the bottom of screen
 * @param {string} message
 * @param {'success'|'error'|'warning'|'info'} type
 * @param {number} duration  milliseconds (default 3000)
 */
function showToast(message, type = 'info', duration = 3000) {
  // Remove existing toast
  const existing = document.getElementById('dl-toast');
  if (existing) existing.remove();

  const colors = {
    success: { bg: 'rgba(26,107,60,0.95)',  border: 'rgba(82,196,126,0.5)',  icon: '✅' },
    error:   { bg: 'rgba(180,30,30,0.95)',  border: 'rgba(220,60,60,0.5)',   icon: '❌' },
    warning: { bg: 'rgba(150,100,0,0.95)',  border: 'rgba(230,160,0,0.5)',   icon: '⚠️' },
    info:    { bg: 'rgba(20,40,28,0.95)',   border: 'rgba(82,196,126,0.3)',  icon: 'ℹ️' }
  };

  const c = colors[type] || colors.info;

  const toast = document.createElement('div');
  toast.id = 'dl-toast';
  toast.style.cssText = `
    position: fixed; bottom: 24px; left: 50%;
    transform: translateX(-50%) translateY(80px);
    background: ${c.bg};
    border: 1px solid ${c.border};
    color: #e8f5ec; padding: 13px 22px;
    border-radius: 12px; font-family: 'DM Sans', sans-serif;
    font-size: 0.9rem; font-weight: 500;
    display: flex; align-items: center; gap: 10px;
    z-index: 9999; max-width: 360px; text-align: center;
    backdrop-filter: blur(12px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    transition: transform 0.3s cubic-bezier(0.34,1.56,0.64,1), opacity 0.3s ease;
  `;
  toast.innerHTML = `<span>${c.icon}</span><span>${message}</span>`;
  document.body.appendChild(toast);

  // Animate in
  requestAnimationFrame(() => {
    toast.style.transform = 'translateX(-50%) translateY(0)';
  });

  // Animate out and remove
  setTimeout(() => {
    toast.style.transform = 'translateX(-50%) translateY(80px)';
    toast.style.opacity   = '0';
    setTimeout(() => toast.remove(), 320);
  }, duration);
}

/**
 * Show a full-page loading overlay
 * @param {string} message
 */
function showPageLoader(message = 'Loading…') {
  let overlay = document.getElementById('dl-page-loader');

  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'dl-page-loader';
    overlay.style.cssText = `
      position: fixed; inset: 0; z-index: 8888;
      background: rgba(10,15,13,0.88);
      backdrop-filter: blur(8px);
      display: flex; flex-direction: column;
      align-items: center; justify-content: center;
      gap: 20px; font-family: 'DM Sans', sans-serif;
    `;
    overlay.innerHTML = `
      <div style="
        width: 56px; height: 56px; border-radius: 50%;
        border: 3px solid rgba(82,196,126,0.2);
        border-top-color: #52c47e;
        animation: dl-spin 0.9s linear infinite;
      "></div>
      <p id="dl-loader-text" style="color:#7a9b82; font-size:0.95rem;"></p>
      <style>
        @keyframes dl-spin { to { transform: rotate(360deg); } }
      </style>
    `;
    document.body.appendChild(overlay);
  }

  document.getElementById('dl-loader-text').textContent = message;
  overlay.style.display = 'flex';
}

/**
 * Hide the full-page loading overlay
 */
function hidePageLoader() {
  const overlay = document.getElementById('dl-page-loader');
  if (overlay) overlay.style.display = 'none';
}

/**
 * Format a number as Indian currency string
 * @param {number} amount
 * @returns {string}  e.g. "₹1,000"
 */
function formatINR(amount) {
  if (!amount && amount !== 0) return '—';
  return '₹' + Number(amount).toLocaleString('en-IN');
}

/**
 * Highlight ₹ amounts in a string with a styled span
 * @param {string} text
 * @returns {string}  HTML string
 */
function highlightAmounts(text) {
  return text.replace(
    /₹[\d,]+/g,
    m => `<span class="fine-highlight">${m}</span>`
  );
}

/**
 * Escape HTML special characters (prevent XSS)
 * @param {string} str
 * @returns {string}
 */
function escapeHTML(str) {
  return String(str)
    .replace(/&/g,  '&amp;')
    .replace(/</g,  '&lt;')
    .replace(/>/g,  '&gt;')
    .replace(/"/g,  '&quot;')
    .replace(/'/g,  '&#039;');
}

/**
 * Convert newlines to <br> tags
 * @param {string} text
 * @returns {string}
 */
function nl2br(text) {
  return String(text).replace(/\n/g, '<br/>');
}

/**
 * Auto-resize a textarea to fit its content
 * @param {HTMLTextAreaElement} el
 * @param {number} maxHeight  px (default 140)
 */
function autoResize(el, maxHeight = 140) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, maxHeight) + 'px';
}

/**
 * Smooth scroll to an element
 * @param {string|HTMLElement} target  selector string or element
 */
function scrollTo(target) {
  const el = typeof target === 'string'
    ? document.querySelector(target)
    : target;
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/**
 * Copy text to clipboard and show a toast
 * @param {string} text
 * @param {string} label  (what was copied, for toast message)
 */
async function copyToClipboard(text, label = 'Text') {
  try {
    await navigator.clipboard.writeText(text);
    showToast(`${label} copied!`, 'success', 2000);
  } catch {
    showToast('Could not copy. Please copy manually.', 'error');
  }
}

/**
 * Native share or clipboard fallback
 * @param {object} shareData  { title, text, url }
 */
async function shareContent(shareData) {
  if (navigator.share) {
    try {
      await navigator.share(shareData);
    } catch { /* user cancelled */ }
  } else {
    copyToClipboard(shareData.url || window.location.href, 'Link');
  }
}


/* ─────────────────────────────────────────────────────────
   4. VOICE INPUT
   ───────────────────────────────────────────────────────── */

let _recognition     = null;
let _voiceListening  = false;

/**
 * Start voice recognition and put result in a text input/textarea
 * @param {HTMLElement} targetInput  - input or textarea to fill
 * @param {Function}    onResult     - optional callback(transcript)
 * @param {string}      lang         - BCP-47 language (default 'hi-IN')
 */
function startVoiceInput(targetInput, onResult = null, lang = 'hi-IN') {
  const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;

  if (!SpeechRecognition) {
    showToast('Voice input not supported. Use Chrome browser.', 'warning');
    return;
  }

  if (_voiceListening) {
    _recognition?.stop();
    return;
  }

  _recognition = new SpeechRecognition();
  _recognition.lang            = lang;
  _recognition.interimResults  = false;
  _recognition.maxAlternatives = 1;

  _recognition.onstart = () => {
    _voiceListening = true;
    showToast('Listening… speak now', 'info', 5000);
    // Add listening class to any voice buttons
    document.querySelectorAll('.voice-btn').forEach(btn => {
      btn.classList.add('listening');
      btn.textContent = '🔴';
    });
  };

  _recognition.onresult = (e) => {
    const transcript = e.results[0][0].transcript;
    if (targetInput) {
      targetInput.value = transcript;
      autoResize(targetInput);
    }
    if (typeof onResult === 'function') onResult(transcript);
  };

  _recognition.onend = () => {
    _voiceListening = false;
    document.querySelectorAll('.voice-btn').forEach(btn => {
      btn.classList.remove('listening');
      btn.textContent = '🎙️';
    });
  };

  _recognition.onerror = (e) => {
    _voiceListening = false;
    document.querySelectorAll('.voice-btn').forEach(btn => {
      btn.classList.remove('listening');
      btn.textContent = '🎙️';
    });
    if (e.error !== 'aborted') {
      showToast('Voice recognition failed. Try again.', 'error');
    }
  };

  _recognition.start();
}


/* ─────────────────────────────────────────────────────────
   5. BACKEND STATUS BANNER
   ───────────────────────────────────────────────────────── */

/**
 * Check backend health and show a warning banner if offline
 */
async function checkBackendStatus() {
  const online = await checkBackend();

  if (!online) {
    // Show a dismissable top banner
    const existing = document.getElementById('backend-banner');
    if (existing) return;

    const banner = document.createElement('div');
    banner.id = 'backend-banner';
    banner.style.cssText = `
      background: rgba(180,80,0,0.9); color: #ffe0b2;
      padding: 10px 20px; font-size: 0.85rem;
      font-family: 'DM Sans', sans-serif;
      display: flex; align-items: center; justify-content: space-between;
      gap: 12px; position: relative; z-index: 200;
      border-bottom: 1px solid rgba(230,120,0,0.4);
    `;
    banner.innerHTML = `
      <span>⚠️ Backend server not running. Start it with: <code style="background:rgba(0,0,0,0.2);padding:2px 6px;border-radius:4px;">python app.py</code></span>
      <button onclick="this.parentElement.remove()" style="background:transparent;border:none;color:#ffe0b2;font-size:1.1rem;cursor:pointer;padding:0 4px;">✕</button>
    `;

    // Insert after topbar or at top of body
    const topbar = document.querySelector('.topbar');
    if (topbar) topbar.after(banner);
    else document.body.prepend(banner);
  }
}


/* ─────────────────────────────────────────────────────────
   6. FINE CALCULATOR HELPER (used on multiple pages)
   ───────────────────────────────────────────────────────── */

/**
 * Calculate fine via API
 * @param {string} violation
 * @param {string} state
 * @param {string} vehicle
 * @param {boolean} repeat
 * @returns {object|null}
 */
async function calculateFine(violation, state, vehicle, repeat = false) {
  return await apiPost('/calculate', { violation, state, vehicle, repeat });
}


/* ─────────────────────────────────────────────────────────
   7. OFFLINE DATA CACHE
   ───────────────────────────────────────────────────────── */

const CACHE_KEY    = 'dl_fines_cache';
const CACHE_EXPIRY = 24 * 60 * 60 * 1000; // 24 hours

/**
 * Cache violations list from backend for offline use
 */
async function cacheFinesData() {
  try {
    const res  = await fetch(`${API_BASE}/violations`);
    const data = await res.json();
    const payload = {
      data:      data.violations,
      timestamp: Date.now()
    };
    localStorage.setItem(CACHE_KEY, JSON.stringify(payload));
    return data.violations;
  } catch {
    return null;
  }
}

/**
 * Get violations — from cache if fresh, else from API
 * @returns {Array|null}
 */
async function getViolations() {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (raw) {
      const cached = JSON.parse(raw);
      if (Date.now() - cached.timestamp < CACHE_EXPIRY) {
        return cached.data;
      }
    }
  } catch { /* bad cache */ }

  return await cacheFinesData();
}


/* ─────────────────────────────────────────────────────────
   8. KEYBOARD SHORTCUTS
   ───────────────────────────────────────────────────────── */

/**
 * Register global keyboard shortcuts
 * Alt+C → chatbot, Alt+S → scanner, Alt+R → route, Alt+M → cop mode
 */
function registerShortcuts() {
  document.addEventListener('keydown', (e) => {
    if (!e.altKey) return;
    const shortcuts = {
      'c': 'chatbot.html',
      's': 'scanner.html',
      'r': 'route.html',
      'k': 'calculator.html',
      'm': 'copmode.html'
    };
    const target = shortcuts[e.key.toLowerCase()];
    if (target && !window.location.href.includes(target)) {
      e.preventDefault();
      window.location.href = target;
    }
  });
}


/* ─────────────────────────────────────────────────────────
   9. DATE / TIME HELPERS
   ───────────────────────────────────────────────────────── */

/**
 * Get current time as "HH:MM" string (for chat timestamps)
 * @returns {string}
 */
function nowTime() {
  return new Date().toLocaleTimeString('en-IN', {
    hour: '2-digit', minute: '2-digit'
  });
}

/**
 * Get current date as readable string
 * @returns {string}  e.g. "31 May 2026"
 */
function nowDate() {
  return new Date().toLocaleDateString('en-IN', {
    day: 'numeric', month: 'long', year: 'numeric'
  });
}


/* ─────────────────────────────────────────────────────────
   10. INIT — runs on every page load
   ───────────────────────────────────────────────────────── */

document.addEventListener('DOMContentLoaded', () => {
  initStateSelector();
  registerShortcuts();

  // Check backend health after a short delay
  // (so it doesn't block page render)
  setTimeout(checkBackendStatus, 1200);

  // Add keyboard shortcut hint to console
  console.log(
    '%cDriveLegal 🚗⚖️\n%cKeyboard shortcuts:\n' +
    'Alt+C → Chatbot  Alt+S → Scanner\n' +
    'Alt+R → Route    Alt+K → Calculator  Alt+M → Cop Mode',
    'color:#52c47e;font-size:1.2rem;font-weight:bold;',
    'color:#7a9b82;font-size:0.9rem;'
  );
});