# 多模态数据接入文档

## 支持的数据源

| 类型 | Connector | 状态 |
|------|-----------|------|
| 文件上传 | UploadConnector | ✅ |
| 本地文件夹 | LocalFolderConnector | ✅ |
| NAS 路径 | NASConnector | ✅ |
| Obsidian Vault | ObsidianConnector | ✅ |
| Git 仓库 | GitConnector | 🔜 Phase 6 |
| URL 网页 | URLConnector | 🔜 Phase 6 |

## 支持的文件类型

| 类型 | Parser | 状态 |
|------|--------|------|
| Markdown (.md) | MarkdownParser | ✅ |
| 纯文本 (.txt) | TXTParser | ✅ |
| PDF (.pdf) | PDFParser | ✅ 基础 |
| Word (.docx) | DOCXParser | ✅ |
| PowerPoint (.pptx) | PPTXParser | ✅ |
| LaTeX (.tex/.latex) | LaTeXParser | ✅ |
| 音频 (mp3/wav/m4a/aac/flac/ogg/wma) | AudioParser | ✅ |
| 视频 (mp4/mov/mkv/avi/webm/flv/wmv) | VideoParser | ✅ |
| Excel (.xlsx) | XLSXParser | 🔜 Phase 4 |
| 图片 (jpg/png/webp) | ImageParser | 🔜 Phase 4 |
| 代码 (py/js/ts/go 等) | CodeParser | 🔜 Phase 4 |
| 压缩包 (zip/tar.gz) | ArchiveParser | 🔜 Phase 6 |

## Parser 插件机制

所有 Parser 实现 `BaseParser` 并通过 `ParserRegistry` 自动注册：

```python
class MyParser(BaseParser):
    supported_mime_types = ["application/my-format"]
    supported_extensions = [".myf"]

    def parse(self, file_path, options=None) -> UnifiedDocument:
        ...
        return udr

# 自动注册
ParserRegistry.register(MyParser())
```

## 统一文档表示 (UDR)

所有 Parser 输出 `UnifiedDocument`，包含标准化的 blocks/assets/relations。

## 解析器详细说明

### DOCXParser

**输入格式：** `.docx` (application/vnd.openxmlformats-officedocument.wordprocessingml.document)

**工具依赖：** `python-docx`（不可用时 fallback 到纯文本占位）

**输出 UDR 结构：**
- blocks: heading（标题层级1~6）、paragraph（正文段落，保留加粗/斜体/删除线等 markdown 样式）、table（含 structured_data）、image（内嵌图片，上传至 MinIO）、annotation（批注）、metadata（脚注）
- assets: 内嵌图片（上传至 MinIO 或 inline 占位）
- metadata: title、author、subject、keywords、created、modified、comment_count、footnote_count、hyperlinks

**切片策略：** 按 block 独立切片，heading/paragraph 短文本合并，table 整体为一个 chunk

### PPTXParser

**输入格式：** `.pptx` (application/vnd.openxmlformats-officedocument.presentationml.presentation)

**工具依赖：** `python-pptx`（不可用时 fallback 到纯文本占位）

**输出 UDR 结构：**
- blocks: paragraph（每页 slide 合并为一个 block，含标题/正文/notes）、table（slide 内表格，含 structured_data）、image（slide 内图片）
- assets: slide 内嵌图片
- metadata: title、slide_count

**切片策略：** 每页 slide 生成一个主 block（含标题+正文+notes），表格和图片作为独立 block

### LaTeXParser

**输入格式：** `.tex`, `.latex` (text/x-latex)

**工具依赖：** 无（纯 Python 正则解析）

**输出 UDR 结构：**
- blocks: heading（\section/\subsection/\subsubsection）、paragraph（普通文本）、equation（equation/align/gather/multline 等环境 + `$$...$$` 展示公式）、annotation（theorem/definition/lemma/proof 等环境）、image（figure 环境，含 caption）、table（table 环境，含 caption）、list（itemize/enumerate/description）
- relations: `\cite{}` 引用关系（cites 类型）
- metadata: title（\title{}）、labels、refs、cites

