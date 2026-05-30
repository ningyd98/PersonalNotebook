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
| ASR WER | 音频 ASR 词错率（音视频评测） |
| Keyframe Coverage | 视频关键帧覆盖率（视频评测） |

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
- audio_qa: 音频转写问答

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

## 导出脚本

项目提供两个导出脚本，用于从评测数据和用户反馈中生成微调数据集。

### 1. SFT 微调数据集导出

**脚本：** `scripts/export_sft_dataset.py`

从数据库的 conversations + messages + feedback 表中提取高质量对话对，生成 SFT 微调数据。

```bash
# 导出到 stdout
python scripts/export_sft_dataset.py

# 导出到文件
python scripts/export_sft_dataset.py -o datasets/sft/train.jsonl

# 自定义最低评分阈值（默认 4）
python scripts/export_sft_dataset.py -o datasets/sft/train.jsonl --min-rating 4
```

**参数说明：**

| 参数 | 说明 | 默认值 |
|------|------|--------|
| -o, --output | 输出文件路径 | stdout |
| --min-rating | 最低评分阈值，仅导出 rating >= 此值的对话 | 4 |

**输出格式：** JSONL，每行一条记录

```json
{
  "instruction": "根据知识库回答问题，并给出引用。",
  "input": "问题：Q-learning是什么？\n资料：Q-learning更新公式为 Q(s,a) ← Q(s,a) + α[...]",
  "output": "Q-learning是一种无模型的时序差分控制算法..."
}
```

**数据筛选逻辑：**
1. 查询 Feedback 表中 rating >= min_rating 的记录
2. 关联对应 assistant 消息和同一会话中前一条 user 消息
3. 将 user 问题 + 引用资料作为 input，assistant 回答作为 output

### 2. Reranker 微调数据集导出

**脚本：** `scripts/export_rerank_dataset.py`

导出 query-positive-negative 三元组，用于 Reranker 模型微调。

```bash
python scripts/export_rerank_dataset.py
```

**输出路径：** `datasets/rerank/rerank_train.jsonl`

**输出格式：** JSONL，每行一条记录

```json
{
  "query": "Q-learning 的更新公式是什么？",
  "positive": "Q-learning 更新公式为 Q(s,a) ← Q(s,a) + α[r + γ max_a' Q(s',a') - Q(s,a)]",
  "negative": "蒙特卡洛方法通过完整轨迹估计回报，需要等到回合结束才能更新。"
}
```

### 导出数据集汇总

| 数据集 | 脚本 | 格式 | 用途 |
|--------|------|------|------|
| SFT 训练集 | export_sft_dataset.py | instruction/input/output JSONL | LLM 微调 |
| Rerank 训练集 | export_rerank_dataset.py | query/positive/negative JSONL | Reranker 微调 |
