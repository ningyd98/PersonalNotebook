import 'package:flutter/material.dart';
import '../api/client.dart';

class ChatScreen extends StatefulWidget {
  final String? kbId;
  const ChatScreen({super.key, this.kbId});
  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _questionCtrl = TextEditingController();
  String _kbId = '';
  String _answer = '';
  List<dynamic> _citations = [];
  bool _loading = false;
  String? _error;

  Future<void> _send() async {
    final q = _questionCtrl.text.trim();
    if (q.isEmpty || _kbId.isEmpty) return;
    setState(() { _loading = true; _error = null; _answer = ''; _citations = []; });
    try {
      final resp = await apiClient.post('/api/chat', body: {'kb_id': _kbId, 'question': q, 'top_k': 8, 'use_rerank': true, 'strict_citation': true});
      setState(() { _answer = resp['answer'] ?? ''; _citations = (resp['citations'] as List<dynamic>?) ?? []; });
    } catch (e) { setState(() => _error = e.toString()); }
    finally { setState(() => _loading = false); }
  }

  @override
  Widget build(BuildContext context) {
    final isRefusal = _answer.contains('未找到可靠依据');
    return Scaffold(
      appBar: AppBar(title: const Text('问答')),
      body: Column(children: [
        Padding(padding: const EdgeInsets.all(12), child: Row(children: [
          Expanded(child: TextField(controller: TextEditingController(text: _kbId), onChanged: (v) => _kbId = v, decoration: const InputDecoration(labelText: '知识库 ID', border: OutlineInputBorder(), isDense: true))),
        ])),
        Expanded(child: ListView(padding: const EdgeInsets.all(12), children: [
          if (_answer.isNotEmpty) ...[
            if (isRefusal) Container(padding: const EdgeInsets.all(12), margin: const EdgeInsets.only(bottom: 12), decoration: BoxDecoration(color: Colors.orange.shade50, borderRadius: BorderRadius.circular(8), border: Border.all(color: Colors.orange.shade200)), child: const Text('⚠️ 低置信拒答 — 知识库中未找到足够的可靠证据', style: TextStyle(color: Colors.deepOrange))),
            Card(child: Padding(padding: const EdgeInsets.all(12), child: Text(_answer, style: const TextStyle(fontSize: 15)))),
            if (_citations.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 8), child: Text('引用 (${_citations.length})', style: const TextStyle(fontWeight: FontWeight.w600))),
            ..._citations.map((c) => Card(child: ListTile(dense: true, title: Text(c['filename'] ?? '', style: const TextStyle(fontSize: 13)), subtitle: Text('score=${(c['score'] as num?)?.toStringAsFixed(2)} · ${c['section_path'] ?? ''}', style: const TextStyle(fontSize: 11)))))
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
