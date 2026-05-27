import 'package:flutter/material.dart';
import '../api/client.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});
  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  Map<String, dynamic>? _health;
  Map<String, dynamic>? _kbs;
  bool _loading = true;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    try {
      final results = await Future.wait([apiClient.get('/health'), apiClient.get('/api/kbs?page_size=50')]);
      if (mounted) setState(() { _health = results[0]; _kbs = results[1]; _loading = false; });
    } catch (_) { if (mounted) setState(() => _loading = false); }
  }

  @override
  Widget build(BuildContext context) {
    final kbs = (_kbs?['items'] as List<dynamic>?) ?? [];
    final docCount = kbs.fold<int>(0, (s, kb) => s + ((kb as Map)['document_count'] as int? ?? 0));
    return Scaffold(
      appBar: AppBar(title: const Text('仪表盘'), actions: [IconButton(icon: const Icon(Icons.refresh), onPressed: _load)]),
      body: _loading ? const Center(child: CircularProgressIndicator()) : RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.all(16), children: [
          _StatCard(title: '知识库', value: '${kbs.length}', icon: Icons.book),
          _StatCard(title: '文档', value: '$docCount', icon: Icons.description),
          _StatCard(title: 'Core', value: _health?['status'] ?? '?', icon: Icons.cloud, color: _health?['status'] == 'ok' ? Colors.green : Colors.red),
          const SizedBox(height: 16),
          _NavButton(Icons.book, '知识库管理', '/kb-list'),
          _NavButton(Icons.upload_file, '上传文档', '/document-upload'),
          _NavButton(Icons.chat, '问答', '/chat'),
          _NavButton(Icons.bug_report, 'Debug Trace', '/debug-trace'),
          _NavButton(Icons.assessment, '评测', '/eval'),
          _NavButton(Icons.monitor_heart, '系统状态', '/system-status'),
          _NavButton(Icons.settings, '设置', '/settings'),
        ]),
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  final String title, value;
  final IconData icon;
  final Color? color;
  const _StatCard({required this.title, required this.value, required this.icon, this.color});

  @override
  Widget build(BuildContext context) => Card(
    child: ListTile(leading: Icon(icon, color: color ?? Theme.of(context).colorScheme.primary), title: Text(title), trailing: Text(value, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold))),
  );
}

class _NavButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final String route;
  const _NavButton(this.icon, this.label, this.route);

  @override
  Widget build(BuildContext context) => Card(
    child: ListTile(leading: Icon(icon), title: Text(label), trailing: const Icon(Icons.chevron_right), onTap: () => Navigator.pushNamed(context, route)),
  );
}
