import 'package:flutter/material.dart';

import '../api/client.dart';
import '../services/runtime_manager.dart';

class SystemStatusScreen extends StatefulWidget {
  const SystemStatusScreen({super.key});

  @override
  State<SystemStatusScreen> createState() => _SystemStatusScreenState();
}

class _SystemStatusScreenState extends State<SystemStatusScreen> {
  final _runtime = RuntimeManager();
  Map<String, dynamic>? _health;
  bool _loadingHealth = false;
  bool _runningCommand = false;
  String? _error;
  RuntimeCommandResult? _commandResult;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loadingHealth = true;
      _error = null;
    });
    try {
      final health = await apiClient.get('/health');
      if (mounted) {
        setState(() {
          _health = health;
          _loadingHealth = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _loadingHealth = false;
        });
      }
    }
  }

  Future<void> _run(String label, Future<RuntimeCommandResult> Function() action) async {
    setState(() {
      _runningCommand = true;
      _error = null;
      _commandResult = null;
    });
    final result = await action();
    if (!mounted) return;
    setState(() {
      _runningCommand = false;
      _commandResult = result;
      if (!result.ok) _error = '$label 失败：${result.output}';
    });
  }

  @override
  Widget build(BuildContext context) {
    final desktop = _runtime.isSupportedDesktop;
    return Scaffold(
      appBar: AppBar(title: const Text('系统状态'), actions: [IconButton(icon: const Icon(Icons.refresh), onPressed: _load)]),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (_loadingHealth) const LinearProgressIndicator(),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Text(_error!, style: const TextStyle(color: Colors.red)),
            ),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Core Health', style: TextStyle(fontWeight: FontWeight.w600)),
                  const SizedBox(height: 8),
                  _StatusTile('Status', _health?['status']?.toString()),
                  _StatusTile('PostgreSQL', _health?['postgres']?.toString()),
                  _StatusTile('Qdrant', _health?['qdrant']?.toString()),
                  _StatusTile('MinIO', _health?['minio']?.toString()),
                  _StatusTile('Redis', _health?['redis']?.toString()),
                  _StatusTile('Model Gateway', _health?['model_gateway']?.toString()),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          if (desktop)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Desktop Runtime Manager', style: TextStyle(fontWeight: FontWeight.w600)),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        OutlinedButton.icon(onPressed: _runningCommand ? null : () => _run('检查 Docker', _runtime.dockerVersion), icon: const Icon(Icons.terminal), label: const Text('检查 Docker')),
                        OutlinedButton.icon(onPressed: _runningCommand ? null : () => _run('检查 Compose', _runtime.dockerComposeVersion), icon: const Icon(Icons.fact_check), label: const Text('检查 Compose')),
                        FilledButton.icon(onPressed: _runningCommand ? null : () => _run('启动 Core', _runtime.startCore), icon: const Icon(Icons.play_arrow), label: const Text('启动 Core')),
                        OutlinedButton.icon(onPressed: _runningCommand ? null : () => _run('停止 Core', _runtime.stopCore), icon: const Icon(Icons.stop), label: const Text('停止 Core')),
                        OutlinedButton.icon(onPressed: _runningCommand ? null : () => _run('重启 Core', _runtime.restartCore), icon: const Icon(Icons.restart_alt), label: const Text('重启 Core')),
                        OutlinedButton.icon(onPressed: _runningCommand ? null : () => _run('查看状态', _runtime.composePs), icon: const Icon(Icons.list), label: const Text('查看状态')),
                        OutlinedButton.icon(onPressed: _runningCommand ? null : () => _run('查看日志', _runtime.composeLogs), icon: const Icon(Icons.article), label: const Text('查看日志')),
                      ],
                    ),
                    if (_runningCommand) const Padding(padding: EdgeInsets.only(top: 12), child: LinearProgressIndicator()),
                    if (_commandResult != null) ...[
                      const SizedBox(height: 12),
                      Text('${_commandResult!.command} · exit=${_commandResult!.exitCode}', style: const TextStyle(fontWeight: FontWeight.w600)),
                      const SizedBox(height: 8),
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Theme.of(context).colorScheme.surfaceContainerHighest,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: SelectableText(_commandResult!.output),
                      ),
                    ],
                  ],
                ),
              ),
            )
          else
            const Card(
              child: ListTile(
                leading: Icon(Icons.info_outline),
                title: Text('移动端通过配对连接 Core'),
                subtitle: Text('Docker 控制只在 macOS / Windows 桌面端显示'),
              ),
            ),
        ],
      ),
    );
  }
}

class _StatusTile extends StatelessWidget {
  final String name;
  final String? status;

  const _StatusTile(this.name, this.status);

  @override
  Widget build(BuildContext context) {
    final ok = status == 'ok';
    return ListTile(
      dense: true,
      contentPadding: EdgeInsets.zero,
      leading: Icon(ok ? Icons.check_circle : Icons.error, color: ok ? Colors.green : Colors.red),
      title: Text(name),
      subtitle: Text(status ?? '?'),
    );
  }
}
