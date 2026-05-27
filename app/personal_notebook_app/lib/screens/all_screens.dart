/// Remaining Screens: Debug, System Status, Settings, Document screens
import 'package:flutter/material.dart';
import '../api/client.dart';

// --- Debug Trace Screen ---
class DebugTraceScreen extends StatefulWidget {
  const DebugTraceScreen({super.key});
  @override State<DebugTraceScreen> createState() => _DebugTraceScreenState();
}
class _DebugTraceScreenState extends State<DebugTraceScreen> {
  final _kbCtrl = TextEditingController();
  final _qCtrl = TextEditingController();
  Map<String, dynamic>? _result;
  bool _loading = false;

  Future<void> _run() async {
    setState(() => _loading = true);
    try {
      _result = await apiClient.post('/api/chat/debug', body: {'kb_id': _kbCtrl.text, 'question': _qCtrl.text, 'top_k': 8, 'use_rerank': true, 'strict_citation': true});
    } catch (_) {}
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Debug Trace')),
    body: Column(children: [
      Padding(padding: const EdgeInsets.all(8), child: Row(children: [
        Expanded(child: TextField(controller: _kbCtrl, decoration: const InputDecoration(labelText: 'KB ID', border: OutlineInputBorder(), isDense: true))),
        const SizedBox(width: 8),
        Expanded(flex: 2, child: TextField(controller: _qCtrl, decoration: const InputDecoration(labelText: '问题', border: OutlineInputBorder(), isDense: true))),
        const SizedBox(width: 8),
        FilledButton(onPressed: _loading ? null : _run, child: const Text('Debug')),
      ])),
      if (_loading) const LinearProgressIndicator(),
      Expanded(child: _result == null ? const Center(child: Text('输入 KB ID 和问题后点击 Debug')) : ListView(padding: const EdgeInsets.all(12), children: [
        Text('Type: ${_result!['query_type']} · Coverage: ${((_result!['citation_coverage'] as num?) ?? 0 * 100).toStringAsFixed(0)}% · Latency: ${_result!['latency_ms']}ms'),
        if (_result!['refusal_reason'] != null) Container(padding: const EdgeInsets.all(8), color: Colors.orange.shade100, child: Text('Refusal: ${_result!['refusal_reason']}')),
        const Divider(), const Text('Answer', style: TextStyle(fontWeight: FontWeight.w600)),
        Card(child: Padding(padding: const EdgeInsets.all(8), child: Text(_result!['answer'] ?? ''))),
        const Text('Unsupported Claims', style: TextStyle(fontWeight: FontWeight.w600, color: Colors.red)),
        ...((_result!['unsupported_claims'] as List<dynamic>?) ?? []).map((c) => Text('· $c', style: const TextStyle(fontSize: 12, color: Colors.red))),
      ])),
    ]),
  );
}

// --- System Status Screen ---
class SystemStatusScreen extends StatefulWidget {
  const SystemStatusScreen({super.key});
  @override State<SystemStatusScreen> createState() => _SystemStatusScreenState();
}
class _SystemStatusScreenState extends State<SystemStatusScreen> {
  Map<String, dynamic>? _health;
  @override void initState() { super.initState(); _load(); }
  Future<void> _load() async { try { _health = await apiClient.get('/health'); setState(() {}); } catch (_) {} }
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('系统状态'), actions: [IconButton(icon: const Icon(Icons.refresh), onPressed: _load)]),
    body: _health == null ? const Center(child: CircularProgressIndicator()) : ListView(padding: const EdgeInsets.all(16), children: [
      _StatusTile('PostgreSQL', _health!['postgres']?.toString()),
      _StatusTile('Qdrant', _health!['qdrant']?.toString()),
      _StatusTile('MinIO', _health!['minio']?.toString()),
      _StatusTile('Redis', _health!['redis']?.toString()),
      _StatusTile('Model Gateway', _health!['model_gateway']?.toString()),
    ]),
  );
}
class _StatusTile extends StatelessWidget {
  final String name, String? status;
  const _StatusTile(this.name, this.status);
  @override Widget build(BuildContext context) => ListTile(
    leading: Icon(status == 'ok' ? Icons.check_circle : Icons.error, color: status == 'ok' ? Colors.green : Colors.red),
    title: Text(name), subtitle: Text(status ?? '?'),
  );
}

// --- Settings Screen ---
class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('设置')),
    body: ListView(children: [
      ListTile(title: const Text('Core 地址'), subtitle: Text(apiClient.baseUrl)),
      ListTile(title: const Text('版本'), subtitle: const Text('0.2.0')),
      ListTile(title: const Text('断开连接'), leading: const Icon(Icons.link_off), onTap: () {}),
    ]),
  );
}

