import 'package:flutter/material.dart';

import '../api/client.dart';
import 'chat_screen.dart';
import 'debug_trace_screen.dart';
import 'document_list_screen.dart';
import 'document_upload_screen.dart';

class KbDetailScreen extends StatefulWidget {
  final String? kbId;

  const KbDetailScreen({super.key, this.kbId});

  @override
  State<KbDetailScreen> createState() => _KbDetailScreenState();
}

class _KbDetailScreenState extends State<KbDetailScreen> {
  Map<String, dynamic>? _kb;
  bool _loading = false;
  String? _error;

  String get _kbId => widget.kbId ?? '';

  @override
  void initState() {
    super.initState();
    if (_kbId.isNotEmpty) _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final r = await apiClient.get('/api/kbs/$_kbId');
      if (mounted) {
        setState(() {
          _kb = r;
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

  Future<void> _checkConsistency() async {
    try {
      final resp = await apiClient.get('/api/kbs/$_kbId/consistency?dry_run=true');
      if (!mounted) return;
      final ok = resp['report']?['is_consistent'];
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Consistency: ${ok ?? resp.toString()}')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Consistency 检查失败：$e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_kbId.isEmpty) {
      return const Scaffold(
        body: Center(child: Text('缺少知识库 ID')),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(_kb?['name']?.toString() ?? '知识库详情'),
        actions: [IconButton(icon: const Icon(Icons.refresh), onPressed: _load)],
      ),
      body: _loading && _kb == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                if (_error != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: Text(_error!, style: const TextStyle(color: Colors.red)),
                  ),
                if (_kb != null) ...[
                  Text(
                    _kb!['name']?.toString() ?? '',
                    style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
                  ),
                  Text(
                    '文档: ${_kb!['document_count'] ?? 0} · Chunks: ${_kb!['chunk_count'] ?? 0}',
                    style: const TextStyle(color: Colors.grey),
                  ),
                  if ((_kb!['description']?.toString() ?? '').isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 8),
                      child: Text(_kb!['description'].toString()),
                    ),
                  const Divider(height: 32),
                ],
                _NavCard(
                  Icons.description,
                  '文档列表',
                  () => Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => DocumentListScreen(kbId: _kbId)),
                  ),
                ),
                _NavCard(
                  Icons.upload_file,
                  '上传文档',
                  () => Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => DocumentUploadScreen(kbId: _kbId)),
                  ),
                ),
                _NavCard(
                  Icons.chat,
                  '问答',
                  () => Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => ChatScreen(kbId: _kbId)),
                  ),
                ),
                _NavCard(
                  Icons.bug_report,
                  'Debug Trace',
                  () => Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => DebugTraceScreen(kbId: _kbId)),
                  ),
                ),
                _NavCard(
                  Icons.assessment,
                  '评测',
                  () => Navigator.pushNamed(context, '/eval', arguments: {'kb_id': _kbId}),
                ),
                _NavCard(Icons.check_circle, 'Consistency', _checkConsistency),
              ],
            ),
    );
  }
}

class _NavCard extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  const _NavCard(this.icon, this.label, this.onTap);

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: Icon(icon),
        title: Text(label),
        trailing: const Icon(Icons.chevron_right),
        onTap: onTap,
      ),
    );
  }
}
