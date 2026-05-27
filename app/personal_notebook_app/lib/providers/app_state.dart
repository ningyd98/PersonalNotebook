import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../api/client.dart';

class AppState extends ChangeNotifier {
  final _storage = const FlutterSecureStorage();
  bool _initialized = false;
  bool _paired = false;
  String _coreUrl = '';
  String _tenantId = 'default';
  bool _coreRunning = false;

  bool get initialized => _initialized;
  bool get paired => _paired;
  String get coreUrl => _coreUrl;
  String get tenantId => _tenantId;
  bool get coreRunning => _coreRunning;

  Future<void> init() async {
    final url = await _storage.read(key: 'core_url');
    final token = await _storage.read(key: 'auth_token');
    if (url != null && url.isNotEmpty) {
      _coreUrl = url;
      apiClient.configure(baseUrl: url, token: token);
      _paired = true;
    }
    _initialized = true;
    notifyListeners();
  }

  Future<bool> pair({required String url, required String token}) async {
    try {
      apiClient.configure(baseUrl: url, token: token);
      final resp = await apiClient.post('/auth/pair/verify', body: {'token': token});
      if (resp['success'] == true || resp['status'] == 'ok') {
        await _storage.write(key: 'core_url', value: url);
        await _storage.write(key: 'auth_token', value: token);
        _coreUrl = url;
        _paired = true;
        notifyListeners();
        return true;
      }
    } catch (_) {}
    return false;
  }

  Future<void> unpair() async {
    await _storage.delete(key: 'core_url');
    await _storage.delete(key: 'auth_token');
    apiClient.configure(baseUrl: _coreUrl, token: null);
    _paired = false;
    notifyListeners();
  }

  void setCoreRunning(bool running) {
    _coreRunning = running;
    notifyListeners();
  }
}
