# 评测体系文档

## 评测指标

| 指标 | 说明 |
|------|------|
| Recall@K | 正确 chunk 是否被召回（K=5,10,20） |
| MRR | 正确 chunk 排名倒数均值 |
| Rerank Accuracy | Reranker 是否将正确 chunk 排前 |
| Answer Faithfulness | 回答是否忠实于证据 |
| Citation Accuracy | 引用是否真实对应 evidence |
| Hallucination Rate | 回答中幻觉信息比例 |
| Refusal Accuracy | 无答案时是否正确拒答 |
| Latency | 平均响应耗时 |
| Cost | 单次问答成本（预留） |

## 测试集格式

```json
{
  "question": "Q-learning 和蒙特卡洛方法有什么区别？",
  "expected_docs": ["rl_notes.md"],
  "expected_chunks": ["chunk_123", "chunk_456"],
  "reference_answer": "Q-learning 是时序差分方法...",
  "answer_type": "comparison"
}
```

## 答案类型

- factoid: 事实查询
- summary: 总结归纳
- comparison: 多文档对比
- reasoning: 技术推理
- no_answer: 无答案拒答
- table_qa: 表格问答
- image_qa: 图片问答
- video_qa: 视频定位问答

## 运行评测

```bash
# 导入评测集
POST /api/eval/datasets

# 添加用例
POST /api/eval/datasets/{id}/cases

# 运行评测
POST /api/eval/run
{
  "dataset_id": "uuid",
  "kb_id": "uuid",
  "top_k": 8,
  "use_rerank": true
}

# 查看报告
GET /api/eval/runs/{id}/report
```
