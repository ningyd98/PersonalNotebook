import 'package:flutter/material.dart';
import '../api/client.dart';

class DiagnosticsScreen extends StatefulWidget {
  const DiagnosticsScreen({super.key});
  @override State<DiagnosticsScreen> createState() => _DiagnosticsScreenState();
}

class _DiagnosticsScreenState extends State<DiagnosticsScreen> {
  Map<String, dynamic>? _diag;
  Map<String, dynamic>? _modelTest;
  Map<String, dynamic>? _embedTest;
  bool _loading = true;
  String? _error;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      _diag = await apiClient.get('/api/system/diagnostics');
    } on ApiException catch (e) {
      _error = e.message;
    } catch (e) {
      _error = e.toString();
    }
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _testModel() async {
    setState(() => _modelTest = null);
    try {
      _modelTest = await apiClient.post('/api/system/test-model');
    } catch (e) { _modelTest = {'success': false, 'error': e.toString()}; }
    if (mounted) setState(() {});
  }

  Future<void> _testEmbedding() async {
    setState(() => _embedTest = null);
    try {
      _embedTest = await apiClient.post('/api/system/test-embedding');
    } catch (e) { _embedTest = {'success': false, 'error': e.toString()}; }
    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('诊断中心'), actions: [
        IconButton(icon: const Icon(Icons.refresh), onPressed: _load),
      ]),
      body: _loading
        ? const Center(child: CircularProgressIndicator())
        : _error != null
          ? Center(child: Text('加载失败: $_error', style: const TextStyle(color: Colors.red)))
          : ListView(padding: const EdgeInsets.all(16), children: [
              _sectionHeader('服务状态'),
              _serviceCard(_diag),
              const SizedBox(height: 16),
              _sectionHeader('模型测试'),
              Row(children: [
                Expanded(child: ElevatedButton(onPressed: _testModel, child: const Text('测试 Chat'))),
                const SizedBox(width: 8),
                Expanded(child: ElevatedButton(onPressed: _testEmbedding, child: const Text('测试 Embedding'))),
              ]),
              if (_modelTest != null) _testResultCard('Chat', _modelTest!),
              if (_embedTest != null) _testResultCard('Embedding', _embedTest!),
              const SizedBox(height: 16),
              _sectionHeader('配置信息'),
              _configCard(_diag),
            ]),
    );
  }

  Widget _sectionHeader(String title) => Padding(
    padding: const EdgeInsets.only(bottom: 8),
    child: Text(title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
  );

  Widget _serviceCard(Map<String, dynamic> diag) {
    final svc = (diag['services'] as Map<String, dynamic>?) ?? {};
    return Card(child: Column(children: svc.entries.map((e) {
      final info = e.value is Map ? e.value as Map<String, dynamic> : <String, dynamic>{};
      final ok = info['status'] == 'ok';
      return ListTile(
        leading: Icon(ok ? Icons.check_circle : Icons.error, color: ok ? Colors.green : Colors.red, size: 20),
        title: Text(e.key),
        subtitle: Text(ok ? '正常' : (info['error']?.toString() ?? info['status']?.toString() ?? '?')),
        dense: true,
      );
    }).toList()));
  }

  Widget _configCard(Map<String, dynamic> diag) => Card(child: Column(children: [
    ListTile(dense: true, title: const Text('API Key'), subtitle: Text(diag['api_key_configured'] == true ? 'configured: true' : 'configured: false')),
    ListTile(dense: true, title: const Text('Overall'), subtitle: Text(diag['overall']?.toString() ?? '?')),
    if (diag['last_error'] != null)
      ListTile(dense: true, title: const Text('Last Error'), subtitle: Text((diag['last_error'] as Map)['error']?.toString() ?? '?', style: const TextStyle(color: Colors.red, fontSize: 11))),
  ]));

  Widget _testResultCard(String label, Map<String, dynamic> r) => Card(
    color: r['success'] == true ? Colors.green.shade50 : Colors.red.shade50,
    child: ListTile(
      dense: true,
      leading: Icon(r['success'] == true ? Icons.check_circle : Icons.error, color: r['success'] == true ? Colors.green : Colors.red, size: 18),
      title: Text('$label: ${r['success'] == true ? "OK" : "Failed"}', style: const TextStyle(fontSize: 13)),
      subtitle: Text(r['model']?.toString() ?? r['error']?.toString() ?? '', style: const TextStyle(fontSize: 11)),
    ),
  );
}
