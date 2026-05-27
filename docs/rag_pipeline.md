# RAG Pipeline 文档

## 完整链路

```
用户问题
  → QueryUnderstanding (问题类型分类)
  → EmbeddingService.embed_text() → query_vector
  → QdrantService.search(kb_id, top_k=40)
  → [BM25 search — Phase 4 预留]
  → [Table index search — Phase 4 预留]
  → [Media timeline search — Phase 3 预留]
  → Hit deduplication
  → RerankService.rerank(top_k=8)
  → EvidencePackBuilder.build()
  → GenerationService.generate()
    → RAG prompt 构造
    → model-gateway /model/chat
  → Citation extraction & verification
  → 返回 answer + citations + trace
```

## Query 类型分类

| 类型 | 触发关键词 | 检索路径 |
|------|-----------|---------|
| text | 默认 | vector + BM25 |
| table | 表格/统计/多少 | table index |
| image | 图片/截图/图中 | OCR + caption |
| video | 视频/录像/片段 | transcript + keyframe |
| audio | 录音/音频/说了 | transcript |
| code | 代码/函数/报错 | symbol + vector |
| formula | 公式/方程/推导 | LaTeX + vector |

## RAG Prompt

```
你是个人知识库问答助手。
你必须优先依据提供的知识库证据回答。
如果证据不足，必须明确说明"当前知识库未找到可靠依据"。
不得编造文件名、页码、章节、时间戳、表格范围。
回答中必须给出引用来源，格式为 [证据X]。
如果多个证据存在冲突，请指出冲突。
回答要用中文，结构清晰。
```

## 引用格式

| 来源类型 | 格式 | 示例 |
|---------|------|------|
| 文档 | 文件名 + 页码/章节 | 《笔记.pdf》第12页，第3.2节 |
| PPT | 文件名 + slide | 《课件.pptx》第18页幻灯片 |
| Excel | 文件名 + sheet + range | 《预算.xlsx》Sheet「支出」B2:F30 |
| Markdown | 路径 + 标题 | notes/rl.md > 第3章 > Q-learning |
| 图片 | 文件名 + OCR区域 | 《截图.png》OCR区域 |
| 音频 | 文件名 + 时间段 | 《录音.m4a》00:02:03-00:02:36 |
| 视频 | 文件名 + 时间段 | 《第5讲.mp4》05:20-06:30 |
| 代码 | 文件路径 + 行号 | retrieval.py:L120-L168 |
