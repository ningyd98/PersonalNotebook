import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../api/client.dart';
import '../providers/app_state.dart';

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
        _shouldRefuse = (resp['should_refuse'] as bool?) ?? (resp['refusal'] as bool?) ?? false;
        _refusalReason = resp['refusal_reason']?.toString();
        final coverage = resp['citation_coverage'];
        _citationCoverage = coverage is num ? coverage.toDouble() : null;
      });
    } on ApiException catch (e) {
      setState(() => _error = e.message);
      if (e.statusCode == 401) Navigator.pushReplacementNamed(context, '/pairing');
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

class _CitationCard extends StatefulWidget {
  final Map citation;
  const _CitationCard({required this.citation});
  @override State<_CitationCard> createState() => _CitationCardState();
}

class _CitationCardState extends State<_CitationCard> {
  bool _loading = false; String? _fullContent, _error;

  String _safeChunkId(String? cid) {
    if (cid == null || cid.isEmpty) return '-';
    return cid.length >= 8 ? cid.substring(0, 8) : cid;
  }

  Future<void> _loadChunk() async {
    final cid = widget.citation['chunk_id']?.toString();
    if (cid == null || cid.isEmpty) return;
    setState(() { _loading = true; _error = null; });
    try {
      final r = await apiClient.get('/api/chunks/$cid');
      _fullContent = r['content']?.toString();
    } on ApiException catch (e) {
      _error = e.message;
      if (e.statusCode == 401 && mounted) Navigator.pushReplacementNamed(context, '/pairing');
    } catch (e) { _error = e.toString(); }
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    final c = widget.citation; final score = c['score']; final rscore = c['rerank_score'];
    final loc = [if (c['section_path'] != null) c['section_path'], if (c['page_number'] != null) 'p.${c['page_number']}', if (c['chunk_index'] != null) 'chunk#${c['chunk_index']}'].join(' · ');
    final doc = c['document_name']?.toString() ?? c['filename']?.toString() ?? 'unknown';
    final ev = c['evidence_text']?.toString() ?? c['content_preview']?.toString() ?? '';
    final chunkId = c['chunk_id']?.toString();
    final hasChunk = chunkId != null && chunkId.isNotEmpty;
    return Card(child: ExpansionTile(
      title: Text(doc, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
      subtitle: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        if (loc.isNotEmpty) Text(loc, style: const TextStyle(fontSize: 11)),
        Text('score: ${score is num ? score.toStringAsFixed(2) : '-'}${rscore is num ? ' · rerank: ${rscore.toStringAsFixed(2)}' : ''} · chunk: ${_safeChunkId(chunkId)}', style: const TextStyle(fontSize: 11, color: Colors.grey)),
      ]),
      childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
      children: [
        if (ev.isNotEmpty) Container(padding: const EdgeInsets.all(8), decoration: BoxDecoration(color: Colors.grey.shade100, borderRadius: BorderRadius.circular(6)), child: SelectableText(ev, style: const TextStyle(fontSize: 12))),
        const SizedBox(height: 8),
        if (!hasChunk && _fullContent == null && !_loading) const Text('无可展开 chunk', style: TextStyle(fontSize: 11, color: Colors.grey)),
        if (hasChunk && _fullContent == null && !_loading) TextButton.icon(onPressed: _loadChunk, icon: const Icon(Icons.open_in_full, size: 14), label: const Text('展开完整原文', style: TextStyle(fontSize: 11))),
        if (_loading) const SizedBox(height: 16, width: 16, child: CircularProgressIndicator(strokeWidth: 2)),
        if (_error != null) Text(_error!, style: const TextStyle(fontSize: 11, color: Colors.red)),
        if (_fullContent != null) Container(padding: const EdgeInsets.all(8), decoration: BoxDecoration(color: Colors.blue.shade50, borderRadius: BorderRadius.circular(6)), child: SelectableText(_fullContent!, style: const TextStyle(fontSize: 12))),
      ]));
  }
}
