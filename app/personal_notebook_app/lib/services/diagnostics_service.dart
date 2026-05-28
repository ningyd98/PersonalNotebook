import 'dart:io';

class DiagnosticsService {
  static const _sensitivePatterns = [
    'authorization', 'bearer', 'token', 'password', 'secret', 'api_key', 'key=',
  ];

  String? _lastErrorSummary;

  String? get lastErrorSummary => _lastErrorSummary;

  void recordError(String summary) {
    final lower = summary.toLowerCase();
    for (final kw in _sensitivePatterns) {
      if (lower.contains(kw)) {
        _lastErrorSummary = '[redacted sensitive error]';
        return;
      }
    }
    _lastErrorSummary = summary.substring(0, summary.length < 200 ? summary.length : 200);
  }

  String generateReport(String coreUrl, String tenantId, String? deviceId, bool isPaired) {
    String deviceDisplay;
    if (deviceId == null || deviceId.isEmpty) {
      deviceDisplay = 'none';
    } else if (deviceId.length < 8) {
      deviceDisplay = deviceId;
    } else {
      deviceDisplay = '${deviceId.substring(0, 8)}…';
    }

    final buffer = StringBuffer();
    buffer.writeln('=== PersonalNotebook Diagnostics ===');
    buffer.writeln('App Version: 0.2.0+2');
    buffer.writeln('Platform: ${Platform.operatingSystem} ${Platform.operatingSystemVersion}');
    buffer.writeln('Core URL: $coreUrl');
    buffer.writeln('Tenant ID: $tenantId');
    buffer.writeln('Device ID: $deviceDisplay');
    buffer.writeln('Paired: $isPaired');
    if (_lastErrorSummary != null) {
      buffer.writeln('Last API Error: $_lastErrorSummary');
    }
    buffer.writeln('=== End Diagnostics ===');
    return buffer.toString();
  }
}

final diagnosticsService = DiagnosticsService();
