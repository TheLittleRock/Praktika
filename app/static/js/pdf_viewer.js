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
  historyStack: [],
  redoStack: [],
  protocolId: null,
  currentUser: null,
  floatingBoxEl: null,
  tooltipEl: null,
  isRendering: false,
  pendingRender: false,
  activeSelectedAnnot: null,
  activeEditingCommentAnnot: null,
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
    // Never retroactively recolor previously drawn tools/shapes.
    // Only update if user is actively in the comment editing dialog for a highlight/strikeout/note:
    if (this.activeEditingCommentAnnot) {
      this.activeEditingCommentAnnot.color = hex;
      this.redrawPageAnnotations(this.activeEditingCommentAnnot.page);
      this.syncAnnotationsWithBackend();
    }
  },

  changeCommentHighlightColor(hex) {
    if (this.activeEditingCommentAnnot) {
      this.activeEditingCommentAnnot.color = hex;
      if (this.floatingBoxEl) {
        this.floatingBoxEl.querySelectorAll('.comment-box-color-btn').forEach(b => {
          b.style.borderColor = (b.dataset.color === hex) ? 'var(--text-main)' : 'transparent';
          b.style.transform = (b.dataset.color === hex) ? 'scale(1.2)' : 'scale(1)';
        });
      }
      this.redrawPageAnnotations(this.activeEditingCommentAnnot.page);
      this.syncAnnotationsWithBackend();
    }
  },

  getFillColorForStroke(strokeColor, opacity = 0.12) {
    if (!strokeColor) return `rgba(239, 68, 68, ${opacity})`;
    if (strokeColor.startsWith('#')) {
      const hex = strokeColor.replace('#', '');
      if (hex.length === 6) {
        const r = parseInt(hex.substring(0, 2), 16);
        const g = parseInt(hex.substring(2, 4), 16);
        const b = parseInt(hex.substring(4, 6), 16);
        return `rgba(${r}, ${g}, ${b}, ${opacity})`;
      } else if (hex.length === 3) {
        const r = parseInt(hex[0] + hex[0], 16);
        const g = parseInt(hex[1] + hex[1], 16);
        const b = parseInt(hex[2] + hex[2], 16);
        return `rgba(${r}, ${g}, ${b}, ${opacity})`;
      }
    }
    return strokeColor;
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

  smoothStrokeChaikin(points, iterations = 2) {
    if (!points || points.length <= 2) return points ? points.map(p => [p[0], p[1]]) : [];
    let pts = points.map(p => [p[0], p[1]]);
    for (let it = 0; it < iterations; it++) {
      const smoothed = [pts[0]];
      for (let i = 0; i < pts.length - 1; i++) {
        const p0 = pts[i];
        const p1 = pts[i + 1];
        const q = [0.75 * p0[0] + 0.25 * p1[0], 0.75 * p0[1] + 0.25 * p1[1]];
        const r = [0.25 * p0[0] + 0.75 * p1[0], 0.25 * p0[1] + 0.75 * p1[1]];
        smoothed.push(q, r);
      }
      smoothed.push(pts[pts.length - 1]);
      pts = smoothed;
    }
    return pts;
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
    this.setupKeyboardShortcuts();

    if (this.container) {
      this.container.addEventListener('scroll', () => this.hideTooltip(), { passive: true });
      this.container.addEventListener('mouseleave', () => this.hideTooltip());
    }
    window.addEventListener('blur', () => this.hideTooltip());
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

  setupKeyboardShortcuts() {
    window.addEventListener('keydown', (e) => {
      if (e.target.matches('input, textarea, [contenteditable="true"]')) return;
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
        if (e.shiftKey) {
          e.preventDefault();
          this.redo();
        } else {
          e.preventDefault();
          this.undo();
        }
      } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'y') {
        e.preventDefault();
        this.redo();
      }
    });
  },

  setupZoomGestures() {
    const handleWheelZoom = (e) => {
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault();
        e.stopPropagation();

        // Distinguish discrete physical mouse wheel vs continuous trackpad pinch
        // Physical notch mouse wheels typically have deltaMode === 1 (lines), or integer multiples of 120 (standard notch)
        const isDiscreteMouse = (e.deltaMode !== 0) ||
                                (Math.abs(e.deltaY) >= 100 && (Math.abs(e.deltaY) % 50 === 0) && Number.isInteger(e.deltaY) && (e.wheelDelta === undefined || e.wheelDelta % 120 === 0));

        if (isDiscreteMouse) {
          // Physical mouse wheel: user-configured step (default 0.08, ~8%)
          const wheelStep = parseFloat(localStorage.getItem('praktika_zoom_ctrl_wheel_step') || localStorage.getItem('praktika_zoom_wheel_step') || '0.08');
          const delta = -Math.sign(e.deltaY) * wheelStep;
          this.handlePinchZoom(delta, e.clientX, e.clientY);
        } else {
          // Trackpad pinch gesture: silky-smooth continuous exponential scaling
          const touchpadSens = parseFloat(localStorage.getItem('praktika_zoom_touchpad_sens') || '0.005');
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

  convertCurrentSelectionToAnnotation(toolName, sel) {
    if (!sel || sel.isCollapsed || !sel.rangeCount) return;
    const range = sel.getRangeAt(0);
    const clientRects = range.getClientRects();
    if (!clientRects || clientRects.length === 0) return;

    let node = range.commonAncestorContainer;
    if (node && node.nodeType === 3) node = node.parentNode;
    const pageWrap = node ? node.closest('.pdf-page-container') : null;
    if (!pageWrap) return;
    const pageNum = parseInt(pageWrap.dataset.pageNumber, 10) || 1;

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
        id: `annot_${this.protocolId || 0}_${Date.now()}_${Math.floor(Math.random() * 1000)}`,
        page: pageNum,
        type: toolName,
        rect: [minX, minY, maxX, maxY],
        rects: lineRects.length > 0 ? lineRects : [[minX, minY, maxX, maxY]],
        color: toolName === 'highlight' ? this.highlightColor : '#ef4444',
        content: '',
        author: this.getAuthorName()
      };
      this.addAnnotation(newAnnot);
      this.redrawPageAnnotations(pageNum);

      const lastRect = clientRects[clientRects.length - 1];
      this.openCommentBox(newAnnot, lastRect.right, lastRect.bottom, false);
    }
  },

  setTool(toolName) {
    this.activeTool = toolName;
    this.activeSelectedAnnot = null;
    this.hideTooltip();

    if (toolName === 'highlight' || toolName === 'strikeout') {
      const sel = window.getSelection();
      if (sel && !sel.isCollapsed && sel.rangeCount > 0) {
        this.convertCurrentSelectionToAnnotation(toolName, sel);
      }
    }

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
        btnApply.addEventListener('mouseup', (ev) => ev.stopPropagation());
        btnApply.addEventListener('click', (ev) => {
          ev.preventDefault();
          ev.stopPropagation();
          PDFStudio.approveAIProposal(prop);
        });
      }
      if (btnReject) {
        btnReject.addEventListener('mousedown', (ev) => ev.stopPropagation());
        btnReject.addEventListener('mouseup', (ev) => ev.stopPropagation());
        btnReject.addEventListener('click', (ev) => {
          ev.preventDefault();
          ev.stopPropagation();
          PDFStudio.rejectAIProposal(prop);
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
    this.hideTooltip();
    let pId = null;
    let prop = null;
    if (typeof target === 'string') {
      pId = target;
      prop = this.aiProposals.find(p => p.proposal_id === pId || p.proposal_id === target);
    } else if (target && target.proposal_id) {
      pId = target.proposal_id;
      prop = target;
    } else if (typeof target === 'number' && this.aiProposals[target]) {
      prop = this.aiProposals[target];
      pId = prop.proposal_id;
    }
    if (!pId && !prop) return;
    if (!pId && prop) pId = prop.proposal_id;

    // Instant local application to canvas
    const idx = prop ? this.aiProposals.indexOf(prop) : this.aiProposals.findIndex(p => p.proposal_id === pId);
    let approvedItem = prop;
    if (idx !== -1) {
      approvedItem = this.aiProposals.splice(idx, 1)[0];
    }
    if (approvedItem) {
      const pageNum = parseInt(approvedItem.page, 10) || 1;
      const rawR = approvedItem.rect || (approvedItem.point ? [approvedItem.point[0] - 10, approvedItem.point[1] - 8, approvedItem.point[0] + 120, approvedItem.point[1] + 14] : [80, 80, 240, 100]);
      const normR = this.normalizeRect(rawR);
      const newAnnot = {
        id: `annot_${this.protocolId || 0}_${Date.now()}_${Math.floor(Math.random() * 1000)}`,
        page: pageNum,
        type: 'highlight',
        rect: normR,
        rects: [normR],
        point: approvedItem.point || [normR[0], normR[1]],
        content: approvedItem.comment || '',
        author: this.getAuthorName(),
        color: '#ef4444',
        created_at: new Date().toISOString()
      };
      this.addAnnotation(newAnnot);
      this.redrawPageAnnotations(pageNum);
      const canvasEl = document.querySelector(`.ai-canvas-proposal[data-proposal-id="${pId}"]`);
      if (canvasEl) canvasEl.remove();
    }

    if (window.App && window.App.executeAIProposalAction) {
      window.App.executeAIProposalAction('approve_annotation', pId);
    }
  },

  // Reject AI proposal via atomic backend action
  rejectAIProposal(target) {
    this.hideTooltip();
    let pId = null;
    let prop = null;
    if (typeof target === 'string') {
      pId = target;
      prop = this.aiProposals.find(p => p.proposal_id === pId || p.proposal_id === target);
    } else if (target && target.proposal_id) {
      pId = target.proposal_id;
      prop = target;
    } else if (typeof target === 'number' && this.aiProposals[target]) {
      prop = this.aiProposals[target];
      pId = prop.proposal_id;
    }
    if (!pId && !prop) return;
    if (!pId && prop) pId = prop.proposal_id;

    const idx = prop ? this.aiProposals.indexOf(prop) : this.aiProposals.findIndex(p => p.proposal_id === pId);
    let rejectedItem = prop;
    if (idx !== -1) {
      rejectedItem = this.aiProposals.splice(idx, 1)[0];
    }
    const pageNum = rejectedItem ? (parseInt(rejectedItem.page, 10) || 1) : 1;
    this.redrawPageAnnotations(pageNum);
    const canvasEl = document.querySelector(`.ai-canvas-proposal[data-proposal-id="${pId}"]`);
    if (canvasEl) canvasEl.remove();

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

        // 3. LinksLayer for clickable PDF hyperlinks
        const linksLayerDiv = document.createElement('div');
        linksLayerDiv.className = 'pdf-links-layer';
        pageWrap.appendChild(linksLayerDiv);

        // 4. SVG Overlay for interactive annotations & Acrobat pins
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

      // Render clickable links from PDF
      await this.renderPageLinks(page, pageWrap, viewport);

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

  scrollToPage(pageNum) {
    const pageWrap = this.container.querySelector(`.pdf-page-container[data-page-number="${pageNum}"]`);
    if (pageWrap) {
      pageWrap.scrollIntoView({ behavior: 'smooth', block: 'start' });
      this.hideTooltip();
    }
  },

  async renderPageLinks(page, pageWrap, viewport) {
    let linksDiv = pageWrap.querySelector('.pdf-links-layer');
    if (!linksDiv) {
      linksDiv = document.createElement('div');
      linksDiv.className = 'pdf-links-layer';
      const textLayer = pageWrap.querySelector('.textLayer');
      if (textLayer && textLayer.nextSibling) {
        pageWrap.insertBefore(linksDiv, textLayer.nextSibling);
      } else {
        pageWrap.appendChild(linksDiv);
      }
    }
    linksDiv.innerHTML = '';
    linksDiv.style.width = `${Math.floor(viewport.width)}px`;
    linksDiv.style.height = `${Math.floor(viewport.height)}px`;

    try {
      const annots = await page.getAnnotations({ intent: 'display' });
      for (const a of annots) {
        if (a.subtype !== 'Link' || !a.rect) continue;
        const vRect = viewport.convertToViewportRectangle(a.rect);
        const minX = Math.min(vRect[0], vRect[2]);
        const maxX = Math.max(vRect[0], vRect[2]);
        const minY = Math.min(vRect[1], vRect[3]);
        const maxY = Math.max(vRect[1], vRect[3]);
        const width = maxX - minX;
        const height = maxY - minY;
        if (width <= 0 || height <= 0) continue;

        const linkEl = document.createElement('a');
        linkEl.className = 'pdf-link-element';
        linkEl.style.left = `${Math.floor(minX)}px`;
        linkEl.style.top = `${Math.floor(minY)}px`;
        linkEl.style.width = `${Math.ceil(width)}px`;
        linkEl.style.height = `${Math.ceil(height)}px`;

        if (a.url) {
          linkEl.href = a.url;
          linkEl.target = '_blank';
          linkEl.rel = 'noopener noreferrer';
          linkEl.title = `Otevřít odkaz: ${a.url}`;
          linkEl.addEventListener('click', (e) => {
            if (this.activeTool !== 'pan') {
              e.preventDefault();
            }
          });
        } else if (a.dest) {
          linkEl.href = '#';
          linkEl.title = 'Přejít na odkaz v dokumentu';
          linkEl.addEventListener('click', async (e) => {
            e.preventDefault();
            if (this.activeTool !== 'pan') return;
            try {
              let dest = a.dest;
              if (typeof dest === 'string') {
                dest = await this.pdfDoc.getDestination(dest);
              }
              if (Array.isArray(dest) && dest.length > 0) {
                const pageRef = dest[0];
                const pageIdx = await this.pdfDoc.getPageIndex(pageRef);
                const targetPageNum = pageIdx + 1;
                this.scrollToPage(targetPageNum);
              }
            } catch (err) {
              console.warn("Error navigating internal PDF link:", err);
            }
          });
        }
        linksDiv.appendChild(linkEl);
      }
    } catch (e) {
      console.warn("Error rendering PDF links:", e);
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
      if (this.activeTool === 'pan') {
        if (this.activeSelectedAnnot && !e.target.closest('.acrobat-active-selection-box, .pdf-drawn-shape, .acrobat-comment-icon, .pdf-direct-text-item, .acrobat-highlight-overlay')) {
          this.activeSelectedAnnot = null;
          this.redrawPageAnnotations(pageNum);
        }
        return;
      }
      if (['highlight', 'strikeout'].includes(this.activeTool)) return;
      if (e.target.closest('.acrobat-comment-card') || e.target.closest('.inline-typewriter-input')) return;

      const pt = getCoords(e);
      startPoint = pt;

      // Acrobat Note pin anywhere on click
      if (this.activeTool === 'note') {
        const existingIcon = e.target.closest('.acrobat-comment-icon, .pdf-pin');
        if (existingIcon) {
          const matched = this.annotations.find(an => {
            if (an.page !== pageNum) return false;
            if (an.type === 'note' && an.point) {
              return Math.hypot((an.point[0] * this.scale) - pt.viewX, (an.point[1] * this.scale) - pt.viewY) < 35;
            }
            if (an.rect) {
              const [rx0, ry0] = this.normalizeRect(an.rect);
              return Math.hypot((rx0 * this.scale) - pt.viewX, (ry0 * this.scale) - pt.viewY) < 35;
            }
            return false;
          });
          if (matched) {
            this.openCommentBox(matched, pt.screenX, pt.screenY, false);
            return;
          }
        }

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
        currentShapeEl.setAttribute('fill', this.getFillColorForStroke(this.penColor, 0.12));
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
        const last = currentStroke[currentStroke.length - 1];
        if (!last || Math.hypot(pt.x - last[0], pt.y - last[1]) >= 1.8) {
          currentStroke.push([pt.x, pt.y]);
          currentShapeEl.setAttribute('d', this.buildSmoothSvgPath(currentStroke, this.scale));
        }
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
        const smoothedStroke = this.smoothStrokeChaikin(currentStroke, 2);
        this.addAnnotation({
          page: pageNum,
          type: 'ink',
          strokes: [smoothedStroke],
          color: this.penColor || '#ef4444',
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
            rect: [minX, minY, maxX, maxY],
            color: this.penColor || '#ef4444'
          });
        }
      } else if (this.activeTool === 'arrow') {
        if (Math.hypot(pt.x - startPoint.x, pt.y - startPoint.y) > 10) {
          this.addAnnotation({
            page: pageNum,
            type: 'arrow',
            p1: [startPoint.x, startPoint.y],
            p2: [pt.x, pt.y],
            color: this.penColor || '#ef4444'
          });
        }
      }

      this.redrawPageAnnotations(pageNum);
    };

    pageWrap.addEventListener('mousedown', onStart);
    pageWrap.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onEnd);
    pageWrap.addEventListener('mouseleave', () => this.hideTooltip());

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
    this.activeEditingCommentAnnot = annot;
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

      <!-- Color selector for this highlight/comment -->
      <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px; padding-bottom:6px; border-bottom:1px solid var(--border);">
        <span style="font-size:0.74rem; color:var(--text-muted); font-weight:600;">Barva označení:</span>
        <div style="display:flex; gap:6px; align-items:center;">
          ${this.highlightColors.map(c => `
            <button type="button" class="comment-box-color-btn" 
              data-color="${c.hex}" 
              style="width:18px; height:18px; border-radius:50%; background:${c.hex}; border: 2px solid ${(annot.color || '#ef4444') === c.hex ? 'var(--text-main)' : 'transparent'}; cursor:pointer; padding:0; transition:transform 0.1s ease; ${(annot.color || '#ef4444') === c.hex ? 'transform:scale(1.25);' : ''}"
              onclick="PDFStudio.changeCommentHighlightColor('${c.hex}')"
              title="${c.name}"></button>
          `).join('')}
        </div>
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
          <input type="checkbox" id="acrobat-deduct-check">
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

    const origContent = annot ? (annot.content || '') : '';
    const origColor = annot ? (annot.color || '#ef4444') : '#ef4444';

    const textarea = card.querySelector('#acrobat-comment-textarea');
    textarea.focus();
    textarea.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        const postBtn = card.querySelector('#acrobat-post-btn');
        if (postBtn) postBtn.click();
      }
    });

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
      const lastAction = this.historyStack.length > 0 ? this.historyStack[this.historyStack.length - 1] : null;
      if (lastAction && lastAction.type === 'add' && lastAction.annot && lastAction.annot.id === annot.id) {
        // Atomic creation: update comment and color on the initial add event so Undo/Redo is 1 single step!
        lastAction.annot.content = val;
        lastAction.annot.color = annot.color;
      } else if (!isNew && (origContent !== val || origColor !== annot.color)) {
        this.pushHistoryAction({
          type: 'edit',
          annotId: annot.id,
          oldContent: origContent,
          newContent: val,
          oldColor: origColor,
          newColor: annot.color,
          page: annot.page
        });
      }
      annot.content = val;
      annot.author = author;

      if (isNew) {
        if (!this.annotations.includes(annot)) {
          this.addAnnotation(annot);
        } else {
          this.redrawPageAnnotations(annot.page);
          this.syncAnnotationsWithBackend();
        }
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
    // Clean up empty newly created note if cancelled without content
    if (this._isCreatingNewNote && this.activeEditingCommentAnnot && !this.activeEditingCommentAnnot.content) {
      const idx = this.annotations.indexOf(this.activeEditingCommentAnnot);
      if (idx !== -1) {
        this.annotations.splice(idx, 1);
      }
    }
    this._isCreatingNewNote = false;
    this.activeSelectedAnnot = null;
    this.activeEditingCommentAnnot = null;
    if (this.container) {
      const pages = this.container.querySelectorAll('.pdf-page-container');
      pages.forEach(p => this.redrawPageAnnotations(parseInt(p.dataset.pageNumber)));
    }
  },

  deleteAnnotationObj(idx) {
    this.hideTooltip();
    if (idx >= 0 && idx < this.annotations.length) {
      const removed = this.annotations.splice(idx, 1)[0];
      this.pushHistoryAction({
        type: 'delete',
        annot: JSON.parse(JSON.stringify(removed)),
        index: idx,
        page: removed.page
      });
      this.activeSelectedAnnot = null;
      this.redrawPageAnnotations(removed.page);
      this.syncAnnotationsWithBackend();
    }
    this.closeCommentBox();
  },

  deleteSelectedAnnotation() {
    this.hideTooltip();
    if (!this.activeSelectedAnnot) return;
    const idx = this.annotations.indexOf(this.activeSelectedAnnot);
    if (idx !== -1) {
      this.deleteAnnotationObj(idx);
      if (window.App && window.App.showToast) {
        window.App.showToast("Anotace byla smazána.");
      }
    }
  },

  bindShapeInteractions(el, a, pageNumInt) {
    el.addEventListener('mousedown', (e) => {
      if (this.activeTool !== 'pan') return;
      e.stopPropagation();
      e.preventDefault();
      this.selectAnnotation(a, pageNumInt, e);
    });
  },

  selectAnnotation(a, pageNumInt, downEvent) {
    this.activeSelectedAnnot = a;
    this.redrawPageAnnotations(pageNumInt);

    if (!downEvent) return;

    // Highlights must not be moved! Open comment card directly to edit text, color and deduction
    if (a.type === 'highlight') {
      this.openCommentBox(a, downEvent.clientX, downEvent.clientY, false);
      return;
    }

    const startX = downEvent.clientX;
    const startY = downEvent.clientY;
    let hasMoved = false;

    // Snapshot original coordinates
    const origRect = a.rect ? [...a.rect] : null;
    const origRects = a.rects ? a.rects.map(r => [...r]) : null;
    const origP1 = a.p1 ? [...a.p1] : null;
    const origP2 = a.p2 ? [...a.p2] : null;
    const origPoint = a.point ? [...a.point] : null;
    const origStrokes = a.strokes ? a.strokes.map(st => st.map(pt => [...pt])) : null;

    const onWindowMove = (ev) => {
      const dx = (ev.clientX - startX) / this.scale;
      const dy = (ev.clientY - startY) / this.scale;

      if (!hasMoved && Math.hypot(ev.clientX - startX, ev.clientY - startY) > 3) {
        hasMoved = true;
      }

      if (hasMoved) {
        if (origRect) {
          a.rect = [origRect[0] + dx, origRect[1] + dy, origRect[2] + dx, origRect[3] + dy];
        }
        if (origRects) {
          a.rects = origRects.map(r => [r[0] + dx, r[1] + dy, r[2] + dx, r[3] + dy]);
        }
        if (origP1 && origP2) {
          a.p1 = [origP1[0] + dx, origP1[1] + dy];
          a.p2 = [origP2[0] + dx, origP2[1] + dy];
        }
        if (origPoint) {
          a.point = [origPoint[0] + dx, origPoint[1] + dy];
        }
        if (origStrokes) {
          a.strokes = origStrokes.map(st => st.map(pt => [pt[0] + dx, pt[1] + dy]));
        }
        this.redrawPageAnnotations(pageNumInt);
      }
    };

    const onWindowUp = () => {
      window.removeEventListener('mousemove', onWindowMove);
      window.removeEventListener('mouseup', onWindowUp);
      if (hasMoved) {
        const origCoords = {
          rect: origRect,
          rects: origRects,
          p1: origP1,
          p2: origP2,
          point: origPoint,
          strokes: origStrokes
        };
        const newCoords = {
          rect: a.rect ? [...a.rect] : null,
          rects: a.rects ? a.rects.map(r => [...r]) : null,
          p1: a.p1 ? [...a.p1] : null,
          p2: a.p2 ? [...a.p2] : null,
          point: a.point ? [...a.point] : null,
          strokes: a.strokes ? a.strokes.map(st => st.map(pt => [...pt])) : null
        };
        this.pushHistoryAction({
          type: 'move',
          annotId: a.id,
          oldCoords: origCoords,
          newCoords: newCoords,
          page: a.page
        });
        this.syncAnnotationsWithBackend();
      } else {
        // Simple click without dragging opens comment box to edit!
        this.openCommentBox(a, downEvent.clientX, downEvent.clientY, false);
      }
    };

    window.addEventListener('mousemove', onWindowMove);
    window.addEventListener('mouseup', onWindowUp);
  },

  addAnnotation(annot, recordHistory = true) {
    if (!annot) return;
    if (!this.annotations.includes(annot)) {
      if (annot.id && this.annotations.some(existing => existing.id === annot.id)) {
        return;
      }
      if (!annot.id) {
        annot.id = `annot_${this.protocolId || 0}_${Date.now()}_${Math.floor(Math.random() * 1000)}`;
      }
      this.annotations.push(annot);
      if (recordHistory) {
        this.pushHistoryAction({
          type: 'add',
          annot: JSON.parse(JSON.stringify(annot)),
          page: annot.page
        });
      }
    }
    this.activeSelectedAnnot = null;
    this.redrawPageAnnotations(annot.page);
    this.syncAnnotationsWithBackend();
  },

  pushHistoryAction(action) {
    this.historyStack.push(action);
    this.redoStack = [];
    this.updateUndoRedoButtons();
  },

  updateUndoRedoButtons() {
    const undoBtn = document.getElementById('btn-undo-action');
    const redoBtn = document.getElementById('btn-redo-action');
    if (undoBtn) undoBtn.disabled = this.historyStack.length === 0;
    if (redoBtn) redoBtn.disabled = this.redoStack.length === 0;
  },

  undo() {
    this.hideTooltip();
    if (this.historyStack.length === 0) return;
    const action = this.historyStack.pop();

    if (action.type === 'add') {
      const idx = this.annotations.findIndex(x => x.id === action.annot.id);
      if (idx !== -1) {
        this.annotations.splice(idx, 1);
      }
      this.redoStack.push(action);
      this.redrawPageAnnotations(action.page);
      this.syncAnnotationsWithBackend();
    } else if (action.type === 'delete') {
      const insertIdx = Math.min(action.index !== undefined ? action.index : this.annotations.length, this.annotations.length);
      this.annotations.splice(insertIdx, 0, action.annot);
      this.redoStack.push(action);
      this.redrawPageAnnotations(action.page);
      this.syncAnnotationsWithBackend();
    } else if (action.type === 'move') {
      const annot = this.annotations.find(x => x.id === action.annotId);
      if (annot && action.oldCoords) {
        if (action.oldCoords.rect) annot.rect = [...action.oldCoords.rect];
        if (action.oldCoords.rects) annot.rects = action.oldCoords.rects.map(r => [...r]);
        if (action.oldCoords.point) annot.point = [...action.oldCoords.point];
        if (action.oldCoords.p1) annot.p1 = [...action.oldCoords.p1];
        if (action.oldCoords.p2) annot.p2 = [...action.oldCoords.p2];
        if (action.oldCoords.strokes) annot.strokes = action.oldCoords.strokes.map(st => st.map(pt => [...pt]));
      }
      this.redoStack.push(action);
      this.redrawPageAnnotations(action.page);
      this.syncAnnotationsWithBackend();
    } else if (action.type === 'edit') {
      const annot = this.annotations.find(x => x.id === action.annotId);
      if (annot) {
        annot.content = action.oldContent;
        annot.color = action.oldColor;
      }
      this.redoStack.push(action);
      this.redrawPageAnnotations(action.page);
      this.syncAnnotationsWithBackend();
    }

    this.activeSelectedAnnot = null;
    this.updateUndoRedoButtons();
  },

  redo() {
    this.hideTooltip();
    if (this.redoStack.length === 0) return;
    const action = this.redoStack.pop();

    if (action.type === 'add') {
      this.annotations.push(action.annot);
      this.historyStack.push(action);
      this.redrawPageAnnotations(action.page);
      this.syncAnnotationsWithBackend();
    } else if (action.type === 'delete') {
      const idx = this.annotations.findIndex(x => x.id === action.annot.id);
      if (idx !== -1) {
        this.annotations.splice(idx, 1);
      }
      this.historyStack.push(action);
      this.redrawPageAnnotations(action.page);
      this.syncAnnotationsWithBackend();
    } else if (action.type === 'move') {
      const annot = this.annotations.find(x => x.id === action.annotId);
      if (annot && action.newCoords) {
        if (action.newCoords.rect) annot.rect = [...action.newCoords.rect];
        if (action.newCoords.rects) annot.rects = action.newCoords.rects.map(r => [...r]);
        if (action.newCoords.point) annot.point = [...action.newCoords.point];
        if (action.newCoords.p1) annot.p1 = [...action.newCoords.p1];
        if (action.newCoords.p2) annot.newCoords = [...action.newCoords.p2];
        if (action.newCoords.strokes) annot.strokes = action.newCoords.strokes.map(st => st.map(pt => [...pt]));
      }
      this.historyStack.push(action);
      this.redrawPageAnnotations(action.page);
      this.syncAnnotationsWithBackend();
    } else if (action.type === 'edit') {
      const annot = this.annotations.find(x => x.id === action.annotId);
      if (annot) {
        annot.content = action.newContent;
        annot.color = action.newColor;
      }
      this.historyStack.push(action);
      this.redrawPageAnnotations(action.page);
      this.syncAnnotationsWithBackend();
    }

    this.activeSelectedAnnot = null;
    this.updateUndoRedoButtons();
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
        textItem.className = 'pdf-direct-text-item pdf-drawn-shape';
        textItem.style.position = 'absolute';
        textItem.style.left = `${a.point[0] * this.scale}px`;
        textItem.style.top = `${(a.point[1] - 12) * this.scale}px`;
        textItem.style.color = a.color || '#ef4444';
        textItem.style.fontFamily = 'Helvetica, Arial, sans-serif';
        textItem.style.fontSize = `${(a.fontsize || 14) * this.scale}px`;
        textItem.textContent = a.content;
        this.bindShapeInteractions(textItem, a, pageNumInt);
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
        const strokeColor = this.formatColor(a.color) || '#ef4444';
        a.strokes.forEach(stroke => {
          if (!stroke || stroke.length === 0) return;
          const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
          path.setAttribute('d', this.buildSmoothSvgPath(stroke, this.scale));
          path.setAttribute('stroke', strokeColor);
          path.setAttribute('stroke-width', Math.max(4, (a.width || 2) * this.scale));
          path.setAttribute('fill', 'none');
          path.setAttribute('stroke-linecap', 'round');
          path.setAttribute('stroke-linejoin', 'round');
          path.setAttribute('class', 'pdf-drawn-shape pdf-shape-ink');
          path.style.pointerEvents = 'stroke';
          path.style.cursor = 'pointer';
          this.bindShapeInteractions(path, a, pageNumInt);
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
            if (this.activeTool === 'pan') {
              e.stopPropagation();
              this.selectAnnotation(a, pageNumInt, e);
            } else {
              e.stopPropagation();
              this.openCommentBox(a, e.clientX, e.clientY, false);
            }
          });
          pageWrap.appendChild(hDiv);
        });

        // Red circular Acrobat comment icon [⊖]
        const mainRect = this.normalizeRect(a.rect || (a.rects && a.rects[0]));
        if (mainRect && (mainRect[2] > mainRect[0])) {
          const [rx0, ry0] = mainRect;
          const icon = document.createElement('div');
          icon.className = 'acrobat-comment-icon pdf-drawn-shape';
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
          this.bindShapeInteractions(icon, a, pageNumInt);
          pageWrap.appendChild(icon);
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
        line.setAttribute('stroke', a.color || '#ef4444');
        line.setAttribute('stroke-width', Math.max(2, 2.5 * this.scale));
        line.setAttribute('stroke-linecap', 'round');
        line.setAttribute('class', 'pdf-drawn-shape pdf-shape-strikeout');
        line.style.pointerEvents = 'stroke';
        line.style.cursor = 'pointer';

        line.addEventListener('mouseenter', (e) => {
          if (a.content) this.showTooltip(a.author, a.content, e.clientX, e.clientY);
        });
        line.addEventListener('mouseleave', () => this.hideTooltip());
        line.addEventListener('click', (e) => {
          if (this.activeTool === 'pan') {
            e.stopPropagation();
            this.selectAnnotation(a, pageNumInt, e);
          } else {
            e.stopPropagation();
            this.openCommentBox(a, e.clientX, e.clientY, false);
          }
        });
        this.bindShapeInteractions(line, a, pageNumInt);
        svg.appendChild(line);

        const icon = document.createElement('div');
        icon.className = 'acrobat-comment-icon pdf-drawn-shape';
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
        this.bindShapeInteractions(icon, a, pageNumInt);
        pageWrap.appendChild(icon);
      }

      // 5. Rect (Bounding box)
      else if (a.type === 'rect' && a.rect) {
        const [x0, y0, x1, y1] = this.normalizeRect(a.rect);
        const rectColor = a.color || '#ef4444';
        const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        rect.setAttribute('x', x0 * this.scale);
        rect.setAttribute('y', y0 * this.scale);
        rect.setAttribute('width', Math.max(4, (x1 - x0) * this.scale));
        rect.setAttribute('height', Math.max(4, (y1 - y0) * this.scale));
        rect.setAttribute('fill', this.getFillColorForStroke(rectColor, 0.15));
        rect.setAttribute('stroke', rectColor);
        rect.setAttribute('stroke-width', 2);
        rect.setAttribute('class', 'pdf-drawn-shape pdf-shape-rect');
        rect.style.pointerEvents = 'auto';
        rect.style.cursor = 'pointer';
        this.bindShapeInteractions(rect, a, pageNumInt);
        svg.appendChild(rect);
      }

      // 6. Arrow with real arrowhead polygon
      else if (a.type === 'arrow' && a.p1 && a.p2) {
        const arrowGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        arrowGroup.setAttribute('class', 'pdf-drawn-shape pdf-shape-arrow');
        arrowGroup.style.pointerEvents = 'auto';
        arrowGroup.style.cursor = 'pointer';
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        const arrowColor = a.color || '#ef4444';
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
        this.bindShapeInteractions(arrowGroup, a, pageNumInt);
        svg.appendChild(arrowGroup);
      }

      // 7. Sticky Note Pin (Acrobat [⊖] circular pin)
      else if (a.type === 'note' && a.point) {
        const pin = document.createElement('div');
        pin.className = 'acrobat-comment-icon pdf-drawn-shape';
        pin.style.left = `${(a.point[0] * this.scale) - 9}px`;
        pin.style.top = `${(a.point[1] * this.scale) - 9}px`;
        pin.title = a.content || 'Komentář';
        pin.addEventListener('mouseenter', (e) => {
          if (a.content) this.showTooltip(a.author, a.content, e.clientX, e.clientY);
        });
        pin.addEventListener('mouseleave', () => this.hideTooltip());
        pin.addEventListener('click', (e) => {
          if (this.activeTool === 'pan') {
            e.stopPropagation();
            this.selectAnnotation(a, pageNumInt, e);
          } else {
            e.stopPropagation();
            this.openCommentBox(a, e.clientX, e.clientY, false);
          }
        });
        this.bindShapeInteractions(pin, a, pageNumInt);
        pageWrap.appendChild(pin);
      }

      // Universal Active Acrobat Selection Box for selected annotation
      if (isActive) {
        let bBox = null;
        if (a.rect) {
          bBox = this.normalizeRect(a.rect);
        } else if (a.p1 && a.p2) {
          bBox = [
            Math.min(a.p1[0], a.p2[0]) - 6,
            Math.min(a.p1[1], a.p2[1]) - 6,
            Math.max(a.p1[0], a.p2[0]) + 6,
            Math.max(a.p1[1], a.p2[1]) + 6
          ];
        } else if (a.point) {
          bBox = [a.point[0] - 14, a.point[1] - 14, a.point[0] + 14, a.point[1] + 14];
        } else if (a.strokes && a.strokes.length > 0) {
          let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
          a.strokes.forEach(st => st.forEach(([x, y]) => {
            minX = Math.min(minX, x);
            minY = Math.min(minY, y);
            maxX = Math.max(maxX, x);
            maxY = Math.max(maxY, y);
          }));
          if (minX !== Infinity) {
            bBox = [minX - 4, minY - 4, maxX + 4, maxY + 4];
          }
        } else if (a.rects && a.rects.length > 0) {
          bBox = this.normalizeRect(a.rects[0]);
        }

        if (bBox && bBox[2] > bBox[0] && bBox[3] > bBox[1]) {
          const [bx0, by0, bx1, by1] = bBox;
          const activeBox = document.createElement('div');
          activeBox.className = 'acrobat-active-selection-box';
          activeBox.style.left = `${(bx0 * this.scale) - 3}px`;
          activeBox.style.top = `${(by0 * this.scale) - 3}px`;
          activeBox.style.width = `${((bx1 - bx0) * this.scale) + 6}px`;
          activeBox.style.height = `${((by1 - by0) * this.scale) + 6}px`;

          activeBox.innerHTML = `
            <div class="acrobat-selection-handle handle-nw"></div>
            <div class="acrobat-selection-handle handle-ne"></div>
            <div class="acrobat-selection-handle handle-sw"></div>
            <div class="acrobat-selection-handle handle-se"></div>
            <button type="button" class="acrobat-selection-trash-btn" title="Smazat anotaci (Delete / Backspace)">🗑</button>
          `;

          const trashBtn = activeBox.querySelector('.acrobat-selection-trash-btn');
          if (trashBtn) {
            trashBtn.addEventListener('mousedown', (e) => e.stopPropagation());
            trashBtn.addEventListener('click', (e) => {
              e.stopPropagation();
              e.preventDefault();
              this.deleteSelectedAnnotation();
            });
          }

          // Allow dragging the bounding box directly in pan tool
          activeBox.addEventListener('mousedown', (e) => {
            if (e.target.closest('button')) return;
            e.stopPropagation();
            e.preventDefault();
            this.selectAnnotation(a, pageNumInt, e);
          });

          pageWrap.appendChild(activeBox);
        }
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
