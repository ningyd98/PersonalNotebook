import 'package:flutter/material.dart';

import '../api/client.dart';

class DebugTraceScreen extends StatefulWidget {
  final String? kbId;

  const DebugTraceScreen({super.key, this.kbId});

  @override
  State<DebugTraceScreen> createState() => _DebugTraceScreenState();
}

class _DebugTraceScreenState extends State<DebugTraceScreen> {
  final _kbCtrl = TextEditingController();
  final _qCtrl = TextEditingController();
  Map<String, dynamic>? _result;
  bool _loading = false;
  String? _error;

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
    _qCtrl.dispose();
    super.dispose();
  }

  Future<void> _run() async {
    final kbId = _kbCtrl.text.trim();
    final question = _qCtrl.text.trim();
    if (kbId.isEmpty || question.isEmpty) {
      setState(() => _error = '请先填写 KB ID 和问题');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
      _result = null;
    });
    try {
      final resp = await apiClient.post(
        '/api/chat/debug',
        body: {'kb_id': kbId, 'question': question, 'top_k': 8, 'use_rerank': true, 'strict_citation': true},
      );
      if (mounted) {
        setState(() {
          _result = resp;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _loading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final result = _result;
    final coverage = (((result?['citation_coverage'] as num?) ?? 0) * 100).toStringAsFixed(0);
    final evidencePack = result?['evidence_pack'];
    final evidences = evidencePack is Map<String, dynamic> ? _asList(evidencePack['evidences']) : <dynamic>[];
    return Scaffold(
      appBar: AppBar(title: const Text('Debug Trace')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(8),
            child: Row(
              children: [
                Expanded(child: TextField(controller: _kbCtrl, decoration: const InputDecoration(labelText: 'KB ID', border: OutlineInputBorder(), isDense: true))),
                const SizedBox(width: 8),
                Expanded(flex: 2, child: TextField(controller: _qCtrl, decoration: const InputDecoration(labelText: '问题', border: OutlineInputBorder(), isDense: true))),
                const SizedBox(width: 8),
                FilledButton(onPressed: _loading ? null : _run, child: const Text('Debug')),
              ],
            ),
          ),
          if (_loading) const LinearProgressIndicator(),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.all(8),
              child: Text(_error!, style: const TextStyle(color: Colors.red)),
            ),
          Expanded(
            child: result == null
                ? const Center(child: Text('输入 KB ID 和问题后点击 Debug'))
                : ListView(
                    padding: const EdgeInsets.all(12),
                    children: [
                      Text(
                        'Type: ${result['query_type']} · Coverage: $coverage% · Latency: ${result['latency_ms']}ms',
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      ),
                      Text('should_refuse: ${result['should_refuse'] ?? false}'),
                      if (result['refusal_reason'] != null)
                        Container(
                          margin: const EdgeInsets.only(top: 8),
                          padding: const EdgeInsets.all(8),
                          color: Colors.orange.shade100,
                          child: Text('Refusal: ${result['refusal_reason']}'),
                        ),
                      const Divider(),
                      const Text('Answer', style: TextStyle(fontWeight: FontWeight.w600)),
                      Card(child: Padding(padding: const EdgeInsets.all(8), child: SelectableText(result['answer']?.toString() ?? ''))),
                      _ListSection(title: 'Dense Results', items: _asList(result['dense_results']), builder: _compactResult),
                      _ListSection(title: 'Reranked Results', items: _asList(result['reranked_results']), builder: _compactResult),
                      _EvidenceSection(evidences: evidences),
                      _ClaimSection(title: 'Supported Claims', claims: _asList(result['supported_claims']), color: Colors.green),
                      _ClaimSection(title: 'Unsupported Claims', claims: _asList(result['unsupported_claims']), color: Colors.red),
                    ],
                  ),
          ),
        ],
      ),
    );
  }

  static List<dynamic> _asList(dynamic value) => value is List ? value : <dynamic>[];

  static Widget _compactResult(dynamic item) {
    final m = item as Map;
    return ListTile(
      dense: true,
      title: Text('id=${m['id'] ?? '-'} · score=${m['score'] ?? m['rerank_score'] ?? '-'}'),
      subtitle: Text(m['content']?.toString() ?? '', maxLines: 3, overflow: TextOverflow.ellipsis),
    );
  }
}

class _ListSection extends StatelessWidget {
  final String title;
  final List<dynamic> items;
  final Widget Function(dynamic item) builder;

  const _ListSection({required this.title, required this.items, required this.builder});

  @override
  Widget build(BuildContext context) {
    return ExpansionTile(
      title: Text('$title (${items.length})'),
      children: items.map(builder).toList(),
    );
  }
}

class _EvidenceSection extends StatelessWidget {
  final List<dynamic> evidences;

  const _EvidenceSection({required this.evidences});

  @override
  Widget build(BuildContext context) {
    return ExpansionTile(
      initiallyExpanded: true,
      title: Text('Evidence Pack (${evidences.length})'),
      children: evidences.map((item) {
        final evidence = item as Map;
        return ExpansionTile(
          title: Text(evidence['evidence_id']?.toString() ?? '-'),
          subtitle: Text(
            'doc=${evidence['document_id'] ?? '-'} · chunk=${evidence['chunk_id'] ?? '-'} · version=${evidence['version_id'] ?? '-'}\n'
            'dense=${evidence['dense_score'] ?? '-'} · rerank=${evidence['rerank_score'] ?? '-'} · final=${evidence['final_score'] ?? '-'}',
            style: const TextStyle(fontSize: 11),
          ),
          childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
          children: [
            Align(
              alignment: Alignment.centerLeft,
              child: SelectableText(evidence['content']?.toString() ?? ''),
            ),
          ],
        );
      }).toList(),
    );
  }
}

class _ClaimSection extends StatelessWidget {
  final String title;
  final List<dynamic> claims;
  final Color color;

  const _ClaimSection({required this.title, required this.claims, required this.color});

  @override
  Widget build(BuildContext context) {
    return ExpansionTile(
      title: Text('$title (${claims.length})', style: TextStyle(color: color)),
      children: claims.map((claim) {
        return ListTile(
          dense: true,
          title: SelectableText(claim.toString(), style: TextStyle(color: color)),
        );
      }).toList(),
    );
  }
}
