// KB list screen.
import 'package:flutter/material.dart';
import '../api/client.dart';
import 'kb_detail_screen.dart';

class KbListScreen extends StatefulWidget {
  final String? selectMode;
  const KbListScreen({super.key, this.selectMode});
  @override
  State<KbListScreen> createState() => _KbListScreenState();
}

class _KbListScreenState extends State<KbListScreen> {
  List<dynamic> _kbs = [];
  bool _loading = true;
  String? _error;
  final _nameCtrl = TextEditingController();

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final resp = await apiClient.get('/api/kbs?page_size=50');
      if (mounted) {
        setState(() {
          _kbs = (resp['items'] as List<dynamic>?) ?? [];
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _loading = false;
          _error = e.toString();
        });
      }
    }
  }

  Future<void> _create() async {
    final name = _nameCtrl.text.trim();
    if (name.isEmpty) return;
    try {
      await apiClient.post('/api/kbs', body: {'name': name});
      _nameCtrl.clear();
      _load();
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('知识库')),
      body: Column(children: [
        Padding(padding: const EdgeInsets.all(12), child: Row(children: [
          Expanded(child: TextField(controller: _nameCtrl, decoration: const InputDecoration(labelText: '名称', border: OutlineInputBorder()))),
          const SizedBox(width: 8),
          FilledButton(onPressed: _create, child: const Text('创建')),
        ])),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Text(_error!, style: const TextStyle(color: Colors.red)),
          ),
        Expanded(child: _loading ? const Center(child: CircularProgressIndicator()) : ListView.builder(
          itemCount: _kbs.length,
          itemBuilder: (_, i) {
            final kb = _kbs[i] as Map<String, dynamic>;
            return ListTile(
              title: Text(kb['name'] ?? ''),
              subtitle: Text('${kb['document_count'] ?? 0} 文档 · ${kb['chunk_count'] ?? 0} Chunks'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () {
                if (widget.selectMode != null) {
                  Navigator.pop(context, kb['id']);
                } else {
                  Navigator.push(context, MaterialPageRoute(builder: (_) => KbDetailScreen(kbId: kb['id'])));
                }
              },
            );
          },
        )),
      ]),
    );
  }
}
