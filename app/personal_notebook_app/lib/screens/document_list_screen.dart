import 'package:flutter/material.dart';

import '../api/client.dart';
import 'document_detail_screen.dart';

class DocumentListScreen extends StatefulWidget {
  final String? kbId;

  const DocumentListScreen({super.key, this.kbId});

  @override
  State<DocumentListScreen> createState() => _DocumentListScreenState();
}

class _DocumentListScreenState extends State<DocumentListScreen> {
  final _kbCtrl = TextEditingController();
  List<dynamic> _docs = [];
  bool _loading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    if (widget.kbId != null && widget.kbId!.isNotEmpty) {
      _kbCtrl.text = widget.kbId!;
      _load();
    }
  }

  @override
  void dispose() {
    _kbCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final kbId = _kbCtrl.text.trim();
    if (kbId.isEmpty) {
      setState(() => _error = '请先填写 KB ID');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final r = await apiClient.get('/api/kbs/$kbId/documents?page_size=100');
      if (mounted) {
        setState(() {
          _docs = (r['items'] as List<dynamic>?) ?? [];
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
    return Scaffold(
      appBar: AppBar(title: const Text('文档列表'), actions: [IconButton(icon: const Icon(Icons.refresh), onPressed: _load)]),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(12),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _kbCtrl,
                    decoration: const InputDecoration(labelText: 'KB ID', border: OutlineInputBorder(), isDense: true),
                    onSubmitted: (_) => _load(),
                  ),
                ),
                const SizedBox(width: 8),
                FilledButton(onPressed: _loading ? null : _load, child: const Text('刷新')),
              ],
            ),
          ),
          if (_loading) const LinearProgressIndicator(),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: Text(_error!, style: const TextStyle(color: Colors.red)),
            ),
          Expanded(
            child: _docs.isEmpty && !_loading
                ? const Center(child: Text('暂无文档'))
                : ListView.builder(
                    itemCount: _docs.length,
                    itemBuilder: (_, i) {
                      final d = _docs[i] as Map<String, dynamic>;
                      final docId = d['id']?.toString() ?? '';
                      return Card(
                        margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                        child: ListTile(
                          title: Text(d['filename']?.toString() ?? ''),
                          subtitle: Text(
                            '${d['file_type'] ?? '-'} · parse=${d['parse_status'] ?? '-'} · index=${d['index_status'] ?? '-'} · chunks=${d['chunk_count'] ?? 0}',
                          ),
                          trailing: Text(d['status']?.toString() ?? 'v${d['document_version'] ?? 1}'),
                          onTap: docId.isEmpty
                              ? null
                              : () => Navigator.push(
                                    context,
                                    MaterialPageRoute(builder: (_) => DocumentDetailScreen(docId: docId)),
                                  ),
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}
