import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../api/client.dart';

class AppState extends ChangeNotifier {
  final _storage = const FlutterSecureStorage();
  bool _initialized = false;
  bool _paired = false;
  String _coreUrl = '';
  String _tenantId = 'default';
  String? _deviceId;
  bool _coreRunning = false;

  String _deepSeekApiKey = '';

  bool get initialized => _initialized;
  bool get paired => _paired;
  String get coreUrl => _coreUrl;
  String get tenantId => _tenantId;
  String? get deviceId => _deviceId;
  bool get coreRunning => _coreRunning;
  String get deepSeekApiKey => _deepSeekApiKey;

  Future<void> init() async {
    final url = await _storage.read(key: 'core_url');
    final token = await _storage.read(key: 'auth_token');
    final tenantId = await _storage.read(key: 'tenant_id');
    final deviceId = await _storage.read(key: 'device_id');
    if (tenantId != null && tenantId.isNotEmpty) _tenantId = tenantId;
    if (deviceId != null && deviceId.isNotEmpty) _deviceId = deviceId;
    final apiKey = await _storage.read(key: 'deepseek_api_key');
    if (apiKey != null) _deepSeekApiKey = apiKey;
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
      final data = resp['data'] as Map<String, dynamic>?;
      final verified = resp['verified'] == true ||
          data?['verified'] == true ||
          resp['success'] == true ||
          resp['status'] == 'ok';
      if (verified) {
        await _storage.write(key: 'core_url', value: url);
        await _storage.write(key: 'auth_token', value: token);
        final tenantId = (resp['tenant_id'] ?? data?['tenant_id'])?.toString();
        if (tenantId != null && tenantId.isNotEmpty) {
          _tenantId = tenantId;
          await _storage.write(key: 'tenant_id', value: tenantId);
        }
        final deviceId = (resp['device_id'] ?? data?['device_id'])?.toString();
        if (deviceId != null && deviceId.isNotEmpty) {
          _deviceId = deviceId;
          await _storage.write(key: 'device_id', value: deviceId);
        }
        _coreUrl = url;
        _paired = true;
        notifyListeners();
        return true;
      }
    } on ApiException catch (e) {
      debugPrint('Pairing failed: $e');
      rethrow; // let PairingScreen handle categorization
    } catch (e) {
      debugPrint('Pairing failed: $e');
    }
    return false;
  }

  Future<void> unpair() async {
    await _storage.delete(key: 'core_url');
    await _storage.delete(key: 'auth_token');
    await _storage.delete(key: 'tenant_id');
    await _storage.delete(key: 'device_id');
    apiClient.configure(baseUrl: _coreUrl, token: null);
    _paired = false;
    _deviceId = null;
    notifyListeners();
  }

  void setCoreRunning(bool running) {
    _coreRunning = running;
    notifyListeners();
  }

  Future<void> setDeepSeekApiKey(String key) async {
    _deepSeekApiKey = key;
    if (key.isNotEmpty) {
      await _storage.write(key: 'deepseek_api_key', value: key);
    } else {
      await _storage.delete(key: 'deepseek_api_key');
    }
    notifyListeners();
  }
}
