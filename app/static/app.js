(() => {
  const $ = (id) => document.getElementById(id);
  const t = (key, vars) => window.I18N.t(key, vars);

  const drop = $("drop");
  const fileInput = $("fileInput");
  const fileName = $("fileName");
  const submit = $("submit");
  const formError = $("formError");
  const statusline = document.querySelector(".statusline");
  const statusText = $("statusText");
  const metaBox = $("metaBox");
  const preview = $("preview");
  const copyBtn = $("copyBtn");
  const downloadBtn = $("downloadBtn");
  const health = $("health");
  const langToggle = $("langToggle");

  let selectedFile = null;
  let lastMarkdown = "";
  let lastFilename = "output.md";
  let pollTimer = null;
  let busy = false;
  let hasResult = false;
  let lastStatus = { key: "idle", vars: null };
  let lastError = null;
  let lastHealthKey = "healthUnknown";

  const ACCEPT = new Set([
    ".pdf", ".doc", ".docx", ".docm",
    ".ppt", ".pps", ".pot", ".pptx", ".pptm", ".ppsx", ".ppsm",
    ".xls", ".xlsx", ".xlsm", ".xlsb",
    ".odt", ".ods", ".odp", ".rtf", ".epub", ".csv",
  ]);

  function currentMode() {
    const el = document.querySelector('input[name="mode"]:checked');
    return el ? el.value : "async";
  }

  function setStatus(key, kind, vars) {
    lastStatus = { key, vars };
    statusText.textContent = t(key, vars);
    statusline.className = "statusline" + (kind ? ` ${kind}` : "");
  }

  function setLoading(loading) {
    busy = loading;
    submit.classList.toggle("loading", loading);
    submit.disabled = loading || !selectedFile;
  }

  function renderError() {
    if (!lastError) {
      formError.hidden = true;
      formError.textContent = "";
      return;
    }
    formError.hidden = false;
    formError.textContent = lastError.key
      ? t(lastError.key, lastError.vars)
      : lastError.raw;
  }

  function setErrorKey(key, vars) {
    lastError = key ? { key, vars } : null;
    renderError();
  }

  function setErrorRaw(raw) {
    lastError = raw ? { raw: String(raw) } : null;
    renderError();
  }

  function extOf(name) {
    const i = name.lastIndexOf(".");
    return i >= 0 ? name.slice(i).toLowerCase() : "";
  }

  function pickFile(file) {
    if (!file) return;
    const ext = extOf(file.name);
    if (ext && !ACCEPT.has(ext)) {
      setErrorKey("unsupported", { ext });
      return;
    }
    selectedFile = file;
    fileName.textContent = `${file.name}  ·  ${(file.size / 1024).toFixed(1)} KB`;
    fileName.hidden = false;
    submit.disabled = false;
    setErrorRaw(null);
    setStatus("fileSelected", "");
  }

  function showResult(payload, sourceName) {
    const md = payload.markdown || "";
    lastMarkdown = md;
    hasResult = true;
    lastFilename = (sourceName || "output").replace(/\.[^.]+$/, "") + ".md";
    preview.textContent = md || t("emptyResult");
    preview.classList.add("has-content");
    copyBtn.disabled = !md;
    downloadBtn.disabled = !md;

    const meta = payload.meta || {};
    metaBox.hidden = false;
    metaBox.textContent = JSON.stringify(
      {
        engine: meta.engine,
        pdf_type: meta.pdf_type,
        page_count: meta.page_count,
        ocr_applied: meta.ocr_applied,
        pages_needing_ocr: meta.pages_needing_ocr,
        warnings: meta.warnings,
      },
      null,
      2
    );
  }

  async function checkHealth() {
    try {
      const res = await fetch("/health");
      const data = await res.json();
      const ok =
        data.status === "ok" &&
        data.engines &&
        data.engines["pdf-inspector"] &&
        data.engines.anydoc;
      lastHealthKey = ok ? "healthOk" : "healthBad";
      health.className = "dot " + (ok ? "dot-ok" : "dot-bad");
    } catch {
      lastHealthKey = "healthDown";
      health.className = "dot dot-bad";
    }
    health.title = t(lastHealthKey);
  }

  function formatDetail(data) {
    if (!data) return "";
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail)) {
      return data.detail.map((d) => d.msg || JSON.stringify(d)).join("; ");
    }
    return data.error || "";
  }

  async function parseSync(file) {
    setStatus("syncRunning", "run");
    const fd = new FormData();
    fd.append("file", file, file.name);
    const res = await fetch("/v1/parse", { method: "POST", body: fd });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(formatDetail(data) || `HTTP ${res.status}`);
    setStatus("syncDone", "ok");
    showResult(data, file.name);
  }

  async function parseAsync(file) {
    setStatus("submitted", "run");
    const fd = new FormData();
    fd.append("file", file, file.name);
    const res = await fetch("/v1/parse/async", { method: "POST", body: fd });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(formatDetail(data) || `HTTP ${res.status}`);

    const jobId = data.job_id;
    setStatus("jobStatus", "run", { id: jobId.slice(0, 8), status: data.status });
    await pollJob(jobId, file.name);
  }

  function pollJob(jobId, sourceName) {
    return new Promise((resolve, reject) => {
      if (pollTimer) clearInterval(pollTimer);
      const shortId = jobId.slice(0, 8);
      const tick = async () => {
        try {
          const res = await fetch(`/v1/jobs/${jobId}`);
          const data = await res.json().catch(() => ({}));
          if (!res.ok) throw new Error(formatDetail(data) || `HTTP ${res.status}`);

          if (data.status === "queued") {
            setStatus("queued", "run", { id: shortId });
          } else if (data.status === "running") {
            setStatus("running", "run", { id: shortId });
          } else if (data.status === "succeeded") {
            clearInterval(pollTimer);
            pollTimer = null;
            setStatus("asyncDone", "ok");
            showResult(data.result, sourceName);
            resolve(data);
          } else if (data.status === "failed") {
            clearInterval(pollTimer);
            pollTimer = null;
            const msg = data.error || "unknown";
            setStatus("failed", "err", { msg });
            reject(new Error(msg));
          }
        } catch (err) {
          clearInterval(pollTimer);
          pollTimer = null;
          reject(err);
        }
      };
      tick();
      pollTimer = setInterval(tick, 2500);
    });
  }

  function updateLangToggle() {
    langToggle.textContent = window.I18N.lang === "zh-CN" ? "EN" : "中文";
  }

  document.addEventListener("docparse:langchange", () => {
    statusText.textContent = t(lastStatus.key, lastStatus.vars);
    renderError();
    health.title = t(lastHealthKey);
    if (!hasResult) {
      preview.textContent = busy ? t("processing") : t("previewEmpty");
    }
    updateLangToggle();
  });

  langToggle.addEventListener("click", () => window.I18N.toggle());

  drop.addEventListener("click", () => fileInput.click());
  drop.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") fileInput.click();
  });
  fileInput.addEventListener("change", () => pickFile(fileInput.files[0]));

  ;["dragenter", "dragover"].forEach((ev) => {
    drop.addEventListener(ev, (e) => {
      e.preventDefault();
      drop.classList.add("dragover");
    });
  });
  ;["dragleave", "drop"].forEach((ev) => {
    drop.addEventListener(ev, (e) => {
      e.preventDefault();
      drop.classList.remove("dragover");
    });
  });
  drop.addEventListener("drop", (e) => {
    const file = e.dataTransfer.files && e.dataTransfer.files[0];
    pickFile(file);
  });

  submit.addEventListener("click", async () => {
    if (!selectedFile) return;
    setErrorRaw(null);
    copyBtn.disabled = true;
    downloadBtn.disabled = true;
    hasResult = false;
    preview.textContent = t("processing");
    preview.classList.remove("has-content");
    metaBox.hidden = true;
    setLoading(true);
    try {
      if (currentMode() === "sync") await parseSync(selectedFile);
      else await parseAsync(selectedFile);
    } catch (err) {
      const msg = String(err.message || err);
      setStatus("error", "err", { msg });
      setErrorRaw(msg);
    } finally {
      setLoading(false);
    }
  });

  copyBtn.addEventListener("click", async () => {
    if (!lastMarkdown) return;
    await navigator.clipboard.writeText(lastMarkdown);
    setStatus("copied", "ok");
  });

  downloadBtn.addEventListener("click", () => {
    if (!lastMarkdown) return;
    const blob = new Blob([lastMarkdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = lastFilename;
    a.click();
    URL.revokeObjectURL(url);
  });

  updateLangToggle();
  checkHealth();
})();
