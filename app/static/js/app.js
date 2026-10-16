// Generic In-App Modal Dialog Manager (replaces browser alert, confirm, prompt)
const AppModal = {
  activeResolver: null,

  _esc(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  },

  alert({ title = "Upozornění", message = "", confirmText = "Rozumím" } = {}) {
    return new Promise((resolve) => {
      this.activeResolver = () => resolve(true);
      const backdrop = document.getElementById('app-modal-backdrop');
      const titleEl = document.getElementById('app-modal-title');
      const bodyEl = document.getElementById('app-modal-body');
      const actionsEl = document.getElementById('app-modal-actions');
      if (!backdrop || !bodyEl) {
        return resolve(true);
      }

      titleEl.textContent = title;
      bodyEl.innerHTML = `<p style="margin:0; font-size:0.9rem; line-height:1.5; color:var(--text-main);">${this._esc(message)}</p>`;
      actionsEl.innerHTML = `
        <button type="button" class="btn btn-primary btn-sm" id="app-modal-ok-btn">${this._esc(confirmText)}</button>
      `;

      backdrop.style.display = 'flex';
      const okBtn = document.getElementById('app-modal-ok-btn');
      if (okBtn) {
        okBtn.focus();
        okBtn.onclick = () => this.close(true);
      }
    });
  },

  confirm({ title = "Potvrzení akce", message = "Opravdu chcete provést tuto akci?", confirmText = "Potvrdit", cancelText = "Zrušit", danger = false } = {}) {
    return new Promise((resolve) => {
      this.activeResolver = (val) => resolve(!!val);
      const backdrop = document.getElementById('app-modal-backdrop');
      const titleEl = document.getElementById('app-modal-title');
      const bodyEl = document.getElementById('app-modal-body');
      const actionsEl = document.getElementById('app-modal-actions');
      if (!backdrop || !bodyEl) {
        return resolve(false);
      }

      titleEl.textContent = title;
      bodyEl.innerHTML = `<p style="margin:0; font-size:0.9rem; line-height:1.5; color:var(--text-main);">${this._esc(message)}</p>`;
      actionsEl.innerHTML = `
        <button type="button" class="btn btn-secondary btn-sm" id="app-modal-cancel-btn">${this._esc(cancelText)}</button>
        <button type="button" class="btn ${danger ? 'btn-danger' : 'btn-primary'} btn-sm" id="app-modal-confirm-btn">${this._esc(confirmText)}</button>
      `;

      backdrop.style.display = 'flex';
      const cBtn = document.getElementById('app-modal-confirm-btn');
      const cancelBtn = document.getElementById('app-modal-cancel-btn');
      if (cancelBtn) cancelBtn.onclick = () => this.close(false);
      if (cBtn) {
        cBtn.focus();
        cBtn.onclick = () => this.close(true);
      }
    });
  },

  prompt({ title = "Zadání hodnoty", message = "", defaultValue = "", placeholder = "", confirmText = "Uložit", cancelText = "Zrušit", inputType = "text" } = {}) {
    return new Promise((resolve) => {
      this.activeResolver = (val) => resolve(val);
      const backdrop = document.getElementById('app-modal-backdrop');
      const titleEl = document.getElementById('app-modal-title');
      const bodyEl = document.getElementById('app-modal-body');
      const actionsEl = document.getElementById('app-modal-actions');
      if (!backdrop || !bodyEl) {
        return resolve(null);
      }

      titleEl.textContent = title;
      bodyEl.innerHTML = `
        ${message ? `<p style="margin:0 0 10px 0; font-size:0.88rem; color:var(--text-main);">${this._esc(message)}</p>` : ''}
        <input type="${inputType}" id="app-modal-prompt-input" class="form-control" value="${this._esc(String(defaultValue || ''))}" placeholder="${this._esc(placeholder)}" style="width:100%; box-sizing:border-box;">
      `;
      actionsEl.innerHTML = `
        <button type="button" class="btn btn-secondary btn-sm" id="app-modal-cancel-btn">${this._esc(cancelText)}</button>
        <button type="button" class="btn btn-primary btn-sm" id="app-modal-confirm-btn">${this._esc(confirmText)}</button>
      `;

      backdrop.style.display = 'flex';
      const inp = document.getElementById('app-modal-prompt-input');
      const cBtn = document.getElementById('app-modal-confirm-btn');
      const cancelBtn = document.getElementById('app-modal-cancel-btn');
      if (cancelBtn) cancelBtn.onclick = () => this.close(null);

      const submit = () => {
        const val = inp ? inp.value : '';
        this.close(val);
      };

      if (cBtn) cBtn.onclick = submit;
      if (inp) {
        inp.focus();
        inp.select();
        inp.onkeydown = (e) => {
          if (e.key === 'Enter') {
            e.preventDefault();
            submit();
          } else if (e.key === 'Escape') {
            e.preventDefault();
            this.close(null);
          }
        };
      }
    });
  },

  showForm({ title = "Formulář", fields = [], confirmText = "Uložit", cancelText = "Zrušit" } = {}) {
    return new Promise((resolve) => {
      this.activeResolver = (val) => resolve(val);
      const backdrop = document.getElementById('app-modal-backdrop');
      const titleEl = document.getElementById('app-modal-title');
      const bodyEl = document.getElementById('app-modal-body');
      const actionsEl = document.getElementById('app-modal-actions');
      if (!backdrop || !bodyEl) return resolve(null);

      titleEl.textContent = title;
      
      const formHtml = fields.map(f => {
        if (f.type === 'select') {
          const opts = (f.options || []).map(o => {
            const val = typeof o === 'object' ? o.value : o;
            const lbl = typeof o === 'object' ? o.label : o;
            const sel = String(val) === String(f.value) ? 'selected' : '';
            return `<option value="${this._esc(String(val))}" ${sel}>${this._esc(String(lbl))}</option>`;
          }).join('');
          return `
            <div class="form-group" style="margin-bottom:12px;">
              <label class="form-label" style="font-size:0.82rem; font-weight:600; display:block; margin-bottom:4px;">${this._esc(f.label)}</label>
              <select id="modal-field-${f.id}" class="form-control" style="width:100%;">${opts}</select>
            </div>
          `;
        } else if (f.type === 'textarea') {
          return `
            <div class="form-group" style="margin-bottom:12px;">
              <label class="form-label" style="font-size:0.82rem; font-weight:600; display:block; margin-bottom:4px;">${this._esc(f.label)}</label>
              <textarea id="modal-field-${f.id}" class="form-control" rows="${f.rows || 3}" style="width:100%; box-sizing:border-box;">${this._esc(String(f.value || ''))}</textarea>
            </div>
          `;
        } else {
          const stepAttr = f.step ? `step="${f.step}"` : '';
          const minAttr = f.min !== undefined ? `min="${f.min}"` : '';
          return `
            <div class="form-group" style="margin-bottom:12px;">
              <label class="form-label" style="font-size:0.82rem; font-weight:600; display:block; margin-bottom:4px;">${this._esc(f.label)}</label>
              <input type="${f.type || 'text'}" id="modal-field-${f.id}" class="form-control" value="${this._esc(String(f.value !== undefined ? f.value : ''))}" ${stepAttr} ${minAttr} style="width:100%; box-sizing:border-box;">
            </div>
          `;
        }
      }).join('');

      bodyEl.innerHTML = `<form id="app-modal-form" onsubmit="event.preventDefault();">${formHtml}</form>`;
      actionsEl.innerHTML = `
        <button type="button" class="btn btn-secondary btn-sm" id="app-modal-cancel-btn">${this._esc(cancelText)}</button>
        <button type="button" class="btn btn-primary btn-sm" id="app-modal-confirm-btn">${this._esc(confirmText)}</button>
      `;

      backdrop.style.display = 'flex';
      const cBtn = document.getElementById('app-modal-confirm-btn');
      const cancelBtn = document.getElementById('app-modal-cancel-btn');
      if (cancelBtn) cancelBtn.onclick = () => this.close(null);

      const collect = () => {
        const result = {};
        for (const f of fields) {
          const el = document.getElementById(`modal-field-${f.id}`);
          if (el) {
            result[f.id] = f.type === 'number' ? (parseFloat(el.value) || 0) : el.value;
          }
        }
        this.close(result);
      };

      if (cBtn) cBtn.onclick = collect;
      const firstInp = bodyEl.querySelector('input, select, textarea');
      if (firstInp) {
        firstInp.focus();
        if (firstInp.select) firstInp.select();
      }
    });
  },

  close(result = null) {
    const backdrop = document.getElementById('app-modal-backdrop');
    if (backdrop) backdrop.style.display = 'none';
    if (this.activeResolver) {
      const res = this.activeResolver;
      this.activeResolver = null;
      res(result);
    }
  }
};
window.AppModal = AppModal;

