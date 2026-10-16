// Adobe Acrobat Style PDF Studio with Anchor-Based Smooth Zoom, Real Text Selection, Native Acrobat Annotations & Tooltips, and AI Proposals
const PDFStudio = {
  pdfDoc: null,
  scale: 1.25,
  totalPages: 0,
  activeTool: 'pan', // 'pan', 'highlight', 'strikeout', 'text', 'note', 'pen', 'rect', 'arrow'
  penColor: '#e11d48',
  penWidth: 2,
  annotations: [],
  aiProposals: [],
  protocolId: null,
  currentUser: null,
  floatingBoxEl: null,
  tooltipEl: null,
  isRendering: false,
  pendingRender: false,
  activeSelectedAnnot: null,
  highlightColor: '#ef4444',
  penColor: '#ef4444',
  highlightColors: [
    { name: 'red',    hex: '#ef4444', bg: 'rgba(239, 68, 68, 0.55)', border: 'rgba(220, 38, 38, 0.85)' },
    { name: 'yellow', hex: '#fef08a', bg: 'rgba(254, 240, 138, 0.55)', border: 'rgba(234, 179, 8, 0.8)' },
    { name: 'green',  hex: '#bbf7d0', bg: 'rgba(187, 247, 208, 0.55)', border: 'rgba(34, 197, 94, 0.8)' },
    { name: 'blue',   hex: '#bae6fd', bg: 'rgba(186, 230, 253, 0.55)', border: 'rgba(14, 165, 233, 0.8)' },
    { name: 'pink',   hex: '#fbcfe8', bg: 'rgba(251, 207, 232, 0.55)', border: 'rgba(236, 72, 153, 0.8)' },
    { name: 'orange', hex: '#fed7aa', bg: 'rgba(254, 215, 170, 0.55)', border: 'rgba(249, 115, 22, 0.8)' }
  ],

  setHighlightColor(hex) {
    this.highlightColor = hex;
    this.penColor = hex;
    document.querySelectorAll('.highlight-color-btn').forEach(btn => {
      if (btn.dataset.color === hex) btn.classList.add('active');
      else btn.classList.remove('active');
    });
    if (this.activeSelectedAnnot) {
      this.activeSelectedAnnot.color = hex;
      this.redrawPageAnnotations(this.activeSelectedAnnot.page);
      this.syncAnnotationsWithBackend();
    }
  },

  normalizeRect(r) {
    if (!r) return [0, 0, 0, 0];
    if (Array.isArray(r) && r.length >= 4) {
      return [Number(r[0]), Number(r[1]), Number(r[2]), Number(r[3])];
    }
    if (typeof r === 'object') {
      const x0 = Number(r.x ?? r.x0 ?? 0);
      const y0 = Number(r.y ?? r.y0 ?? 0);
      const w = r.width !== undefined ? Number(r.width) : (Number(r.x1 ?? x0) - x0);
      const h = r.height !== undefined ? Number(r.height) : (Number(r.y1 ?? y0) - y0);
      return [x0, y0, x0 + w, y0 + h];
    }
    return [0, 0, 0, 0];
  },

  getHighlightColorConfig(colorVal) {
    if (Array.isArray(colorVal) && colorVal.length >= 3) {
      const r = Math.round(colorVal[0] * 255);
      const g = Math.round(colorVal[1] * 255);
      const b = Math.round(colorVal[2] * 255);
      return {
        bg: `rgba(${r}, ${g}, ${b}, 0.55)`,
        border: `rgba(${r}, ${g}, ${b}, 0.85)`
      };
    }
    if (typeof colorVal === 'string') {
      const match = this.highlightColors.find(c => c.hex.toLowerCase() === colorVal.toLowerCase());
      if (match) return { bg: match.bg, border: match.border };
      if (colorVal.startsWith('#') && colorVal.length === 7) {
        const r = parseInt(colorVal.slice(1, 3), 16);
        const g = parseInt(colorVal.slice(3, 5), 16);
        const b = parseInt(colorVal.slice(5, 7), 16);
        return {
          bg: `rgba(${r}, ${g}, ${b}, 0.55)`,
          border: `rgba(${r}, ${g}, ${b}, 0.85)`
        };
      }
    }
    return { bg: 'rgba(254, 240, 138, 0.55)', border: 'rgba(234, 179, 8, 0.8)' };
  },

  formatColor(colorVal) {
    if (!colorVal) return this.penColor || '#ef4444';
    if (Array.isArray(colorVal) && colorVal.length >= 3) {
      const r = Math.round(colorVal[0] <= 1.0 ? colorVal[0] * 255 : colorVal[0]);
      const g = Math.round(colorVal[1] <= 1.0 ? colorVal[1] * 255 : colorVal[1]);
      const b = Math.round(colorVal[2] <= 1.0 ? colorVal[2] * 255 : colorVal[2]);
      return `rgb(${r}, ${g}, ${b})`;
    }
    if (typeof colorVal === 'string') return colorVal;
    return this.penColor || '#ef4444';
  },

  buildSmoothSvgPath(points, scale = 1) {
    if (!points || points.length === 0) return '';
    if (points.length === 1) {
      const p = points[0];
      return `M ${p[0] * scale} ${p[1] * scale} L ${p[0] * scale + 0.1} ${p[1] * scale + 0.1}`;
    }
    if (points.length === 2) {
      return `M ${points[0][0] * scale} ${points[0][1] * scale} L ${points[1][0] * scale} ${points[1][1] * scale}`;
    }
    let d = `M ${points[0][0] * scale} ${points[0][1] * scale}`;
    for (let i = 1; i < points.length - 1; i++) {
      const xc = ((points[i][0] + points[i + 1][0]) / 2) * scale;
      const yc = ((points[i][1] + points[i + 1][1]) / 2) * scale;
      const cpX = points[i][0] * scale;
      const cpY = points[i][1] * scale;
      d += ` Q ${cpX} ${cpY}, ${xc} ${yc}`;
    }
    const last = points[points.length - 1];
    d += ` L ${last[0] * scale} ${last[1] * scale}`;
    return d;
  },

  getAuthorName(annotAuthor) {
    if (annotAuthor && annotAuthor !== 'Správce aplikace' && annotAuthor !== 'Správce praktika') {
      return annotAuthor;
    }
    const stored = localStorage.getItem('evaluator_display_name');
    if (stored && stored.trim()) return stored.trim();
    if (this.currentUser) {
      if (this.currentUser.full_name && this.currentUser.full_name !== 'Správce aplikace' && this.currentUser.full_name !== 'Správce praktika') {
        return this.currentUser.full_name;
      }
      if (this.currentUser.username && this.currentUser.username !== 'admin') {
        return this.currentUser.username;
      }
    }
    return 'Vyučující';
  },

  init(containerEl, onNoteCreatedCallback, currentUser) {
    this.container = containerEl;
    this.onNoteCreated = onNoteCreatedCallback;
    this.currentUser = currentUser || { full_name: 'Asistent' };
    if (window.pdfjsLib) {
      window.pdfjsLib.GlobalWorkerOptions.workerSrc = '/static/vendor/pdf.worker.min.js';
    }
    this.createFloatingCommentCard();
    this.createTooltipBubble();
    this.setupZoomGestures();
  },

  createTooltipBubble() {
    let el = document.getElementById('acrobat-hover-tooltip');
    if (!el) {
      el = document.createElement('div');
      el.id = 'acrobat-hover-tooltip';
      el.className = 'acrobat-tooltip-bubble';
      el.style.display = 'none';
      document.body.appendChild(el);
    }
    this.tooltipEl = el;
  },

  showTooltip(author, text, x, y) {
    if (!this.tooltipEl || !text) return;
    this.tooltipEl.innerHTML = `
      <div class="acrobat-tooltip-author">${this.escape(author || 'Asistent')}</div>
      <div class="acrobat-tooltip-body">${this.escape(text)}</div>
    `;
    this.tooltipEl.style.display = 'block';

    const rect = this.tooltipEl.getBoundingClientRect();
    let posX = x - (rect.width / 2);
    let posY = y - rect.height - 12;

    if (posX < 10) posX = 10;
    if (posX + rect.width > window.innerWidth - 10) posX = window.innerWidth - rect.width - 10;
    if (posY < 10) posY = y + 20;

    this.tooltipEl.style.left = `${posX}px`;
    this.tooltipEl.style.top = `${posY}px`;
  },

  hideTooltip() {
    if (this.tooltipEl) {
      this.tooltipEl.style.display = 'none';
    }
  },

  createFloatingCommentCard() {
    let el = document.getElementById('acrobat-floating-comment');
    if (!el) {
      el = document.createElement('div');
      el.id = 'acrobat-floating-comment';
      el.className = 'acrobat-comment-card';
      document.body.appendChild(el);
    }
    this.floatingBoxEl = el;
  },

  setupZoomGestures() {
    const handleWheelZoom = (e) => {
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault();
        e.stopPropagation();

        // Distinguish discrete physical mouse wheel vs continuous trackpad pinch
        // Mouse wheel events typically have deltaMode === 1 (lines), or large integer multiples (e.g. 100, 120)
        const isDiscreteMouse = (e.deltaMode !== 0) ||
                                (Math.abs(e.deltaY) >= 80 && Math.abs(e.deltaY) % 10 === 0) ||
                                (e.wheelDelta !== undefined && Math.abs(e.wheelDelta) % 120 === 0);

        if (isDiscreteMouse) {
          // Physical mouse wheel: user-configured step (default 0.08, ~8%)
          const wheelStep = parseFloat(localStorage.getItem('praktika_zoom_wheel_step') || '0.08');
          const delta = -Math.sign(e.deltaY) * wheelStep;
          this.handlePinchZoom(delta, e.clientX, e.clientY);
        } else {
          // Trackpad pinch gesture: silky-smooth continuous exponential scaling
          const touchpadSens = parseFloat(localStorage.getItem('praktika_zoom_touchpad_sens') || '0.008');
          const multiplier = Math.exp(-e.deltaY * touchpadSens);
          this.handleContinuousZoom(multiplier, e.clientX, e.clientY);
        }
      }
    };

    if (this._containerWheelHandler && this.container) {
      this.container.removeEventListener('wheel', this._containerWheelHandler);
    }
    this._containerWheelHandler = handleWheelZoom;
    this.container.addEventListener('wheel', handleWheelZoom, { passive: false });

    if (!this._hasGlobalWheelHandler) {
      this._hasGlobalWheelHandler = true;
      window.addEventListener('wheel', (e) => {
        if ((e.ctrlKey || e.metaKey) && window.App && window.App.currentView === 'studio') {
          if (!this.container || !this.container.contains(e.target)) {
            e.preventDefault();
          }
        }
      }, { passive: false });

      window.addEventListener('gesturestart', (e) => {
        if (window.App && window.App.currentView === 'studio') e.preventDefault();
      }, { passive: false });

      window.addEventListener('gesturechange', (e) => {
        if (window.App && window.App.currentView === 'studio') {
          e.preventDefault();
          if (e.scale) {
            this.handleContinuousZoom(e.scale, e.clientX, e.clientY);
          }
        }
      }, { passive: false });
    }
  },

  handleContinuousZoom(multiplier, clientX, clientY) {
    if (!this.pdfDoc) return;
    const targetScale = Math.max(0.4, Math.min(3.5, Math.round(this.scale * multiplier * 1000) / 1000));
    if (Math.abs(targetScale - this.scale) < 0.002) return;

    if (!this._activePinchLoc) {
      this._activePinchLoc = this.getCurrentVisibleLocation(clientX, clientY);
    }

    const oldScale = this.scale;
    this.scale = targetScale;
    this.updateZoomBadge();

    const ratio = this.scale / (this.lastRenderedScale || 1.25);
    const pages = this.container ? this.container.querySelectorAll('.pdf-page-container') : [];
    pages.forEach(p => {
      p.style.transformOrigin = '50% 0';
      p.style.transform = `scale(${ratio})`;
      p.style.transition = 'none';
      const unscaledH = p.offsetHeight || 0;
      p.style.marginBottom = `${20 + unscaledH * (ratio - 1)}px`;
    });

    if (clientX && clientY && this.container) {
      const rect = this.container.getBoundingClientRect();
      const cursorY = clientY - rect.top;
      const zoomFactor = targetScale / oldScale;
      this.container.scrollTop = (this.container.scrollTop + cursorY) * zoomFactor - cursorY;

      const firstPage = this.container.querySelector('.pdf-page-container');
      const pageW = firstPage ? (firstPage.offsetWidth * ratio) : 0;
      if (pageW > this.container.clientWidth) {
        const cursorX = clientX - rect.left;
        this.container.scrollLeft = (this.container.scrollLeft + cursorX) * zoomFactor - cursorX;
      } else {
        this.container.scrollLeft = 0;
      }
    }

    clearTimeout(this.zoomDebounceTimer);
    const savedLoc = this._activePinchLoc;
    this.zoomDebounceTimer = setTimeout(() => {
      this._activePinchLoc = null;
      this.lastRenderedScale = this.scale;
      this.renderAllPages(true, savedLoc);
    }, 180);
  },

  zoomDebounceTimer: null,
  lastRenderedScale: 1.25,
  _activePinchLoc: null,

  // Anchor calculation: finds visible page and exact vertical and horizontal offset in invariant PDF units
  getCurrentVisibleLocation(clientX, clientY) {
    if (!this.container) return null;
    const container = this.container;
    const containerRect = container.getBoundingClientRect();
    const viewY = (clientY !== undefined && clientY !== null) ? (clientY - containerRect.top) : (containerRect.height / 2);
    const viewX = (clientX !== undefined && clientX !== null) ? (clientX - containerRect.left) : (containerRect.width / 2);

    const targetAbsY = container.scrollTop + viewY;
    const targetAbsX = container.scrollLeft + viewX;

    const pages = container.querySelectorAll('.pdf-page-container');
    let matchedPage = null;
    let pageTop = 0;
    let pageLeft = 0;
    for (const p of pages) {
      if (targetAbsY >= p.offsetTop && targetAbsY <= p.offsetTop + p.offsetHeight + 24) {
        matchedPage = p;
        pageTop = p.offsetTop;
        pageLeft = p.offsetLeft;
        break;
      }
    }
    if (!matchedPage && pages.length > 0) {
      matchedPage = pages[0];
      pageTop = matchedPage.offsetTop;
      pageLeft = matchedPage.offsetLeft;
    }

    const pageNum = matchedPage ? parseInt(matchedPage.dataset.pageNumber, 10) : 1;
    const renderScale = this.lastRenderedScale || this.scale || 1.25;
    const pdfY = (targetAbsY - pageTop) / renderScale;
    const pdfX = (targetAbsX - pageLeft) / renderScale;
    return { pageNum, pdfY, pdfX, viewY, viewX };
  },

  restoreLocation(loc) {
    if (!loc || !this.container) return;
    if (loc.pageNum) {
      const page = this.container.querySelector(`.pdf-page-container[data-page-number="${loc.pageNum}"]`);
      if (page) {
        const curScale = this.scale || 1.25;
        const targetScrollTop = page.offsetTop + (loc.pdfY * curScale) - loc.viewY;
        this.container.scrollTop = Math.max(0, targetScrollTop);

        // Keep centered horizontally if page fits container
        if (page.offsetWidth > this.container.clientWidth) {
          const targetScrollLeft = page.offsetLeft + (loc.pdfX * curScale) - loc.viewX;
          this.container.scrollLeft = Math.max(0, targetScrollLeft);
        } else {
          this.container.scrollLeft = 0;
        }
        return;
      }
    }
  },

  handlePinchZoom(delta, clientX, clientY) {
    if (!this.pdfDoc) return;
    const targetScale = Math.max(0.5, Math.min(3.0, Math.round((this.scale + delta) * 100) / 100));
    if (targetScale === this.scale) return;

    // Anchor captured at gesture start in invariant PDF coordinates
    if (!this._activePinchLoc) {
      this._activePinchLoc = this.getCurrentVisibleLocation(clientX, clientY);
    }

    const oldScale = this.scale;
    this.scale = targetScale;
    this.updateZoomBadge();

    const ratio = this.scale / (this.lastRenderedScale || 1.25);
    const pages = this.container ? this.container.querySelectorAll('.pdf-page-container') : [];
    pages.forEach(p => {
      p.style.transformOrigin = '50% 0';
      p.style.transform = `scale(${ratio})`;
      p.style.transition = 'none';
      const unscaledH = p.offsetHeight || 0;
      p.style.marginBottom = `${20 + unscaledH * (ratio - 1)}px`;
    });

    // Smooth scroll adjustment around cursor during active gesture
    if (clientX && clientY && this.container) {
      const rect = this.container.getBoundingClientRect();
      const cursorY = clientY - rect.top;
      const zoomFactor = targetScale / oldScale;
      this.container.scrollTop = (this.container.scrollTop + cursorY) * zoomFactor - cursorY;

      // Only adjust horizontal scroll if page content overflows the container width!
      // If page fits container, leave scrollLeft at 0 so it stays perfectly centered via CSS margin: 0 auto!
      const firstPage = this.container.querySelector('.pdf-page-container');
      const pageW = firstPage ? (firstPage.offsetWidth * ratio) : 0;
      if (pageW > this.container.clientWidth) {
        const cursorX = clientX - rect.left;
        this.container.scrollLeft = (this.container.scrollLeft + cursorX) * zoomFactor - cursorX;
      } else {
        this.container.scrollLeft = 0;
      }
    }

    clearTimeout(this.zoomDebounceTimer);
    const savedLoc = this._activePinchLoc;
    this.zoomDebounceTimer = setTimeout(() => {
      this._activePinchLoc = null;
      this.lastRenderedScale = this.scale;
      this.renderAllPages(true, savedLoc);
    }, 120);
  },

  updateZoomBadge() {
    const badge = document.getElementById('studio-zoom-badge');
    if (badge) {
      badge.textContent = `${Math.round(this.scale * 100)}%`;
    }
  },

  zoomSteps: [0.5, 0.65, 0.8, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0],

  setZoom(newScale) {
    const savedLoc = this.getCurrentVisibleLocation();
    this.scale = Math.max(0.5, Math.min(3.0, Math.round(newScale * 100) / 100));
    this.lastRenderedScale = this.scale;
    this.updateZoomBadge();
    this.renderAllPages(true, savedLoc);
  },

  zoom(delta) {
    this.setZoom(this.scale + delta);
  },

  zoomIn() {
    const cur = this.scale;
    const next = this.zoomSteps.find(s => s > cur + 0.02) || this.zoomSteps[this.zoomSteps.length - 1];
    this.setZoom(next);
  },

  zoomOut() {
    const cur = this.scale;
    const prev = [...this.zoomSteps].reverse().find(s => s < cur - 0.02) || this.zoomSteps[0];
    this.setZoom(prev);
  },

  zoomFit() {
    if (!this.container || !this.pdfDoc) return;
    const firstPage = this.container.querySelector('.pdf-page-container');
    if (!firstPage) return;
    const containerH = this.container.clientHeight - 40;
    const unscaledH = firstPage.offsetHeight / (this.lastRenderedScale || this.scale || 1.0);
    if (unscaledH <= 0) return;
    const targetScale = Math.max(0.5, Math.min(3.0, Math.round((containerH / unscaledH) * 100) / 100));
    this.setZoom(targetScale);
  },

  zoomFill() {
    if (!this.container || !this.pdfDoc) return;
    const firstPage = this.container.querySelector('.pdf-page-container');
    if (!firstPage) return;
    const containerW = this.container.clientWidth - 48;
    const unscaledW = firstPage.offsetWidth / (this.lastRenderedScale || this.scale || 1.0);
    if (unscaledW <= 0) return;
    const targetScale = Math.max(0.5, Math.min(3.0, Math.round((containerW / unscaledW) * 100) / 100));
    this.setZoom(targetScale);
  },

  resetZoom() {
    this.zoomFit();
  },

  setTool(toolName) {
    this.activeTool = toolName;
    document.querySelectorAll('.tool-btn').forEach(btn => {
      if (btn.dataset.tool === toolName) btn.classList.add('active');
      else btn.classList.remove('active');
    });

    const overlays = document.querySelectorAll('.annotation-overlay');
    const textLayers = document.querySelectorAll('.textLayer');

    overlays.forEach(overlay => {
      if (toolName === 'pan' || toolName === 'highlight' || toolName === 'strikeout') {
        // Allow textLayer to receive mouse events for real text selection
        overlay.style.pointerEvents = 'none';
      } else {
        overlay.style.pointerEvents = 'auto';
        if (toolName === 'note') overlay.style.cursor = 'cell';
        else if (toolName === 'text') overlay.style.cursor = 'text';
        else overlay.style.cursor = 'crosshair';
      }
    });

    textLayers.forEach(tl => {
      if (toolName === 'highlight' || toolName === 'strikeout') {
        tl.style.pointerEvents = 'auto';
        tl.style.cursor = 'text';
      } else if (toolName === 'pan') {
        tl.style.pointerEvents = 'auto';
        tl.style.cursor = 'default';
      } else {
        tl.style.pointerEvents = 'none';
      }
    });
  },

  async loadPDF(url, protoId, existingAnnotations = [], aiProposals = null) {
    this.protocolId = protoId;
    this.annotations = existingAnnotations ? [...existingAnnotations] : [];
    this.aiProposals = (aiProposals && aiProposals.annotations) ? [...aiProposals.annotations] : [];
    this.aiProposals.forEach((p, i) => {
      p.page = parseInt(p.page, 10) || 1;
      p.proposal_id = p.proposal_id || `annot_${this.protocolId || 0}_${i + 1}`;
    });
    this.activeSelectedAnnot = null;
    this.hideTooltip();
    this.closeCommentBox();

    try {
      const loadingTask = window.pdfjsLib.getDocument({
        url: url,
        cMapUrl: '/static/vendor/cmaps/',
        cMapPacked: true
      });
      this.pdfDoc = await loadingTask.promise;
      this.totalPages = this.pdfDoc.numPages;
      this.updateZoomBadge();
      await this.renderAllPages(false);
    } catch(err) {
      console.error("PDF load error:", err);
      if (window.AppModal) {
        window.AppModal.alert({ title: "Chyba načítání PDF", message: "Nepodařilo se načíst PDF soubor: " + err.message });
      }
    }
  },

  setAIProposals(proposalsData) {
    if (!proposalsData) {
      this.aiProposals = [];
    } else if (Array.isArray(proposalsData)) {
      this.aiProposals = [...proposalsData];
    } else if (proposalsData.annotations) {
      this.aiProposals = [...proposalsData.annotations];
    }
    this.aiProposals.forEach((p, i) => {
      p.page = parseInt(p.page, 10) || 1;
      p.proposal_id = p.proposal_id || `annot_${this.protocolId || 0}_${i + 1}`;
    });

    this.renderAIProposals();
  },

  renderAIProposals(targetPage = null) {
    if (!this.container) return;
    if (targetPage) {
      const pageWrap = this.container.querySelector(`.pdf-page-container[data-page-number="${targetPage}"]`);
      if (pageWrap) pageWrap.querySelectorAll('.ai-canvas-proposal').forEach(el => el.remove());
    } else {
      this.container.querySelectorAll('.ai-canvas-proposal').forEach(el => el.remove());
    }
    if (!Array.isArray(this.aiProposals) || this.aiProposals.length === 0) return;

    const list = targetPage 
      ? this.aiProposals.filter(p => (parseInt(p.page, 10) || 1) === parseInt(targetPage, 10))
      : this.aiProposals;

    list.forEach((prop, i) => {
      const pageNum = parseInt(prop.page, 10) || 1;
      const pageWrap = this.container.querySelector(`.pdf-page-container[data-page-number="${pageNum}"]`);
      if (!pageWrap) return;

      const pId = prop.proposal_id || `annot_${this.protocolId || 0}_${this.aiProposals.indexOf(prop) + 1}`;
      prop.proposal_id = pId;

      const rawR = prop.rect || (prop.point ? [prop.point[0] - 10, prop.point[1] - 8, prop.point[0] + 120, prop.point[1] + 14] : [80, 80, 240, 100]);
      const [x0, y0, x1, y1] = this.normalizeRect(rawR);

      const aiBox = document.createElement('div');
      aiBox.className = 'ai-canvas-proposal ai-proposal-highlight';
      aiBox.dataset.proposalId = pId;
      aiBox.style.left = `${x0 * this.scale}px`;
      aiBox.style.top = `${y0 * this.scale}px`;
      aiBox.style.width = `${Math.max(36, (x1 - x0) * this.scale)}px`;
      aiBox.style.height = `${Math.max(18, (y1 - y0) * this.scale)}px`;

      const pill = document.createElement('div');
      pill.className = 'ai-canvas-proposal-pill';
      if ((y0 * this.scale) < 32) {
        pill.style.top = 'calc(100% + 4px)';
      }
      pill.innerHTML = `
        <span class="ai-pill-text">✨ AI: ${this.escape((prop.comment || '').slice(0, 36))}...</span>
        <button type="button" class="ai-canvas-proposal-btn btn-apply" title="Schválit a aplikovat do PDF">✓ Aplikovat</button>
        <button type="button" class="ai-canvas-proposal-btn btn-reject" title="Zahodit návrh">✕ Zahodit</button>
      `;
      const btnApply = pill.querySelector('.btn-apply');
      const btnReject = pill.querySelector('.btn-reject');
      if (btnApply) {
        btnApply.addEventListener('mousedown', (ev) => ev.stopPropagation());
        btnApply.addEventListener('click', (ev) => {
          ev.preventDefault();
          ev.stopPropagation();
          PDFStudio.approveAIProposal(pId);
        });
      }
      if (btnReject) {
        btnReject.addEventListener('mousedown', (ev) => ev.stopPropagation());
        btnReject.addEventListener('click', (ev) => {
          ev.preventDefault();
          ev.stopPropagation();
          PDFStudio.rejectAIProposal(pId);
        });
      }
      aiBox.appendChild(pill);

      aiBox.addEventListener('mouseenter', (e) => {
        this.showTooltip("✨ Návrh AI asistenta", prop.comment, e.clientX, e.clientY);
      });
      aiBox.addEventListener('mouseleave', () => this.hideTooltip());
      aiBox.addEventListener('click', (e) => {
        if (e.target.closest('button')) return;
        e.stopPropagation();
        if (window.App && window.App.focusAIProposalFromCanvas) {
          window.App.focusAIProposalFromCanvas(pId);
        }
      });

      pageWrap.appendChild(aiBox);
    });
  },

  // Approve AI proposal and turn into standard teacher highlight annotation via atomic backend action
  approveAIProposal(target) {
    let pId = null;
    if (typeof target === 'string') {
      pId = target;
    } else if (target && target.proposal_id) {
      pId = target.proposal_id;
    } else if (typeof target === 'number' && this.aiProposals[target]) {
      pId = this.aiProposals[target].proposal_id;
    }
    if (!pId) return;

    if (window.App && window.App.executeAIProposalAction) {
      window.App.executeAIProposalAction('approve_annotation', pId);
    }
  },

  // Reject AI proposal via atomic backend action
  rejectAIProposal(target) {
    let pId = null;
    if (typeof target === 'string') {
      pId = target;
    } else if (target && target.proposal_id) {
      pId = target.proposal_id;
    } else if (typeof target === 'number' && this.aiProposals[target]) {
      pId = this.aiProposals[target].proposal_id;
    }
    if (!pId) return;

    if (window.App && window.App.executeAIProposalAction) {
      window.App.executeAIProposalAction('reject_annotation', pId);
    }
  },

  // Edit AI proposal before saving
  editAIProposal(target, screenX, screenY) {
    let idx = -1;
    if (typeof target === 'string') {
      idx = this.aiProposals.findIndex((p, i) => (p.proposal_id === target || `ai_prop_${i}` === target || `annot_${this.protocolId || 0}_${i+1}` === target || `prop_${i}` === target || `annot_${i}` === target));
    } else if (typeof target === 'number') {
      idx = target;
    }
    if (idx < 0 || idx >= this.aiProposals.length) return;
    const item = this.aiProposals[idx];
    const pageNum = parseInt(item.page, 10) || 1;
    const normRect = this.normalizeRect(item.rect);
    const dummyAnnot = {
      page: pageNum,
      type: item.type || 'highlight',
      rect: normRect,
      rects: [normRect],
      content: item.comment,
      author: this.getAuthorName()
    };
    this.openCommentBox(dummyAnnot, screenX, screenY, true, () => {
      this.aiProposals.splice(idx, 1);
      this.redrawPageAnnotations(pageNum);
      if (window.App && window.App.updateAIDrawerLists) window.App.updateAIDrawerLists();
    });
  },

  // Smooth HiDPI in-place render without deleting page DOM wrappers on zoom
  async renderAllPages(preservePosition = true, overrideLoc = null) {
    if (!this.pdfDoc) return;
    const savedLoc = overrideLoc || (preservePosition ? this.getCurrentVisibleLocation() : null);

    // Target DPR: devicePixelRatio tuned to high quality text smoothing
    const dpr = Math.min(window.devicePixelRatio || 1, 2.0);

    for (let pageNum = 1; pageNum <= this.totalPages; pageNum++) {
      const page = await this.pdfDoc.getPage(pageNum);
      const viewport = page.getViewport({ scale: this.scale });

      let pageWrap = this.container.querySelector(`.pdf-page-container[data-page-number="${pageNum}"]`);
      let canvas, textLayerDiv, svgOverlay;

      if (!pageWrap) {
        pageWrap = document.createElement('div');
        pageWrap.className = 'pdf-page-container';
        pageWrap.dataset.pageNumber = pageNum;
        pageWrap.style.position = 'relative';
        pageWrap.style.margin = '0 auto 20px auto';
        pageWrap.style.boxShadow = '0 3px 12px rgba(0,0,0,0.18)';
        pageWrap.style.background = '#ffffff';

        // 1. Canvas
        canvas = document.createElement('canvas');
        canvas.className = 'pdf-canvas';
        pageWrap.appendChild(canvas);

        // 2. TextLayer for native selection
        textLayerDiv = document.createElement('div');
        textLayerDiv.className = 'textLayer';
        pageWrap.appendChild(textLayerDiv);

        // 3. SVG Overlay for interactive annotations & Acrobat pins
        svgOverlay = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svgOverlay.setAttribute('class', 'annotation-layer annotation-overlay');
        svgOverlay.dataset.page = pageNum;
        pageWrap.appendChild(svgOverlay);

        this.setupOverlayEvents(svgOverlay, pageWrap, pageNum);
        this.container.appendChild(pageWrap);
      } else {
        canvas = pageWrap.querySelector('.pdf-canvas');
        textLayerDiv = pageWrap.querySelector('.textLayer');
        svgOverlay = pageWrap.querySelector('.annotation-layer');
      }

      // Render to offscreen canvas first to prevent white flash during re-render
      const nextCanvas = document.createElement('canvas');
      nextCanvas.className = 'pdf-canvas';
      nextCanvas.width = Math.floor(viewport.width * dpr);
      nextCanvas.height = Math.floor(viewport.height * dpr);
      nextCanvas.style.width = `${Math.floor(viewport.width)}px`;
      nextCanvas.style.height = `${Math.floor(viewport.height)}px`;

      const ctx = nextCanvas.getContext('2d', { alpha: false });
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = 'high';

      const renderCtx = {
        canvasContext: ctx,
        viewport: viewport,
        transform: [dpr, 0, 0, dpr, 0, 0]
      };
      await page.render(renderCtx).promise;

      // Swap canvas and reset transform synchronously without blank frames
      if (canvas && canvas.parentNode) {
        canvas.replaceWith(nextCanvas);
      } else {
        pageWrap.prepend(nextCanvas);
      }
      pageWrap.style.transform = '';
      pageWrap.style.marginBottom = '20px';
      pageWrap.style.width = `${Math.floor(viewport.width)}px`;
      pageWrap.style.height = `${Math.floor(viewport.height)}px`;

      // Update TextLayer
      textLayerDiv.style.width = `${Math.floor(viewport.width)}px`;
      textLayerDiv.style.height = `${Math.floor(viewport.height)}px`;
      textLayerDiv.innerHTML = '';
      const textContent = await page.getTextContent();
      window.pdfjsLib.renderTextLayer({
        textContent: textContent,
        container: textLayerDiv,
        viewport: viewport,
        textDivs: []
      });

      // Update SVG Overlay
      svgOverlay.setAttribute('width', Math.floor(viewport.width));
      svgOverlay.setAttribute('height', Math.floor(viewport.height));
      if (this.activeTool === 'pan' || this.activeTool === 'highlight' || this.activeTool === 'strikeout') {
        svgOverlay.style.pointerEvents = 'none';
      } else {
        svgOverlay.style.pointerEvents = 'auto';
      }

      // Redraw all annotations on this page
      this.redrawPageAnnotations(pageNum);
    }

    if (savedLoc) {
      this.restoreLocation(savedLoc);
    }
  },

  setupOverlayEvents(svg, pageWrap, pageNum) {
    let isDrawing = false;
    let currentStroke = [];
    let startPoint = null;
    let currentShapeEl = null;

    const getCoords = (e) => {
      const rect = pageWrap.getBoundingClientRect();
      const clientX = e.clientX || (e.touches && e.touches[0].clientX);
      const clientY = e.clientY || (e.touches && e.touches[0].clientY);
      const x = (clientX - rect.left) / this.scale;
      const y = (clientY - rect.top) / this.scale;
      return { x, y, viewX: clientX - rect.left, viewY: clientY - rect.top, screenX: clientX, screenY: clientY };
    };

    const onStart = (e) => {
      if (['pan', 'highlight', 'strikeout'].includes(this.activeTool)) return;
      if (e.target.closest('.acrobat-comment-card') || e.target.closest('.inline-typewriter-input')) return;

      const pt = getCoords(e);
      startPoint = pt;

      // Acrobat Note pin anywhere on click
      if (this.activeTool === 'note') {
        this.openCommentBox({
          page: pageNum,
          type: 'note',
          point: [pt.x, pt.y],
          content: ''
        }, pt.screenX, pt.screenY, true);
        return;
      }

      // Direct text / Typewriter
      if (this.activeTool === 'text') {
        this.openTypewriterInput(pageWrap, pageNum, pt);
        return;
      }

      isDrawing = true;

      // Pen
      if (this.activeTool === 'pen') {
        currentStroke = [[pt.x, pt.y]];
        currentShapeEl = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        currentShapeEl.setAttribute('stroke', this.penColor);
        currentShapeEl.setAttribute('stroke-width', this.penWidth * this.scale);
        currentShapeEl.setAttribute('fill', 'none');
        currentShapeEl.setAttribute('stroke-linecap', 'round');
        currentShapeEl.setAttribute('stroke-linejoin', 'round');
        svg.appendChild(currentShapeEl);
      }

      // Rect or Arrow
      if (this.activeTool === 'rect') {
        currentShapeEl = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        currentShapeEl.setAttribute('fill', 'rgba(225, 29, 72, 0.08)');
        currentShapeEl.setAttribute('stroke', this.penColor);
        currentShapeEl.setAttribute('stroke-width', 2);
        svg.appendChild(currentShapeEl);
      } else if (this.activeTool === 'arrow') {
        currentShapeEl = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        const arrowColor = this.highlightColor || this.penColor || '#ef4444';
        line.setAttribute('stroke', arrowColor);
        line.setAttribute('stroke-width', Math.max(2, 2.5 * this.scale));
        line.setAttribute('stroke-linecap', 'round');
        const head = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
        head.setAttribute('fill', arrowColor);
        currentShapeEl.appendChild(line);
        currentShapeEl.appendChild(head);
        svg.appendChild(currentShapeEl);
      }
    };

    const onMove = (e) => {
      if (!isDrawing) return;
      const pt = getCoords(e);

      if (this.activeTool === 'pen' && currentShapeEl) {
        currentStroke.push([pt.x, pt.y]);
        currentShapeEl.setAttribute('d', this.buildSmoothSvgPath(currentStroke, this.scale));
      } else if (this.activeTool === 'rect' && currentShapeEl) {
        const x = Math.min(startPoint.viewX, pt.viewX);
        const y = Math.min(startPoint.viewY, pt.viewY);
        const w = Math.abs(pt.viewX - startPoint.viewX);
        const h = Math.abs(pt.viewY - startPoint.viewY);
        currentShapeEl.setAttribute('x', x);
        currentShapeEl.setAttribute('y', y);
        currentShapeEl.setAttribute('width', w);
        currentShapeEl.setAttribute('height', h);
      } else if (this.activeTool === 'arrow' && currentShapeEl) {
        const line = currentShapeEl.querySelector('line');
        const head = currentShapeEl.querySelector('polygon');
        if (line) {
          line.setAttribute('x1', startPoint.viewX);
          line.setAttribute('y1', startPoint.viewY);
          line.setAttribute('x2', pt.viewX);
          line.setAttribute('y2', pt.viewY);
        }
        if (head) {
          const theta = Math.atan2(pt.viewY - startPoint.viewY, pt.viewX - startPoint.viewX);
          const headLen = Math.max(10, 14 * Math.min(1.5, this.scale));
          const p1x = pt.viewX - headLen * Math.cos(theta - 0.45);
          const p1y = pt.viewY - headLen * Math.sin(theta - 0.45);
          const p2x = pt.viewX - headLen * Math.cos(theta + 0.45);
          const p2y = pt.viewY - headLen * Math.sin(theta + 0.45);
          head.setAttribute('points', `${pt.viewX},${pt.viewY} ${p1x},${p1y} ${p2x},${p2y}`);
        }
      }
    };

    const onEnd = (e) => {
      if (!isDrawing) return;
      isDrawing = false;
      const pt = getCoords(e);

      if (this.activeTool === 'pen' && currentStroke.length >= 1) {
        if (currentStroke.length === 1) {
          currentStroke.push([currentStroke[0][0] + 0.5, currentStroke[0][1] + 0.5]);
        }
        this.addAnnotation({
          page: pageNum,
          type: 'ink',
          strokes: [currentStroke],
          color: this.highlightColor || this.penColor || '#ef4444',
          width: this.penWidth || 2
        });
      } else if (this.activeTool === 'rect') {
        const minX = Math.min(startPoint.x, pt.x);
        const minY = Math.min(startPoint.y, pt.y);
        const maxX = Math.max(startPoint.x, pt.x);
        const maxY = Math.max(startPoint.y, pt.y);
        if (maxX - minX > 5 && maxY - minY > 5) {
          this.addAnnotation({
            page: pageNum,
            type: 'rect',
            rect: [minX, minY, maxX, maxY]
          });
        }
      } else if (this.activeTool === 'arrow') {
        if (Math.hypot(pt.x - startPoint.x, pt.y - startPoint.y) > 10) {
          this.addAnnotation({
            page: pageNum,
            type: 'arrow',
            p1: [startPoint.x, startPoint.y],
            p2: [pt.x, pt.y],
            color: this.highlightColor || this.penColor || '#ef4444'
          });
        }
      }

      this.redrawPageAnnotations(pageNum);
    };

    pageWrap.addEventListener('mousedown', onStart);
    pageWrap.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onEnd);

    // Native Acrobat text selection listener on TextLayer
    pageWrap.addEventListener('mouseup', (e) => {
      if (this.activeTool !== 'highlight' && this.activeTool !== 'strikeout') return;
      const sel = window.getSelection();
      if (!sel || sel.isCollapsed || !sel.rangeCount) return;

      const range = sel.getRangeAt(0);
      const clientRects = range.getClientRects();
      if (clientRects.length === 0) return;

      const pageBox = pageWrap.getBoundingClientRect();
      const lineRects = [];
      let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;

      for (const r of clientRects) {
        if (r.width > 2 && r.height > 2) {
          const x0 = (r.left - pageBox.left) / this.scale;
          const y0 = (r.top - pageBox.top) / this.scale;
          const x1 = (r.right - pageBox.left) / this.scale;
          const y1 = (r.bottom - pageBox.top) / this.scale;
          lineRects.push([x0, y0, x1, y1]);
          minX = Math.min(minX, x0);
          minY = Math.min(minY, y0);
          maxX = Math.max(maxX, x1);
          maxY = Math.max(maxY, y1);
        }
      }

      sel.removeAllRanges();

      if (maxX > minX && maxY > minY) {
        const newAnnot = {
          page: pageNum,
          type: this.activeTool,
          rect: [minX, minY, maxX, maxY],
          rects: lineRects.length > 0 ? lineRects : [[minX, minY, maxX, maxY]],
          color: this.activeTool === 'highlight' ? this.highlightColor : '#ef4444',
          content: '',
          author: this.getAuthorName()
        };
        // Add highlight immediately to canvas so user sees the visual highlight right away!
        this.addAnnotation(newAnnot);
        this.redrawPageAnnotations(pageNum);

        const lastRect = clientRects[clientRects.length - 1];
        this.openCommentBox(newAnnot, lastRect.right, lastRect.bottom, false);
      }
    });
  },

  // Typewriter tool (type directly into text, inherits selected palette color)
  openTypewriterInput(pageWrap, pageNum, pt) {
    const textColor = this.highlightColor || this.penColor || '#ef4444';
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'inline-typewriter-input';
    input.style.position = 'absolute';
    input.style.left = `${pt.viewX}px`;
    input.style.top = `${pt.viewY - 10}px`;
    input.style.color = textColor;
    input.style.fontFamily = 'Helvetica, Arial, sans-serif';
    input.style.fontSize = '14px';
    input.style.fontWeight = 'bold';
    input.placeholder = 'Napište text...';
    input.style.background = 'rgba(255,255,255,0.95)';
    input.style.border = `1px solid ${textColor}`;
    input.style.borderRadius = '3px';
    input.style.padding = '2px 6px';
    input.style.zIndex = '30';
    input.style.outline = 'none';

    const finish = () => {
      const val = input.value.trim();
      input.remove();
      if (val) {
        this.addAnnotation({
          page: pageNum,
          type: 'text_direct',
          point: [pt.x, pt.y],
          content: val,
          color: textColor,
          fontsize: 14,
          author: this.getAuthorName()
        });
      }
    };

    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') finish();
      else if (e.key === 'Escape') input.remove();
    });
    input.addEventListener('blur', finish);

    pageWrap.appendChild(input);
    setTimeout(() => input.focus(), 20);
  },

  // Adobe Acrobat Floating Comment Card
  openCommentBox(annot, screenX, screenY, isNew = false, onCompleteCallback = null) {
    this.hideTooltip();
    const card = this.floatingBoxEl;
    if (!card) return;

    this.activeSelectedAnnot = annot;
    this.redrawPageAnnotations(annot.page);

    const author = this.getAuthorName(annot ? annot.author : null);
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    // Preset comments from App
    const quickComments = (window.App && window.App.commentPresets) || [
      "to není akademický styl",
      ", kde....čárka!",
      "Opět, graf není referencován v textu.",
      "Tato část textu je naprosto zbytečná.",
      "Chybí jednotka veličiny"
    ];

    card.innerHTML = `
      <div class="acrobat-comment-header">
        <div style="display:flex; align-items:center; gap:8px;">
          <div class="acrobat-avatar">${author.charAt(0)}</div>
          <div>
            <div style="font-weight:700; font-size:0.85rem; color:var(--text-main);">${this.escape(author)}</div>
            <div style="font-size:0.72rem; color:var(--text-muted);">${timeStr}</div>
          </div>
        </div>
        <button class="acrobat-close-btn" onclick="PDFStudio.closeCommentBox()" title="Zavřít">✕</button>
      </div>

      <textarea id="acrobat-comment-textarea" class="acrobat-textarea" placeholder="Napište poznámku k označenému místu...">${this.escape(annot.content || '')}</textarea>

      <!-- Quick Comment Chips -->
      <div style="display:flex; flex-wrap:wrap; gap:4px; margin-bottom:8px;">
        ${quickComments.slice(0, 5).map(qc => `
          <button type="button" class="quick-chip" onclick="PDFStudio.insertQuickComment('${this.escape(qc)}')">${this.escape(qc)}</button>
        `).join('')}
      </div>

      <!-- Quick Deduction option -->
      <div style="display:flex; align-items:center; justify-content:space-between; padding-top:6px; border-top:1px solid var(--border); font-size:0.78rem;">
        <label style="display:flex; align-items:center; gap:6px; cursor:pointer; color:var(--text-main);">
          <input type="checkbox" id="acrobat-deduct-check" ${isNew ? 'checked' : ''}>
          <span>Strhnout body</span>
        </label>
        <div style="display:flex; gap:4px; align-items:center;">
          <select id="acrobat-deduct-cat" class="form-control" style="font-size:0.75rem; padding:2px 4px; width:auto;">
            <option value="format">Formát</option>
            <option value="diskuze">Diskuze</option>
            <option value="chyby">Chyby</option>
            <option value="vysledky">Výsledky</option>
          </select>
          <select id="acrobat-deduct-pts" class="form-control" style="font-size:0.75rem; padding:2px 4px; width:auto; font-family:'JetBrains Mono',monospace;">
            <option value="0.125">-0.125 b</option>
            <option value="0.250" selected>-0.250 b</option>
            <option value="0.375">-0.375 b</option>
            <option value="0.500">-0.500 b</option>
            <option value="0.750">-0.750 b</option>
            <option value="1.000">-1.000 b</option>
          </select>
        </div>
      </div>

      <div class="acrobat-actions-row" style="display:flex; align-items:center; justify-content:space-between; margin-top:10px; gap:6px; flex-wrap:wrap;">
        <div style="display:flex; gap:6px; align-items:center;">
          <button type="button" class="btn btn-secondary btn-sm" id="acrobat-preset-btn" style="font-size:0.72rem; padding:3px 8px; white-space:nowrap;" title="Uložit tento text jako osobní šablonu">⭐ Uložit předvolbu</button>
          ${!isNew ? `<button type="button" class="btn btn-danger btn-sm" onclick="PDFStudio.deleteAnnotationObj(${this.annotations.indexOf(annot)})" style="padding:3px 8px; font-size:0.72rem;">Smazat</button>` : ''}
        </div>
        <div style="display:flex; gap:6px; align-items:center; margin-left:auto;">
          <button type="button" class="btn btn-secondary btn-sm" onclick="PDFStudio.closeCommentBox()" style="padding:3px 8px; font-size:0.72rem;">Zrušit</button>
          <button type="button" class="btn btn-primary btn-sm" id="acrobat-post-btn" style="padding:3px 10px; font-size:0.72rem; font-weight:700; white-space:nowrap; flex-shrink:0;">Uložit komentář</button>
        </div>
      </div>
    `;

    card.style.display = 'flex';
    const cardWidth = 410;
    const cardHeight = 240;
    let posX = Math.min(window.innerWidth - cardWidth - 20, Math.max(20, screenX + 15));
    let posY = Math.min(window.innerHeight - cardHeight - 20, Math.max(20, screenY - 20));
    card.style.left = `${posX}px`;
    card.style.top = `${posY}px`;

    // Make card draggable across screen by header
    const headerEl = card.querySelector('.acrobat-comment-header');
    if (headerEl) {
      headerEl.style.cursor = 'grab';
      headerEl.onmousedown = (e) => {
        if (e.target.closest('button')) return;
        headerEl.style.cursor = 'grabbing';
        const startX = e.clientX;
        const startY = e.clientY;
        const startLeft = parseFloat(card.style.left) || posX;
        const startTop = parseFloat(card.style.top) || posY;

        const onDragMove = (ev) => {
          const dx = ev.clientX - startX;
          const dy = ev.clientY - startY;
          const nextLeft = Math.max(10, Math.min(window.innerWidth - card.offsetWidth - 10, startLeft + dx));
          const nextTop = Math.max(10, Math.min(window.innerHeight - card.offsetHeight - 10, startTop + dy));
          card.style.left = `${nextLeft}px`;
          card.style.top = `${nextTop}px`;
        };

        const onDragEnd = () => {
          headerEl.style.cursor = 'grab';
          window.removeEventListener('mousemove', onDragMove);
          window.removeEventListener('mouseup', onDragEnd);
        };

        window.addEventListener('mousemove', onDragMove);
        window.addEventListener('mouseup', onDragEnd);
      };
    }

    const textarea = card.querySelector('#acrobat-comment-textarea');
    textarea.focus();

    card.querySelector('#acrobat-preset-btn').onclick = async () => {
      const val = textarea.value.trim();
      if (!val) {
        if (window.App && window.App.showToast) window.App.showToast("Nejdříve zadejte text poznámky.");
        return;
      }
      const shouldDeduct = card.querySelector('#acrobat-deduct-check').checked;
      const deductCat = card.querySelector('#acrobat-deduct-cat').value;
      const deductPts = parseFloat(card.querySelector('#acrobat-deduct-pts').value);

      try {
        const resp = await fetch('/api/presets', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            type: shouldDeduct ? 'deduction' : 'comment',
            category: deductCat,
            pts: shouldDeduct ? deductPts : 0,
            text: val
          })
        });
        if (resp.ok) {
          if (window.App && window.App.showToast) window.App.showToast("Předvolba byla úspěšně uložena do vašich osobních šablon!");
          if (window.App && window.App.loadInitialMetadata) window.App.loadInitialMetadata();
        }
      } catch (e) {
        console.warn("Preset save error:", e);
      }
    };

    card.querySelector('#acrobat-post-btn').onclick = () => {
      const val = textarea.value.trim();
      annot.content = val;
      annot.author = author;

      if (isNew) {
        this.addAnnotation(annot);
      } else {
        this.redrawPageAnnotations(annot.page);
        this.syncAnnotationsWithBackend();
      }

      const shouldDeduct = card.querySelector('#acrobat-deduct-check').checked;
      const deductCat = card.querySelector('#acrobat-deduct-cat').value;
      const deductPts = parseFloat(card.querySelector('#acrobat-deduct-pts').value);

      const engine = window.GradingEngine || (typeof GradingEngine !== 'undefined' ? GradingEngine : null);
      if (val && shouldDeduct && engine) {
        engine.addDeduction(deductCat, deductPts, val);
        if (window.App && window.App.showToast) {
          window.App.showToast(`Bodová srážka -${engine.formatPoints(deductPts)} b byla přidána do hodnocení!`);
        }
        if (window.App && window.App.scheduleAutosave) {
          window.App.scheduleAutosave();
        }
      }

      if (onCompleteCallback) onCompleteCallback();
      this.closeCommentBox();
    };
  },

  insertQuickComment(text) {
    const ta = document.getElementById('acrobat-comment-textarea');
    if (ta) {
      ta.value = text;
      ta.focus();
    }
  },

  closeCommentBox() {
    if (this.floatingBoxEl) {
      this.floatingBoxEl.style.display = 'none';
    }
    this.activeSelectedAnnot = null;
    if (this.container) {
      const pages = this.container.querySelectorAll('.pdf-page-container');
      pages.forEach(p => this.redrawPageAnnotations(parseInt(p.dataset.pageNumber)));
    }
  },

  deleteAnnotationObj(idx) {
    if (idx >= 0 && idx < this.annotations.length) {
      const removed = this.annotations.splice(idx, 1)[0];
      this.activeSelectedAnnot = null;
      this.redrawPageAnnotations(removed.page);
      this.syncAnnotationsWithBackend();
    }
    this.closeCommentBox();
  },

  addAnnotation(annot) {
    this.annotations.push(annot);
    this.activeSelectedAnnot = annot;
    this.redrawPageAnnotations(annot.page);
    this.syncAnnotationsWithBackend();
  },

  undo() {
    if (this.annotations.length === 0) return;
    const removed = this.annotations.pop();
    this.redrawPageAnnotations(removed.page);
    this.syncAnnotationsWithBackend();
  },

  // Redraw all annotations and AI proposals on a specific page
  redrawPageAnnotations(pageNum) {
    const pageNumInt = parseInt(pageNum, 10) || 1;
    const pageWrap = this.container.querySelector(`.pdf-page-container[data-page-number="${pageNumInt}"]`);
    if (!pageWrap) return;
    const svg = pageWrap.querySelector('svg.annotation-layer');
    if (!svg) return;

    svg.innerHTML = '';
    pageWrap.querySelectorAll('.pdf-pin, .acrobat-comment-icon, .pdf-direct-text-item, .acrobat-active-selection-box, .ai-canvas-proposal, .acrobat-highlight-overlay').forEach(el => el.remove());

    const pageAnnots = this.annotations.filter(a => (parseInt(a.page, 10) || 1) === pageNumInt);

    pageAnnots.forEach((a) => {
      const isActive = (this.activeSelectedAnnot === a);

      // 1. Direct text on page (Acrobat typewriter)
      if (a.type === 'text_direct' && a.point) {
        const textItem = document.createElement('div');
        textItem.className = 'pdf-direct-text-item';
        textItem.style.position = 'absolute';
        textItem.style.left = `${a.point[0] * this.scale}px`;
        textItem.style.top = `${(a.point[1] - 12) * this.scale}px`;
        textItem.style.color = a.color || this.highlightColor || '#ef4444';
        textItem.style.fontFamily = 'Helvetica, Arial, sans-serif';
        textItem.style.fontSize = `${(a.fontsize || 14) * this.scale}px`;
        textItem.textContent = a.content;
        textItem.addEventListener('dblclick', async () => {
          const edit = await window.AppModal.prompt({
            title: "Upravit text poznámky",
            message: "Upravte text (ponechte prázdné pro smazání):",
            defaultValue: a.content,
            confirmText: "Uložit"
          });
          if (edit === null) return;
          if (edit.trim() === '') {
            this.deleteAnnotationObj(this.annotations.indexOf(a));
          } else {
            a.content = edit.trim();
            this.redrawPageAnnotations(pageNumInt);
            this.syncAnnotationsWithBackend();
          }
        });
        pageWrap.appendChild(textItem);
      }

      // 2. Ink / Freehand drawing
      else if (a.type === 'ink' && a.strokes) {
        const strokeColor = this.formatColor(a.color) || this.penColor || '#ef4444';
        a.strokes.forEach(stroke => {
          if (!stroke || stroke.length === 0) return;
          const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
          path.setAttribute('d', this.buildSmoothSvgPath(stroke, this.scale));
          path.setAttribute('stroke', strokeColor);
          path.setAttribute('stroke-width', (a.width || 2) * this.scale);
          path.setAttribute('fill', 'none');
          path.setAttribute('stroke-linecap', 'round');
          path.setAttribute('stroke-linejoin', 'round');
          svg.appendChild(path);
        });
      }

      // 3. Highlight (Acrobat style with multi-line rects, interactive hover overlay, and red comment icon [⊖])
      else if (a.type === 'highlight' && (a.rect || a.rects)) {
        const rectList = (a.rects && a.rects.length > 0) ? a.rects : [a.rect];
        const colorCfg = this.getHighlightColorConfig(a.color);
        
        rectList.forEach(r => {
          const [x0, y0, x1, y1] = this.normalizeRect(r);
          if (x1 <= x0 || y1 <= y0) return;

          const hDiv = document.createElement('div');
          hDiv.className = 'acrobat-highlight-overlay';
          hDiv.style.position = 'absolute';
          hDiv.style.left = `${x0 * this.scale}px`;
          hDiv.style.top = `${y0 * this.scale}px`;
          hDiv.style.width = `${(x1 - x0) * this.scale}px`;
          hDiv.style.height = `${(y1 - y0) * this.scale}px`;
          hDiv.style.background = colorCfg.bg;
          hDiv.style.borderBottom = `2px solid ${colorCfg.border}`;
          hDiv.style.cursor = 'pointer';
          hDiv.style.pointerEvents = 'auto';
          hDiv.style.mixBlendMode = 'multiply';
          hDiv.style.zIndex = '15';

          // Tooltip on hover over ANY part of the highlighted text
          hDiv.addEventListener('mouseenter', (e) => {
            if (a.content) this.showTooltip(a.author, a.content, e.clientX, e.clientY);
          });
          hDiv.addEventListener('mouseleave', () => this.hideTooltip());
          hDiv.addEventListener('click', (e) => {
            e.stopPropagation();
            this.openCommentBox(a, e.clientX, e.clientY, false);
          });
          pageWrap.appendChild(hDiv);
        });

        // Red circular Acrobat comment icon [⊖]
        const mainRect = this.normalizeRect(a.rect || (a.rects && a.rects[0]));
        if (mainRect && (mainRect[2] > mainRect[0])) {
          const [rx0, ry0] = mainRect;
          const icon = document.createElement('div');
          icon.className = 'acrobat-comment-icon';
          icon.style.left = `${(rx0 * this.scale) - 9}px`;
          icon.style.top = `${(ry0 * this.scale) - 9}px`;
          icon.title = a.content ? `${a.author || 'Asistent'}: ${a.content}` : 'Acrobat komentář';
          icon.addEventListener('mouseenter', (e) => {
            if (a.content) this.showTooltip(a.author, a.content, e.clientX, e.clientY);
          });
          icon.addEventListener('mouseleave', () => this.hideTooltip());
          icon.addEventListener('click', (e) => {
            e.stopPropagation();
            this.openCommentBox(a, e.clientX, e.clientY, false);
          });
          pageWrap.appendChild(icon);
        }

        // Active blue Acrobat bounding outline when selected
        if (isActive && mainRect) {
          const [x0, y0, x1, y1] = mainRect;
          const activeBox = document.createElement('div');
          activeBox.className = 'acrobat-active-selection-box';
          activeBox.style.left = `${(x0 * this.scale) - 2}px`;
          activeBox.style.top = `${(y0 * this.scale) - 2}px`;
          activeBox.style.width = `${((x1 - x0) * this.scale) + 4}px`;
          activeBox.style.height = `${((y1 - y0) * this.scale) + 4}px`;
          pageWrap.appendChild(activeBox);
        }
      }

      // 4. Strikeout (Acrobat red line)
      else if (a.type === 'strikeout' && (a.rect || a.rects)) {
        const [x0, y0, x1, y1] = this.normalizeRect(a.rect || (a.rects && a.rects[0]));
        const midY = ((y0 + y1) / 2) * this.scale;
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', x0 * this.scale);
        line.setAttribute('y1', midY);
        line.setAttribute('x2', x1 * this.scale);
        line.setAttribute('y2', midY);
        line.setAttribute('stroke', '#ef4444');
        line.setAttribute('stroke-width', Math.max(2, 2.5 * this.scale));
        line.setAttribute('stroke-linecap', 'round');
        line.style.cursor = 'pointer';

        line.addEventListener('mouseenter', (e) => {
          if (a.content) this.showTooltip(a.author, a.content, e.clientX, e.clientY);
        });
        line.addEventListener('mouseleave', () => this.hideTooltip());
        line.addEventListener('click', (e) => {
          e.stopPropagation();
          this.openCommentBox(a, e.clientX, e.clientY, false);
        });
        svg.appendChild(line);

        const icon = document.createElement('div');
        icon.className = 'acrobat-comment-icon';
        icon.style.left = `${(x0 * this.scale) - 9}px`;
        icon.style.top = `${midY - 9}px`;
        icon.title = a.content || 'Přeškrtnutí textu';
        icon.addEventListener('mouseenter', (e) => {
          if (a.content) this.showTooltip(a.author, a.content, e.clientX, e.clientY);
        });
        icon.addEventListener('mouseleave', () => this.hideTooltip());
        icon.addEventListener('click', (e) => {
          e.stopPropagation();
          this.openCommentBox(a, e.clientX, e.clientY, false);
        });
        pageWrap.appendChild(icon);
      }

      // 5. Rect (Bounding box)
      else if (a.type === 'rect' && a.rect) {
        const [x0, y0, x1, y1] = this.normalizeRect(a.rect);
        const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        rect.setAttribute('x', x0 * this.scale);
        rect.setAttribute('y', y0 * this.scale);
        rect.setAttribute('width', (x1 - x0) * this.scale);
        rect.setAttribute('height', (y1 - y0) * this.scale);
        rect.setAttribute('fill', 'rgba(239, 68, 68, 0.08)');
        rect.setAttribute('stroke', a.color || this.penColor || '#ef4444');
        rect.setAttribute('stroke-width', 2);
        svg.appendChild(rect);
      }

      // 6. Arrow with real arrowhead polygon
      else if (a.type === 'arrow' && a.p1 && a.p2) {
        const arrowGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        const arrowColor = a.color || this.highlightColor || '#ef4444';
        const startX = a.p1[0] * this.scale;
        const startY = a.p1[1] * this.scale;
        const endX = a.p2[0] * this.scale;
        const endY = a.p2[1] * this.scale;
        line.setAttribute('x1', startX);
        line.setAttribute('y1', startY);
        line.setAttribute('x2', endX);
        line.setAttribute('y2', endY);
        line.setAttribute('stroke', arrowColor);
        line.setAttribute('stroke-width', Math.max(2, 2.5 * this.scale));
        line.setAttribute('stroke-linecap', 'round');

        const head = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
        const theta = Math.atan2(endY - startY, endX - startX);
        const headLen = Math.max(10, 14 * Math.min(1.5, this.scale));
        const p1x = endX - headLen * Math.cos(theta - 0.45);
        const p1y = endY - headLen * Math.sin(theta - 0.45);
        const p2x = endX - headLen * Math.cos(theta + 0.45);
        const p2y = endY - headLen * Math.sin(theta + 0.45);
        head.setAttribute('points', `${endX},${endY} ${p1x},${p1y} ${p2x},${p2y}`);
        head.setAttribute('fill', arrowColor);

        arrowGroup.appendChild(line);
        arrowGroup.appendChild(head);
        svg.appendChild(arrowGroup);
      }

      // 7. Sticky Note Pin (Acrobat [⊖] circular pin)
      else if (a.type === 'note' && a.point) {
        const pin = document.createElement('div');
        pin.className = 'acrobat-comment-icon';
        pin.style.left = `${(a.point[0] * this.scale) - 9}px`;
        pin.style.top = `${(a.point[1] * this.scale) - 9}px`;
        pin.title = a.content || 'Komentář';
        pin.addEventListener('mouseenter', (e) => {
          if (a.content) this.showTooltip(a.author, a.content, e.clientX, e.clientY);
        });
        pin.addEventListener('mouseleave', () => this.hideTooltip());
        pin.addEventListener('click', (e) => {
          e.stopPropagation();
          this.openCommentBox(a, e.clientX, e.clientY, false);
        });
        pageWrap.appendChild(pin);
      }
    });

    // Render AI proposals on canvas
    this.renderAIProposals(pageNumInt);
  },

  async syncAnnotationsWithBackend() {
    if (!this.protocolId) return;
    try {
      if (window.App && window.App.scheduleAutosave) {
        window.App.scheduleAutosave();
      } else {
        await fetch(`/api/protocols/${this.protocolId}/annotations`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            protocol_id: this.protocolId,
            annotations: this.annotations
          })
        });
      }
    } catch (e) {
      console.warn("Auto-sync annotations warning:", e);
    }
  },

  escape(str) {
    if (!str) return '';
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
};

// Explicit global export so window.PDFStudio is accessible everywhere
window.PDFStudio = PDFStudio;
