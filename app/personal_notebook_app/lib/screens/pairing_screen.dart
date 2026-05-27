import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import '../providers/app_state.dart';

class PairingScreen extends StatefulWidget {
  const PairingScreen({super.key});
  @override
  State<PairingScreen> createState() => _PairingScreenState();
}

class _PairingScreenState extends State<PairingScreen> {
  final _urlCtrl = TextEditingController(text: 'http://192.168.1.10:8000');
  final _tokenCtrl = TextEditingController();
  bool _scanning = false;
  bool _connecting = false;
  String? _error;

  Future<void> _pair() async {
    setState(() { _connecting = true; _error = null; });
    final ok = await context.read<AppState>().pair(url: _urlCtrl.text.trim(), token: _tokenCtrl.text.trim());
    if (!mounted) return;
    if (ok) {
      Navigator.pushReplacementNamed(context, '/dashboard');
    } else {
      setState(() { _error = '连接失败，请检查地址和 Token'; _connecting = false; });
    }
  }

  void _onScan(String barcode) {
    try {
      if (barcode.trimLeft().startsWith('{')) {
        final data = jsonDecode(barcode) as Map<String, dynamic>;
        _urlCtrl.text = data['core_base_url']?.toString() ?? _urlCtrl.text;
        _tokenCtrl.text = data['token']?.toString() ?? '';
        setState(() { _scanning = false; });
        return;
      }
      final qr = Uri.parse(barcode);
      _urlCtrl.text = '${qr.scheme}://${qr.host}:${qr.port}';
      _tokenCtrl.text = qr.queryParameters['token'] ?? '';
      setState(() { _scanning = false; });
    } catch (e) {
      setState(() => _error = '无法解析二维码：$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('配对 Core')),
      body: _scanning ? MobileScanner(onDetect: (capture) {
        for (final barcode in capture.barcodes) {
          if (barcode.rawValue != null) _onScan(barcode.rawValue!);
        }
      }) : Padding(
        padding: const EdgeInsets.all(24),
        child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
          const Icon(Icons.link, size: 64, color: Colors.blue),
          const SizedBox(height: 16),
          const Text('连接 PersonalNotebook Core', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w600)),
          const SizedBox(height: 24),
          TextField(controller: _urlCtrl, decoration: const InputDecoration(labelText: 'Core 地址', hintText: 'http://192.168.1.10:8000', border: OutlineInputBorder())),
          const SizedBox(height: 12),
          TextField(controller: _tokenCtrl, decoration: const InputDecoration(labelText: '访问 Token', border: OutlineInputBorder()), obscureText: true),
          if (_error != null) Padding(padding: const EdgeInsets.only(top: 8), child: Text(_error!, style: const TextStyle(color: Colors.red, fontSize: 13))),
          const SizedBox(height: 24),
          SizedBox(width: double.infinity, child: FilledButton(onPressed: _connecting ? null : _pair, child: _connecting ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2)) : const Text('连接'))),
          const SizedBox(height: 12),
          OutlinedButton.icon(onPressed: () => setState(() => _scanning = true), icon: const Icon(Icons.qr_code_scanner), label: const Text('扫描二维码')),
        ]),
      ),
    );
  }
}