// Main Application Controller with Dark Mode, Settings Overlay, Acrobat Tools, and Role-Based Access
const App = {
  currentUser: null,
  semesters: [],
  activeSemesterId: null,
  slots: [],
  measurements: [],
  commentPresets: [],
  deductionPresets: [],
  currentProtocol: null,
  currentProtocolIndex: -1,
  loadedProtocols: [],
  allUsers: [],
  currentView: 'dashboard',
  layoutMode: localStorage.getItem('praktika_layout_mode') || 'split',
  toolbarPos: localStorage.getItem('praktika_toolbar_pos') || 'vertical',
  theme: localStorage.getItem('praktika_theme') || 'light',
  aiDrawerDockSide: localStorage.getItem('praktika_ai_dock_side') || 'right',
  aiDrawerFloating: localStorage.getItem('praktika_ai_floating') === 'true',
  selectedProtocolIds: new Set(),

  async init() {
    this.applyTheme(this.theme);
    await this.checkAuth();
    await this.loadInitialMetadata();
    await this.loadPresets();
    this.setupEventListeners();
    this.setupGradingDockDrag();
    this.setupAIDrawerDrag();
    this.setupAllPanelResizers();
    this.checkAIKeyStatus();
    this.showView('dashboard');
    this.applyLayoutMode();
    this.applyToolbarPosition();

    // Background interval check for autosave every 30 seconds
    setInterval(() => {
      if (this.isDirty && this.currentView === 'studio') {
        this.triggerAutosave();
      }
    }, 30000);
  },

  // Theme Management
  applyTheme(theme) {
    this.theme = theme;
    localStorage.setItem('praktika_theme', theme);
    document.documentElement.setAttribute('data-theme', theme);
    const themeIcon = document.getElementById('theme-toggle-icon');
    const themeLabel = document.getElementById('theme-toggle-label');
    if (themeIcon) {
      themeIcon.textContent = theme === 'dark' ? '☀️' : '🌙';
    }
    if (themeLabel) {
      themeLabel.textContent = theme === 'dark' ? 'Světlý režim' : 'Tmavý režim';
    }
  },

  toggleTheme() {
    const next = this.theme === 'dark' ? 'light' : 'dark';
    this.applyTheme(next);
    this.showToast(next === 'dark' ? 'Tmavý režim aktivován' : 'Světlý režim aktivován');
  },

  // Toolbar position (Vertical Acrobat style vs Horizontal)
  applyToolbarPosition() {
    const studio = document.getElementById('studio-wrapper');
    if (!studio) return;
    if (this.toolbarPos === 'vertical') {
      studio.classList.add('toolbar-vertical');
    } else {
      studio.classList.remove('toolbar-vertical');
    }
  },

  setToolbarPosition(pos) {
    this.toolbarPos = pos;
    localStorage.setItem('praktika_toolbar_pos', pos);
    this.applyToolbarPosition();
  },

  // Auth & Roles
  async checkAuth() {
    try {
      const resp = await fetch('/api/auth/me');
      if (resp.ok) {
        this.currentUser = await resp.json();
        this.updateUserUI();
      } else {
        this.showLoginModal();
      }
    } catch(e) {
      this.showLoginModal();
    }
  },

  updateUserUI() {
    const userBadge = document.getElementById('user-profile-badge');
    if (userBadge && this.currentUser) {
      const roleText = this.currentUser.role === 'admin' ? 'Správce aplikace' : 'Asistent';
      const parts = (this.currentUser.full_name || 'U').split(' ').filter(p => p && !p.includes('.'));
      const initials = (parts.length >= 2 ? (parts[0][0] + parts[parts.length - 1][0]) : (parts[0] || 'U').slice(0, 2)).toUpperCase();
      userBadge.innerHTML = `
        <div class="sidebar-user-pill" onclick="App.openSwitchUserModal()" title="${this.escape(this.currentUser.full_name)} (${roleText}) – Kliknutím změníte uživatele">
          <div class="user-avatar-badge">${initials}</div>
          <div class="user-details">
            <div class="user-name" title="${this.escape(this.currentUser.full_name)}">${this.escape(this.currentUser.full_name)}</div>
            <div class="user-role">${roleText}</div>
          </div>
          <div class="user-switch-indicator" title="Změnit uživatele">⇄</div>
        </div>
      `;
    }
  },

  openSwitchUserModal() {
    const modal = document.getElementById('switch-user-modal');
    const info = document.getElementById('switch-user-current-info');
    if (info && this.currentUser) {
      info.textContent = `Přihlášen: ${this.currentUser.full_name} (@${this.currentUser.username})`;
    }
    const userInp = document.getElementById('switch-username');
    const pwInp = document.getElementById('switch-password');
    if (userInp) userInp.value = '';
    if (pwInp) pwInp.value = '';
    if (modal) {
      modal.classList.add('active');
      if (userInp) setTimeout(() => userInp.focus(), 60);
    }
  },

  closeSwitchUserModal() {
    const modal = document.getElementById('switch-user-modal');
    if (modal) modal.classList.remove('active');
  },

  async handleSwitchUser(e) {
    if (e) e.preventDefault();
    const username = document.getElementById('switch-username').value.trim();
    const password = document.getElementById('switch-password').value;

    try {
      const resp = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      if (resp.ok) {
        const data = await resp.json();
        this.currentUser = data.user;
        this.closeSwitchUserModal();
        this.updateUserUI();
        await this.loadInitialMetadata();
        this.showToast(`Přepnuto na uživatele: ${this.currentUser.full_name}`);
        if (this.currentView === 'dashboard') {
          this.loadProtocols();
        }
      } else {
        await AppModal.alert({ title: "Chyba přihlášení", message: "Chybné uživatelské jméno nebo heslo." });
      }
    } catch(err) {
      await AppModal.alert({ title: "Chyba přihlášení", message: "Chyba při změně uživatele: " + err.message });
    }
  },

  async logout() {
    await fetch('/api/auth/logout', { method: 'POST' });
    this.currentUser = null;
    window.location.reload();
  },

  showLoginModal() {
    const modal = document.getElementById('login-modal');
    if (modal) modal.classList.add('active');
  },

  hideLoginModal() {
    const modal = document.getElementById('login-modal');
    if (modal) modal.classList.remove('active');
  },

  async handleLogin(e) {
    if (e) e.preventDefault();
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;

    try {
      const resp = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      if (resp.ok) {
        const data = await resp.json();
        this.currentUser = data.user;
        this.hideLoginModal();
        this.updateUserUI();
        await this.loadInitialMetadata();
        this.showToast(`Vítejte, ${this.currentUser.full_name}!`);
      } else {
        await AppModal.alert({ title: "Chyba přihlášení", message: "Chybné uživatelské jméno nebo heslo." });
      }
    } catch(err) {
      await AppModal.alert({ title: "Chyba přihlášení", message: "Chyba při přihlašování: " + err.message });
    }
  },

  // Metadata Loading
  async loadInitialMetadata() {
    try {
      const [semResp, measResp] = await Promise.all([
        fetch('/api/semesters'),
        fetch('/api/measurements')
      ]);

      if (semResp.ok) {
        this.semesters = await semResp.json();
        const active = this.semesters.find(s => s.is_active);
        this.activeSemesterId = active ? active.id : (this.semesters[0] ? this.semesters[0].id : null);
        this.renderSemesterSelectors();
      }

      if (measResp.ok) {
        this.measurements = await measResp.json();
        this.renderMeasurementSelectors();
      }

      await this.loadSlotsForSemester(this.activeSemesterId);

      if (this.currentUser && this.currentUser.role === 'admin') {
        try {
          const uResp = await fetch('/api/users');
          if (uResp.ok) {
            this.allUsers = await uResp.json();
            this.populateEvaluatorFilterOptions();
          }
        } catch(e) {}
      }

      await this.loadProtocols();
    } catch (e) {
      console.error("Error loading metadata:", e);
    }
  },

  async loadSlotsForSemester(semId) {
    if (!semId) return;
    try {
      const resp = await fetch(`/api/slots?semester_id=${semId}`);
      if (resp.ok) {
        this.slots = await resp.json();
        this.renderSlotSelectors();
      }
    } catch(e) {
      console.error("Error loading slots:", e);
    }
  },

  async loadPresets() {
    try {
      const [commResp, dedResp] = await Promise.all([
        fetch('/api/presets?type=comment'),
        fetch('/api/presets?type=deduction')
      ]);
      if (commResp.ok) {
        const data = await commResp.json();
        this.commentPresets = data.map(p => p.text);
      }
      if (dedResp.ok) {
        this.deductionPresets = await dedResp.json();
      }
    } catch(e) {
      console.warn("Could not load presets:", e);
    }
  },

  renderSemesterSelectors() {
    const globalSelect = document.getElementById('global-semester-select');
    const filterSelect = document.getElementById('filter-semester-select');
    const uploadSelect = document.getElementById('upload-semester-select');

    const options = this.semesters.map(s => `
      <option value="${s.id}" ${s.id === this.activeSemesterId ? 'selected' : ''}>${s.code} (${s.name})</option>
    `).join('');

    if (globalSelect) {
      globalSelect.innerHTML = options;
      globalSelect.onchange = (e) => {
        this.handleGlobalSemesterChange(e.target.value);
      };
    }
    if (filterSelect) {
      filterSelect.innerHTML = `<option value="">Všechny semestry</option>` + options;
      if (this.activeSemesterId) filterSelect.value = this.activeSemesterId;
    }
    if (uploadSelect) {
      uploadSelect.innerHTML = options;
      if (this.activeSemesterId) uploadSelect.value = this.activeSemesterId;
    }
  },

  async handleGlobalSemesterChange(val) {
    const semId = parseInt(val);
    if (!semId) return;
    this.activeSemesterId = semId;

    try {
      await fetch(`/api/semesters/${semId}/activate`, { method: 'POST' });
    } catch (e) {
      console.warn("Could not activate semester on server:", e);
    }

    const filterSelect = document.getElementById('filter-semester-select');
    if (filterSelect) filterSelect.value = semId;
    const uploadSelect = document.getElementById('upload-semester-select');
    if (uploadSelect) uploadSelect.value = semId;

    await this.loadSlotsForSemester(semId);
    await this.loadProtocols();
    this.showToast("Aktivní semestr změněn a protokoly načteny.");
  },

  renderSlotSelectors() {
    const filterSelect = document.getElementById('filter-slot-select');
    const uploadSelect = document.getElementById('upload-slot-select');

    const options = this.slots.map(sl => {
      const coursePrefix = sl.course_code ? `[${sl.course_code}] ` : '';
      return `<option value="${sl.id}" data-course="${sl.course_code || 'FPRA1'}">${coursePrefix}${sl.day_of_week} ${sl.time_start}–${sl.time_end}</option>`;
    }).join('');

    if (filterSelect) filterSelect.innerHTML = `<option value="">Všechny termíny</option>` + options;
    if (uploadSelect) {
      uploadSelect.innerHTML = options;
      this.handleUploadSlotChange();
    }
  },

  handleUploadSlotChange() {
    const uploadSlot = document.getElementById('upload-slot-select');
    const uploadMeas = document.getElementById('upload-measurement-select');
    if (!uploadSlot || !uploadMeas) return;

    const selectedOpt = uploadSlot.options[uploadSlot.selectedIndex];
    const course = selectedOpt ? selectedOpt.getAttribute('data-course') : null;
    const currentVal = uploadMeas.value;

    const filtered = course
      ? this.measurements.filter(m => !m.course_code || m.course_code === course)
      : this.measurements;

    uploadMeas.innerHTML = (filtered.length > 0 ? filtered : this.measurements).map(m => `
      <option value="${m.id}">Úloha ${m.number}: ${m.name}</option>
    `).join('');

    if (currentVal && Array.from(uploadMeas.options).some(o => o.value === currentVal)) {
      uploadMeas.value = currentVal;
    }
  },

  renderMeasurementSelectors() {
    const filterSelect = document.getElementById('filter-measurement-select');
    const uploadSelect = document.getElementById('upload-measurement-select');

    const options = this.measurements.map(m => `
      <option value="${m.id}">Úloha ${m.number}: ${m.name}</option>
    `).join('');

    if (filterSelect) filterSelect.innerHTML = `<option value="">Všechny úlohy</option>` + options;
    if (uploadSelect) uploadSelect.innerHTML = options;
  },

  // View Navigation
  showView(viewName) {
    this.currentView = viewName;
    document.querySelectorAll('.view-section').forEach(el => el.style.display = 'none');
    document.querySelectorAll('.sidebar-nav-btn, .nav-link').forEach(el => el.classList.remove('active'));

    const targetEl = document.getElementById(`view-${viewName}`);
    const navBtn = document.getElementById(`nav-btn-${viewName}`);
    if (targetEl) targetEl.style.display = viewName === 'studio' ? 'flex' : 'block';
    if (navBtn) navBtn.classList.add('active');

    // Auto-collapse sidebar in studio mode for maximum screen estate, expand in dashboard
    const sidebar = document.getElementById('app-sidebar');
    if (sidebar) {
      if (viewName === 'studio') {
        sidebar.classList.add('collapsed');
      } else {
        sidebar.classList.remove('collapsed');
      }
    }

    if (viewName === 'dashboard') {
      this.loadProtocols();
    } else if (viewName === 'management') {
      this.loadManagementTables();
    }
  },

  toggleSidebarCollapse() {
    const sb = document.getElementById('app-sidebar');
    if (sb) {
      sb.classList.toggle('collapsed');
    }
  },

  toggleGradingDock() {
    const dock = document.getElementById('studio-grading-dock');
    if (!dock) return;
    const isOpening = (dock.style.display === 'none' || !dock.style.display);
    dock.style.display = isOpening ? 'flex' : 'none';

    if (isOpening) {
      // If AI drawer is open and docked, hide AI drawer so both 410px panels do not collide
      const aiDrawer = document.getElementById('studio-ai-drawer');
      if (aiDrawer && aiDrawer.style.display !== 'none' && !aiDrawer.classList.contains('floating-mode')) {
        this.wasAIDrawerOpen = true;
        aiDrawer.style.display = 'none';
      }
    }
  },

  toggleDockFloatingMode() {
    const dock = document.getElementById('studio-grading-dock');
    const btn = document.getElementById('dock-btn-mode');
    if (!dock) return;
    if (dock.classList.contains('docked-right')) {
      dock.classList.remove('docked-right');
      dock.classList.add('floating-mode');
      if (btn) {
        btn.title = "Přikotvit bodování vpravo";
        btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="15" y1="3" x2="15" y2="21"/><path d="m11 9 3 3-3 3"/></svg>`;
      }
    } else {
      dock.classList.remove('floating-mode');
      dock.classList.add('docked-right');
      dock.style.left = '';
      dock.style.top = '';
      dock.style.right = '';
      if (btn) {
        btn.title = "Přepnout na volně plovoucí okno";
        btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>`;
      }
    }
  },

  setupGradingDockDrag() {
    const header = document.getElementById('grading-dock-header');
    const dock = document.getElementById('studio-grading-dock');
    const snapGuide = document.getElementById('dock-snap-preview');
    if (!header || !dock) return;

    let isDragging = false;
    let startX = 0, startY = 0, initialLeft = 0, initialTop = 0;
    let willSnap = false;

    header.addEventListener('mousedown', (e) => {
      if (e.target.closest('.dock-ctrl-btn') || !dock.classList.contains('floating-mode')) return;
      isDragging = true;
      willSnap = false;
      dock.style.transition = 'none';
      startX = e.clientX;
      startY = e.clientY;
      const rect = dock.getBoundingClientRect();
      initialLeft = rect.left;
      initialTop = rect.top;
      e.preventDefault();
    });

    window.addEventListener('mousemove', (e) => {
      if (!isDragging) return;
      const dx = e.clientX - startX;
      const dy = e.clientY - startY;
      const newLeft = Math.max(10, Math.min(window.innerWidth - 380, initialLeft + dx));
      const newTop = Math.max(10, Math.min(window.innerHeight - 100, initialTop + dy));
      dock.style.left = `${newLeft}px`;
      dock.style.top = `${newTop}px`;
      dock.style.right = 'auto';

      // Detect proximity to right edge for Windows-like snapping (< 70px)
      const rightDistance = window.innerWidth - (newLeft + dock.offsetWidth);
      if (rightDistance < 70 || e.clientX > window.innerWidth - 60) {
        willSnap = true;
        if (snapGuide) snapGuide.classList.add('active');
      } else {
        willSnap = false;
        if (snapGuide) snapGuide.classList.remove('active');
      }
    });

    window.addEventListener('mouseup', () => {
      if (!isDragging) return;
      isDragging = false;
      if (snapGuide) snapGuide.classList.remove('active');

      if (willSnap) {
        // Smooth snap animation into right dock
        dock.style.transition = 'all 0.22s cubic-bezier(0.16, 1, 0.3, 1)';
        dock.style.left = `${window.innerWidth - 380}px`;
        dock.style.top = '0px';
        setTimeout(() => {
          dock.classList.remove('floating-mode');
          dock.classList.add('docked-right');
          dock.style.left = '';
          dock.style.top = '';
          dock.style.right = '';
          dock.style.transition = '';
          const btn = document.getElementById('dock-btn-mode');
          if (btn) {
            btn.title = "Přepnout na volně plovoucí okno";
            btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>`;
          }
        }, 220);
      }
    });
  },

  updateAIDockSideButton() {
    const btn = document.getElementById('ai-dock-btn-side');
    if (!btn) return;
    if (this.aiDrawerDockSide === 'left') {
      btn.title = "Přikotvit panel vpravo";
      btn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m13 17 5-5-5-5"/><path d="m6 17 5-5-5-5"/></svg>`;
    } else {
      btn.title = "Přikotvit panel vlevo";
      btn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m11 17-5-5 5-5"/><path d="m18 17-5-5 5-5"/></svg>`;
    }
  },

  toggleAIDrawerSide() {
    const drawer = document.getElementById('studio-ai-drawer');
    if (!drawer) return;
    if (this.aiDrawerDockSide === 'right') {
      this.aiDrawerDockSide = 'left';
      drawer.classList.remove('docked-right', 'floating-mode');
      drawer.classList.add('docked-left');
      drawer.style.left = '';
      drawer.style.top = '';
      drawer.style.right = '';
    } else {
      this.aiDrawerDockSide = 'right';
      drawer.classList.remove('docked-left', 'floating-mode');
      drawer.classList.add('docked-right');
      drawer.style.left = '';
      drawer.style.top = '';
      drawer.style.right = '';
    }
    this.updateAIDockSideButton();
    localStorage.setItem('praktika_ai_dock_side', this.aiDrawerDockSide);
  },

  toggleAIFloatingMode() {
    const drawer = document.getElementById('studio-ai-drawer');
    if (!drawer) return;
    const btn = document.getElementById('ai-dock-btn-mode');

    if (drawer.classList.contains('floating-mode')) {
      // Return to docked
      drawer.classList.remove('floating-mode');
      drawer.classList.add(this.aiDrawerDockSide === 'left' ? 'docked-left' : 'docked-right');
      drawer.style.left = '';
      drawer.style.top = '';
      drawer.style.right = '';
      this.aiDrawerFloating = false;
      if (btn) {
        btn.title = "Přepnout na volně plovoucí okno";
        btn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h6v6"></path><path d="M10 14L21 3"></path><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path></svg>`;
      }
    } else {
      // Float
      drawer.classList.remove('docked-left', 'docked-right');
      drawer.classList.add('floating-mode');
      drawer.style.top = '60px';
      drawer.style.left = this.aiDrawerDockSide === 'left' ? '40px' : `${Math.max(20, window.innerWidth - 440)}px`;
      drawer.style.right = 'auto';
      this.aiDrawerFloating = true;
      if (btn) {
        btn.title = "Přikotvit panel";
        btn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="15" y1="3" x2="15" y2="21"/><path d="m11 9 3 3-3 3"/></svg>`;
      }
    }
    localStorage.setItem('praktika_ai_floating', this.aiDrawerFloating ? 'true' : 'false');
  },

  setupAIDrawerDrag() {
    const header = document.getElementById('ai-drawer-header');
    const drawer = document.getElementById('studio-ai-drawer');
    const snapGuideRight = document.getElementById('dock-snap-preview');
    const snapGuideLeft = document.getElementById('dock-snap-preview-left');
    if (!header || !drawer) return;

    let isDragging = false;
    let startX = 0, startY = 0, initialLeft = 0, initialTop = 0;
    let willSnap = null; // 'left' | 'right' | null

    header.addEventListener('mousedown', (e) => {
      if (e.target.closest('.dock-ctrl-btn, .btn') || !drawer.classList.contains('floating-mode')) return;
      isDragging = true;
      willSnap = null;
      drawer.style.transition = 'none';
      startX = e.clientX;
      startY = e.clientY;
      const rect = drawer.getBoundingClientRect();
      initialLeft = rect.left;
      initialTop = rect.top;
      e.preventDefault();
    });

    window.addEventListener('mousemove', (e) => {
      if (!isDragging) return;
      const dx = e.clientX - startX;
      const dy = e.clientY - startY;
      const newLeft = Math.max(10, Math.min(window.innerWidth - 380, initialLeft + dx));
      const newTop = Math.max(10, Math.min(window.innerHeight - 100, initialTop + dy));
      drawer.style.left = `${newLeft}px`;
      drawer.style.top = `${newTop}px`;
      drawer.style.right = 'auto';

      // Snap left (< 70px or cursor < 70px)
      if (newLeft < 70 || e.clientX < 70) {
        willSnap = 'left';
        if (snapGuideLeft) snapGuideLeft.classList.add('active');
        if (snapGuideRight) snapGuideRight.classList.remove('active');
      }
      // Snap right (< 70px from right or cursor > right - 70px)
      else if (window.innerWidth - (newLeft + drawer.offsetWidth) < 70 || e.clientX > window.innerWidth - 70) {
        willSnap = 'right';
        if (snapGuideRight) snapGuideRight.classList.add('active');
        if (snapGuideLeft) snapGuideLeft.classList.remove('active');
      } else {
        willSnap = null;
        if (snapGuideLeft) snapGuideLeft.classList.remove('active');
        if (snapGuideRight) snapGuideRight.classList.remove('active');
      }
    });

    window.addEventListener('mouseup', () => {
      if (!isDragging) return;
      isDragging = false;
      if (snapGuideLeft) snapGuideLeft.classList.remove('active');
      if (snapGuideRight) snapGuideRight.classList.remove('active');

      if (willSnap === 'left') {
        drawer.style.transition = 'all 0.22s cubic-bezier(0.16, 1, 0.3, 1)';
        drawer.style.left = '0px';
        drawer.style.top = '0px';
        setTimeout(() => {
          drawer.classList.remove('floating-mode', 'docked-right');
          drawer.classList.add('docked-left');
          drawer.style.left = '';
          drawer.style.top = '';
          drawer.style.right = '';
          drawer.style.transition = '';
          this.aiDrawerDockSide = 'left';
          this.aiDrawerFloating = false;
          localStorage.setItem('praktika_ai_dock_side', 'left');
          localStorage.setItem('praktika_ai_floating', 'false');
          this.updateAIDockSideButton();
          const btn = document.getElementById('ai-dock-btn-mode');
          if (btn) {
            btn.title = "Přepnout na volně plovoucí okno";
            btn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h6v6"></path><path d="M10 14L21 3"></path><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path></svg>`;
          }
        }, 220);
      } else if (willSnap === 'right') {
        drawer.style.transition = 'all 0.22s cubic-bezier(0.16, 1, 0.3, 1)';
        drawer.style.left = `${window.innerWidth - drawer.offsetWidth}px`;
        drawer.style.top = '0px';
        setTimeout(() => {
          drawer.classList.remove('floating-mode', 'docked-left');
          drawer.classList.add('docked-right');
          drawer.style.left = '';
          drawer.style.top = '';
          drawer.style.right = '';
          drawer.style.transition = '';
          this.aiDrawerDockSide = 'right';
          this.aiDrawerFloating = false;
          localStorage.setItem('praktika_ai_dock_side', 'right');
          localStorage.setItem('praktika_ai_floating', 'false');
          this.updateAIDockSideButton();
          const btn = document.getElementById('ai-dock-btn-mode');
          if (btn) {
            btn.title = "Přepnout na volně plovoucí okno";
            btn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h6v6"></path><path d="M10 14L21 3"></path><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path></svg>`;
          }
        }, 220);
      }
    });
  },

  setupPanelResize(panelEl, handleEl, defaultIsRight, storageKey) {
    if (!panelEl || !handleEl) return;

    const savedWidth = localStorage.getItem(storageKey);
    if (savedWidth) {
      const w = parseInt(savedWidth, 10);
      if (w >= 280 && w <= 800) {
        panelEl.style.width = `${w}px`;
      }
    }

    let isResizing = false;
    let startX = 0;
    let startWidth = 0;

    const onMouseDown = (e) => {
      if (e.button !== 0) return;
      isResizing = true;
      startX = e.clientX;
      startWidth = panelEl.offsetWidth;
      handleEl.classList.add('active');
      document.body.style.cursor = 'ew-resize';
      document.body.style.userSelect = 'none';

      const onMouseMove = (ev) => {
        if (!isResizing) return;
        const isRight = panelEl.classList.contains('docked-right');
        const diff = isRight ? (startX - ev.clientX) : (ev.clientX - startX);
        const newWidth = Math.max(280, Math.min(800, startWidth + diff));
        panelEl.style.width = `${newWidth}px`;
      };

      const onMouseUp = () => {
        if (!isResizing) return;
        isResizing = false;
        handleEl.classList.remove('active');
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);
        localStorage.setItem(storageKey, panelEl.offsetWidth);
      };

      document.addEventListener('mousemove', onMouseMove);
      document.addEventListener('mouseup', onMouseUp);
      e.preventDefault();
      e.stopPropagation();
    };

    handleEl.addEventListener('mousedown', onMouseDown);
  },

  setupAllPanelResizers() {
    const aiDrawer = document.getElementById('studio-ai-drawer');
    const aiHandle = document.getElementById('ai-drawer-resize-handle');
    if (aiDrawer && aiHandle) {
      this.setupPanelResize(aiDrawer, aiHandle, true, 'praktika_ai_drawer_width');
    }

    const gradingDock = document.getElementById('studio-grading-dock');
    const gradingHandle = document.getElementById('grading-dock-resize-handle');
    if (gradingDock && gradingHandle) {
      this.setupPanelResize(gradingDock, gradingHandle, true, 'praktika_grading_dock_width');
    }
  },

  async checkAIKeyStatus() {
    try {
      const resp = await fetch('/api/settings/ai');
      if (resp.ok) {
        const data = await resp.json();
        const hasKey = !!(data.has_key || (data.gemini_api_key && data.gemini_api_key.trim().length > 0));
        const warnBanner = document.getElementById('ai-drawer-key-warning');
        if (warnBanner) {
          warnBanner.style.display = hasKey ? 'none' : 'flex';
        }
        return hasKey;
      }
    } catch(e) {}
    return false;
  },

  setLayoutMode(mode) {
    this.layoutMode = mode;
    localStorage.setItem('praktika_layout_mode', mode);
    this.applyLayoutMode();
  },

  toggleLayoutMode() {
    const nextMode = this.layoutMode === 'split' ? 'fullscreen' : 'split';
    this.setLayoutMode(nextMode);
    this.showToast(nextMode === 'split' ? "Rozdělená obrazovka" : "Plná obrazovka (se šuplíkem)");
  },

  applyLayoutMode() {
    const studio = document.getElementById('studio-wrapper');
    const toggleBtn = document.getElementById('btn-toggle-layout');
    if (!studio) return;

    if (this.layoutMode === 'fullscreen') {
      studio.classList.add('fullscreen-mode');
      if (toggleBtn) toggleBtn.innerHTML = '<span>◫ Rozdělit</span>';
    } else {
      studio.classList.remove('fullscreen-mode');
      if (toggleBtn) toggleBtn.innerHTML = '<span>🗖 Na celou obrazovku</span>';
    }
  },

  toggleDrawer() {
    const pane = document.getElementById('studio-grading-pane');
    if (pane) pane.classList.toggle('open');
  },

  // Protocols Dashboard
  async loadProtocols() {
    const semFilter = document.getElementById('filter-semester-select');
    const slotFilter = document.getElementById('filter-slot-select');
    const measFilter = document.getElementById('filter-measurement-select');
    const statusFilter = document.getElementById('filter-status-select');
    const searchInput = document.getElementById('filter-search-input');

    const params = new URLSearchParams();
    if (semFilter && semFilter.value) params.append('semester_id', semFilter.value);
    else if (this.activeSemesterId) params.append('semester_id', this.activeSemesterId);

    const evalFilter = document.getElementById('filter-evaluator-select');
    if (slotFilter && slotFilter.value) params.append('slot_id', slotFilter.value);
    if (measFilter && measFilter.value) params.append('measurement_id', measFilter.value);
    if (evalFilter && evalFilter.value) params.append('evaluator_id', evalFilter.value);
    if (statusFilter && statusFilter.value) params.append('status_filter', statusFilter.value);
    if (searchInput && searchInput.value.trim()) params.append('search', searchInput.value.trim());

    try {
      const resp = await fetch(`/api/protocols?${params.toString()}`);
      if (resp.ok) {
        const protocols = await resp.json();
        this.loadedProtocols = protocols;
        this.renderProtocolsTable(protocols);
        this.updateDashboardStats(protocols);
      }
    } catch (e) {
      console.error("Error loading protocols:", e);
    }
  },

  populateEvaluatorFilterOptions() {
    const sel = document.getElementById('filter-evaluator-select');
    if (!sel || !this.allUsers) return;
    const curVal = sel.value;
    sel.innerHTML = `
      <option value="">Všichni hodnotitelé</option>
      <option value="me">Moje protokoly</option>
      <option value="others">Ostatní asistenti</option>
      <option value="unassigned">Nepřiřazené</option>
      <optgroup label="Konkrétní asistent">
        ${this.allUsers.map(u => `<option value="${u.id}">${this.escape(u.full_name)} (@${u.username})</option>`).join('')}
      </optgroup>
    `;
    if (curVal) sel.value = curVal;
  },

  updateDashboardStats(protocols) {
    const totalEl = document.getElementById('stat-total-protocols');
    const gradedEl = document.getElementById('stat-graded-protocols');
    const pendingEl = document.getElementById('stat-pending-protocols');
    const avgEl = document.getElementById('stat-avg-score');

    if (!totalEl) return;
    const total = protocols.length;
    const graded = protocols.filter(p => p.status === 'graded').length;
    const pending = total - graded;

    let avg = 0;
    if (graded > 0) {
      const sum = protocols.filter(p => p.status === 'graded').reduce((acc, p) => acc + p.total_points, 0);
      avg = (sum / graded).toFixed(2);
    }

    totalEl.textContent = total;
    gradedEl.textContent = graded;
    pendingEl.textContent = pending;
    avgEl.textContent = graded > 0 ? `${avg} / 10` : '—';
  },

  renderProtocolsTable(protocols) {
    const tbody = document.getElementById('protocols-tbody');
    if (!tbody) return;

    if (protocols.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="8" style="text-align:center; padding:36px; color:var(--text-muted);">
            Žádné protokoly nebyly nalezeny pro zadaný filtr.<br>
            <button class="btn btn-primary btn-sm" style="margin-top:12px;" onclick="App.openUploadModal()">+ Nahrát nový protokol</button>
          </td>
        </tr>
      `;
      this.updateBulkActionBar();
      return;
    }

    tbody.innerHTML = protocols.map(p => {
      const statusBadge = p.status === 'graded'
        ? `<span class="status-badge status-graded">✓ Opraveno</span>`
        : p.status === 'revision'
        ? `<span class="status-badge status-revision">⟳ K přepracování</span>`
        : p.status === 'in_progress'
        ? `<span class="status-badge status-in_progress">✎ Rozpracováno</span>`
        : `<span class="status-badge status-new">Nový</span>`;

      const hasGrade = p.grade && p.grade !== '—';
      const gradeBadge = hasGrade
        ? `<span class="grade-badge-sm" style="background:${GradingEngine.getGradeBg(p.grade)}; color:${GradingEngine.getGradeColor(p.grade)}; border:1px solid ${GradingEngine.getGradeColor(p.grade)};">${p.grade}</span>`
        : `<span style="color:#94a3b8;">—</span>`;

      const scoreDisplay = (p.total_points !== null && p.total_points !== undefined)
        ? `<strong style="font-family:'JetBrains Mono';">${GradingEngine.formatPoints(p.total_points)}</strong> / 10`
        : `<span style="color:#94a3b8;">—</span>`;

      const slotDisplay = `${p.day_of_week} ${p.time_start}–${p.time_end}${p.slot_room ? ' (' + p.slot_room + ')' : ''}`;

      const isOwner = (this.currentUser && p.evaluator_id === this.currentUser.id);
      const isAdmin = (this.currentUser && this.currentUser.role === 'admin');
      const isUnassigned = !p.evaluator_id;

      let evaluatorDisplay = '';
      if (isAdmin && this.allUsers && this.allUsers.length > 0) {
        evaluatorDisplay = `
          <select class="form-control" style="font-size:0.75rem; padding:2px 4px; max-width:140px; display:inline-block;" onchange="App.assignProtocol(${p.id}, this.value)" title="Přiřadit asistenta">
            <option value="">Nepřiřazeno</option>
            ${this.allUsers.map(u => `<option value="${u.id}" ${p.evaluator_id === u.id ? 'selected' : ''}>${this.escape(u.full_name)}</option>`).join('')}
          </select>`;
      } else {
        if (isOwner) {
          evaluatorDisplay = `
            <div style="display:inline-flex; align-items:center; gap:4px;">
              <span style="font-size:0.8rem; font-weight:600; color:var(--primary);">${this.escape(p.evaluator_name || 'Moje')}</span>
              <button class="btn btn-secondary btn-sm" style="font-size:0.68rem; padding:1px 5px;" onclick="App.assignProtocol(${p.id}, '')" title="Uvolnit protokol ze svých">Uvolnit</button>
            </div>
          `;
        } else if (isUnassigned) {
          evaluatorDisplay = `
            <div style="display:inline-flex; align-items:center; gap:4px;">
              <em style="color:#94a3b8; font-size:0.8rem;">Nepřiřazeno</em>
              <button class="btn btn-secondary btn-sm" style="font-size:0.68rem; padding:1px 5px;" onclick="App.assignProtocol(${p.id}, ${this.currentUser ? this.currentUser.id : 'null'})" title="Přiřadit tento protokol sobě">Přiřadit sobě</button>
            </div>
          `;
        } else {
          evaluatorDisplay = `<span style="font-size:0.82rem;">${this.escape(p.evaluator_name)}</span>`;
        }
      }

      const canDelete = isAdmin || isOwner || isUnassigned;
      const isChecked = this.selectedProtocolIds.has(p.id) ? 'checked' : '';

      return `
        <tr>
          <td style="text-align:center;">
            <input type="checkbox" class="protocol-checkbox" value="${p.id}" ${isChecked} onchange="App.handleProtocolCheckboxChange()">
          </td>
          <td>
            <div style="font-weight:700; color:var(--text-main);">${this.escape(p.student_name)}</div>
            <div style="font-size:0.75rem; color:var(--text-muted);">${this.escape(p.source_filename)}</div>
          </td>
          <td>
            <span style="font-weight:600; font-size:0.85rem;">Úloha ${p.measurement_number}</span>
            <div style="font-size:0.75rem; color:var(--text-muted);">${this.escape(p.measurement_name)}</div>
          </td>
          <td>
            <span style="font-size:0.85rem;">${slotDisplay}</span>
            ${p.slot_name && p.slot_name !== p.slot_room ? `<div style="font-size:0.75rem; color:var(--text-muted);">${this.escape(p.slot_name)}</div>` : ''}
          </td>
          <td>${statusBadge}</td>
          <td>${scoreDisplay} ${gradeBadge}</td>
          <td>${evaluatorDisplay}</td>
          <td style="text-align:right;">
            <div style="display:inline-flex; gap:6px;">
              <button class="btn btn-primary btn-sm" onclick="App.openStudio(${p.id})">
                ${p.status === 'graded' ? 'Upravit' : 'Opravit'}
              </button>
              <button class="btn btn-secondary btn-sm" onclick="App.openEditMetadataModal(${p.id})" title="Upravit studenta, termín či úlohu">✏️</button>
              ${p.corrected_filename ? `
                <a class="btn btn-secondary btn-sm" href="/api/protocols/${p.id}/pdf/corrected" target="_blank" title="Zobrazit opravené PDF">PDF</a>
                <a class="btn btn-secondary btn-sm" href="/api/protocols/${p.id}/export/bodovani.txt" download title="Stáhnout bodovani.txt">.txt</a>
              ` : ''}
              ${canDelete ? `<button class="btn btn-danger btn-sm" onclick="App.deleteProtocol(${p.id})" title="Smazat">🗑</button>` : ''}
            </div>
          </td>
        </tr>
      `;
    }).join('');

    // Sync select-all checkbox and bulk bar
    const selectAll = document.getElementById('select-all-protocols');
    if (selectAll) {
      const checkboxes = tbody.querySelectorAll('.protocol-checkbox');
      selectAll.checked = checkboxes.length > 0 && Array.from(checkboxes).every(cb => cb.checked);
    }
    this.updateBulkActionBar();
  },

  async assignProtocol(protoId, evaluatorId) {
    const evalId = evaluatorId ? parseInt(evaluatorId) : null;
    try {
      const resp = await fetch(`/api/protocols/${protoId}/assign`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ evaluator_id: evalId })
      });
      if (resp.ok) {
        this.showToast("Přiřazení asistenta uloženo.");
        this.loadProtocols();
      } else {
        const err = await resp.json();
        await AppModal.alert({ title: "Chyba přiřazení", message: err.detail || "Nelze změnit přiřazení protokolu." });
      }
    } catch(e) {
      await AppModal.alert({ title: "Chyba přiřazení", message: e.message });
    }
  },

  // Open Correction Studio
  async openStudio(protoId) {
    try {
      this.setAIResult(null);
      const resp = await fetch(`/api/protocols/${protoId}`);
      if (!resp.ok) throw new Error("Nelze načíst detail protokolu");
      this.currentProtocol = await resp.json();
      this.currentProtocolIndex = (this.loadedProtocols || []).findIndex(p => p.id === protoId);

      const sTitle = document.getElementById('studio-student-title');
      const sFloatTitle = document.getElementById('studio-floating-student-title');
      if (sTitle) sTitle.textContent = this.currentProtocol.student_name;
      if (sFloatTitle) sFloatTitle.textContent = this.currentProtocol.student_name;

      const metaText = `Úloha ${this.currentProtocol.measurement_number}: ${this.currentProtocol.measurement_name} | ${this.currentProtocol.day_of_week} ${this.currentProtocol.time_start}`;
      const sMeta = document.getElementById('studio-meta-badge');
      const sFloatMeta = document.getElementById('studio-floating-meta-badge');
      if (sMeta) sMeta.textContent = metaText;
      if (sFloatMeta) sFloatMeta.textContent = metaText;

      // Init Grading Engine
      await GradingEngine.init(document.getElementById('studio-grading-container'), () => {
        this.scheduleAutosave();
        this.updateGradingDockScore();
      });
      GradingEngine.loadData(this.currentProtocol.evaluation);

      // Init PDF Studio
      PDFStudio.init(document.getElementById('pdf-render-pane'), (newNote) => {
        this.scheduleAutosave();
      }, this.currentUser);

      // Load PDF with annotations & AI proposals
      await PDFStudio.loadPDF(
        `/api/protocols/${protoId}/pdf/source`,
        protoId,
        this.currentProtocol.annotations,
        this.currentProtocol.ai_proposals
      );

      if (this.currentProtocol.ai_proposals) {
        this.setAIResult(this.currentProtocol.ai_proposals);
      } else {
        this.setAIResult(null);
      }

      this.isDirty = false;
      this.updateAutosaveIndicator('saved');
      this.updateGradingDockScore();

      this.showView('studio');
    } catch(e) {
      await AppModal.alert({ title: "Chyba", message: "Chyba při otevírání protokolu: " + e.message });
    }
  },

  updateGradingDockScore() {
    const pill = document.getElementById('grading-dock-score-pill');
    if (pill && window.GradingEngine) {
      const total = GradingEngine.getTotalPoints();
      const mark = GradingEngine.getMark(total);
      pill.textContent = `${GradingEngine.formatPoints(total)} / 10 (${mark})`;
    }
  },

  openPreviousProtocol() {
    if (!this.loadedProtocols || this.currentProtocolIndex <= 0) {
      this.showToast("Jste na začátku seznamu protokolů.");
      return;
    }
    const prev = this.loadedProtocols[this.currentProtocolIndex - 1];
    this.openStudio(prev.id);
  },

  openNextProtocol() {
    if (!this.loadedProtocols || this.currentProtocolIndex >= this.loadedProtocols.length - 1) {
      this.showToast("Jste na konci seznamu protokolů.");
      return;
    }
    const next = this.loadedProtocols[this.currentProtocolIndex + 1];
    this.openStudio(next.id);
  },

  async saveCurrentEvaluation(andBurn = true, statusOverride = null) {
    if (!this.currentProtocol) return;
    const protoId = this.currentProtocol.id;

    const payload = {
      protocol_id: protoId,
      vysledky_score: GradingEngine.getCategoryScore('vysledky'),
      diskuze_score: GradingEngine.getCategoryScore('diskuze'),
      format_score: GradingEngine.getCategoryScore('format'),
      chyby_score: GradingEngine.getCategoryScore('chyby'),
      total_points: GradingEngine.getTotalPoints(),
      grade: GradingEngine.getMark(GradingEngine.getTotalPoints()),
      manual_grade_override: GradingEngine.state.manualGradeOverride,
      deductions: GradingEngine.state.deductions,
      raw_output_1: GradingEngine.generateOutput1(),
      raw_output_2: GradingEngine.generateOutput2(),
      burn_to_pdf: andBurn,
      status: statusOverride || (andBurn ? 'graded' : 'in_progress')
    };

    try {
      const resp = await fetch(`/api/protocols/${protoId}/evaluation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (resp.ok) {
        if (statusOverride === 'revision') {
          this.showToast("Protokol označen: K přepracování");
        } else {
          this.showToast(andBurn ? "Opravené PDF a bodovani.txt úspěšně uloženo!" : "Koncept hodnocení byl uložen.");
        }
        const refreshed = await fetch(`/api/protocols/${protoId}`).then(r => r.json());
        this.currentProtocol = refreshed;
      } else {
        await AppModal.alert({ title: "Chyba ukládání", message: "Chyba při ukládání hodnocení." });
      }
    } catch(e) {
      await AppModal.alert({ title: "Chyba spojení", message: "Chyba spojení: " + e.message });
    }
  },

  // Export handlers
  exportZip() {
    const sem = document.getElementById('filter-semester-select').value;
    const slot = document.getElementById('filter-slot-select').value;
    const meas = document.getElementById('filter-measurement-select').value;
    const stat = document.getElementById('filter-status-select').value;
    const params = new URLSearchParams();
    if (sem) params.append('semester_id', sem);
    if (slot) params.append('slot_id', slot);
    if (meas) params.append('measurement_id', meas);
    if (stat) params.append('status', stat);

    this.showToast("Generuji ZIP archiv ke stažení...");
    window.location.href = `/api/export/zip?${params.toString()}`;
  },

  exportCsv() {
    const sem = document.getElementById('filter-semester-select').value;
    const slot = document.getElementById('filter-slot-select').value;
    const meas = document.getElementById('filter-measurement-select').value;
    const stat = document.getElementById('filter-status-select').value;
    const params = new URLSearchParams();
    if (sem) params.append('semester_id', sem);
    if (slot) params.append('slot_id', slot);
    if (meas) params.append('measurement_id', meas);
    if (stat) params.append('status', stat);

    this.showToast("Generuji CSV tabulku známek...");
    window.location.href = `/api/export/csv?${params.toString()}`;
  },

  // Extract surname from filename (e.g. FPRA1_Boril_uloha1.pdf -> Boril)
  extractStudentName(filename) {
    if (!filename) return "Student";
    let base = filename.replace(/\.pdf$/i, '');
    const parts = base.split(/[_\-\s]+/);
    for (const part of parts) {
      if (part.length >= 3 && !/^FPRA/i.test(part) && !/^uloha/i.test(part) && !/^\d+$/.test(part)) {
        return part;
      }
    }
    return parts[0] || base;
  },

  // Upload Modal
  openUploadModal() {
    const modal = document.getElementById('upload-modal');
    if (modal) modal.classList.add('active');
    const statusBox = document.getElementById('autodetect-status-box');
    if (statusBox) statusBox.style.display = 'none';
  },

  closeUploadModal() {
    const modal = document.getElementById('upload-modal');
    if (modal) modal.classList.remove('active');
  },

  async handleUploadFileSelect(input) {
    const files = input && input.files;
    if (!files || files.length === 0) return;

    const statusBox = document.getElementById('autodetect-status-box');
    const statusText = document.getElementById('autodetect-status-text');
    const statusSpinner = document.getElementById('autodetect-status-spinner');
    const nameInput = document.getElementById('upload-student-name');
    const semSelect = document.getElementById('upload-semester-select');
    const slotSelect = document.getElementById('upload-slot-select');
    const measSelect = document.getElementById('upload-measurement-select');

    if (files.length > 1) {
      if (nameInput) {
        nameInput.value = '';
        nameInput.placeholder = 'Automatická detekce jména pro každý soubor zvlášť...';
      }
      if (statusBox) {
        statusBox.style.display = 'block';
        if (statusText) statusText.innerHTML = `<strong>✨ Dávkové nahrávání:</strong> Vybráno <strong>${files.length} souborů</strong>. Jméno studenta a úloha budou pro každý soubor automaticky vyčteny přímo z obsahu PDF.`;
        if (statusSpinner) statusSpinner.textContent = '✓';
      }
      return;
    }

    if (statusBox) {
      statusBox.style.display = 'block';
      if (statusText) statusText.textContent = `Analyzuji obsah PDF (${files[0].name}) pro autodetekci údajů...`;
      if (statusSpinner) statusSpinner.textContent = '⏳';
    }

    try {
      const fd = new FormData();
      fd.append('file', files[0]);
      const resp = await fetch('/api/protocols/autodetect', {
        method: 'POST',
        body: fd
      });

      if (resp.ok) {
        const data = await resp.json();
        // Prefill student name
        if (data.student_name && nameInput) {
          nameInput.value = data.student_name;
        }

        // Prefill semester if returned
        if (data.semester_id && semSelect) {
          semSelect.value = data.semester_id;
        }

        // Prefill slot if returned
        if (data.slot_id && slotSelect) {
          slotSelect.value = data.slot_id;
          this.handleUploadSlotChange();
        } else if (data.course_code && slotSelect) {
          for (let i = 0; i < slotSelect.options.length; i++) {
            if (slotSelect.options[i].getAttribute('data-course') === data.course_code) {
              slotSelect.selectedIndex = i;
              this.handleUploadSlotChange();
              break;
            }
          }
        }

        // Prefill measurement
        const taskNum = data.measurement_number || data.task_number;
        if (data.measurement_id && measSelect) {
          measSelect.value = data.measurement_id;
        } else if (taskNum && measSelect) {
          const match = Array.from(measSelect.options).find(o => o.textContent.includes(`Úloha ${taskNum}:`));
          if (match) measSelect.value = match.value;
        }

        if (statusBox) {
          const courseLabel = data.course_code ? `[${data.course_code}] ` : '';
          const taskLabel = taskNum ? ` | Úloha ${taskNum}` : '';
          if (statusText) {
            statusText.innerHTML = `<strong>✨ Autodetekce úspěšná:</strong> ${this.escape(data.student_name || 'Student')} (${courseLabel}${data.slot_name || ''}${taskLabel})`;
          }
          if (statusSpinner) statusSpinner.textContent = '✓';
        }
      } else {
        if (statusBox) {
          if (statusText) statusText.textContent = 'Detekce z textu PDF se nezdařila, doplňte prosím údaje ručně.';
          if (statusSpinner) statusSpinner.textContent = 'ℹ️';
        }
      }
    } catch(e) {
      console.warn("Autodetect failed:", e);
      if (statusBox) statusBox.style.display = 'none';
    }
  },

  async handleProtocolUpload(e) {
    e.preventDefault();
    const fileInput = document.getElementById('upload-file-input');
    const semSelect = document.getElementById('upload-semester-select');
    const slotSelect = document.getElementById('upload-slot-select');
    const measSelect = document.getElementById('upload-measurement-select');
    const nameInput = document.getElementById('upload-student-name');
    const progressBox = document.getElementById('upload-progress-box');

    const files = fileInput.files;
    if (!files || files.length === 0) {
      await AppModal.alert({ title: "Chyba", message: "Vyberte prosím alespoň jeden PDF soubor." });
      return;
    }

    const submitBtn = document.getElementById('upload-submit-btn');
    submitBtn.disabled = true;

    if (progressBox) progressBox.style.display = 'block';

    let successCount = 0;
    const manualName = nameInput.value.trim();

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        // If single file and manualName entered, use manualName. If batch upload, leave empty to let backend autodetect from PDF content!
        const studentName = (files.length === 1 && manualName) ? manualName : '';

        submitBtn.textContent = `Nahrávám [${i + 1}/${files.length}]...`;
        if (progressBox) {
          progressBox.textContent = `Nahrávám [${i + 1}/${files.length}]: ${file.name}...`;
        }

        const formData = new FormData();
        formData.append('file', file);
        formData.append('semester_id', semSelect.value);
        formData.append('slot_id', slotSelect.value);
        formData.append('measurement_id', measSelect.value);
        formData.append('student_name', studentName);

        const resp = await fetch('/api/protocols/upload', {
          method: 'POST',
          body: formData
        });

        if (resp.ok) {
          successCount++;
        } else {
          const err = await resp.json();
          console.error(`Chyba při nahrávání ${file.name}:`, err.detail);
        }
      }

      this.closeUploadModal();
      fileInput.value = '';
      nameInput.value = '';
      if (progressBox) progressBox.style.display = 'none';

      this.showToast(`Úspěšně nahráno ${successCount} z ${files.length} protokolů!`);
      this.loadProtocols();
    } catch(err) {
      await AppModal.alert({ title: "Chyba při nahrávání", message: err.message });
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Nahrát protokol';
      if (progressBox) progressBox.style.display = 'none';
    }
  },

  async deleteProtocol(protoId) {
    const ok = await AppModal.confirm({
      title: "Smazat protokol",
      message: "Opravdu chcete smazat tento protokol včetně všech opravených souborů?",
      confirmText: "Smazat",
      danger: true
    });
    if (!ok) return;
    try {
      const resp = await fetch(`/api/protocols/${protoId}`, { method: 'DELETE' });
      if (resp.ok) {
        this.showToast("Protokol byl smazán.");
        this.loadProtocols();
      } else {
        let err;
        try { err = await resp.json(); } catch(e) { err = { detail: resp.statusText }; }
        await AppModal.alert({ title: "Nelze smazat protokol", message: err.detail || "Chyba při mazání." });
      }
    } catch(e) {
      await AppModal.alert({ title: "Chyba při mazání", message: e.message });
    }
  },

  // Bulk Protocol Management
  toggleSelectAllProtocols(checked) {
    const checkboxes = document.querySelectorAll('.protocol-checkbox');
    checkboxes.forEach(cb => {
      cb.checked = checked;
      const pid = parseInt(cb.value);
      if (checked) {
        this.selectedProtocolIds.add(pid);
      } else {
        this.selectedProtocolIds.delete(pid);
      }
    });
    this.updateBulkActionBar();
  },

  handleProtocolCheckboxChange() {
    this.selectedProtocolIds.clear();
    const checkboxes = document.querySelectorAll('.protocol-checkbox');
    let allChecked = checkboxes.length > 0;
    checkboxes.forEach(cb => {
      if (cb.checked) {
        this.selectedProtocolIds.add(parseInt(cb.value));
      } else {
        allChecked = false;
      }
    });
    const selectAll = document.getElementById('select-all-protocols');
    if (selectAll) {
      selectAll.checked = allChecked && checkboxes.length > 0;
    }
    this.updateBulkActionBar();
  },

  clearProtocolSelection() {
    this.selectedProtocolIds.clear();
    const selectAll = document.getElementById('select-all-protocols');
    if (selectAll) selectAll.checked = false;
    document.querySelectorAll('.protocol-checkbox').forEach(cb => cb.checked = false);
    this.updateBulkActionBar();
  },

  updateBulkActionBar() {
    const bar = document.getElementById('bulk-actions-bar');
    const countEl = document.getElementById('bulk-selected-count');
    const count = this.selectedProtocolIds.size;
    if (bar) {
      bar.style.display = count > 0 ? 'flex' : 'none';
    }
    if (countEl) {
      countEl.textContent = `Vybráno: ${count} protokol${count === 1 ? '' : (count >= 2 && count <= 4 ? 'y' : 'ů')}`;
    }
  },

  async openBulkEditModal() {
    if (this.selectedProtocolIds.size === 0) return;
    const count = this.selectedProtocolIds.size;
    const subtitle = document.getElementById('bulk-edit-modal-subtitle');
    if (subtitle) {
      subtitle.textContent = `Upravit vybrané protokoly (${count} ks)`;
    }

    // Populate Semesters
    const semSelect = document.getElementById('bulk-edit-semester');
    semSelect.innerHTML = `<option value="">-- Ponechat beze změny --</option>` +
      this.semesters.map(s => `<option value="${s.id}">${s.code} (${s.name})</option>`).join('');

    // Slot
    const slotSelect = document.getElementById('bulk-edit-slot');
    slotSelect.innerHTML = `<option value="">-- Ponechat beze změny --</option>`;

    // Measurements
    const measSelect = document.getElementById('bulk-edit-measurement');
    measSelect.innerHTML = `<option value="">-- Ponechat beze změny --</option>` +
      this.measurements.map(m => `<option value="${m.id}">Úloha ${m.number}: ${m.name}</option>`).join('');

    // Evaluator
    const evalGroup = document.getElementById('bulk-edit-evaluator-group');
    const evalSelect = document.getElementById('bulk-edit-evaluator');
    const isAdmin = this.currentUser && this.currentUser.role === 'admin';
    if (evalGroup) evalGroup.style.display = isAdmin ? 'block' : 'none';
    if (evalSelect && isAdmin) {
      evalSelect.innerHTML = `<option value="">-- Ponechat beze změny --</option>` +
        `<option value="__unassigned__">Zrušit přiřazení (Nepřiřazeno)</option>` +
        (this.allUsers || []).map(u => `<option value="${u.id}">${this.escape(u.full_name)}</option>`).join('');
    }

    const modal = document.getElementById('bulk-edit-modal');
    if (modal) modal.classList.add('active');
  },

  async handleBulkEditSemesterChange(semId) {
    const slotSelect = document.getElementById('bulk-edit-slot');
    if (!slotSelect) return;
    if (!semId) {
      slotSelect.innerHTML = `<option value="">-- Ponechat beze změny --</option>`;
      return;
    }
    try {
      const resp = await fetch(`/api/slots?semester_id=${semId}`);
      if (resp.ok) {
        const slots = await resp.json();
        slotSelect.innerHTML = `<option value="">-- Ponechat beze změny --</option>` +
          slots.map(sl => {
            const roomSuffix = sl.room ? ` (${sl.room})` : '';
            return `<option value="${sl.id}">${sl.day_of_week} ${sl.time_start}–${sl.time_end}${roomSuffix}</option>`;
          }).join('');
      }
    } catch (e) {
      console.error("Error loading slots for bulk edit:", e);
    }
  },

  closeBulkEditModal() {
    const modal = document.getElementById('bulk-edit-modal');
    if (modal) modal.classList.remove('active');
  },

  async handleBulkSaveMetadata(e) {
    e.preventDefault();
    const ids = Array.from(this.selectedProtocolIds);
    if (ids.length === 0) return;

    const semVal = document.getElementById('bulk-edit-semester').value;
    const slotVal = document.getElementById('bulk-edit-slot').value;
    const measVal = document.getElementById('bulk-edit-measurement').value;
    const evalVal = document.getElementById('bulk-edit-evaluator')?.value;

    const payload = {
      protocol_ids: ids,
      semester_id: semVal ? parseInt(semVal) : null,
      slot_id: slotVal ? parseInt(slotVal) : null,
      measurement_id: measVal ? parseInt(measVal) : null,
    };
    if (evalVal === '__unassigned__') {
      payload.evaluator_id = -1; // Flag for unassign
    } else if (evalVal) {
      payload.evaluator_id = parseInt(evalVal);
    }

    try {
      const resp = await fetch('/api/protocols/bulk-update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (resp.ok) {
        const res = await resp.json();
        this.closeBulkEditModal();
        this.clearProtocolSelection();
        this.showToast(`Úspěšně upraveno ${res.updated_count} protokolů.`);
        this.loadProtocols();
      } else {
        const err = await resp.json();
        await AppModal.alert({ title: "Chyba hromadné úpravy", message: err.detail || "Nelze upravit vybrané protokoly." });
      }
    } catch (err) {
      await AppModal.alert({ title: "Chyba hromadné úpravy", message: err.message });
    }
  },

  async handleBulkDeleteProtocols() {
    const ids = Array.from(this.selectedProtocolIds);
    if (ids.length === 0) return;

    const confirmed = await AppModal.confirm({
      title: "Hromadné smazání protokolů",
      message: `Opravdu chcete nenávratně smazat ${ids.length} vybraných protokolů včetně jejich hodnocení, anotací a vygenerovaných souborů?`,
      confirmText: "Ano, smazat vybrané",
      cancelText: "Zrušit",
      danger: true
    });
    if (!confirmed) return;

    try {
      const resp = await fetch('/api/protocols/bulk-delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ protocol_ids: ids })
      });
      if (resp.ok) {
        const res = await resp.json();
        this.clearProtocolSelection();
        this.showToast(`Úspěšně smazáno ${res.deleted_count} protokolů.`);
        this.loadProtocols();
      } else {
        const err = await resp.json();
        await AppModal.alert({ title: "Chyba smazání", message: err.detail || "Nelze smazat vybrané protokoly." });
      }
    } catch (e) {
      await AppModal.alert({ title: "Chyba smazání", message: e.message });
    }
  },

  // Settings Overlay Modal
  openSettingsModal() {
    const modal = document.getElementById('settings-modal');
    if (modal) {
      modal.classList.add('active');
      this.showSettingsTab('profile');
    }
  },

  closeSettingsModal() {
    const modal = document.getElementById('settings-modal');
    if (modal) modal.classList.remove('active');
  },

  showSettingsTab(tabName) {
    document.querySelectorAll('.settings-tab-pane').forEach(p => p.style.display = 'none');
    document.querySelectorAll('.settings-tab-btn').forEach(b => b.classList.remove('active'));

    const targetPane = document.getElementById(`settings-pane-${tabName}`);
    const targetBtn = document.getElementById(`settings-tab-btn-${tabName}`);
    if (targetPane) targetPane.style.display = 'block';
    if (targetBtn) targetBtn.classList.add('active');

    // Only show Users, Database and Diagnostics tabs if current user is admin
    const isAdmin = (this.currentUser && this.currentUser.role === 'admin');
    const userTabBtn = document.getElementById('settings-tab-btn-users');
    const dbTabBtn = document.getElementById('settings-tab-btn-database');
    const diagTabBtn = document.getElementById('settings-tab-btn-diagnostics');
    if (userTabBtn) userTabBtn.style.display = isAdmin ? 'inline-flex' : 'none';
    if (dbTabBtn) dbTabBtn.style.display = isAdmin ? 'inline-flex' : 'none';
    if (diagTabBtn) diagTabBtn.style.display = isAdmin ? 'inline-flex' : 'none';

    if (tabName === 'profile') {
      const nameInput = document.getElementById('profile-fullname-input');
      const uDisplay = document.getElementById('profile-username-display');
      const rDisplay = document.getElementById('profile-role-display');
      if (nameInput && this.currentUser) nameInput.value = this.currentUser.full_name || '';
      if (uDisplay && this.currentUser) uDisplay.value = `@${this.currentUser.username || ''}`;
      if (rDisplay && this.currentUser) rDisplay.value = this.currentUser.role === 'admin' ? 'Správce aplikace' : 'Asistent';
    }
    else if (tabName === 'appearance') this.loadZoomSettings();
    else if (tabName === 'tasks') this.loadSettingsTasks();
    else if (tabName === 'presets') this.loadSettingsPresets();
    else if (tabName === 'users') this.loadSettingsUsers();
    else if (tabName === 'ai') this.loadAISettings();
    else if (tabName === 'database') this.loadDatabaseStats();
    else if (tabName === 'diagnostics') this.loadSystemDiagnostics();
    else if (tabName === 'about') this.loadChangelog();
  },

  // Per-user Zoom & Gesture settings
  loadZoomSettings() {
    const touchpadSens = localStorage.getItem('praktika_zoom_touchpad_sens') || '0.008';
    const wheelStep = localStorage.getItem('praktika_zoom_wheel_step') || '0.08';
    const touchSelect = document.getElementById('zoom-touchpad-sens-select');
    const wheelSelect = document.getElementById('zoom-wheel-step-select');
    if (touchSelect) touchSelect.value = touchpadSens;
    if (wheelSelect) wheelSelect.value = wheelStep;
  },

  handleZoomSettingChange(type, value) {
    if (type === 'touchpad') {
      localStorage.setItem('praktika_zoom_touchpad_sens', value);
      this.showToast("Citlivost touchpadu uložena.");
    } else if (type === 'wheel') {
      localStorage.setItem('praktika_zoom_wheel_step', value);
      this.showToast("Krok kolečka myši uložen.");
    }
  },

  // Database Management & Backups (Admin Only)
  async loadDatabaseStats() {
    const loading = document.getElementById('db-stats-loading');
    const container = document.getElementById('db-stats-container');
    if (loading) loading.style.display = 'block';
    if (container) container.style.display = 'none';

    try {
      const resp = await fetch('/api/database/stats');
      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || "Chyba při načítání statistik");
      }
      const data = await resp.json();
      if (loading) loading.style.display = 'none';
      if (container) container.style.display = 'flex';

      const formatBytes = (bytes) => {
        if (!bytes || bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
      };

      const sizeEl = document.getElementById('db-stat-size');
      const walEl = document.getElementById('db-stat-wal');
      const protoEl = document.getElementById('db-stat-protocols');
      const evalEl = document.getElementById('db-stat-evaluations');
      const annotEl = document.getElementById('db-stat-annotations');
      const lastBackupEl = document.getElementById('db-stat-last-backup');

      if (sizeEl) sizeEl.textContent = formatBytes(data.db_size_bytes);
      if (walEl) walEl.textContent = `${formatBytes(data.wal_size_bytes)} (${data.journal_mode})`;
      if (protoEl) protoEl.textContent = data.protocols_count;
      if (evalEl) evalEl.textContent = data.evaluations_count;
      if (annotEl) annotEl.textContent = data.annotations_count;
      if (lastBackupEl) {
        if (data.latest_backup) {
          const dt = new Date(data.latest_backup.created_at).toLocaleString('cs-CZ');
          lastBackupEl.textContent = `${data.latest_backup.filename} (${dt}, ${formatBytes(data.latest_backup.size_bytes)})`;
        } else {
          lastBackupEl.textContent = "Zatím žádná záloha";
        }
      }
    } catch (err) {
      if (loading) loading.textContent = `Chyba: ${err.message}`;
    }
  },

  downloadDatabaseBackup() {
    window.location.href = '/api/database/backup';
    this.showToast("Stahování zálohy databáze zahájeno...");
  },

  async optimizeDatabase() {
    const btn = document.getElementById('btn-db-optimize');
    if (btn) btn.disabled = true;
    try {
      const resp = await fetch('/api/database/optimize', { method: 'POST' });
      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || "Chyba při optimalizaci");
      }
      const data = await resp.json();
      this.showToast(data.message || "Databáze byla optimalizována.");
      await this.loadDatabaseStats();
    } catch (e) {
      await AppModal.alert({ title: "Chyba", message: e.message });
    } finally {
      if (btn) btn.disabled = false;
    }
  },

  async handleRestoreDatabase(e) {
    e.preventDefault();
    const fileInput = document.getElementById('db-restore-file-input');
    if (!fileInput || !fileInput.files || fileInput.files.length === 0) return;

    const ok = await AppModal.confirm({
      title: "Varování: Obnova databáze",
      message: "Opravdu chcete přepsat stávající databázi nahranou zálohou? Aplikace před obnovou automaticky vytvoří bezpečnostní zálohu, ale stávající stav bude nahrazen.",
      confirmText: "Obnovit databázi"
    });
    if (!ok) return;

    const btn = document.getElementById('btn-db-restore');
    if (btn) btn.disabled = true;

    try {
      const fd = new FormData();
      fd.append('file', fileInput.files[0]);
      const resp = await fetch('/api/database/restore', {
        method: 'POST',
        body: fd
      });
      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || "Chyba při obnově databáze");
      }
      const data = await resp.json();
      await AppModal.alert({ title: "Úspěch", message: data.message || "Databáze byla úspěšně obnovena." });
      fileInput.value = '';
      await this.loadDatabaseStats();
      await this.loadProtocols();
    } catch (err) {
      await AppModal.alert({ title: "Chyba při obnově", message: err.message });
    } finally {
      if (btn) btn.disabled = false;
    }
  },

  // System Diagnostics & Gemini test (Admin Only)
  async loadSystemDiagnostics() {
    try {
      const resp = await fetch('/api/system/diagnostics');
      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || "Chyba diagnostiky");
      }
      const data = await resp.json();
      const pyEl = document.getElementById('diag-python-ver');
      const osEl = document.getElementById('diag-os');
      const mupdfEl = document.getElementById('diag-pymupdf-ver');
      const sqlEl = document.getElementById('diag-sqlite-ver');
      const jEl = document.getElementById('diag-journal-mode');
      const dbPathEl = document.getElementById('diag-db-path');
      const keyEl = document.getElementById('diag-key-status');
      const modelEl = document.getElementById('diag-model-status');

      if (pyEl) pyEl.textContent = `${data.python_version} (LTS 64-bit)`;
      if (osEl) osEl.textContent = data.os;
      if (mupdfEl) mupdfEl.textContent = data.pymupdf_version;
      if (sqlEl) sqlEl.textContent = `SQLite v${data.sqlite_version}`;
      if (jEl) jEl.textContent = data.journal_mode;
      if (dbPathEl) {
        dbPathEl.textContent = data.db_path;
        dbPathEl.title = data.db_path;
      }
      if (keyEl) keyEl.textContent = data.gemini_api_key_status;
      if (modelEl) modelEl.textContent = data.gemini_preferred_model;
    } catch (e) {
      console.warn("Diagnostics warning:", e);
    }
  },

  async testGeminiConnection() {
    const btn = document.getElementById('btn-test-gemini');
    const resultBox = document.getElementById('diag-test-result-box');
    if (btn) btn.disabled = true;
    if (resultBox) {
      resultBox.style.display = 'block';
      resultBox.style.background = 'rgba(99, 102, 241, 0.1)';
      resultBox.style.color = 'var(--text-main)';
      resultBox.textContent = "Odesílám testovací dotaz na Google Gemini API...";
    }

    try {
      const resp = await fetch('/api/system/test-gemini', { method: 'POST' });
      const data = await resp.json();
      if (!resultBox) return;

      if (resp.ok && data.success) {
        resultBox.style.background = 'rgba(34, 197, 94, 0.15)';
        resultBox.style.color = 'var(--accent-green)';
        resultBox.innerHTML = `<strong>✓ Spojení úspěšné:</strong> Model ${data.model} odpověděl za <strong>${data.latency_ms} ms</strong>.`;
      } else {
        resultBox.style.background = 'rgba(239, 68, 68, 0.15)';
        resultBox.style.color = 'var(--accent-red)';
        resultBox.innerHTML = `<strong>✕ Chyba spojení:</strong> ${this.escape(data.message || data.error || "Neznámá chyba")}`;
      }
    } catch (err) {
      if (resultBox) {
        resultBox.style.background = 'rgba(239, 68, 68, 0.15)';
        resultBox.style.color = 'var(--accent-red)';
        resultBox.textContent = `Chyba požadavku: ${err.message}`;
      }
    } finally {
      if (btn) btn.disabled = false;
    }
  },

  // Settings: Tasks Management by Course (FPRA1 / FPRA2 / ZFM2)
  setTaskCourseFilter(courseCode) {
    this.taskCourseFilter = courseCode;
    ['FPRA1', 'FPRA2', 'ZFM2'].forEach(c => {
      const btn = document.getElementById(`course-tab-${c}`);
      if (btn) {
        if (c === courseCode) {
          btn.classList.add('active');
          btn.style.background = 'var(--primary)';
          btn.style.color = '#ffffff';
          btn.style.fontWeight = '700';
        } else {
          btn.classList.remove('active');
          btn.style.background = 'var(--card-bg)';
          btn.style.color = 'var(--text-main)';
          btn.style.fontWeight = 'normal';
        }
      }
    });
    this.loadSettingsTasks(courseCode);
  },

  async loadSettingsTasks(courseCode = null) {
    const container = document.getElementById('settings-tasks-list');
    if (!container) return;

    const course = courseCode || this.taskCourseFilter || 'FPRA1';
    this.taskCourseFilter = course;

    const isAdmin = (this.currentUser && this.currentUser.role === 'admin');
    const addTaskForm = document.getElementById('task-name')?.closest('form');
    if (addTaskForm) {
      addTaskForm.style.display = isAdmin ? 'flex' : 'none';
    }

    const resp = await fetch(`/api/measurements?course_code=${course}`);
    const tasks = await resp.json();

    if (!tasks || tasks.length === 0) {
      container.innerHTML = `<div style="padding:16px; text-align:center; color:var(--text-muted); font-size:0.85rem;">Žádné úlohy pro předmět ${course}. ${isAdmin ? 'Můžete přidat novou úlohu formulářem výše.' : ''}</div>`;
      return;
    }

    container.innerHTML = tasks.map(t => {
      const hasInstructions = !!(t.instructions_text && t.instructions_text.trim());
      const charCount = hasInstructions ? t.instructions_text.trim().length : 0;
      return `
      <div style="display:flex; align-items:center; justify-content:space-between; background:var(--bg); border:1px solid var(--border); padding:8px 12px; border-radius:4px; margin-bottom:6px;">
        <div style="flex:1; min-width:0; margin-right:12px;">
          <div style="font-weight:700; color:var(--text-main); font-size:0.88rem;">Úloha ${t.number}: ${this.escape(t.name)}</div>
          <div style="font-size:0.75rem; color:var(--text-muted); display:flex; align-items:center; gap:8px; margin-top:2px;">
            <span>Předmět: <strong style="color:var(--primary);">${t.course_code || course}</strong></span>
            <span>Semestr: <strong>${t.semester_type}</strong></span>
            ${hasInstructions ? `<span style="color:var(--accent-green); font-weight:600;">✓ Má zadání (${charCount} znaků)</span>` : '<span style="color:var(--text-muted); font-style:italic;">Zadání pro AI nezadáno</span>'}
          </div>
        </div>
        <div style="display:flex; gap:6px; flex-shrink:0;">
          <button class="btn btn-secondary btn-sm" onclick="App.openInstructionsModal(${t.id})" title="${isAdmin ? 'Zobrazit / upravit zadání' : 'Zobrazit zadání a pokyny'}">📝 Pokyny k úloze</button>
          ${isAdmin ? `
            <button class="btn btn-secondary btn-sm" onclick="App.editTask(${t.id}, '${this.escape(t.name)}')">Přejmenovat</button>
            <button class="btn btn-danger btn-sm" onclick="App.deleteTask(${t.id})">✕</button>
          ` : ''}
        </div>
      </div>
    `;
    }).join('');
  },

  async handleAddTask(e) {
    e.preventDefault();
    const course = this.taskCourseFilter || 'FPRA1';
    const semType = (course === 'FPRA1') ? 'ZS' : 'LS';
    const num = parseInt(document.getElementById('task-num').value);
    const name = document.getElementById('task-name').value.trim();
    if (!name || isNaN(num)) return;

    const resp = await fetch('/api/measurements', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        code: num < 10 ? `0${num}` : `${num}`,
        number: num,
        name: name,
        semester_type: semType,
        course_code: course
      })
    });
    if (resp.ok) {
      this.showToast(`Úloha přidána do ${course}!`);
      document.getElementById('task-name').value = '';
      this.loadSettingsTasks(course);
      this.loadInitialMetadata();
    } else {
      const err = await resp.json();
      await AppModal.alert({ title: "Chyba", message: err.detail || "Chyba při přidávání úlohy." });
    }
  },

  async editTask(id, currentName) {
    const newName = await AppModal.prompt({
      title: "Přejmenovat úlohu",
      message: "Upravte název laboratorní úlohy:",
      defaultValue: currentName,
      confirmText: "Uložit"
    });
    if (newName && newName.trim()) {
      const resp = await fetch(`/api/measurements/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newName.trim() })
      });
      if (resp.ok) {
        this.showToast("Úloha byla upravena.");
        this.loadSettingsTasks(this.taskCourseFilter || 'FPRA1');
        this.loadInitialMetadata();
      } else {
        const err = await resp.json();
        await AppModal.alert({ title: "Chyba", message: err.detail || "Chyba při úpravě úlohy." });
      }
    }
  },

  async deleteTask(id) {
    const ok = await AppModal.confirm({
      title: "Smazat úlohu",
      message: "Opravdu chcete smazat tuto úlohu?",
      confirmText: "Smazat",
      danger: true
    });
    if (!ok) return;
    const resp = await fetch(`/api/measurements/${id}`, { method: 'DELETE' });
    if (resp.ok) {
      this.showToast("Úloha byla smazána.");
      this.loadSettingsTasks(this.taskCourseFilter || 'FPRA1');
      this.loadInitialMetadata();
    } else {
      const err = await resp.json();
      await AppModal.alert({ title: "Chyba při mazání", message: err.detail || "Chyba při mazání." });
    }
  },

  async openInstructionsModal(measId) {
    const modal = document.getElementById('instructions-modal');
    const idInput = document.getElementById('instructions-meas-id');
    const titleEl = document.getElementById('instructions-modal-title');
    const textInput = document.getElementById('instructions-text-input');
    if (!modal) return;

    const isAdmin = (this.currentUser && this.currentUser.role === 'admin');
    if (textInput) textInput.readOnly = !isAdmin;

    const modalForm = modal.querySelector('form');
    const submitBtn = modalForm ? modalForm.querySelector('button[type="submit"]') : null;
    if (submitBtn) submitBtn.style.display = isAdmin ? '' : 'none';

    const uploadArea = document.getElementById('instructions-file-input')?.closest('div');
    if (uploadArea) uploadArea.style.display = isAdmin ? '' : 'none';

    idInput.value = measId;
    textInput.value = 'Načítám pokyny...';
    modal.classList.add('active');

    try {
      const resp = await fetch('/api/measurements');
      if (resp.ok) {
        const list = await resp.json();
        this.measurements = list;
        const found = list.find(m => m.id === measId);
        if (found) {
          if (titleEl) titleEl.textContent = `Pokyny k úloze ${found.number}: ${found.name}`;
          textInput.value = found.instructions_text || '';
        }
      }
    } catch(e) {
      textInput.value = '';
    }
  },

  closeInstructionsModal() {
    const modal = document.getElementById('instructions-modal');
    if (modal) modal.classList.remove('active');
  },

  async handleSaveInstructions(e) {
    e.preventDefault();
    const measId = parseInt(document.getElementById('instructions-meas-id').value);
    const instructionsText = document.getElementById('instructions-text-input').value;

    try {
      const resp = await fetch(`/api/measurements/${measId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instructions_text: instructionsText })
      });
      if (resp.ok) {
        this.showToast("Pokyny k úloze byly úspěšně uloženy pro AI asistenta!");
        this.closeInstructionsModal();
        const semType = document.getElementById('task-sem-type')?.value || 'ZS';
        this.loadSettingsTasks(semType);
        await this.loadInitialMetadata();
      } else {
        const err = await resp.json();
        await AppModal.alert({ title: "Chyba", message: err.detail || "Chyba při ukládání pokynů." });
      }
    } catch(err) {
      await AppModal.alert({ title: "Chyba při ukládání", message: err.message });
    }
  },

  async handleUploadInstructionsFile(event) {
    const file = event.target.files && event.target.files[0];
    if (!file) return;
    const measId = parseInt(document.getElementById('instructions-meas-id').value);
    if (!measId) {
      await AppModal.alert({ title: "Chyba", message: "Není vybrána žádná úloha." });
      return;
    }
    const formData = new FormData();
    formData.append('file', file);
    try {
      this.showToast("Načítám návod a Gemini AI vytváří hodnotící manuál...");
      const textInput = document.getElementById('instructions-text-input');
      if (textInput) textInput.value = "⏳ Zpracovávám soubor a generuji strukturovaný hodnotící manuál pomocí Gemini...";
      const resp = await fetch(`/api/measurements/${measId}/upload-instructions`, {
        method: 'POST',
        body: formData
      });
      if (resp.ok) {
        const data = await resp.json();
        if (textInput) {
          textInput.value = data.instructions_text || '';
        }
        if (data.rubric_generated) {
          this.showToast(`Hodnotící manuál vygenerován pomocí AI (${data.chars_extracted} znaků zdrojového textu)!`);
        } else {
          this.showToast(`Text návodu byl úspěšně načten (${data.chars_extracted} znaků)!`);
        }
      } else {
        const err = await resp.json();
        await AppModal.alert({ title: "Chyba zadání", message: err.detail || "Chyba při nahrávání zadání." });
      }
    } catch (e) {
      await AppModal.alert({ title: "Chyba souboru", message: "Chyba při nahrávání souboru: " + e.message });
    } finally {
      event.target.value = '';
    }
  },

  async generateRubricFromInstructions() {
    const measId = parseInt(document.getElementById('instructions-meas-id').value);
    const textInput = document.getElementById('instructions-text-input');
    const currentText = textInput ? textInput.value.trim() : '';

    if (!measId) {
      await AppModal.alert({ title: "Chyba", message: "Není vybrána žádná úloha." });
      return;
    }
    if (!currentText) {
      await AppModal.alert({ title: "Chybí text", message: "Nejprve nahrajte soubor zadání nebo vložte text pokynů do textového pole." });
      return;
    }

    const btn1 = document.getElementById('btn-generate-rubric');
    const btn2 = document.getElementById('btn-generate-rubric-top');
    const origHtml1 = btn1 ? btn1.innerHTML : '';
    const origHtml2 = btn2 ? btn2.innerHTML : '';
    if (btn1) { btn1.disabled = true; btn1.innerHTML = "⏳ Generuji..."; }
    if (btn2) { btn2.disabled = true; btn2.innerHTML = "⏳ Generuji..."; }

    try {
      this.showToast("Gemini syntetizuje text do strukturovaného hodnotícího manuálu...");
      const resp = await fetch(`/api/measurements/${measId}/generate-rubric`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instructions_text: currentText })
      });
      if (resp.ok) {
        const data = await resp.json();
        if (textInput && data.instructions_text) {
          textInput.value = data.instructions_text;
        }
        this.showToast("Hodnotící manuál byl úspěšně vygenerován!");
      } else {
        const err = await resp.json();
        await AppModal.alert({ title: "Chyba generování", message: err.detail || "Chyba při generování manuálu." });
      }
    } catch (e) {
      await AppModal.alert({ title: "Chyba komunikace s AI", message: "Chyba při komunikaci s AI: " + e.message });
    } finally {
      if (btn1) { btn1.disabled = false; btn1.innerHTML = origHtml1; }
      if (btn2) { btn2.disabled = false; btn2.innerHTML = origHtml2; }
    }
  },

  // Settings: Presets Management
  async loadSettingsPresets() {
    const dedList = document.getElementById('settings-deductions-list');
    const commList = document.getElementById('settings-comments-list');

    const [dResp, cResp] = await Promise.all([
      fetch('/api/presets?type=deduction'),
      fetch('/api/presets?type=comment')
    ]);

    if (dedList && dResp.ok) {
      const deductions = await dResp.json();
      dedList.innerHTML = deductions.map(d => `
        <div style="display:flex; align-items:center; justify-content:space-between; background:var(--bg); border:1px solid var(--border); padding:6px 10px; border-radius:6px; margin-bottom:5px; font-size:0.83rem;">
          <div>
            <span style="font-weight:700; color:var(--accent-red);">-${d.pts}b [${d.category}]:</span>
            <span>${this.escape(d.text)}</span>
          </div>
          <button class="btn btn-danger btn-sm" onclick="App.deletePresetItem(${d.id})">✕</button>
        </div>
      `).join('');
    }

    if (commList && cResp.ok) {
      const comments = await cResp.json();
      commList.innerHTML = comments.map(c => `
        <div style="display:flex; align-items:center; justify-content:space-between; background:var(--bg); border:1px solid var(--border); padding:6px 10px; border-radius:6px; margin-bottom:5px; font-size:0.83rem;">
          <div>${this.escape(c.text)}</div>
          <button class="btn btn-danger btn-sm" onclick="App.deletePresetItem(${c.id})">✕</button>
        </div>
      `).join('');
    }
  },

  async handleAddDeductionPreset(e) {
    e.preventDefault();
    const cat = document.getElementById('preset-ded-cat').value;
    const pts = parseFloat(document.getElementById('preset-ded-pts').value);
    const text = document.getElementById('preset-ded-text').value.trim();
    if (!text) return;

    await fetch('/api/presets', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type: 'deduction', category: cat, pts, text })
    });
    this.showToast("Předvolba srážky přidána!");
    document.getElementById('preset-ded-text').value = '';
    this.loadSettingsPresets();
    this.loadPresets();
  },

  async handleAddCommentPreset(e) {
    e.preventDefault();
    const text = document.getElementById('preset-comm-text').value.trim();
    if (!text) return;

    await fetch('/api/presets', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type: 'comment', category: 'obecne', pts: 0.0, text })
    });
    this.showToast("Rychlý komentář přidán!");
    document.getElementById('preset-comm-text').value = '';
    this.loadSettingsPresets();
    this.loadPresets();
  },

  async deletePresetItem(id) {
    await fetch(`/api/presets/${id}`, { method: 'DELETE' });
    this.showToast("Předvolba smazána.");
    this.loadSettingsPresets();
    this.loadPresets();
  },

  // Settings: Users Management (Admin only)
  async loadSettingsUsers() {
    const list = document.getElementById('settings-users-list');
    if (!list) return;

    const resp = await fetch('/api/users');
    const users = await resp.json();

    list.innerHTML = users.map(u => `
      <div style="display:flex; align-items:center; justify-content:space-between; background:var(--bg); border:1px solid var(--border); padding:8px 12px; border-radius:6px; margin-bottom:6px;">
        <div>
          <strong>${this.escape(u.full_name)}</strong>
          <span style="font-size:0.75rem; color:var(--text-muted); margin-left:6px;">(@${u.username})</span>
          <span class="status-badge ${u.role === 'admin' ? 'status-graded' : 'status-new'}" style="margin-left:6px;">
            ${u.role === 'admin' ? 'Správce aplikace' : 'Asistent'}
          </span>
          <span class="status-badge ${u.is_active ? 'status-graded' : 'status-revision'}" style="margin-left:4px; font-size:0.68rem;">
            ${u.is_active ? 'Aktivní' : 'Deaktivován'}
          </span>
        </div>
        <div style="display:flex; gap:6px; align-items:center;">
          <button class="btn btn-secondary btn-sm" style="font-size:0.75rem; padding:2px 8px;" onclick="App.editUserModal(${u.id}, '${this.escape(u.full_name || '')}', '${u.role}')" title="Upravit jméno či roli">✎ Upravit</button>
          <button class="btn btn-secondary btn-sm" style="font-size:0.75rem; padding:2px 8px;" onclick="App.adminResetPasswordPrompt(${u.id}, '${this.escape(u.full_name || u.username)}')">🔑 Reset hesla</button>
          ${u.id !== this.currentUser.id ? `
            <button class="btn btn-secondary btn-sm" style="font-size:0.75rem; padding:2px 8px;" onclick="App.toggleUserActive(${u.id}, ${!u.is_active})" title="${u.is_active ? 'Deaktivovat účet' : 'Aktivovat účet'}">
              ${u.is_active ? 'Deaktivovat' : 'Aktivovat'}
            </button>
            <button class="btn btn-danger btn-sm" style="font-size:0.75rem; padding:2px 8px;" onclick="App.deleteUserItem(${u.id})">Smazat</button>
          ` : '<span style="font-size:0.75rem; color:var(--text-muted); padding:0 4px;">(Vy)</span>'}
        </div>
      </div>
    `).join('');
  },

  async toggleUserActive(userId, newActive) {
    try {
      const resp = await fetch(`/api/users/${userId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: newActive })
      });
      if (resp.ok) {
        this.showToast(newActive ? "Účet byl aktivován." : "Účet byl deaktivován.");
        this.loadSettingsUsers();
      } else {
        const err = await resp.json();
        await AppModal.alert({ title: "Chyba", message: err.detail || "Chyba při změně stavu účtu." });
      }
    } catch (e) {
      await AppModal.alert({ title: "Chyba komunikace", message: "Chyba při komunikaci: " + e.message });
    }
  },

  async editUserModal(userId, currentName, currentRole) {
    const res = await AppModal.showForm({
      title: "Upravit uživatele / asistenta",
      fields: [
        { id: "full_name", label: "Celé jméno vyučujícího / asistenta:", type: "text", value: currentName, required: true },
        { id: "role", label: "Oprávnění / role v systému:", type: "select", value: currentRole, options: [
          { value: "assistant", label: "Asistent (oprava přidělených protokolů)" },
          { value: "admin", label: "Správce aplikace (plný přístup, správa uživatelů a úloh)" }
        ]}
      ],
      confirmText: "Uložit změny"
    });
    if (!res || !res.full_name || !res.full_name.trim()) return;

    try {
      const resp = await fetch(`/api/users/${userId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ full_name: res.full_name.trim(), role: res.role })
      });
      if (resp.ok) {
        this.showToast("Údaje uživatele byly upraveny.");
        this.loadSettingsUsers();
      } else {
        const err = await resp.json();
        await AppModal.alert({ title: "Chyba", message: err.detail || "Chyba při úpravě uživatele." });
      }
    } catch (e) {
      await AppModal.alert({ title: "Chyba komunikace", message: e.message });
    }
  },

  async handleCreateUser(e) {
    e.preventDefault();
    const username = document.getElementById('create-user-login').value.trim();
    const fullName = document.getElementById('create-user-name').value.trim();
    const password = document.getElementById('create-user-pw').value;
    const role = document.getElementById('create-user-role').value;

    const resp = await fetch('/api/users', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, full_name: fullName, password, role })
    });
    if (resp.ok) {
      this.showToast(`Uživatel ${fullName} vytvořen!`);
      document.getElementById('create-user-login').value = '';
      document.getElementById('create-user-name').value = '';
      document.getElementById('create-user-pw').value = '';
      this.loadSettingsUsers();
    } else {
      const err = await resp.json();
      await AppModal.alert({ title: "Chyba", message: err.detail || "Chyba při vytváření uživatele." });
    }
  },

  async deleteUserItem(id) {
    const ok = await AppModal.confirm({
      title: "Smazat uživatele",
      message: "Opravdu smazat tohoto uživatele? Tato akce je nevratná.",
      confirmText: "Smazat",
      danger: true
    });
    if (!ok) return;
    try {
      const resp = await fetch(`/api/users/${id}`, { method: 'DELETE' });
      if (resp.ok) {
        this.showToast("Uživatel byl smazán.");
        this.loadSettingsUsers();
      } else {
        let err;
        try { err = await resp.json(); } catch(e) { err = { detail: resp.statusText }; }
        await AppModal.alert({ title: "Chyba", message: err.detail || "Chyba při mazání uživatele." });
      }
    } catch(e) {
      await AppModal.alert({ title: "Chyba", message: e.message });
    }
  },

  async adminResetPasswordPrompt(userId, userName) {
    const newPw = await AppModal.prompt({
      title: "Resetovat heslo uživatele",
      message: `Zadejte nové přístupové heslo pro uživatele ${userName} (min. 3 znaky):`,
      placeholder: "Nové heslo...",
      inputType: "password",
      confirmText: "Nastavit heslo"
    });
    if (newPw === null) return;
    if (newPw.trim().length < 3) {
      await AppModal.alert({ title: "Neplatné heslo", message: "Nové heslo musí mít alespoň 3 znaky." });
      return;
    }
    try {
      const resp = await fetch(`/api/users/${userId}/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_password: newPw.trim() })
      });
      if (resp.ok) {
        const data = await resp.json();
        this.showToast(data.message || "Heslo bylo úspěšně změněno!");
      } else {
        const err = await resp.json();
        await AppModal.alert({ title: "Chyba", message: err.detail || "Chyba při změně hesla." });
      }
    } catch (e) {
      await AppModal.alert({ title: "Chyba", message: e.message });
    }
  },

  async handleUpdateProfileName(e) {
    if (e && e.preventDefault) e.preventDefault();
    const input = document.getElementById('profile-fullname-input');
    if (!input || !input.value.trim()) {
      await AppModal.alert({ title: "Neplatné jméno", message: "Zadejte platné jméno." });
      return;
    }
    const newName = input.value.trim();
    try {
      const resp = await fetch('/api/auth/profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ full_name: newName })
      });
      if (resp.ok) {
        if (this.currentUser) this.currentUser.full_name = newName;
        localStorage.setItem('evaluator_display_name', newName);
        this.renderUserBadges();
        this.showToast("Vaše jméno pro komentáře bylo uloženo!");
        if (window.PDFStudio) window.PDFStudio.currentUser = this.currentUser;
      } else {
        const err = await resp.json();
        await AppModal.alert({ title: "Chyba", message: err.detail || "Chyba při ukládání jména." });
      }
    } catch (e) {
      await AppModal.alert({ title: "Chyba komunikace", message: "Chyba při komunikaci: " + e.message });
    }
  },

  togglePasswordVisibility(inputId, btn) {
    const input = document.getElementById(inputId);
    if (!input) return;
    if (input.type === 'password') {
      input.type = 'text';
      btn.textContent = '🙈';
      btn.title = 'Skrýt heslo';
    } else {
      input.type = 'password';
      btn.textContent = '👁';
      btn.title = 'Zobrazit heslo';
    }
  },

  async handleChangePassword(e) {
    e.preventDefault();
    const oldPassword = document.getElementById('pw-current').value;
    const newPassword = document.getElementById('pw-new').value;
    const confirmPassword = document.getElementById('pw-confirm').value;

    if (newPassword !== confirmPassword) {
      await AppModal.alert({ title: "Chyba hesla", message: "Nová hesla se neshodují." });
      return;
    }

    const resp = await fetch('/api/auth/change-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ old_password: oldPassword, new_password: newPassword })
    });
    if (resp.ok) {
      this.showToast("Heslo bylo úspěšně změněno!");
      document.getElementById('pw-current').value = '';
      document.getElementById('pw-new').value = '';
      document.getElementById('pw-confirm').value = '';
    } else {
      const err = await resp.json();
      await AppModal.alert({ title: "Chyba", message: err.detail || "Chyba při změně hesla." });
    }
  },

  // Termíny (Slots) deletion
  async deleteSlotItem(id) {
    const ok = await AppModal.confirm({
      title: "Smazat termín",
      message: "Opravdu smazat tento termín praktika?",
      confirmText: "Smazat",
      danger: true
    });
    if (!ok) return;
    const resp = await fetch(`/api/slots/${id}`, { method: 'DELETE' });
    if (resp.ok) {
      this.showToast("Termín byl smazán.");
      await this.loadSlotsForSemester(this.activeSemesterId);
      this.loadManagementTables();
    } else {
      const err = await resp.json();
      await AppModal.alert({ title: "Chyba", message: err.detail || "Chyba při mazání termínu." });
    }
  },

  async editSlotModal(id, currentCourse, currentDay, currentStart, currentEnd, currentName, currentRoom) {
    const res = await AppModal.showForm({
      title: "Upravit termín praktika",
      fields: [
        { id: "course_code", label: "Předmět praktika:", type: "select", value: currentCourse || "FPRA1", options: [
          { value: "FPRA1", label: "FPRA1 (Zimní semestr)" },
          { value: "FPRA2", label: "FPRA2 (Letní semestr)" },
          { value: "ZFM2", label: "ZFM2 (Letní semestr)" }
        ]},
        { id: "day_of_week", label: "Den v týdnu:", type: "select", value: currentDay || "Pondělí", options: [
          "Pondělí", "Úterý", "Středa", "Čtvrtek", "Pátek"
        ]},
        { id: "time_start", label: "Začátek (HH:MM):", type: "text", value: currentStart || "08:00" },
        { id: "time_end", label: "Konec (HH:MM):", type: "text", value: currentEnd || "11:00" },
        { id: "name", label: "Název skupiny / označení:", type: "text", value: currentName || "" },
        { id: "room", label: "Učebna / laborka:", type: "text", value: currentRoom || "" }
      ],
      confirmText: "Uložit termín"
    });
    if (!res) return;

    try {
      const resp = await fetch(`/api/slots/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          course_code: res.course_code,
          day_of_week: res.day_of_week,
          time_start: res.time_start,
          time_end: res.time_end,
          name: res.name || (res.room ? `Skupina (${res.room})` : `Skupina`),
          room: res.room
        })
      });
      if (resp.ok) {
        this.showToast("Termín byl upraven!");
        await this.loadSlotsForSemester(this.activeSemesterId);
        this.loadManagementTables();
      } else {
        const err = await resp.json();
        await AppModal.alert({ title: "Chyba", message: err.detail || "Chyba při úpravě termínu." });
      }
    } catch(e) {
      await AppModal.alert({ title: "Chyba komunikace", message: e.message });
    }
  },

  async loadManagementTables() {
    const isAdmin = (this.currentUser && this.currentUser.role === 'admin');

    // Forms visibility
    const semForm = document.getElementById('new-sem-code')?.closest('form');
    if (semForm) semForm.style.display = isAdmin ? 'flex' : 'none';
    const slotForm = document.getElementById('new-slot-course')?.closest('form') || document.getElementById('new-slot-day')?.closest('form');
    if (slotForm) slotForm.style.display = isAdmin ? 'grid' : 'none';

    // Semesters
    const semTable = document.getElementById('manage-semesters-tbody');
    if (semTable) {
      const resp = await fetch('/api/semesters');
      const data = await resp.json();
      semTable.innerHTML = data.map(s => `
        <tr>
          <td><strong>${s.code}</strong></td>
          <td>${this.escape(s.name)}</td>
          <td>${s.is_active ? '<span class="status-badge status-graded">Aktivní</span>' : '<span class="status-badge status-new">Neaktivní</span>'}</td>
          <td style="text-align:right;">
            ${isAdmin ? `
              <div style="display:inline-flex; gap:4px;">
                ${!s.is_active ? `<button class="btn btn-secondary btn-sm" onclick="App.activateSemester(${s.id})" title="Nastavit jako aktivní semestr">Aktivovat</button>` : ''}
                <button class="btn btn-secondary btn-sm" onclick="App.editSemester(${s.id}, '${this.escape(s.code)}', '${this.escape(s.name)}')" title="Upravit semestr">✎ Upravit</button>
                <button class="btn btn-danger btn-sm" onclick="App.deleteSemester(${s.id}, '${this.escape(s.code)}')" title="Smazat semestr">✕</button>
              </div>
            ` : '<span style="font-size:0.75rem; color:var(--text-muted);">Jen pro čtení</span>'}
          </td>
        </tr>
      `).join('');
    }

    // Slots
    const slotTable = document.getElementById('manage-slots-tbody');
    if (slotTable) {
      const resp = await fetch(`/api/slots?semester_id=${this.activeSemesterId}`);
      const data = await resp.json();
      slotTable.innerHTML = data.map(sl => `
        <tr>
          <td><span class="status-badge" style="background:var(--primary-subtle); color:var(--primary); font-weight:700;">${sl.course_code || 'FPRA1'}</span></td>
          <td><strong>${sl.day_of_week}</strong></td>
          <td>${sl.time_start} – ${sl.time_end}</td>
          <td>${this.escape(sl.name)}</td>
          <td>${sl.room || '—'}</td>
          <td style="text-align:right;">
            ${isAdmin ? `
              <div style="display:inline-flex; gap:4px;">
                <button class="btn btn-secondary btn-sm" onclick="App.editSlotModal(${sl.id}, '${sl.course_code || 'FPRA1'}', '${sl.day_of_week}', '${sl.time_start}', '${sl.time_end}', '${this.escape(sl.name)}', '${this.escape(sl.room || '')}')" title="Upravit termín">✎ Upravit</button>
                <button class="btn btn-danger btn-sm" onclick="App.deleteSlotItem(${sl.id})" title="Smazat termín">✕</button>
              </div>
            ` : '<span style="font-size:0.75rem; color:var(--text-muted);">Jen pro čtení</span>'}
          </td>
        </tr>
      `).join('');
    }
  },

  async handleAddSemester(e) {
    e.preventDefault();
    const code = document.getElementById('new-sem-code').value.trim();
    const name = document.getElementById('new-sem-name').value.trim();
    if (!code || !name) return;

    const resp = await fetch('/api/semesters', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, name, is_active: true })
    });
    if (resp.ok) {
      this.showToast(`Semestr ${code} vytvořen!`);
      document.getElementById('new-sem-code').value = '';
      document.getElementById('new-sem-name').value = '';
      await this.loadInitialMetadata();
      this.loadManagementTables();
    } else {
      const err = await resp.json();
      await AppModal.alert({ title: "Chyba", message: err.detail || "Chyba při vytváření semestru." });
    }
  },

  async editSemester(id, currentCode, currentName) {
    const res = await AppModal.showForm({
      title: "Upravit semestr",
      fields: [
        { id: "code", label: "Kód semestru (např. 2026ZS):", type: "text", value: currentCode, required: true },
        { id: "name", label: "Název semestru:", type: "text", value: currentName, required: true }
      ],
      confirmText: "Uložit semestr"
    });
    if (!res || !res.code || !res.name) return;

    try {
      const resp = await fetch(`/api/semesters/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: res.code.trim(), name: res.name.trim() })
      });
      if (resp.ok) {
        this.showToast("Semestr byl upraven!");
        await this.loadInitialMetadata();
        this.loadManagementTables();
      } else {
        const err = await resp.json();
        await AppModal.alert({ title: "Chyba", message: err.detail || "Chyba při úpravě semestru." });
      }
    } catch (e) {
      await AppModal.alert({ title: "Chyba komunikace", message: e.message });
    }
  },

  async deleteSemester(id, code) {
    const ok = await AppModal.confirm({
      title: `Smazat semestr ${code}`,
      message: `Opravdu smazat semestr ${code}? Tato akce smaže i všechny přiřazené termíny týdne. Pokud semestr obsahuje protokoly studentů, nelze jej smazat.`,
      confirmText: "Smazat semestr",
      danger: true
    });
    if (!ok) return;
    try {
      const resp = await fetch(`/api/semesters/${id}`, { method: 'DELETE' });
      if (resp.ok) {
        this.showToast(`Semestr ${code} byl smazán.`);
        await this.loadInitialMetadata();
        this.loadManagementTables();
      } else {
        const err = await resp.json();
        await AppModal.alert({ title: "Nelze smazat semestr", message: err.detail || "Chyba při mazání semestru." });
      }
    } catch (e) {
      await AppModal.alert({ title: "Chyba komunikace", message: e.message });
    }
  },

  async activateSemester(semId) {
    await fetch(`/api/semesters/${semId}/activate`, { method: 'POST' });
    this.showToast("Aktivní semestr změněn.");
    await this.loadInitialMetadata();
    this.loadManagementTables();
  },

  async handleAddSlot(e) {
    e.preventDefault();
    const course = document.getElementById('new-slot-course')?.value || 'FPRA1';
    const day = document.getElementById('new-slot-day').value;
    const start = document.getElementById('new-slot-start').value;
    const end = document.getElementById('new-slot-end').value;
    const name = document.getElementById('new-slot-name').value.trim();
    const room = document.getElementById('new-slot-room').value.trim();

    const resp = await fetch('/api/slots', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        semester_id: this.activeSemesterId,
        course_code: course,
        day_of_week: day,
        time_start: start,
        time_end: end,
        name: name || (room ? `Skupina (${room})` : `Skupina`),
        room: room
      })
    });
    if (resp.ok) {
      this.showToast("Nový termín byl přidán!");
      document.getElementById('new-slot-name').value = '';
      await this.loadSlotsForSemester(this.activeSemesterId);
      this.loadManagementTables();
    } else {
      const err = await resp.json();
      await AppModal.alert({ title: "Chyba", message: err.detail || "Chyba při přidávání termínu." });
    }
  },

  // Protocol Metadata Editing Modal
  async openEditMetadataModal(protoId) {
    const p = (this.loadedProtocols || []).find(x => x.id === protoId);
    if (!p) return;

    document.getElementById('edit-meta-proto-id').value = p.id;
    document.getElementById('edit-meta-student').value = p.student_name;

    // Semesters
    const semSelect = document.getElementById('edit-meta-semester');
    semSelect.innerHTML = this.semesters.map(s => `
      <option value="${s.id}" ${s.id === p.semester_id ? 'selected' : ''}>${s.code} (${s.name})</option>
    `).join('');

    // Load slots for that semester and select current slot
    await this.populateEditMetaSlots(p.semester_id, p.slot_id);

    // Measurements
    const measSelect = document.getElementById('edit-meta-measurement');
    measSelect.innerHTML = this.measurements.map(m => `
      <option value="${m.id}" ${m.id === p.measurement_id ? 'selected' : ''}>Úloha ${m.number}: ${m.name}</option>
    `).join('');

    const modal = document.getElementById('edit-metadata-modal');
    if (modal) modal.classList.add('active');
  },

  async handleEditMetaSemesterChange(semId) {
    await this.populateEditMetaSlots(parseInt(semId));
  },

  async populateEditMetaSlots(semId, selectedSlotId = null) {
    const slotSelect = document.getElementById('edit-meta-slot');
    if (!slotSelect) return;
    try {
      const resp = await fetch(`/api/slots?semester_id=${semId}`);
      if (resp.ok) {
        const slots = await resp.json();
        slotSelect.innerHTML = slots.map(sl => {
          const roomSuffix = sl.room ? ` (${sl.room})` : '';
          const isSel = selectedSlotId && sl.id === selectedSlotId ? 'selected' : '';
          return `<option value="${sl.id}" ${isSel}>${sl.day_of_week} ${sl.time_start}–${sl.time_end}${roomSuffix}</option>`;
        }).join('');
      }
    } catch (e) {
      console.error("Error loading slots for edit metadata:", e);
    }
  },

  closeEditMetadataModal() {
    const modal = document.getElementById('edit-metadata-modal');
    if (modal) modal.classList.remove('active');
  },

  async handleSaveMetadata(e) {
    e.preventDefault();
    const protoId = parseInt(document.getElementById('edit-meta-proto-id').value);
    const studentName = document.getElementById('edit-meta-student').value.trim();
    const semesterId = parseInt(document.getElementById('edit-meta-semester').value);
    const slotId = parseInt(document.getElementById('edit-meta-slot').value);
    const measurementId = parseInt(document.getElementById('edit-meta-measurement').value);

    try {
      const resp = await fetch(`/api/protocols/${protoId}/metadata`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          student_name: studentName,
          semester_id: semesterId,
          slot_id: slotId,
          measurement_id: measurementId
        })
      });

      if (resp.ok) {
        this.showToast("Metadata protokolu byla úspěšně upravena!");
        this.closeEditMetadataModal();
        await this.loadProtocols();
      } else {
        const err = await resp.json();
        await AppModal.alert({ title: "Chyba metadat", message: err.detail || "Chyba při ukládání metadat." });
      }
    } catch (err) {
      await AppModal.alert({ title: "Chyba spojení", message: "Chyba při ukládání metadat: " + err.message });
    }
  },

  // ==========================================
  // CONTINUOUS AUTO-SAVE SYSTEM
  // ==========================================
  isDirty: false,
  autosaveTimer: null,

  scheduleAutosave() {
    this.isDirty = true;
    this.updateAutosaveIndicator('dirty');
    clearTimeout(this.autosaveTimer);
    this.autosaveTimer = setTimeout(() => {
      this.triggerAutosave();
    }, 1500); // 1.5s debounce
  },

  async triggerAutosave() {
    if (!this.currentProtocol || !this.isDirty) return;
    this.updateAutosaveIndicator('saving');

    try {
      const engine = window.GradingEngine || (typeof GradingEngine !== 'undefined' ? GradingEngine : null);
      const payload = {
        annotations: (window.PDFStudio && PDFStudio.annotations) ? PDFStudio.annotations : null,
        evaluation: engine ? {
          vysledky_score: engine.getCategoryScore('vysledky'),
          diskuze_score: engine.getCategoryScore('diskuze'),
          format_score: engine.getCategoryScore('format'),
          chyby_score: engine.getCategoryScore('chyby'),
          total_points: engine.getTotalPoints(),
          grade: engine.getMark(engine.getTotalPoints()),
          manual_grade_override: engine.state.manualGradeOverride,
          deductions: engine.state.deductions,
          raw_output_1: engine.generateOutput1(),
          raw_output_2: engine.generateOutput2()
        } : null,
        ai_proposals: this.currentAIResult || { deductions: [], annotations: [] }
      };

      const resp = await fetch(`/api/protocols/${this.currentProtocol.id}/autosave`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (resp.ok) {
        this.isDirty = false;
        const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        this.updateAutosaveIndicator('saved', timeStr);
      } else {
        this.updateAutosaveIndicator('dirty');
      }
    } catch(e) {
      console.warn("Autosave failed:", e);
      this.updateAutosaveIndicator('dirty');
    }
  },

  updateAutosaveIndicator(state, timeStr) {
    const badge = document.getElementById('autosave-indicator');
    if (!badge) return;
    badge.className = `autosave-badge ${state}`;
    const txt = badge.querySelector('.autosave-text');
    if (!txt) return;

    if (state === 'saving') {
      txt.textContent = 'Ukládám...';
    } else if (state === 'dirty') {
      txt.textContent = 'Neuloženo';
    } else {
      txt.textContent = timeStr ? `Uloženo (${timeStr})` : 'Uloženo';
    }
  },

  // ==========================================
  // INLINE AI ASSISTANT SIDE PANEL & ACTIONS
  // ==========================================
  currentAIResult: null,

  setAIResult(data) {
    if (!data) {
      this.currentAIResult = null;
      if (window.PDFStudio) window.PDFStudio.setAIProposals([]);
      const btnText = document.getElementById('btn-ai-drawer-text');
      if (btnText) btnText.textContent = 'AI Asistent';
      const sumText = document.getElementById('ai-drawer-summary-text');
      if (sumText) sumText.textContent = 'Protokol zatím nebyl analyzován pomocí AI.';
      const dedCount = document.getElementById('ai-drawer-ded-count');
      if (dedCount) dedCount.textContent = '0';
      const dedList = document.getElementById('ai-drawer-deductions-list');
      if (dedList) dedList.innerHTML = `<div style="font-size:0.78rem; color:var(--text-muted); font-style:italic;">Žádné návrhy srážek.</div>`;
      const annCount = document.getElementById('ai-drawer-annot-count');
      if (annCount) annCount.textContent = '0';
      const annList = document.getElementById('ai-drawer-annotations-list');
      if (annList) annList.innerHTML = `<div style="font-size:0.78rem; color:var(--text-muted); font-style:italic;">Žádná označení v textu.</div>`;
      const fallbackCont = document.getElementById('ai-drawer-fallback-container');
      if (fallbackCont) { fallbackCont.innerHTML = ''; fallbackCont.style.display = 'none'; }
      return;
    }
    this.currentAIResult = data;
    if (this.currentProtocol) this.currentProtocol.ai_proposals = data;
    const protoId = this.currentProtocol?.id || 0;
    if (Array.isArray(data.deductions)) {
      data.deductions.forEach((d, i) => {
        if (!d.proposal_id) d.proposal_id = `ded_${protoId}_${i + 1}`;
      });
    }
    if (Array.isArray(data.annotations)) {
      data.annotations.forEach((a, i) => {
        if (!a.proposal_id) a.proposal_id = `annot_${protoId}_${i + 1}`;
      });
    }
    if (window.PDFStudio) {
      window.PDFStudio.setAIProposals(data.annotations || []);
    }
    this.updateAIDrawerLists();
  },

  toggleAIRunMenu(e) {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    const menu = document.getElementById('ai-run-menu');
    if (!menu) return;
    const isShown = menu.style.display !== 'none';
    menu.style.display = isShown ? 'none' : 'block';
  },

  async runAIAnalysis(mode = 'merge') {
    const menu = document.getElementById('ai-run-menu');
    if (menu) menu.style.display = 'none';

    if (!this.currentProtocol) {
      await AppModal.alert({ title: "Upozornění", message: "Není otevřen žádný protokol k analýze." });
      return;
    }

    if (mode === 'replace') {
      const ok = await AppModal.confirm({
        title: "Kompletní přegenerování AI",
        message: "Opravdu chcete kompletně přegenerovat celou AI analýzu? Všechny dosavadní neschválené návrhy budou nahrazeny novými.",
        confirmText: "Nahradit vše",
        danger: true
      });
      if (!ok) return;
    }

    const btn = document.getElementById('btn-run-ai-action');
    const origText = btn ? btn.textContent : '↻ Spustit';
    if (btn) btn.textContent = 'Analyzuji...';

    const sumText = document.getElementById('ai-drawer-summary-text');
    if (sumText) sumText.innerHTML = '<em>Probíhá hloubková analýza protokolu pomocí AI...</em>';

    try {
      const resp = await fetch(`/api/protocols/${this.currentProtocol.id}/ai-analyze?mode=${mode}`, {
        method: 'POST'
      });
      if (resp.ok) {
        const data = await resp.json();
        this.currentProtocol.ai_proposals = data;
        this.setAIResult(data);
        if (window.PDFStudio) {
          window.PDFStudio.setAIProposals(data.annotations || []);
          window.PDFStudio.renderAIProposals();
        }
        const drawer = document.getElementById('studio-ai-drawer');
        if (drawer) drawer.style.display = 'flex';
        this.showToast(mode === 'replace' ? "AI analýza byla kompletně přegenerována!" : "Nové návrhy AI byly přidány k protokolu!");
      } else {
        const err = await resp.json();
        const fallbackCont = document.getElementById('ai-drawer-fallback-container');
        if (fallbackCont) {
          fallbackCont.innerHTML = `<div class="ai-fallback-alert" style="background:rgba(239,68,68,0.12); border:1px solid var(--accent-red); color:var(--accent-red); padding:8px 10px; border-radius:6px; font-size:0.8rem; margin-bottom:8px;">⚠️ ${this.escape(err.detail || "Chyba při volání AI analýzy.")}</div>`;
          fallbackCont.style.display = 'block';
        }
        await AppModal.alert({ title: "Chyba AI analýzy", message: err.detail || "Chyba při volání AI analýzy." });
      }
    } catch (e) {
      const fallbackCont = document.getElementById('ai-drawer-fallback-container');
      if (fallbackCont) {
        fallbackCont.innerHTML = `<div class="ai-fallback-alert" style="background:rgba(239,68,68,0.12); border:1px solid var(--accent-red); color:var(--accent-red); padding:8px 10px; border-radius:6px; font-size:0.8rem; margin-bottom:8px;">⚠️ Chyba při komunikaci s AI službou: ${this.escape(e.message)}</div>`;
        fallbackCont.style.display = 'block';
      }
      await AppModal.alert({ title: "Chyba komunikace", message: "Chyba při komunikaci s AI službou: " + e.message });
    } finally {
      if (btn) btn.textContent = origText;
    }
  },

  toggleAIDrawer() {
    const drawer = document.getElementById('studio-ai-drawer');
    if (!drawer) return;
    const isHidden = (drawer.style.display === 'none' || !drawer.style.display);
    drawer.style.display = isHidden ? 'flex' : 'none';
    if (isHidden) {
      // Opening AI drawer: if grading dock is open and docked, minimize it so both 410px panels do not collide
      const gradingDock = document.getElementById('studio-grading-dock');
      if (gradingDock && gradingDock.style.display !== 'none' && !gradingDock.classList.contains('floating-mode')) {
        this.wasGradingDockOpen = true;
        gradingDock.style.display = 'none';
      }
      this.updateAIDockSideButton();
      this.updateAIDrawerLists();
    } else {
      // Closing AI drawer: restore grading dock if it was open before
      if (this.wasGradingDockOpen) {
        this.wasGradingDockOpen = false;
        const gradingDock = document.getElementById('studio-grading-dock');
        if (gradingDock) gradingDock.style.display = 'flex';
      }
    }
  },

  focusAIProposalFromCanvas(proposalId) {
    const drawer = document.getElementById('studio-ai-drawer');
    if (drawer && (drawer.style.display === 'none' || !drawer.style.display)) {
      this.toggleAIDrawer();
    }
    document.querySelectorAll('.ai-proposal-item').forEach(el => el.classList.remove('ai-item-active'));
    const sideCard = document.querySelector(`.ai-proposal-item[data-proposal-id="${proposalId}"]`);
    if (sideCard) {
      sideCard.classList.add('ai-item-active');
      sideCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  },

  focusAIProposal(proposalId) {
    if (!window.PDFStudio || !window.PDFStudio.container) return;
    const prop = (window.PDFStudio.aiProposals || []).find((p, i) => (p.proposal_id === proposalId || `ai_prop_${i}` === proposalId || `annot_${i}` === proposalId))
      || (this.currentAIResult?.annotations || []).find((p, i) => (p.proposal_id === proposalId || `ai_prop_${i}` === proposalId || `annot_${i}` === proposalId));
    if (!prop) return;

    // Highlight active card in side drawer
    document.querySelectorAll('.ai-proposal-item').forEach(el => el.classList.remove('ai-item-active'));
    const sideCard = document.querySelector(`.ai-proposal-item[data-proposal-id="${proposalId}"]`);
    if (sideCard) sideCard.classList.add('ai-item-active');

    const pageNum = parseInt(prop.page, 10) || 1;
    const pageWrap = window.PDFStudio.container.querySelector(`.pdf-page-container[data-page-number="${pageNum}"]`);
    if (!pageWrap) return;

    const container = window.PDFStudio.container;
    const targetEl = pageWrap.querySelector(`.ai-canvas-proposal[data-proposal-id="${proposalId}"]`)
      || (prop.proposal_id ? pageWrap.querySelector(`.ai-canvas-proposal[data-proposal-id="${prop.proposal_id}"]`) : null);
    if (targetEl) {
      document.querySelectorAll('.ai-canvas-proposal').forEach(el => el.classList.remove('ai-proposal-focused'));
      targetEl.classList.add('ai-proposal-focused');
      setTimeout(() => targetEl.classList.remove('ai-proposal-focused'), 3500);

      const targetRect = targetEl.getBoundingClientRect();
      const contRect = container.getBoundingClientRect();
      const offset = (targetRect.top - contRect.top) + container.scrollTop - (container.clientHeight / 2) + (targetRect.height / 2);
      container.scrollTo({ top: Math.max(0, offset), behavior: 'smooth' });

      if (window.PDFStudio && window.PDFStudio.showTooltip) {
        window.PDFStudio.showTooltip("✨ Návrh AI asistenta", prop.comment, targetRect.left + (targetRect.width / 2), targetRect.top);
        setTimeout(() => { if (window.PDFStudio) window.PDFStudio.hideTooltip(); }, 3500);
      }
    } else {
      const normRect = window.PDFStudio.normalizeRect(prop.rect);
      const topOffset = pageWrap.offsetTop + (normRect ? normRect[1] * window.PDFStudio.scale : 0) - (container.clientHeight / 2);
      container.scrollTo({ top: Math.max(0, topOffset), behavior: 'smooth' });
    }
  },

  focusAIDeduction(proposalId) {
    if (!this.currentAIResult || !Array.isArray(this.currentAIResult.deductions)) return;
    const ded = this.currentAIResult.deductions.find((d, i) => (d.proposal_id === proposalId || `ded_${i}` === proposalId));
    if (!ded) return;

    // Highlight active card in side drawer
    document.querySelectorAll('.ai-proposal-item').forEach(el => el.classList.remove('ai-item-active'));
    const sideCard = document.querySelector(`.ai-proposal-item[data-proposal-id="${proposalId}"]`);
    if (sideCard) sideCard.classList.add('ai-item-active');

    const pageNum = parseInt(ded.page, 10) || 1;
    if (window.PDFStudio && window.PDFStudio.container) {
      const pageWrap = window.PDFStudio.container.querySelector(`.pdf-page-container[data-page-number="${pageNum}"]`);
      if (pageWrap) {
        const topOffset = pageWrap.offsetTop - 20;
        window.PDFStudio.container.scrollTo({ top: Math.max(0, topOffset), behavior: 'smooth' });
      }
    }
  },

  updateAIDrawerLists() {
    if (!this.currentAIResult) return;
    const data = this.currentAIResult;

    // Model badge & fallback info
    const modelBadge = document.getElementById('ai-drawer-model-badge');
    if (modelBadge) {
      modelBadge.textContent = data.model_used ? `Model: ${data.model_used}` : 'Gemini Flash';
      if (data.preferred_model) {
        modelBadge.title = `Požadovaný model: ${data.preferred_model}`;
      }
    }

    const fallbackCont = document.getElementById('ai-drawer-fallback-container');
    if (fallbackCont) {
      if (data.fallback_note) {
        fallbackCont.innerHTML = `
          <div class="ai-fallback-alert">
            ${this.escape(data.fallback_note)}
          </div>
        `;
        fallbackCont.style.display = 'block';
      } else {
        fallbackCont.innerHTML = '';
        fallbackCont.style.display = 'none';
      }
    }

    const sumText = document.getElementById('ai-drawer-summary-text');
    if (sumText) sumText.textContent = data.summary || 'Protokol byl zkontrolován.';

    // Deductions
    const dedCount = document.getElementById('ai-drawer-ded-count');
    if (dedCount) dedCount.textContent = (data.deductions || []).length;

    const dedList = document.getElementById('ai-drawer-deductions-list');
    if (dedList) {
      if (!data.deductions || data.deductions.length === 0) {
        dedList.innerHTML = `<div style="font-size:0.78rem; color:var(--text-muted); font-style:italic;">Žádné další návrhy srážek.</div>`;
      } else {
        dedList.innerHTML = data.deductions.map((d, idx) => {
          const pId = d.proposal_id || `ded_${idx}`;
          const pageNum = d.page ? parseInt(d.page, 10) : 1;
          const ptsVal = d.pts || d.points || 0.25;
          return `
          <div class="ai-proposal-item" data-proposal-id="${pId}" onclick="App.focusAIDeduction('${pId}')" title="Kliknutím přejdete na stranu ${pageNum} v protokolu">
            <div class="ai-proposal-meta">
              <span class="ai-proposal-pts">-${GradingEngine.formatPoints(ptsVal)} b</span>
              <span style="font-weight:700; text-transform:capitalize; color:var(--text-main); font-size:0.75rem;">${d.category}</span>
              <span class="badge" style="font-size:0.68rem; padding:1px 5px; margin-left:auto;">Strana ${pageNum}</span>
            </div>
            <div style="font-weight:500; color:var(--text-main); font-size:0.8rem;">${this.escape(d.reason)}</div>
            <div class="ai-proposal-actions">
              <button class="btn btn-secondary btn-sm" style="font-size:0.7rem; padding:2px 6px;" onclick="event.stopPropagation(); App.rejectAIDeduction('${pId}')">✕ Zahodit</button>
              <button class="btn btn-primary btn-sm" style="font-size:0.7rem; padding:2px 6px;" onclick="event.stopPropagation(); App.approveAIDeduction('${pId}')">✓ Přidat do bodování</button>
            </div>
          </div>
        `;
        }).join('');
      }
    }

    // Annotations
    const annotProposals = (window.PDFStudio && window.PDFStudio.aiProposals) || (data.annotations || []);
    const annCount = document.getElementById('ai-drawer-annot-count');
    if (annCount) annCount.textContent = annotProposals.length;

    const annList = document.getElementById('ai-drawer-annotations-list');
    if (annList) {
      if (annotProposals.length === 0) {
        annList.innerHTML = `<div style="font-size:0.78rem; color:var(--text-muted); font-style:italic;">Žádná další označení v textu.</div>`;
      } else {
        annList.innerHTML = annotProposals.map((a, idx) => {
          const pId = a.proposal_id || `ai_prop_${idx}`;
          return `
          <div class="ai-proposal-item" data-proposal-id="${pId}" onclick="App.focusAIProposal('${pId}')" title="Kliknutím přejdete na návrh v textu protokolu">
            <div class="ai-proposal-meta">
              <span class="badge" style="font-size:0.7rem; padding:1px 5px;">Strana ${a.page}</span>
              <span style="font-weight:600; color:var(--primary); font-size:0.72rem;">${a.type === 'strikeout' ? 'Přeškrtnutí' : 'Zvýraznění'}</span>
            </div>
            <div style="font-weight:600; color:var(--text-main); font-size:0.78rem;">${this.escape(a.comment)}</div>
            <div class="ai-proposal-actions">
              <button class="btn btn-secondary btn-sm" style="font-size:0.7rem; padding:2px 6px;" onclick="event.stopPropagation(); App.rejectAIAnnotation('${pId}')">✕ Zahodit</button>
              <button class="btn btn-primary btn-sm" style="font-size:0.7rem; padding:2px 6px;" onclick="event.stopPropagation(); App.approveAIAnnotation('${pId}')">✓ Aplikovat do PDF</button>
            </div>
          </div>
        `;
        }).join('');
      }
    }

    // Update button text with badge
    const totalCount = ((data.deductions || []).length) + annotProposals.length;
    const btnText2 = document.getElementById('btn-ai-drawer-text');
    if (btnText2) {
      btnText2.textContent = totalCount > 0 ? `AI Asistent (${totalCount})` : `AI Asistent`;
    }
  },

  async executeAIProposalAction(action, proposalId = null, extraData = null) {
    if (!this.currentProtocol) return;
    const protoId = this.currentProtocol.id;

    try {
      const resp = await fetch(`/api/protocols/${protoId}/ai-proposals/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: action,
          proposal_id: proposalId,
          annotation_data: extraData
        })
      });

      if (!resp.ok) {
        let err;
        try { err = await resp.json(); } catch(e) { err = { detail: resp.statusText }; }
        throw new Error(err.detail || "Chyba při zpracování akce");
      }

      const result = await resp.json();

      // Immediate DB update synchronization:
      if (result.ai_proposals) {
        this.currentProtocol.ai_proposals = result.ai_proposals;
        this.currentAIResult = result.ai_proposals;
        if (window.PDFStudio) {
          window.PDFStudio.aiProposals = result.ai_proposals.annotations || [];
        }
      }

      if (action === 'approve_annotation') {
        if (result.created_annotation && window.PDFStudio) {
          window.PDFStudio.addAnnotation(result.created_annotation);
          window.PDFStudio.redrawPageAnnotations(result.created_annotation.page);
        }
        const canvasEl = document.querySelector(`.ai-canvas-proposal[data-proposal-id="${proposalId}"]`);
        if (canvasEl) canvasEl.remove();
        this.showToast("Návrh byl schválen a aplikován do PDF.");
      } else if (action === 'reject_annotation') {
        const canvasEl = document.querySelector(`.ai-canvas-proposal[data-proposal-id="${proposalId}"]`);
        if (canvasEl) canvasEl.remove();
        this.showToast("Návrh byl zahozen.");
      } else if (action === 'approve_deduction') {
        if (result.deduction && window.GradingEngine) {
          window.GradingEngine.addDeduction(result.deduction.category, result.deduction.pts, result.deduction.reason);
        }
        this.updateGradingDockScore();
        this.showToast("Srážka byla přidána do bodování.");
      } else if (action === 'reject_deduction') {
        this.showToast("Návrh srážky byl zahozen.");
      } else if (action === 'approve_all_annotations') {
        if (window.PDFStudio) {
          (result.created_annotations || []).forEach(ann => {
            window.PDFStudio.addAnnotation(ann);
          });
          for (let p = 1; p <= (window.PDFStudio.totalPages || 1); p++) {
            window.PDFStudio.redrawPageAnnotations(p);
          }
          window.PDFStudio.renderAIProposals();
        }
        this.showToast("Všechny anotace byly aplikovány do PDF.");
      } else if (action === 'approve_all_deductions') {
        if (window.GradingEngine && Array.isArray(result.deductions)) {
          result.deductions.forEach(d => {
            window.GradingEngine.addDeduction(d.category, d.pts, d.reason);
          });
        }
        this.updateGradingDockScore();
        this.showToast("Všechny navržené srážky byly přidány do bodování.");
      }

      this.updateAIDrawerLists();
      if (window.PDFStudio && window.PDFStudio.renderAIProposals) {
        window.PDFStudio.renderAIProposals();
      }
    } catch (e) {
      console.error("AI action failed:", e);
      await AppModal.alert({ title: "Chyba", message: e.message || "Nepodařilo se provést akci s AI návrhem." });
    }
  },

  approveAIDeduction(target) {
    const pId = typeof target === 'string' ? target : (target && target.proposal_id);
    if (pId) this.executeAIProposalAction('approve_deduction', pId);
  },

  rejectAIDeduction(target) {
    const pId = typeof target === 'string' ? target : (target && target.proposal_id);
    if (pId) this.executeAIProposalAction('reject_deduction', pId);
  },

  approveAIAnnotation(target) {
    const pId = typeof target === 'string' ? target : (target && target.proposal_id);
    if (pId) this.executeAIProposalAction('approve_annotation', pId);
  },

  rejectAIAnnotation(target) {
    const pId = typeof target === 'string' ? target : (target && target.proposal_id);
    if (pId) this.executeAIProposalAction('reject_annotation', pId);
  },

  approveAllAIDeductions() {
    this.executeAIProposalAction('approve_all_deductions');
  },

  approveAllAIAnnotations() {
    this.executeAIProposalAction('approve_all_annotations');
  },

  // Settings: AI API Key and Settings
  async loadAISettings() {
    try {
      const resp = await fetch('/api/settings/ai');
      if (resp.ok) {
        const data = await resp.json();
        const toggle = document.getElementById('ai-enabled-toggle');
        const keyInput = document.getElementById('ai-api-key-input');
        const keyStatus = document.getElementById('ai-key-status');
        const modelSelect = document.getElementById('ai-model-select');
        const customInput = document.getElementById('ai-custom-model-input');
        const autoAnalyzeToggle = document.getElementById('ai-auto-analyze-toggle');
        const langSelect = document.getElementById('ai-language-select');

        if (toggle) toggle.checked = !!data.ai_enabled;
        if (keyInput) keyInput.value = data.gemini_api_key || '';
        if (autoAnalyzeToggle) autoAnalyzeToggle.checked = (data.auto_analyze_on_upload !== false);
        if (langSelect && data.ai_language) langSelect.value = data.ai_language;

        if (modelSelect) {
          const m = data.model_name || 'gemini-3.5-flash-lite';
          const validModels = ['gemini-3.5-flash-lite', 'gemini-flash-lite-latest', 'gemini-3.5-flash', 'gemini-3.8-flash', 'gemini-3.1-flash-lite', 'gemini-flash-latest'];
          if (validModels.includes(m)) {
            modelSelect.value = m;
            if (customInput) customInput.style.display = 'none';
          } else {
            modelSelect.value = 'custom';
            if (customInput) {
              customInput.style.display = 'block';
              customInput.value = m;
            }
          }
        }

        if (keyStatus) {
          if (data.has_key || (data.gemini_api_key && data.gemini_api_key.trim().length > 0)) {
            const keyStr = data.gemini_api_key || '••••••••';
            keyStatus.innerHTML = `✓ API klíč je nastaven (${keyStr.substring(0, 6)}...${keyStr.slice(-4)})`;
            keyStatus.style.color = 'var(--accent-green)';
          } else {
            keyStatus.innerHTML = `⚠️ API klíč není zadán – AI asistent nemůže fungovat bez Gemini API klíče.`;
            keyStatus.style.color = 'var(--accent-red)';
          }
        }
        this.checkAIKeyStatus();
      }
    } catch (e) {
      console.error("Error loading AI settings:", e);
    }
  },

  handleAIModelSelectChange(val) {
    const customInput = document.getElementById('ai-custom-model-input');
    if (customInput) {
      customInput.style.display = val === 'custom' ? 'block' : 'none';
      if (val === 'custom') customInput.focus();
    }
  },

  async handleSaveAISettings(e) {
    e.preventDefault();
    const enabled = document.getElementById('ai-enabled-toggle').checked;
    const apiKey = document.getElementById('ai-api-key-input').value.trim();
    const modelSelect = document.getElementById('ai-model-select').value;
    const customModel = document.getElementById('ai-custom-model-input').value.trim();
    const autoAnalyze = document.getElementById('ai-auto-analyze-toggle').checked;
    const langSelect = document.getElementById('ai-language-select');
    const aiLanguage = langSelect ? langSelect.value : 'cs';
    const modelName = (modelSelect === 'custom' && customModel) ? customModel : modelSelect;

    try {
      const resp = await fetch('/api/settings/ai', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          gemini_api_key: apiKey,
          ai_enabled: enabled,
          model_name: modelName,
          auto_analyze_on_upload: autoAnalyze,
          ai_language: aiLanguage
        })
      });
      if (resp.ok) {
        this.showToast("Nastavení AI asistenta uloženo!");
        this.loadAISettings();
        this.checkAIKeyStatus();
      } else {
        const err = await resp.json();
        await AppModal.alert({ title: "Chyba", message: err.detail || "Chyba při ukládání nastavení AI." });
      }
    } catch(err) {
      await AppModal.alert({ title: "Chyba", message: "Chyba spojení: " + err.message });
    }
  },

  toggleApiKeyVisibility() {
    const inp = document.getElementById('ai-api-key-input');
    if (inp) {
      inp.type = inp.type === 'password' ? 'text' : 'password';
    }
  },

  // Settings: Changelog
  async loadChangelog() {
    const container = document.getElementById('about-changelog-container');
    if (!container) return;

    try {
      const resp = await fetch('/api/changelog');
      if (resp.ok) {
        const data = await resp.json();
        let html = data.content
          .replace(/^### (.*$)/gim, '<h5 style="margin-top:12px; margin-bottom:4px; color:var(--text-main); font-weight:700;">$1</h5>')
          .replace(/^## (.*$)/gim, '<h4 style="margin-top:16px; margin-bottom:6px; color:var(--primary); font-weight:800; border-bottom:1px solid var(--border); padding-bottom:4px;">$1</h4>')
          .replace(/^# (.*$)/gim, '<h3 style="margin-bottom:8px; color:var(--text-main);">$1</h3>')
          .replace(/^\* (.*$)/gim, '<li style="margin-left:16px;">$1</li>')
          .replace(/^- (.*$)/gim, '<li style="margin-left:16px;">$1</li>')
          .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
          .replace(/\*(.*?)\*/gim, '<em>$1</em>')
          .replace(/`([^`]+)`/gim, '<code style="background:var(--bg); border:1px solid var(--border); padding:1px 4px; border-radius:3px; font-family:\'JetBrains Mono\'; font-size:0.85em;">$1</code>');
        
        container.innerHTML = html;
      } else {
        container.innerHTML = `<span style="color:var(--text-muted);">Nelze načíst historii změn.</span>`;
      }
    } catch (e) {
      container.innerHTML = `<span style="color:var(--text-muted);">Chyba při načítání changelogu: ${e.message}</span>`;
    }
  },

  setupEventListeners() {
    window.addEventListener('keydown', (e) => {
      // ESC closes any modal or floating comment box
      if (e.key === 'Escape') {
        this.closeUploadModal();
        this.closeSettingsModal();
        this.closeEditMetadataModal();
        this.closeAIReviewModal();
        if (window.PDFStudio) window.PDFStudio.closeCommentBox();
        return;
      }

      // Check if user is typing in a text field or form input
      const activeEl = document.activeElement;
      const isInput = activeEl && (
        activeEl.tagName === 'INPUT' ||
        activeEl.tagName === 'TEXTAREA' ||
        activeEl.tagName === 'SELECT' ||
        activeEl.isContentEditable
      );

      const hasModal = document.querySelector('.modal-backdrop.active');

      if (this.currentView === 'studio' && !hasModal) {
        // Ctrl+S / Cmd+S: Save Draft
        if ((e.ctrlKey || e.metaKey) && (e.key === 's' || e.key === 'S')) {
          e.preventDefault();
          this.saveCurrentEvaluation(false);
          return;
        }

        // Ctrl+Enter / Cmd+Enter: Save & Burn Finished PDF
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
          e.preventDefault();
          this.saveCurrentEvaluation(true);
          return;
        }

        // Alt+ArrowLeft / Alt+ArrowRight: Previous / Next student protocol
        if (e.altKey && e.key === 'ArrowLeft') {
          e.preventDefault();
          this.openPreviousProtocol();
          return;
        }
        if (e.altKey && e.key === 'ArrowRight') {
          e.preventDefault();
          this.openNextProtocol();
          return;
        }

        // Single-key shortcuts and Undo (only active when not typing in form controls)
        if (!isInput) {
          // Delete / Backspace: Delete currently selected annotation on canvas
          if (e.key === 'Delete' || e.key === 'Backspace') {
            if (window.PDFStudio && window.PDFStudio.activeSelectedAnnot) {
              e.preventDefault();
              window.PDFStudio.deleteSelectedAnnotation();
              return;
            }
          }

          // Ctrl+Z: Undo annotation
          if ((e.ctrlKey || e.metaKey) && (e.key === 'z' || e.key === 'Z')) {
            e.preventDefault();
            if (window.PDFStudio) window.PDFStudio.undo();
            return;
          }

          const k = e.key.toLowerCase();
          if (k === 'v') {
            if (window.PDFStudio) window.PDFStudio.setTool('pan');
          } else if (k === 'h') {
            if (window.PDFStudio) window.PDFStudio.setTool('highlight');
          } else if (k === 's') {
            if (window.PDFStudio) window.PDFStudio.setTool('strikeout');
          } else if (k === 't') {
            if (window.PDFStudio) window.PDFStudio.setTool('text');
          } else if (k === 'n') {
            if (window.PDFStudio) window.PDFStudio.setTool('note');
          } else if (k === 'p') {
            if (window.PDFStudio) window.PDFStudio.setTool('pen');
          } else if (k === 'r') {
            if (window.PDFStudio) window.PDFStudio.setTool('rect');
          } else if (k === 'a') {
            if (window.PDFStudio) window.PDFStudio.setTool('arrow');
          } else if (e.key === '+' || e.key === '=') {
            if (window.PDFStudio) window.PDFStudio.zoom(0.15);
          } else if (e.key === '-' || e.key === '_') {
            if (window.PDFStudio) window.PDFStudio.zoom(-0.15);
          } else if (e.key === '0') {
            if (window.PDFStudio) window.PDFStudio.resetZoom();
          }
        }
      }
    });

    document.addEventListener('click', (e) => {
      const menu = document.getElementById('ai-run-menu');
      if (menu && menu.style.display !== 'none') {
        const toggleBtn = document.getElementById('btn-run-ai-menu') || document.getElementById('btn-ai-run-dropdown');
        if (!menu.contains(e.target) && e.target !== toggleBtn && !toggleBtn?.contains(e.target)) {
          menu.style.display = 'none';
        }
      }
    });
  },

  showToast(msg) {
    const toast = document.getElementById('toast');
    const msgEl = document.getElementById('toast-msg');
    if (toast && msgEl) {
      msgEl.textContent = msg;
      toast.classList.add('show');
      setTimeout(() => toast.classList.remove('show'), 3000);
    }
  },

  escape(str) {
    if (!str) return '';
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
};

window.App = App;

window.addEventListener('DOMContentLoaded', () => {
  App.init();
});
