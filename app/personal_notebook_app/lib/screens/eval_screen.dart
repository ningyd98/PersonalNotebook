import 'package:flutter/material.dart';

import '../api/client.dart';

class EvalScreen extends StatefulWidget {
  const EvalScreen({super.key});

  @override
  State<EvalScreen> createState() => _EvalScreenState();
}

class _EvalScreenState extends State<EvalScreen> {
  List<dynamic> _datasets = [];
  bool _loading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final r = await apiClient.get('/api/eval/datasets');
      if (mounted) {
        setState(() {
          _datasets = (r['datasets'] as List<dynamic>?) ?? (r['items'] as List<dynamic>?) ?? [];
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

  Future<void> _create() async {
    final nameCtrl = TextEditingController();
    final name = await showDialog<String>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('创建评测集'),
        content: TextField(controller: nameCtrl, decoration: const InputDecoration(hintText: '名称')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('取消')),
          FilledButton(onPressed: () => Navigator.pop(context, nameCtrl.text.trim()), child: const Text('创建')),
        ],
      ),
    );
    nameCtrl.dispose();
    if (name == null || name.isEmpty) return;
    try {
      await apiClient.post('/api/eval/datasets', body: {'name': name});
      await _load();
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('评测'), actions: [IconButton(icon: const Icon(Icons.refresh), onPressed: _load)]),
      body: Column(
        children: [
          if (_loading) const LinearProgressIndicator(),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.all(12),
              child: Text(_error!, style: const TextStyle(color: Colors.red)),
            ),
          Expanded(
            child: _datasets.isEmpty && !_loading
                ? const Center(child: Text('暂无评测集'))
                : ListView.builder(
                    itemCount: _datasets.length,
                    itemBuilder: (_, i) {
                      final item = _datasets[i] as Map<String, dynamic>;
                      return Card(
                        margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                        child: ListTile(
                          title: Text(item['name']?.toString() ?? ''),
                          subtitle: Text('cases=${item['case_count'] ?? 0}'),
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(onPressed: _create, child: const Icon(Icons.add)),
    );
  }
}
