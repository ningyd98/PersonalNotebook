import 'package:flutter/material.dart';
import '../api/client.dart';

class ChatScreen extends StatefulWidget {
  final String? kbId;
  const ChatScreen({super.key, this.kbId});
  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _kbCtrl = TextEditingController();
  final _questionCtrl = TextEditingController();
  String _answer = '';
  List<dynamic> _citations = [];
  bool _loading = false;
  String? _error;
  bool? _shouldRefuse;
  String? _refusalReason;
  double? _citationCoverage;

  @override
  void initState() {
    super.initState();
    if (widget.kbId != null && widget.kbId!.isNotEmpty) {
      _kbCtrl.text = widget.kbId!;
    }
  }

  @override
  void dispose() {
    _kbCtrl.dispose();
    _questionCtrl.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final q = _questionCtrl.text.trim();
    final kbId = _kbCtrl.text.trim();
    if (q.isEmpty || kbId.isEmpty) {
      setState(() => _error = '请先填写 KB ID 和问题');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
      _answer = '';
      _citations = [];
      _shouldRefuse = null;
      _refusalReason = null;
      _citationCoverage = null;
    });
    try {
      final resp = await apiClient.post(
        '/api/chat',
        body: {'kb_id': kbId, 'question': q, 'top_k': 8, 'use_rerank': true, 'strict_citation': true},
      );
      setState(() {
        _answer = resp['answer']?.toString() ?? '';
        _citations = (resp['citations'] as List<dynamic>?) ?? [];
        _shouldRefuse = resp['should_refuse'] as bool?;
        _refusalReason = resp['refusal_reason']?.toString();
        final coverage = resp['citation_coverage'];
        _citationCoverage = coverage is num ? coverage.toDouble() : null;
      });
    } catch (e) { setState(() => _error = e.toString()); }
    finally { setState(() => _loading = false); }
  }

  @override
  Widget build(BuildContext context) {
    final isRefusal = _shouldRefuse == true || _answer.contains('未找到可靠依据') || (_refusalReason?.isNotEmpty ?? false);
    return Scaffold(
      appBar: AppBar(title: const Text('问答')),
      body: Column(children: [
        Padding(padding: const EdgeInsets.all(12), child: Row(children: [
          Expanded(child: TextField(controller: _kbCtrl, decoration: const InputDecoration(labelText: '知识库 ID', border: OutlineInputBorder(), isDense: true))),
        ])),
        Expanded(child: ListView(padding: const EdgeInsets.all(12), children: [
          if (_answer.isNotEmpty) ...[
            if (isRefusal)
              Container(
                padding: const EdgeInsets.all(12),
                margin: const EdgeInsets.only(bottom: 12),
                decoration: BoxDecoration(color: Colors.orange.shade50, borderRadius: BorderRadius.circular(8), border: Border.all(color: Colors.orange.shade200)),
                child: Text(
                  '低置信拒答：${_refusalReason ?? '知识库中未找到足够的可靠证据'}',
                  style: const TextStyle(color: Colors.deepOrange),
                ),
              ),
            if (_citationCoverage != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Text('Citation coverage: ${(_citationCoverage! * 100).toStringAsFixed(0)}%'),
              ),
            Card(child: Padding(padding: const EdgeInsets.all(12), child: Text(_answer, style: const TextStyle(fontSize: 15)))),
            if (_citations.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 8), child: Text('引用 (${_citations.length})', style: const TextStyle(fontWeight: FontWeight.w600))),
            ..._citations.map((c) => _CitationCard(citation: c as Map)),
          ],
          if (_error != null) Text(_error!, style: const TextStyle(color: Colors.red)),
          if (_loading) const Center(child: CircularProgressIndicator()),
        ])),
        Padding(padding: const EdgeInsets.all(12), child: Row(children: [
          Expanded(child: TextField(controller: _questionCtrl, decoration: const InputDecoration(hintText: '输入问题...', border: OutlineInputBorder()))),
          const SizedBox(width: 8),
          FilledButton(onPressed: _loading ? null : _send, child: const Text('发送')),
        ])),
      ]),
    );
  }
}

class _CitationCard extends StatelessWidget {
  final Map citation;

  const _CitationCard({required this.citation});

  @override
  Widget build(BuildContext context) {
    final score = citation['score'];
    final location = [
      if (citation['section_path'] != null) citation['section_path'],
      if (citation['page_number'] != null) 'page=${citation['page_number']}',
      if (citation['slide_number'] != null) 'slide=${citation['slide_number']}',
    ].join(' · ');
    final preview = citation['content_preview']?.toString() ?? '';

    return Card(
      child: ExpansionTile(
        title: Text(citation['filename']?.toString() ?? '', style: const TextStyle(fontSize: 13)),
        subtitle: Text(
          'doc=${citation['document_id'] ?? '-'}\n'
          'chunk=${citation['chunk_id'] ?? '-'} · version=${citation['version_id'] ?? '-'} · '
          'score=${score is num ? score.toStringAsFixed(2) : '-'}\n'
          '${location.isEmpty ? '-' : location}',
          style: const TextStyle(fontSize: 11),
        ),
        childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
        children: [
          Align(
            alignment: Alignment.centerLeft,
            child: SelectableText(preview.isEmpty ? '无原文预览' : preview),
          ),
        ],
      ),
    );
  }
}
