import 'package:flutter/material.dart';
import '../api/client.dart';

class KbDetailScreen extends StatefulWidget {
  final String kbId;
  final String kbName;
  const KbDetailScreen({super.key, required this.kbId, required this.kbName});
  @override State<KbDetailScreen> createState() => _KbDetailScreenState();
}

class _KbDetailScreenState extends State<KbDetailScreen> {
  Map<String, dynamic>? _stats;
  List<dynamic>? _docs;
  bool _loading = true;
  String? _error;

  @override void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      _stats = await apiClient.get('/api/kbs/${widget.kbId}/stats');
      final docsResp = await apiClient.get('/api/kbs/${widget.kbId}/documents');
      _docs = docsResp['items'] as List<dynamic>?;
    } on ApiException catch (e) { _error = e.message; } catch (e) { _error = e.toString(); }
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _retry(String docId) async {
    final ok = await showDialog<bool>(context: context, builder: (ctx) => AlertDialog(
      title: const Text('重试确认'), content: const Text('将重新处理此文档。'),
      actions: [TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('取消')), FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('重试'))],
    ));
    if (ok != true) return;
    try { await apiClient.post('/api/documents/$docId/retry', body: {'force': true}); _load(); }
    on ApiException catch (e) { if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('失败: ${e.message}'))); }
  }

  Future<void> _delete(String docId, String name) async {
    final ok = await showDialog<bool>(context: context, builder: (ctx) => AlertDialog(
      title: const Text('删除文档'), content: Text('确定要删除 "$name" 吗？删除后该文档不再参与问答。'),
      actions: [TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('取消')), FilledButton(onPressed: () => Navigator.pop(ctx, true), style: FilledButton.styleFrom(backgroundColor: Colors.red), child: const Text('删除'))],
    ));
    if (ok != true) return;
    try { await apiClient.delete('/api/documents/$docId'); _load(); }
    on ApiException catch (e) { if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('失败: ${e.message}'))); }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.kbName), actions: [IconButton(icon: const Icon(Icons.refresh), onPressed: _load)]),
      body: _loading ? const Center(child: CircularProgressIndicator())
        : _error != null ? Center(child: Text('加载失败: $_error', style: const TextStyle(color: Colors.red)))
        : ListView(padding: const EdgeInsets.all(16), children: [
          if (_stats != null) ...[
            _sectionHeader('知识库统计'),
            Card(child: Padding(padding: const EdgeInsets.all(12), child: Column(children: [
              _statRow('文档总数', '${(_stats!['documents'] as Map)['total']}'),
              _statRow('就绪', '${(_stats!['documents'] as Map)['ready']}', color: Colors.green),
              _statRow('已上传', '${(_stats!['documents'] as Map)['uploaded']}', color: Colors.orange),
              _statRow('解析中', '${(_stats!['documents'] as Map)['parsing']}'),
              _statRow('失败', '${(_stats!['documents'] as Map)['failed']}', color: Colors.red),
              const Divider(),
              _statRow('Chunks', '${(_stats!['index'] as Map)['total_chunks']}'),
              _statRow('Vectors', '${(_stats!['index'] as Map)['total_vectors']}'),
              _statRow('Active Version', '${(_stats!['index'] as Map)['active_version']}'),
              if (_stats!['last_error'] != null)
                Padding(padding: const EdgeInsets.only(top: 8), child: Text('Last Error: ${_stats!['last_error']}', style: const TextStyle(color: Colors.red, fontSize: 11))),
            ]))),
            const SizedBox(height: 16),
            _sectionHeader('文档列表 (${_docs?.length ?? 0})'),
          ],
          if (_docs != null) ..._docs!.map((d) => _docCard(d)),
        ]),
    );
  }

  Widget _sectionHeader(String t) => Padding(padding: const EdgeInsets.only(bottom: 8), child: Text(t, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)));
  Widget _statRow(String label, String value, {Color? color}) => Row(children: [
    Expanded(child: Text(label, style: const TextStyle(fontSize: 13))),
    Text(value, style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: color)),
  ]);

  Widget _docCard(Map<String, dynamic> d) {
    final status = d['status']?.toString() ?? '?';
    final isReady = status == 'READY';
    final isFailed = status == 'FAILED';
    return Card(child: ListTile(
      leading: Icon(isReady ? Icons.check_circle : isFailed ? Icons.error : Icons.hourglass_empty,
        color: isReady ? Colors.green : isFailed ? Colors.red : Colors.orange, size: 24),
      title: Text(d['original_filename']?.toString() ?? '?', maxLines: 1, overflow: TextOverflow.ellipsis),
      subtitle: Text('$status | chunks: ${d['chunk_count']} | vectors: ${d['vector_count']} | ${d['file_size']}B', style: const TextStyle(fontSize: 11)),
      trailing: PopupMenuButton<String>(onSelected: (v) {
        final id = d['document_id']?.toString() ?? '';
        final name = d['original_filename']?.toString() ?? '';
        if (v == 'retry') _retry(id);
        if (v == 'delete') _delete(id, name);
      }, itemBuilder: (_) => [
        const PopupMenuItem(value: 'retry', child: ListTile(leading: Icon(Icons.refresh, size: 18), title: Text('重试', style: TextStyle(fontSize: 14)), dense: true)),
        const PopupMenuItem(value: 'delete', child: ListTile(leading: Icon(Icons.delete, size: 18, color: Colors.red), title: Text('删除', style: TextStyle(fontSize: 14, color: Colors.red)), dense: true)),
      ]),
    ));
  }
}
