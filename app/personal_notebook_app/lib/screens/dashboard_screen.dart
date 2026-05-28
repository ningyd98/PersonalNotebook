import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../api/client.dart';
import '../providers/app_state.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});
  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  Map<String, dynamic>? _health;
  Map<String, dynamic>? _kbs;
  int _recentJobs = 0;
  bool _loading = true;
  String? _error;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    try {
      setState(() { _loading = true; _error = null; });
      final results = await Future.wait([
        apiClient.get('/health'),
        apiClient.get('/api/kbs?page_size=50'),
        apiClient.get('/api/jobs/recent?limit=5'),
      ]);
      if (mounted) setState(() {
        _health = results[0]; _kbs = results[1];
        _recentJobs = ((results[2]['data'] as Map<String, dynamic>?)?['jobs'] as List<dynamic>?)?.length ?? 0;
        _loading = false;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() { _loading = false; _error = e.message; });
      if (e.statusCode == 401) _handle401();
    } catch (e) {
      if (mounted) setState(() { _error = e.toString(); _loading = false; });
    }
  }

  void _handle401() {
    context.read<AppState>().unpair();
    Navigator.pushReplacementNamed(context, '/pairing');
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    final kbs = (_kbs?['items'] as List<dynamic>?) ?? [];
    final docCount = kbs.fold<int>(0, (s, kb) => s + ((kb as Map)['document_count'] as int? ?? 0));

    return Scaffold(
      appBar: AppBar(title: const Text('仪表盘'), actions: [
        IconButton(icon: const Icon(Icons.refresh), onPressed: _load),
      ]),
      body: _loading
        ? const Center(child: CircularProgressIndicator())
        : RefreshIndicator(
            onRefresh: _load,
            child: ListView(padding: const EdgeInsets.all(16), children: [
              if (_error != null)
                Container(padding: const EdgeInsets.all(12), margin: const EdgeInsets.only(bottom: 12),
                  decoration: BoxDecoration(color: Colors.red.shade50, borderRadius: BorderRadius.circular(8)),
                  child: Row(children: [const Icon(Icons.error_outline, size: 16, color: Colors.red), const SizedBox(width: 8), Expanded(child: Text(_error!, style: const TextStyle(color: Colors.red, fontSize: 13)))])),

              // Connection info
              Card(
                child: Padding(padding: const EdgeInsets.all(12), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  const Text('连接信息', style: TextStyle(fontWeight: FontWeight.w600)),
                  const SizedBox(height: 4),
                  Text('Core: ${app.coreUrl}', style: const TextStyle(fontSize: 12, color: Colors.grey)),
                  Text('Tenant: ${app.tenantId}', style: const TextStyle(fontSize: 12, color: Colors.grey)),
                  if (app.deviceId != null) Text('Device: ${app.deviceId!.substring(0, 8)}…', style: const TextStyle(fontSize: 12, color: Colors.grey)),
                ])),
              ),
              const SizedBox(height: 8),

              _StatCard(title: '知识库', value: '${kbs.length}', icon: Icons.book),
              _StatCard(title: '文档', value: '$docCount', icon: Icons.description),
              _StatCard(title: '最近任务', value: '$_recentJobs', icon: Icons.history),
              _StatCard(title: 'Core', value: _health?['status'] ?? '?', icon: Icons.cloud,
                color: _health?['status'] == 'ok' ? Colors.green : Colors.red),
              const SizedBox(height: 16),
              const _NavButton(Icons.book, '知识库管理', '/kb-list'),
              const _NavButton(Icons.upload_file, '上传文档', '/document-upload'),
              const _NavButton(Icons.chat, '问答', '/chat'),
              const _NavButton(Icons.bug_report, 'Debug Trace', '/debug-trace'),
              const _NavButton(Icons.assessment, '评测', '/eval'),
              const _NavButton(Icons.monitor_heart, '系统状态', '/system-status'),
              const _NavButton(Icons.settings, '设置', '/settings'),
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
  final IconData icon; final String label; final String route;
  const _NavButton(this.icon, this.label, this.route);
  @override
  Widget build(BuildContext context) => Card(
    child: ListTile(leading: Icon(icon), title: Text(label), trailing: const Icon(Icons.chevron_right), onTap: () => Navigator.pushNamed(context, route)),
  );
}
