/// KB List + KB Detail Screens
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
  final _nameCtrl = TextEditingController();

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final resp = await apiClient.get('/api/kbs?page_size=50');
      setState(() { _kbs = (resp['items'] as List<dynamic>?) ?? []; _loading = false; });
    } catch (_) { setState(() => _loading = false); }
  }

  Future<void> _create() async {
    final name = _nameCtrl.text.trim();
    if (name.isEmpty) return;
    await apiClient.post('/api/kbs', body: {'name': name});
    _nameCtrl.clear();
    _load();
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
        Expanded(child: _loading ? const Center(child: CircularProgressIndicator()) : ListView.builder(
          itemCount: _kbs.length,
          itemBuilder: (_, i) {
            final kb = _kbs[i] as Map<String, dynamic>;
            return ListTile(
              title: Text(kb['name'] ?? ''),
              subtitle: Text('${kb['document_count'] ?? 0} 文档 · ${kb['chunk_count'] ?? 0} Chunks'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () {
                if (widget.selectMode != null) Navigator.pop(context, kb['id']);
                else Navigator.push(context, MaterialPageRoute(builder: (_) => KbDetailScreen(kbId: kb['id'])));
              },
            );
          },
        )),
      ]),
    );
  }
}

/// --- KB Detail Screen ---
class KbDetailScreen extends StatefulWidget {
  final String kbId;
  const KbDetailScreen({super.key, required this.kbId});
  @override
  State<KbDetailScreen> createState() => _KbDetailScreenState();
}

class _KbDetailScreenState extends State<KbDetailScreen> {
  Map<String, dynamic>? _kb;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    try { final r = await apiClient.get('/api/kbs/${widget.kbId}'); setState(() => _kb = r); } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(_kb?['name'] ?? '知识库详情')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        if (_kb != null) ...[
          Text('名称: ${_kb!['name']}', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600)),
          Text('文档: ${_kb!['document_count']} · Chunks: ${_kb!['chunk_count']}', style: const TextStyle(color: Colors.grey)),
          const Divider(),
          _NavCard(Icons.description, '文档列表', () => Navigator.push(context, MaterialPageRoute(builder: (_) => DocListScreen(kbId: widget.kbId)))),
          _NavCard(Icons.upload_file, '上传文档', () => Navigator.push(context, MaterialPageRoute(builder: (_) => DocUploadScreen(kbId: widget.kbId)))),
          _NavCard(Icons.chat, '问答', () => Navigator.push(context, MaterialPageRoute(builder: (_) => ChatScreen(kbId: widget.kbId)))),
          _NavCard(Icons.bug_report, 'Debug', () => Navigator.pushNamed(context, '/debug-trace')),
          _NavCard(Icons.assessment, '评测', () => Navigator.pushNamed(context, '/eval')),
          _NavCard(Icons.check_circle, 'Consistency', () async { await apiClient.get('/api/kbs/${widget.kbId}/consistency?dry_run=true'); }),
        ] else
          const Center(child: CircularProgressIndicator()),
      ]),
    );
  }
}

class _NavCard extends StatelessWidget {
  final IconData icon; final String label; final VoidCallback onTap;
  const _NavCard(this.icon, this.label, this.onTap);
  @override
  Widget build(BuildContext context) => Card(child: ListTile(leading: Icon(icon), title: Text(label), trailing: const Icon(Icons.chevron_right), onTap: onTap));
}

// Stub imports for screens in same file
class DocListScreen extends StatelessWidget {
  final String kbId; const DocListScreen({super.key, required this.kbId});
  @override Widget build(BuildContext context) => Scaffold(appBar: AppBar(title: const Text('文档列表')), body: const Center(child: Text('从 KB Detail 跳转')));
}
class DocUploadScreen extends StatelessWidget {
  final String kbId; const DocUploadScreen({super.key, required this.kbId});
  @override Widget build(BuildContext context) => Scaffold(appBar: AppBar(title: const Text('上传文档')), body: const Center(child: Text('从 KB Detail 跳转')));
}
class ChatScreen extends StatelessWidget {
  final String kbId; const ChatScreen({super.key, required this.kbId});
  @override Widget build(BuildContext context) => Scaffold(appBar: AppBar(title: const Text('问答')), body: const Center(child: Text('从 KB Detail 跳转')));
}
