import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../api/client.dart';
import '../providers/app_state.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    return Scaffold(
      appBar: AppBar(title: const Text('设置')),
      body: ListView(
        children: [
          ListTile(title: const Text('Core 地址'), subtitle: Text(apiClient.baseUrl)),
          ListTile(title: const Text('Tenant'), subtitle: Text(app.tenantId)),
          const ListTile(title: Text('版本'), subtitle: Text('0.2.0')),
          ListTile(
            title: const Text('断开连接'),
            leading: const Icon(Icons.link_off),
            onTap: () async {
              await context.read<AppState>().unpair();
              if (context.mounted) Navigator.pushReplacementNamed(context, '/pairing');
            },
          ),
        ],
      ),
    );
  }
}
