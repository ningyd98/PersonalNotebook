import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../api/client.dart';
import '../providers/app_state.dart';
import '../services/diagnostics_service.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});
  @override State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _apiKeyCtrl = TextEditingController();
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    final app = context.read<AppState>();
    _apiKeyCtrl.text = app.deepSeekApiKey;
  }

  Future<void> _saveApiKey() async {
    setState(() => _saving = true);
    await context.read<AppState>().setDeepSeekApiKey(_apiKeyCtrl.text.trim());
    if (mounted) {
      setState(() => _saving = false);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('API Key 已保存')),
      );
    }
  }

  @override
  void dispose() { _apiKeyCtrl.dispose(); super.dispose(); }

  void _showDiagnostics(BuildContext context) {
    final app = context.read<AppState>();
    final report = diagnosticsService.generateReport(
      apiClient.baseUrl, app.tenantId, app.deviceId, app.paired,
    );
    showModalBottomSheet(
      context: context, isScrollControlled: true,
      builder: (ctx) => Padding(
        padding: const EdgeInsets.all(24),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('诊断信息', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          const SizedBox(height: 4),
          const Text('以下信息不包含 Token 或文档内容，可安全分享', style: TextStyle(fontSize: 12, color: Colors.grey)),
          const SizedBox(height: 12),
          Container(width: double.infinity, padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(color: Colors.grey.shade100, borderRadius: BorderRadius.circular(8)),
            child: SelectableText(report, style: const TextStyle(fontSize: 12, fontFamily: 'monospace'))),
          const SizedBox(height: 16),
          Row(children: [
            Expanded(child: FilledButton.icon(
              onPressed: () { Clipboard.setData(ClipboardData(text: report)); Navigator.pop(ctx); ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('已复制到剪贴板'))); },
              icon: const Icon(Icons.copy, size: 18), label: const Text('复制诊断信息'))),
            const SizedBox(width: 8),
            OutlinedButton(onPressed: () => Navigator.pop(ctx), child: const Text('关闭')),
          ]),
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    return Scaffold(
      appBar: AppBar(title: const Text('设置')),
      body: ListView(children: [
        ListTile(title: const Text('Core 地址'), subtitle: Text(apiClient.baseUrl)),
        ListTile(title: const Text('Tenant'), subtitle: Text(app.tenantId)),
        if (app.deviceId != null)
          ListTile(title: const Text('Device'), subtitle: Text('${app.deviceId!.substring(0, 8)}…')),
        const ListTile(title: Text('版本'), subtitle: Text('0.2.0+2')),
        const Divider(),
        // Model Provider
        Padding(padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('模型提供商', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
          const SizedBox(height: 4),
          Container(padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(color: Colors.blue.shade50, borderRadius: BorderRadius.circular(8)),
            child: Row(children: [
              const Icon(Icons.info_outline, size: 16, color: Colors.blue),
              const SizedBox(width: 8),
              Expanded(child: Text(app.deepSeekApiKey.isNotEmpty
                ? '当前模式: Hybrid\n生成: DeepSeek / OpenAI API\n索引与检索: 本地 Core'
                : '当前模式: Local\n生成: 本地 Ollama\n索引与检索: 本地 Core',
                style: const TextStyle(fontSize: 12, color: Colors.blue))),
            ])),
          const SizedBox(height: 8),
          const Text('DeepSeek / OpenAI API Key', style: TextStyle(fontSize: 13)),
          const SizedBox(height: 4),
          const Text('填写后使用在线 API (DeepSeek/OpenAI)。留空则自动使用本地 Ollama。Key 仅保存在本地。', style: TextStyle(fontSize: 11, color: Colors.grey)),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(child: TextField(controller: _apiKeyCtrl,
              decoration: const InputDecoration(hintText: 'sk-...', border: OutlineInputBorder(), isDense: true),
              obscureText: true)),
            const SizedBox(width: 8),
            FilledButton(onPressed: _saving ? null : _saveApiKey,
              child: _saving ? const SizedBox(height: 16, width: 16, child: CircularProgressIndicator(strokeWidth: 2)) : const Text('保存')),
          ]),
        ])),
        const Divider(),
        ListTile(
          leading: const Icon(Icons.bug_report),
          title: const Text('反馈问题'),
          subtitle: const Text('查看并复制诊断信息'),
          onTap: () => _showDiagnostics(context),
        ),
        ListTile(
          leading: const Icon(Icons.link_off, color: Colors.red),
          title: const Text('断开连接'),
          subtitle: const Text('清除配对信息并返回配对页'),
          onTap: () async {
            await context.read<AppState>().unpair();
            if (context.mounted) Navigator.pushReplacementNamed(context, '/pairing');
          },
        ),
      ]),
    );
  }
}
