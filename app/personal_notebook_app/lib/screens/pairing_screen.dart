import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import '../api/client.dart';
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

  String? _validate() {
    final url = _urlCtrl.text.trim();
    if (url.isEmpty) return '请输入 Core 地址';
    if (!url.startsWith('http://') && !url.startsWith('https://')) return 'Core 地址必须以 http:// 或 https:// 开头';
    if (_tokenCtrl.text.trim().isEmpty) return '请输入访问 Token';
    return null;
  }

  Future<void> _pair() async {
    final validationError = _validate();
    if (validationError != null) { setState(() => _error = validationError); return; }

    setState(() { _connecting = true; _error = null; });
    try {
      final ok = await context.read<AppState>().pair(
        url: _urlCtrl.text.trim(),
        token: _tokenCtrl.text.trim(),
      );
      if (!mounted) return;
      if (ok) {
        Navigator.pushReplacementNamed(context, '/dashboard');
      } else {
        setState(() { _error = '配对失败：Core 返回验证失败'; _connecting = false; });
      }
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _connecting = false;
        switch (e.statusCode) {
          case 401: _error = 'Token 无效、已过期或已撤销，请重新配对'; break;
          case 403: _error = 'Core 拒绝访问 (403)'; break;
          case 408: case 0: _error = '网络不可达或连接超时，请检查 Core 地址'; break;
          default: _error = e.message;
        }
      });
    } catch (e) {
      if (!mounted) return;
      setState(() { _error = '连接失败：$e'; _connecting = false; });
    }
  }

  Future<void> _clearPairing() async {
    await context.read<AppState>().unpair();
    _urlCtrl.text = 'http://192.168.1.10:8000';
    _tokenCtrl.clear();
    setState(() => _error = null);
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
      setState(() { _scanning = false; _error = '扫码失败，请手动输入 URL 和 Token'; });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_scanning) {
      return Scaffold(
        appBar: AppBar(title: const Text('扫码配对'), leading: IconButton(icon: const Icon(Icons.arrow_back), onPressed: () => setState(() => _scanning = false))),
        body: MobileScanner(onDetect: (capture) {
          for (final barcode in capture.barcodes) {
            if (barcode.rawValue != null) _onScan(barcode.rawValue!);
          }
        }),
      );
    }

    return Scaffold(
      appBar: AppBar(title: const Text('配对 Core')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
          const Icon(Icons.link, size: 64, color: Colors.blue),
          const SizedBox(height: 16),
          const Text('连接 PersonalNotebook Core', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w600)),
          const SizedBox(height: 24),
          TextField(controller: _urlCtrl, decoration: const InputDecoration(labelText: 'Core 地址', hintText: 'http://192.168.1.10:8000', border: OutlineInputBorder()), keyboardType: TextInputType.url),
          const SizedBox(height: 12),
          TextField(controller: _tokenCtrl, decoration: const InputDecoration(labelText: '访问 Token', border: OutlineInputBorder()), obscureText: true),
          if (_error != null) Padding(padding: const EdgeInsets.only(top: 8), child: Container(width: double.infinity, padding: const EdgeInsets.all(10), decoration: BoxDecoration(color: Colors.red.shade50, borderRadius: BorderRadius.circular(8), border: Border.all(color: Colors.red.shade200)), child: Row(children: [Icon(Icons.error_outline, size: 16, color: Colors.red.shade700), const SizedBox(width: 8), Expanded(child: Text(_error!, style: TextStyle(color: Colors.red.shade700, fontSize: 13)))],))),
          const SizedBox(height: 24),
          SizedBox(width: double.infinity, child: FilledButton(onPressed: _connecting ? null : _pair, child: _connecting ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2)) : const Text('连接'))),
          const SizedBox(height: 12),
          Row(children: [
            Expanded(child: OutlinedButton.icon(onPressed: () => setState(() => _scanning = true), icon: const Icon(Icons.qr_code_scanner, size: 18), label: const Text('扫码'))),
            const SizedBox(width: 8),
            OutlinedButton.icon(onPressed: _clearPairing, icon: const Icon(Icons.delete_outline, size: 18), label: const Text('清除'), style: OutlinedButton.styleFrom(foregroundColor: Colors.red)),
          ]),
        ]),
      ),
    );
  }
}
