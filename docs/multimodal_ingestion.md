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
| Word (.docx) | — | 🔜 Phase 2 |
| PowerPoint (.pptx) | — | 🔜 Phase 2 |
| Excel (.xlsx) | — | 🔜 Phase 2 |
| LaTeX (.tex) | — | 🔜 Phase 2 |
| 图片 (jpg/png/webp) | — | 🔜 Phase 2 |
| 音频 (mp3/wav/m4a) | — | 🔜 Phase 3 |
| 视频 (mp4/mov/mkv) | — | 🔜 Phase 3 |
| 代码 (py/js/ts/go 等) | — | 🔜 Phase 4 |
| 压缩包 (zip/tar.gz) | — | 🔜 Phase 6 |

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

## 导入选项

| 选项 | 说明 |
|------|------|
| 快速解析 | 仅提取文本，跳过 OCR/ASR |
| 精准解析 | 完整解析，含表格/图片/公式 |
| OCR 强制模式 | 对所有页面执行 OCR |
| 多模态增强 | 图片 caption + 视频关键帧 + 音频转写 |
