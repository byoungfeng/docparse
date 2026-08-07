# DocParse

统一文档 → Markdown API。底层使用 Firecrawl 开源库：

- [pdf-inspector](https://github.com/firecrawl/pdf-inspector)（MIT）— PDF 分类与文本抽取
- [anydoc](https://github.com/firecrawl/anydoc)（MIT）— Office / EPUB / CSV 等 → Markdown
- **RapidOCR**（可选）— 扫描页本地 OCR（中文友好）

## 快速开始

```powershell
cd H:\work\codes\docparse
.\.venv\Scripts\activate
pip install -e ".[ocr,dev]"
uvicorn app.main:app --reload --port 8787
```

打开 http://127.0.0.1:8787/ 使用网页上传；API 文档见 http://127.0.0.1:8787/docs

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查（含 OCR 是否可用） |
| POST | `/v1/parse` | 同步解析（小文件） |
| POST | `/v1/parse/async` | 异步提交，返回 `job_id` |
| GET | `/v1/jobs/{job_id}` | 查询任务状态 / 结果 |
| POST | `/v1/detect` | 仅检测 PDF 类型（是否需 OCR） |

### 同步（小文件）

```powershell
curl.exe -F "file=@report.docx" http://127.0.0.1:8787/v1/parse -o out.json
```

### 异步（大书 / OCR）

```powershell
# 1) 提交
curl.exe -F "file=@H:/电子书/穷查理宝典.pdf" http://127.0.0.1:8787/v1/parse/async -o job.json
# 打开 job.json 看 job_id

# 2) 轮询（把 JOB_ID 换成实际值）
curl.exe http://127.0.0.1:8787/v1/jobs/JOB_ID -o status.json
```

`status` 为 `succeeded` 时，`result.markdown` 即为正文。

## OCR

| 配置 | 含义 |
|------|------|
| `DOCPARSE_OCR_PROVIDER=rapid` | 默认；本地 RapidOCR |
| `DOCPARSE_OCR_PROVIDER=stub` | 只提示需 OCR 的页，不识别 |
| `DOCPARSE_OCR_PROVIDER=none` | 跳过 OCR |
| `DOCPARSE_OCR_MAX_PAGES=50` | 单次最多 OCR 页数 |
| `DOCPARSE_OCR_SCALE=2.0` | 渲染清晰度 |
| `DOCPARSE_JOB_WORKERS=1` | 并行任务数 |
| `DOCPARSE_JOBS_DIR=data/jobs` | 任务落盘目录 |

```powershell
pip install -e ".[ocr]"
copy .env.example .env
```

## Docker（私有化部署）

```powershell
# 构建镜像（含 OCR 全部依赖，约 1GB）
docker build -t docparse .

# 运行
docker run -d -p 8787:8787 -v docparse-data:/data --name docparse docparse

# 或用 compose
docker compose up -d --build
```

打开 http://127.0.0.1:8787/ 。任务数据持久化在 `docparse-data` 卷；配置通过环境变量覆盖（见 `docker-compose.yml`）。

## 架构

```
上传 → /v1/parse        → 立即返回 Markdown
     → /v1/parse/async  → 落盘排队 → 线程池解析 → GET /v1/jobs/:id
              ├─ PDF  → pdf-inspector →（扫描页）RapidOCR
              └─ 其它 → anydoc
```

## 协议与致谢

本项目代码 MIT。上游 pdf-inspector / anydoc 为 MIT，见 `NOTICE`。

## 下一步

- [x] 接入真实 OCR（RapidOCR）
- [x] 异步任务队列（大文件 / OCR）
- [x] 私有化 Docker 镜像
- [ ] API Key + 按页计费
