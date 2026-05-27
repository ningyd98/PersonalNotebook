import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiClient {
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

  Future<Map<String, dynamic>> get(String path) async {
    final resp = await http.get(Uri.parse('$_baseUrl$path'), headers: _headers).timeout(const Duration(seconds: 30));
    return _handle(resp);
  }

  Future<Map<String, dynamic>> post(String path, {Map<String, dynamic>? body}) async {
    final resp = await http.post(Uri.parse('$_baseUrl$path'), headers: _headers, body: body != null ? jsonEncode(body) : null).timeout(const Duration(seconds: 120));
    return _handle(resp);
  }

  Future<Map<String, dynamic>> patch(String path, {Map<String, dynamic>? body}) async {
    final resp = await http.patch(Uri.parse('$_baseUrl$path'), headers: _headers, body: body != null ? jsonEncode(body) : null).timeout(const Duration(seconds: 30));
    return _handle(resp);
  }

  Future<Map<String, dynamic>> delete(String path) async {
    final resp = await http.delete(Uri.parse('$_baseUrl$path'), headers: _headers).timeout(const Duration(seconds: 30));
    return _handle(resp);
  }

  Future<Map<String, dynamic>> upload(String path, String filePath, {Map<String, String>? fields}) async {
    final req = http.MultipartRequest('POST', Uri.parse('$_baseUrl$path'));
    req.headers.addAll({'Authorization': _headers['Authorization'] ?? ''});
    if (fields != null) req.fields.addAll(fields);
    req.files.add(await http.MultipartFile.fromPath('file', filePath));
    final resp = await req.send().timeout(const Duration(seconds: 120));
    final body = await resp.stream.bytesToString();
    return jsonDecode(body) as Map<String, dynamic>;
  }

  Map<String, dynamic> _handle(http.Response resp) {
    if (resp.statusCode >= 200 && resp.statusCode < 300) {
      return jsonDecode(resp.body) as Map<String, dynamic>;
    }
    Map<String, dynamic> err;
    try {
      err = jsonDecode(resp.body) as Map<String, dynamic>;
    } catch (_) {
      err = {'error': {'code': 'HTTP_${resp.statusCode}', 'message': resp.body}};
    }
    throw ApiException(err['error']?['message'] ?? resp.body, resp.statusCode, err);
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
