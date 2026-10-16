// Grading & Deduction Engine (Multiples of 0.125) with Dynamic Presets from DB
const GradingEngine = {
  categories: [
    { id: 'vysledky', name: 'Výsledky', max: 3, desc: 'Splnění úkolů, srozumitelný postup a mezivýsledky (0–3 b)' },
    { id: 'diskuze', name: 'Diskuze', max: 3, desc: 'Komentář výsledků, srovnání s teorií, systematické vlivy (0–3 b)' },
    { id: 'format', name: 'Formát', max: 2, desc: 'Vzhled protokolu, popisky grafů a tabulek, jednotky, literatura (0–2 b)' },
    { id: 'chyby', name: 'Chyby', max: 2, desc: 'Určení nejistot, šíření chyb, správné zaokrouhlení, errorbary (0–2 b)' }
  ],

  presets: [], // Loaded from /api/presets?type=deduction
  state: {
    deductions: [], // [{ category, pts, reason }]
    manualGradeOverride: null,
    generalComment: ""
  },

  async init(containerEl, onStateChangeCallback) {
    this.container = containerEl;
    this.onStateChange = onStateChangeCallback;
    await this.loadPresets();
    this.render();
  },

  async loadPresets() {
    try {
      const resp = await fetch('/api/presets?type=deduction');
      if (resp.ok) {
        this.presets = await resp.json();
      }
    } catch(e) {
      console.warn("Could not load deduction presets:", e);
    }
  },

  loadData(evalData) {
    if (evalData) {
      this.state.deductions = evalData.deductions || [];
      const ov = evalData.manual_grade_override;
      this.state.manualGradeOverride = (typeof ov === 'string' && ['A', 'B', 'C', 'D', 'E', 'F'].includes(ov.toUpperCase())) ? ov.toUpperCase() : null;
      this.state.generalComment = evalData.general_comment || "";
    } else {
      this.state.deductions = [];
      this.state.manualGradeOverride = null;
      this.state.generalComment = "";
    }
    this.render();
  },

  getCategoryScore(catId) {
    const config = this.categories.find(c => c.id === catId);
    const catDeductions = this.state.deductions.filter(d => d.category === catId);
    const sum = catDeductions.reduce((acc, d) => acc + d.pts, 0);
    const score = Math.max(0, config.max - sum);
    return Math.round(score * 1000) / 1000;
  },

  getTotalPoints() {
    let total = 0;
    for (const c of this.categories) {
      total += this.getCategoryScore(c.id);
    }
    return Math.round(total * 1000) / 1000;
  },

  getMark(points) {
    if (this.state.manualGradeOverride && ['A', 'B', 'C', 'D', 'E', 'F'].includes(String(this.state.manualGradeOverride).toUpperCase())) {
      return String(this.state.manualGradeOverride).toUpperCase();
    }
    if (points >= 9.00 - 1e-6) return "A";
    if (points >= 8.00 - 1e-6) return "B";
    if (points >= 6.00 - 1e-6) return "C";
    if (points >= 4.00 - 1e-6) return "D";
    if (points >= 2.00 - 1e-6) return "E";
    return "F";
  },

  getInterpolatedColor(p, max) {
    let percentage = Math.max(0, Math.min(p / max, 1));
    let color1, color2, t;
    if (max === 3) {
      if (percentage <= 1/3) {
        color1 = color2 = [229,57,53];
        t = 0;
      } else if (percentage <= 2/3) {
        color1 = [229,57,53];
        color2 = [255,112,67];
        t = (percentage - 1/3) / (1/3);
      } else {
        color1 = [255,112,67];
        color2 = [67,160,71];
        t = (percentage - 2/3) / (1/3);
      }
    } else {
      if (percentage <= 0.5) {
        color1 = [229,57,53];
        color2 = [255,112,67];
        t = percentage / 0.5;
      } else {
        color1 = [255,112,67];
        color2 = [67,160,71];
        t = (percentage - 0.5) / 0.5;
      }
    }
    let r = Math.round(color1[0] + (color2[0] - color1[0]) * t);
    let g = Math.round(color1[1] + (color2[1] - color1[1]) * t);
    let b = Math.round(color1[2] + (color2[2] - color1[2]) * t);
    return `rgb(${r},${g},${b})`;
  },

  formatPoints(num) {
    if (num === null || num === undefined || isNaN(num)) return "0";
    let s = Number(num).toFixed(3);
    s = s.replace(/\.?0+$/, "");
    return s || "0";
  },

  formatNumber(num) {
    return this.formatPoints(num);
  },

  autoResizeTextarea(el) {
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.max(38, el.scrollHeight) + 'px';
  },

  handleKeydown(event, catId) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.handleAddFromInputs(catId);
    }
  },

  addDeduction(category, pts, reason) {
    if (!reason || !reason.trim()) return;
    this.state.deductions.push({
      category: category,
      pts: Math.round(pts * 1000) / 1000,
      reason: reason.trim()
    });
    this.render();
    if (this.onStateChange) this.onStateChange();
  },

  removeDeduction(index) {
    this.state.deductions.splice(index, 1);
    this.render();
    if (this.onStateChange) this.onStateChange();
  },

  async editDeduction(index) {
    const item = this.state.deductions[index];
    if (!item) return;

    if (window.AppModal) {
      const res = await window.AppModal.showForm({
        title: "Upravit srážku bodů",
        fields: [
          {
            name: "pts",
            label: "Počet bodů k odečtení:",
            type: "select",
            value: item.pts.toString(),
            options: [
              { value: "0.125", label: "-0.125 b" },
              { value: "0.25", label: "-0.250 b" },
              { value: "0.375", label: "-0.375 b" },
              { value: "0.5", label: "-0.500 b" },
              { value: "0.75", label: "-0.750 b" },
              { value: "1.0", label: "-1.000 b" },
              { value: "1.5", label: "-1.500 b" },
              { value: "2.0", label: "-2.000 b" }
            ]
          },
          {
            name: "reason",
            label: "Důvod srážky:",
            type: "textarea",
            value: item.reason,
            placeholder: "Popište nalezený nedostatek..."
          }
        ],
        confirmText: "Uložit změny"
      });
      if (res && res.reason && res.reason.trim()) {
        item.pts = Math.round(parseFloat(res.pts || item.pts) * 1000) / 1000;
        item.reason = res.reason.trim();
        this.render();
        if (this.onStateChange) this.onStateChange();
      }
    }
  },

  generateOutput1() {
    const total = this.getTotalPoints();
    const mark = this.getMark(total);
    const parts = this.categories.map(c => `${c.name}: ${this.formatPoints(this.getCategoryScore(c.id))} / ${c.max}`);
    return `${parts.join(', ')}, Celkem bodů: ${this.formatPoints(total)} / 10, Známka: ${mark}`;
  },

  generateOutput2() {
    const total = this.getTotalPoints();
    const mark = this.getMark(total);
    const blocks = [];

    this.categories.forEach(c => {
      const score = this.getCategoryScore(c.id);
      const catDeductions = this.state.deductions.filter(d => d.category === c.id);
      let block = `${c.name}: ${this.formatPoints(score)} / ${c.max}`;
      if (catDeductions.length > 0) {
        block += "\n" + catDeductions.map(d => `-${this.formatPoints(d.pts)}b ${d.reason}`).join("\n");
      }
      blocks.push(block);
    });

    let res = blocks.join("\n\n") + `\n\nCelkem bodů: ${this.formatPoints(total)} / 10, Známka: ${mark}`;
    if (this.state.generalComment && this.state.generalComment.trim()) {
      res += `\n\nSlovní hodnocení protokolu:\n${this.state.generalComment.trim()}`;
    }
    return res;
  },

  render() {
    if (!this.container) return;
    const total = this.getTotalPoints();
    const mark = this.getMark(total);

    let html = `
      <!-- Sleek Score Hero Card -->
      <div class="grading-total-card" style="padding:12px 14px; background:var(--card-bg); border:1px solid var(--border); border-radius:8px; display:flex; align-items:center; justify-content:space-between; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
        <div style="flex:1;">
          <div style="font-size:0.7rem; font-weight:700; text-transform:uppercase; letter-spacing:0.5px; color:var(--text-muted); margin-bottom:2px;">Celkové hodnocení</div>
          <div style="font-size:1.6rem; font-weight:800; font-family:'JetBrains Mono',monospace; color:var(--text-main); line-height:1.1;">
            ${this.formatPoints(total)} <span style="font-size:0.85rem; font-weight:600; color:var(--text-muted);">/ 10 b</span>
          </div>
          <div style="width:100%; height:4px; background:var(--border); border-radius:2px; margin-top:6px; overflow:hidden;">
            <div style="width:${Math.min(100, Math.max(0, (total / 10) * 100))}%; height:100%; background:${this.getInterpolatedColor(total, 10)}; transition:width 0.25s ease, background 0.25s ease; border-radius:2px;"></div>
          </div>
        </div>
        <div style="margin-left:16px; text-align:center;">
          <div style="font-size:0.68rem; font-weight:700; text-transform:uppercase; color:var(--text-muted); margin-bottom:3px;">Známka</div>
          <div onclick="GradingEngine.promptGradeOverride()" title="Klikněte pro ruční úpravu známky" style="cursor:pointer; width:38px; height:38px; border-radius:6px; display:flex; align-items:center; justify-content:center; font-size:1.35rem; font-weight:800; font-family:'JetBrains Mono',monospace; background:${this.getGradeBg(mark)}; color:${this.getGradeColor(mark)}; border:2px solid ${this.getGradeColor(mark)}; transition:transform 0.15s ease;" onmouseover="this.style.transform='scale(1.06)'" onmouseout="this.style.transform='scale(1)'">
            ${mark}
          </div>
        </div>
      </div>

      <!-- Categories List -->
      <div style="display:flex; flex-direction:column; gap:8px; margin-top:8px;">
    `;

    this.categories.forEach(c => {
      const score = this.getCategoryScore(c.id);
      const color = this.getInterpolatedColor(score, c.max);
      const pct = (score / c.max) * 100;
      const catDeductions = this.state.deductions.filter(d => d.category === c.id);
      const catPresets = this.presets.filter(p => p.category === c.id);

      html += `
        <div class="category-panel-card" style="padding:10px 12px; border-radius:6px; background:var(--card-bg); border:1px solid var(--border);">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
            <span style="font-weight:700; font-size:0.86rem; color:var(--text-main);">${c.name}</span>
            <span style="font-family:'JetBrains Mono', monospace; font-weight:700; font-size:0.84rem; color:${color};">${this.formatPoints(score)} / ${c.max} b</span>
          </div>

          <!-- Thin Progress Track -->
          <div style="background:var(--border); border-radius:2px; height:3px; position:relative; overflow:hidden; margin-bottom:6px;">
            <div style="width:${pct}%; height:100%; background:${color}; transition:width 0.25s, background 0.25s; border-radius:2px;"></div>
          </div>

          <!-- Deductions in this category -->
          <div style="display:flex; flex-direction:column; gap:4px; margin-bottom:6px;">
            ${catDeductions.length === 0 ? `
              <div style="font-size:0.72rem; color:var(--text-muted); font-style:italic; padding:1px 0;">Bez srážek (plný počet bodů)</div>
            ` : catDeductions.map((d) => {
              const globalIdx = this.state.deductions.indexOf(d);
              return `
                <div class="deduction-row-item" style="display:flex; align-items:center; justify-content:space-between; background:var(--bg); border:1px solid var(--border); padding:4px 6px; border-radius:4px; font-size:0.76rem;">
                  <div style="display:flex; align-items:center; gap:6px; flex:1; min-width:0;">
                    <span onclick="GradingEngine.editDeduction(${globalIdx})" title="Kliknutím upravíte body" class="deduction-pts-pill" style="flex-shrink:0;">-${this.formatPoints(d.pts)} b</span>
                    <span onclick="GradingEngine.editDeduction(${globalIdx})" title="Kliknutím upravíte text" style="color:var(--text-main); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; cursor:pointer;">${this.escape(d.reason)}</span>
                  </div>
                  <div style="display:flex; gap:2px; align-items:center; margin-left:6px; flex-shrink:0;">
                    <button type="button" onclick="GradingEngine.editDeduction(${globalIdx})" class="btn-icon-subtle" title="Upravit">✎</button>
                    <button type="button" onclick="GradingEngine.removeDeduction(${globalIdx})" class="btn-icon-subtle" style="color:#ef4444;" title="Odstranit">✕</button>
                  </div>
                </div>
              `;
            }).join('')}
          </div>

          <!-- Modern Full-Width Deduction Input Block -->
          <div class="deduction-input-block" style="margin-top:8px; padding-top:8px; border-top:1px dashed var(--border);">
            <div style="display:flex; gap:6px; align-items:center; margin-bottom:6px;">
              <div style="display:flex; align-items:center; gap:4px;">
                <span style="font-size:0.7rem; font-weight:600; color:var(--text-muted);">Srážka:</span>
                <select id="pts-input-${c.id}" class="form-control" style="font-size:0.74rem; padding:3px 6px; width:80px; font-family:'JetBrains Mono',monospace;">
                  <option value="0.125">-0.125</option>
                  <option value="0.25" selected>-0.250</option>
                  <option value="0.375">-0.375</option>
                  <option value="0.5">-0.500</option>
                  <option value="0.75">-0.750</option>
                  <option value="1.0">-1.000</option>
                  <option value="1.5">-1.500</option>
                  <option value="2.0">-2.000</option>
                </select>
              </div>

              <select onchange="GradingEngine.onPresetSelect('${c.id}', this)" class="form-control" style="font-size:0.74rem; padding:3px 6px; flex:1; min-width:0;">
                <option value="">-- Šablony srážek --</option>
                ${catPresets.map(p => `<option value="${p.pts}|${this.escape(p.text)}">-${this.formatPoints(p.pts)} b: ${p.text.length > 26 ? p.text.substring(0, 26) + '…' : p.text}</option>`).join('')}
              </select>

              <button type="button" class="btn btn-primary btn-sm" style="font-size:0.72rem; padding:3px 8px; flex-shrink:0;" onclick="GradingEngine.handleAddFromInputs('${c.id}')">+ Odečíst</button>
            </div>

            <!-- Full-width auto-expanding textarea -->
            <textarea id="reason-input-${c.id}" placeholder="Důvod srážky... (Enter přidat, Shift+Enter nový řádek)" rows="1" class="form-control" style="width:100%; box-sizing:border-box; font-size:0.75rem; padding:6px 8px; line-height:1.35; resize:none; overflow-y:hidden; min-height:38px;" oninput="GradingEngine.autoResizeTextarea(this)" onkeydown="GradingEngine.handleKeydown(event, '${c.id}')"></textarea>
          </div>
        </div>
      `;
    });

    html += `
      </div>

      <!-- Overall Comment Block for Moodle & Student -->
      <div class="general-comment-card" style="padding:10px 12px; border-radius:6px; background:var(--card-bg); border:1px solid var(--border); margin-top:8px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
          <div style="display:flex; align-items:center; gap:6px;">
            <span style="font-weight:700; font-size:0.82rem; color:var(--text-main);">💬 Celkové slovní hodnocení</span>
            <span style="font-size:0.68rem; color:var(--text-muted);">(pro Moodle i studenta)</span>
          </div>
        </div>
        <textarea id="general-comment-input" placeholder="Souhrnné slovní hodnocení protokolu jako celku..." rows="2" class="form-control" style="width:100%; box-sizing:border-box; font-size:0.75rem; padding:6px 8px; line-height:1.35; resize:vertical; min-height:48px;" oninput="GradingEngine.onGeneralCommentInput(this)">${this.escape(this.state.generalComment || '')}</textarea>
      </div>

      <!-- Dedicated Outputs Section (Independently Copyable Cards) -->
      <div style="margin-top:10px; display:flex; flex-direction:column; gap:8px;">
        <!-- Card 1: Moodle Summary -->
        <div class="output-preview-card" style="background:var(--card-bg); border:1px solid var(--border); border-radius:6px; padding:10px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <div style="display:flex; align-items:center; gap:6px;">
              <span style="font-weight:700; font-size:0.78rem; color:var(--text-main);">📋 Souhrn</span>
              <span style="font-size:0.68rem; color:var(--text-muted);">(1 řádek)</span>
            </div>
            <button type="button" class="btn btn-secondary btn-sm" style="font-size:0.7rem; padding:2px 8px; display:inline-flex; align-items:center; gap:4px;" onclick="GradingEngine.copyText(GradingEngine.generateOutput1(), 'Souhrn zkopírován!')">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>
              <span>Kopírovat</span>
            </button>
          </div>
          <div class="output-code-line" style="font-size:0.72rem; padding:6px 8px; border-radius:4px; cursor:pointer;" onclick="GradingEngine.copyText(this.innerText, 'Souhrn zkopírován!')" title="Klikněte pro zkopírování do schránky">
            ${this.escape(this.generateOutput1())}
          </div>
        </div>

        <!-- Card 2: bodovani.txt Detail -->
        <div class="output-preview-card" style="background:var(--card-bg); border:1px solid var(--border); border-radius:6px; padding:10px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <div style="display:flex; align-items:center; gap:6px;">
              <span style="font-weight:700; font-size:0.78rem; color:var(--text-main);">📄 Bodování pro Moodle</span>
              <span style="font-size:0.68rem; color:var(--text-muted);">(detail)</span>
            </div>
            <button type="button" class="btn btn-secondary btn-sm" style="font-size:0.7rem; padding:2px 8px; display:inline-flex; align-items:center; gap:4px;" onclick="GradingEngine.copyText(GradingEngine.generateOutput2(), 'Bodování pro Moodle zkopírováno!')">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>
              <span>Kopírovat</span>
            </button>
          </div>
          <pre class="output-code-pre" style="font-size:0.72rem; padding:8px; border-radius:4px; max-height:120px; overflow-y:auto; cursor:pointer; margin:0;" onclick="GradingEngine.copyText(this.innerText, 'Bodování pro Moodle zkopírováno!')" title="Klikněte pro zkopírování do schránky">${this.escape(this.generateOutput2())}</pre>
        </div>
      </div>
    `;

    this.container.innerHTML = html;
    this.container.querySelectorAll('textarea[id^="reason-input-"]').forEach(ta => this.autoResizeTextarea(ta));
  },

  onGeneralCommentInput(el) {
    this.state.generalComment = el.value;
    const preEl = this.container ? this.container.querySelector('.output-code-pre') : null;
    if (preEl) {
      preEl.textContent = this.generateOutput2();
    }
    if (this.onStateChange) this.onStateChange();
  },

  handleAddFromInputs(catId) {
    const reasonInput = document.getElementById(`reason-input-${catId}`);
    const ptsInput = document.getElementById(`pts-input-${catId}`);
    const reason = reasonInput ? reasonInput.value.trim() : "";
    const pts = ptsInput ? parseFloat(ptsInput.value) : 0.25;

    if (!reason) {
      if (window.AppModal) {
        window.AppModal.alert({ title: "Chybí důvod", message: "Zadejte důvod stržení bodů." });
      }
      return;
    }
    if (!pts || isNaN(pts) || pts <= 0) {
      if (window.AppModal) {
        window.AppModal.alert({ title: "Neplatné body", message: "Zadejte platný počet bodů k odečtení." });
      }
      return;
    }

    this.addDeduction(catId, pts, reason);
    if (reasonInput) {
      reasonInput.value = "";
      reasonInput.style.height = 'auto';
    }
  },

  onPresetSelect(catId, selectEl) {
    if (!selectEl.value) return;
    const [ptsStr, text] = selectEl.value.split('|');
    const pts = parseFloat(ptsStr);
    const ptsInput = document.getElementById(`pts-input-${catId}`);
    const reasonInput = document.getElementById(`reason-input-${catId}`);
    if (ptsInput) {
      ptsInput.value = pts.toString();
      if (!ptsInput.value) {
        const opt = document.createElement('option');
        opt.value = pts.toString();
        opt.textContent = `-${pts}`;
        ptsInput.appendChild(opt);
        ptsInput.value = pts.toString();
      }
    }
    if (reasonInput) {
      reasonInput.value = text;
      this.autoResizeTextarea(reasonInput);
    }
    selectEl.value = "";
  },

  async promptGradeOverride() {
    const total = this.getTotalPoints();
    const cur = this.getMark(total);
    if (window.AppModal) {
      const res = await window.AppModal.showForm({
        title: "Ruční úprava známky",
        fields: [
          {
            name: "grade",
            label: "Vyberte známku:",
            type: "select",
            value: this.state.manualGradeOverride || "",
            options: [
              { value: "", label: `Automatická podle bodů (${cur})` },
              { value: "A", label: "A (Výborně)" },
              { value: "B", label: "B (Velmi dobře)" },
              { value: "C", label: "C (Dobře)" },
              { value: "D", label: "D (Uspokojivě)" },
              { value: "E", label: "E (Dostatečně)" },
              { value: "F", label: "F (Nedostatečně)" }
            ]
          }
        ],
        confirmText: "Uložit známku"
      });
      if (res !== null) {
        const clean = (res.grade || "").trim().toUpperCase();
        this.state.manualGradeOverride = ['A', 'B', 'C', 'D', 'E', 'F'].includes(clean) ? clean : null;
        this.render();
        if (this.onStateChange) this.onStateChange();
      }
    }
  },

  getGradeBg(mark) {
    const map = { A: '#dcfce7', B: '#e0f2fe', C: '#fef3c7', D: '#ffedd5', E: '#fee2e2', F: '#450a0a' };
    return map[mark] || '#f1f5f9';
  },

  getGradeColor(mark) {
    const map = { A: '#15803d', B: '#0369a1', C: '#b45309', D: '#c2410c', E: '#b91c1c', F: '#fecaca' };
    return map[mark] || '#334155';
  },

  copyText(text, successMsg) {
    navigator.clipboard.writeText(text).then(() => {
      if (window.App && window.App.showToast) {
        window.App.showToast(successMsg || "Zkopírováno do schránky!");
      }
    });
  },

  escape(str) {
    if (!str) return '';
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
};

window.GradingEngine = GradingEngine;

