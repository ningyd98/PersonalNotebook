import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiClient {
  static const Duration shortTimeout = Duration(seconds: 30);
  static const Duration longTimeout = Duration(seconds: 120);

  String _baseUrl = 'http://localhost:8000';
  String? _token;

  String get baseUrl => _baseUrl;
  bool get isPaired => _token != null && _token!.isNotEmpty;

  void configure({required String baseUrl, String? token}) {
    _baseUrl = baseUrl.endsWith('/') ? baseUrl.substring(0, baseUrl.length - 1) : baseUrl;
    _token = token;
  }

  Map<String, String> get _headers => {
    'Content-Type': 'application/json',
    if (_token != null && _token!.isNotEmpty) 'Authorization': 'Bearer $_token',
  };

  Uri _uri(String path) {
    if (path.startsWith('http://') || path.startsWith('https://')) {
      return Uri.parse(path);
    }
    final normalized = path.startsWith('/') ? path : '/$path';
    return Uri.parse('$_baseUrl$normalized');
  }

  Future<Map<String, dynamic>> get(String path) {
    return _send(() => http.get(_uri(path), headers: _headers), timeout: shortTimeout);
  }

  Future<Map<String, dynamic>> post(String path, {Map<String, dynamic>? body}) {
    return _send(
      () => http.post(_uri(path), headers: _headers, body: body != null ? jsonEncode(body) : null),
      timeout: longTimeout,
    );
  }

  Future<Map<String, dynamic>> patch(String path, {Map<String, dynamic>? body}) {
    return _send(
      () => http.patch(_uri(path), headers: _headers, body: body != null ? jsonEncode(body) : null),
      timeout: shortTimeout,
    );
  }

  Future<Map<String, dynamic>> delete(String path) {
    return _send(() => http.delete(_uri(path), headers: _headers), timeout: shortTimeout);
  }

  Future<Map<String, dynamic>> upload(String path, String filePath, {Map<String, String>? fields}) async {
    try {
      final req = http.MultipartRequest('POST', _uri(path));
      final authHeader = _headers['Authorization'];
      if (authHeader != null && authHeader.isNotEmpty) {
        req.headers['Authorization'] = authHeader;
      }
      if (fields != null) req.fields.addAll(fields);
      req.files.add(await http.MultipartFile.fromPath('file', filePath));
      final streamed = await req.send().timeout(longTimeout);
      final body = await streamed.stream.bytesToString();
      return _handleBody(streamed.statusCode, body, streamed.reasonPhrase);
    } on TimeoutException {
      throw ApiException('请求超时，请检查 Core 服务或网络连接', 408);
    } on ApiException {
      rethrow;
    } catch (e) {
      throw ApiException('上传失败：$e', 0);
    }
  }

  Future<Map<String, dynamic>> _send(
    Future<http.Response> Function() request, {
    required Duration timeout,
  }) async {
    try {
      final resp = await request().timeout(timeout);
      return _handle(resp);
    } on TimeoutException {
      throw ApiException('请求超时，请检查 Core 服务或网络连接', 408);
    } on ApiException {
      rethrow;
    } catch (e) {
      throw ApiException('请求失败：$e', 0);
    }
  }

  Map<String, dynamic> _handle(http.Response resp) {
    return _handleBody(resp.statusCode, resp.body, resp.reasonPhrase);
  }

  Map<String, dynamic> _handleBody(int statusCode, String body, String? reasonPhrase) {
    if (statusCode >= 200 && statusCode < 300) {
      if (body.trim().isEmpty) return <String, dynamic>{};
      final decoded = _decodeJsonOrThrow(body, statusCode);
      if (decoded is Map<String, dynamic>) return decoded;
      return {'data': decoded};
    }

    Map<String, dynamic> err;
    try {
      final decoded = jsonDecode(body);
      err = decoded is Map<String, dynamic>
          ? decoded
          : {'error': {'code': 'HTTP_$statusCode', 'message': decoded.toString()}};
    } catch (_) {
      err = {
        'error': {
          'code': 'HTTP_$statusCode',
          'message': body.isNotEmpty ? body : (reasonPhrase ?? 'HTTP $statusCode'),
        }
      };
    }
    throw ApiException(_extractErrorMessage(err, body, statusCode), statusCode, err);
  }

  Object? _decodeJsonOrThrow(String body, int statusCode) {
    try {
      return jsonDecode(body);
    } catch (e) {
      final previewLength = body.length < 300 ? body.length : 300;
      throw ApiException('Core 返回了非 JSON 内容：${body.substring(0, previewLength)}', statusCode);
    }
  }

  String _extractErrorMessage(Map<String, dynamic> err, String fallback, int statusCode) {
    final error = err['error'];
    if (error is Map && error['message'] != null) return error['message'].toString();
    if (err['detail'] != null) return err['detail'].toString();
    if (err['message'] != null) return err['message'].toString();
    if (fallback.isNotEmpty) return fallback;
    return 'HTTP $statusCode';
  }
}

class ApiException implements Exception {
  final String message;
  final int statusCode;
  final Map<String, dynamic>? body;
  ApiException(this.message, this.statusCode, [this.body]);
  @override
  String toString() => 'ApiException($statusCode): $message';
}

final apiClient = ApiClient();
