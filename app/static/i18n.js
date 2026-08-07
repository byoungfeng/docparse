(() => {
  const STORAGE_KEY = "docparse-lang";

  const dicts = {
    "zh-CN": {
      kicker: "文档 → Markdown 转换台",
      colIn: "01 · 输入",
      colOut: "02 · 输出",
      dropTitle: "拖入文件",
      dropHint: "或点击浏览 · PDF / Office / EPUB / CSV",
      dropAria: "选择或拖入文件",
      modeAsync: "异步",
      modeAsyncHint: "大文件 / OCR",
      modeSync: "同步",
      modeSyncHint: "小文件即时返回",
      cta: "开始转换",
      copy: "复制",
      download: "下载 .md",
      previewEmpty: "转换结果将显示在这里",
      footOcr: "文本页直抽 / 扫描页 OCR",
      langAria: "切换语言",
      healthUnknown: "服务状态",
      healthOk: "服务正常",
      healthBad: "引擎不完整",
      healthDown: "无法连接",
      idle: "空闲",
      fileSelected: "已选择文件",
      unsupported: "暂不支持格式：{ext}",
      syncRunning: "同步解析中…",
      syncDone: "完成（同步）",
      submitted: "已提交，排队中…",
      jobStatus: "任务 {id}… {status}",
      queued: "排队中… ({id})",
      running: "解析中… ({id})",
      asyncDone: "完成（异步）",
      failed: "失败：{msg}",
      error: "错误：{msg}",
      copied: "已复制",
      processing: "处理中…",
      emptyResult: "(空结果)",
    },
    en: {
      kicker: "Documents → Markdown workbench",
      colIn: "01 · Input",
      colOut: "02 · Output",
      dropTitle: "Drop a file",
      dropHint: "or click to browse · PDF / Office / EPUB / CSV",
      dropAria: "Select or drop a file",
      modeAsync: "Async",
      modeAsyncHint: "Large files / OCR",
      modeSync: "Sync",
      modeSyncHint: "Instant for small files",
      cta: "Convert",
      copy: "Copy",
      download: "Download .md",
      previewEmpty: "Converted Markdown will appear here",
      footOcr: "native text extraction / OCR for scanned pages",
      langAria: "Switch language",
      healthUnknown: "Service status",
      healthOk: "Healthy",
      healthBad: "Engines incomplete",
      healthDown: "Unreachable",
      idle: "Idle",
      fileSelected: "File selected",
      unsupported: "Unsupported format: {ext}",
      syncRunning: "Parsing (sync)…",
      syncDone: "Done (sync)",
      submitted: "Submitted, queued…",
      jobStatus: "Job {id}… {status}",
      queued: "Queued… ({id})",
      running: "Parsing… ({id})",
      asyncDone: "Done (async)",
      failed: "Failed: {msg}",
      error: "Error: {msg}",
      copied: "Copied",
      processing: "Processing…",
      emptyResult: "(empty result)",
    },
  };

  let lang = detect();

  function detect() {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved && dicts[saved]) return saved;
    } catch { /* storage unavailable */ }
    return (navigator.language || "").toLowerCase().startsWith("zh") ? "zh-CN" : "en";
  }

  function t(key, vars) {
    let s = (dicts[lang] && dicts[lang][key]) ?? dicts["zh-CN"][key] ?? key;
    if (vars) {
      for (const [k, v] of Object.entries(vars)) {
        s = s.replaceAll(`{${k}}`, String(v));
      }
    }
    return s;
  }

  function apply(root = document) {
    root.querySelectorAll("[data-i18n]").forEach((el) => {
      el.textContent = t(el.dataset.i18n);
    });
    root.querySelectorAll("[data-i18n-title]").forEach((el) => {
      el.title = t(el.dataset.i18nTitle);
    });
    root.querySelectorAll("[data-i18n-aria]").forEach((el) => {
      el.setAttribute("aria-label", t(el.dataset.i18nAria));
    });
    document.documentElement.lang = lang;
  }

  function setLang(next) {
    if (!dicts[next] || next === lang) return;
    lang = next;
    try { localStorage.setItem(STORAGE_KEY, next); } catch { /* ignore */ }
    apply();
    document.dispatchEvent(new CustomEvent("docparse:langchange", { detail: { lang } }));
  }

  window.I18N = {
    t,
    apply,
    setLang,
    get lang() { return lang; },
    toggle() { setLang(lang === "zh-CN" ? "en" : "zh-CN"); },
  };

  apply();
})();