**切片策略：** 按 block 类型切片，公式环境保留完整，定理/证明整体为一个 chunk

### AudioParser

**输入格式：** `.mp3`, `.wav`, `.m4a`, `.aac`, `.flac`, `.ogg`, `.wma`

**工具依赖：**
- `ffmpeg` — 音频格式转换（转 16kHz mono WAV 用于 ASR）
- `ffprobe` — 获取音频时长
- `faster-whisper` — ASR 语音转写（不可用时跳过转写，生成占位 block）

**输出 UDR 结构：**
- blocks: transcript（按 30~90 秒分段，含 start_time/end_time，预留 speaker 字段）
- assets: 原始音频文件
- metadata: title、duration_seconds、asr_available

**切片策略：** ASR segments 按 30~90 秒合并为 transcript blocks，每个 transcript block 直接作为一个 chunk

**ASR 模型选项：**

| 模型 | 大小 | 说明 |
|------|------|------|
| tiny | ~75MB | 最快，精度低 |
| base | ~150MB | 快速，精度中等 |
| small | ~500MB | 平衡 |
| medium | ~1.5GB | 推荐，中文效果较好 |
| large | ~3GB | 最高精度 |

### VideoParser

**输入格式：** `.mp4`, `.mov`, `.mkv`, `.avi`, `.webm`, `.flv`, `.wmv`

**工具依赖：**
- `ffmpeg` — 音频轨道抽取 + 关键帧抽取
- `ffprobe` — 获取视频时长
- `faster-whisper` — ASR 语音转写
- `PaddleOCR` — 关键帧 OCR（预留，未实现）
- Caption 模型 — 视觉描述生成（预留，未实现）

**输出 UDR 结构：**
- blocks: video_segment（按时间轴合并，包含 transcript/OCR/caption 内容）、transcript（ASR 转写段落）、image（关键帧 OCR/caption）
- assets: 原始视频文件 + 关键帧图片（JPEG）
- metadata: title、duration_seconds、asr_available、keyframe_count、keyframe_interval

**处理流程：**
1. ffmpeg 抽取音频轨道 → 16kHz mono WAV
2. faster-whisper ASR 转写 → transcript blocks（30~90 秒分段）
3. ffmpeg 关键帧抽取（每 N 秒一帧，默认 10 秒）
4. 关键帧 OCR / Caption 生成（预留接口）
5. 按时间轴合并 transcript + OCR + caption → video_segment blocks

**切片策略：** video_segment blocks 按时间轴独立切片

## 导入选项

| 选项 | 参数名 | 默认值 | 说明 |
|------|--------|--------|------|
| 快速解析 | fast_parse | false | 仅提取文本，跳过 OCR/ASR，适用于大批量预览 |
| 精准解析 | fast_parse=false | 默认 | 完整解析，含表格/图片/公式/ASR |
| OCR 强制模式 | ocr_mode="force" | "auto" | 对所有页面/关键帧执行 OCR |
| OCR 跳过 | ocr_mode="skip" | "auto" | 跳过 OCR 处理 |
| 多模态增强 | multimodal_enhance | false | 图片 caption + 视频关键帧 + 音频转写 |
| ASR 模型 | whisper_model | "medium" | faster-whisper 模型选择 |
| ASR 语言 | language | "zh" | 语音识别语言代码 |
| 关键帧间隔 | keyframe_interval | 10 | 视频关键帧抽取间隔（秒） |

**使用示例：**

```bash
# 上传音频并指定 ASR 模型
curl -X POST http://localhost:8000/api/kbs/{kb_id}/documents/upload \
  -F "file=@recording.mp3" \
  -F 'options={"whisper_model":"large","language":"zh"}'

# 上传视频并调整关键帧间隔
curl -X POST http://localhost:8000/api/kbs/{kb_id}/documents/upload \
  -F "file=@lecture.mp4" \
  -F 'options={"keyframe_interval":30,"whisper_model":"medium"}'

# 快速解析模式（跳过 ASR）
curl -X POST http://localhost:8000/api/kbs/{kb_id}/documents/upload \
  -F "file=@presentation.pptx" \
  -F 'options={"fast_parse":true}'
```