// --- Document Upload Screen ---
class DocumentUploadScreen extends StatefulWidget {
  final String? kbId;
  const DocumentUploadScreen({super.key, this.kbId});
  @override State<DocumentUploadScreen> createState() => _DocumentUploadScreenState();
}
class _DocumentUploadScreenState extends State<DocumentUploadScreen> {
  String _kbId = '';
  String? _result;
  @override Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('上传文档')),
    body: Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
      TextField(decoration: const InputDecoration(labelText: 'KB ID', border: OutlineInputBorder()), onChanged: (v) => _kbId = v),
      const SizedBox(height: 16),
      FilledButton.icon(onPressed: () {}, icon: const Icon(Icons.upload_file), label: const Text('选择文件')),
      if (_result != null) Text(_result!),
    ])),
  );
}

// --- Document List Screen ---
class DocumentListScreen extends StatefulWidget {
  final String kbId;
  const DocumentListScreen({super.key, required this.kbId});
  @override State<DocumentListScreen> createState() => _DocumentListScreenState();
}
class _DocumentListScreenState extends State<DocumentListScreen> {
  List<dynamic> _docs = [];
  @override void initState() { super.initState(); _load(); }
  Future<void> _load() async { try { final r = await apiClient.get('/api/kbs/${widget.kbId}/documents'); setState(() { _docs = (r['items'] as List<dynamic>?) ?? []; }); } catch (_) {} }
  @override Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('文档列表')),
    body: ListView.builder(itemCount: _docs.length, itemBuilder: (_, i) {
      final d = _docs[i] as Map; return ListTile(title: Text(d['filename'] ?? ''), subtitle: Text('${d['parse_status']} · v${d['document_version']}'), trailing: Text(d['status'] ?? ''));
    }),
  );
}

// --- Document Detail Screen ---
class DocumentDetailScreen extends StatefulWidget {
  final String docId;
  const DocumentDetailScreen({super.key, required this.docId});
  @override State<DocumentDetailScreen> createState() => _DocumentDetailScreenState();
}
class _DocumentDetailScreenState extends State<DocumentDetailScreen> {
  Map<String, dynamic>? _doc;
  @override void initState() { super.initState(); _load(); }
  Future<void> _load() async { try { _doc = await apiClient.get('/api/documents/${widget.docId}'); setState(() {}); } catch (_) {} }
  Future<void> _reindex() async { await apiClient.post('/api/documents/${widget.docId}/reindex'); _load(); }
  @override Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: Text(_doc?['filename'] ?? '文档详情')),
    body: _doc == null ? const Center(child: CircularProgressIndicator()) : ListView(padding: const EdgeInsets.all(16), children: [
      Text('状态: ${_doc!['status']}', style: const TextStyle(fontWeight: FontWeight.w600)),
      Text('Parse: ${_doc!['parse_status']} · Embed: ${_doc!['embed_status']} · Index: ${_doc!['index_status']}'),
      Text('Version: ${_doc!['document_version']} · Active: ${_doc!['active_version']}'),
      const Divider(),
      FilledButton.icon(onPressed: _reindex, icon: const Icon(Icons.refresh), label: const Text('Reindex')),
      const SizedBox(height: 8),
      OutlinedButton(onPressed: () async { await apiClient.get('/api/documents/${widget.docId}/quality-report'); }, child: const Text('质量报告')),
    ]),
  );
}

// --- Eval Screen ---
class EvalScreen extends StatefulWidget {
  const EvalScreen({super.key});
  @override State<EvalScreen> createState() => _EvalScreenState();
}
class _EvalScreenState extends State<EvalScreen> {
  List<dynamic> _datasets = [];
  @override void initState() { super.initState(); _load(); }
  Future<void> _load() async { try { final r = await apiClient.get('/api/eval/datasets'); setState(() { _datasets = (r['datasets'] as List<dynamic>?) ?? (r['items'] as List<dynamic>?) ?? []; }); } catch (_) {} }
  @override Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('评测')),
    body: _datasets.isEmpty ? const Center(child: Text('暂无评测集')) : ListView.builder(itemCount: _datasets.length, itemBuilder: (_, i) => ListTile(title: Text((_datasets[i] as Map)['name'] ?? ''))),
    floatingActionButton: FloatingActionButton(onPressed: () async {
      final nameCtrl = TextEditingController();
      final name = await showDialog<String>(context: context, builder: (_) => AlertDialog(title: const Text('创建评测集'), content: TextField(controller: nameCtrl, decoration: const InputDecoration(hintText: '名称')), actions: [TextButton(onPressed: () => Navigator.pop(context), child: const Text('取消')), FilledButton(onPressed: () => Navigator.pop(context, nameCtrl.text), child: const Text('创建'))]));
      if (name != null && name.isNotEmpty) { await apiClient.post('/api/eval/datasets', body: {'name': name}); _load(); }
    }, child: const Icon(Icons.add)),
  );
}
