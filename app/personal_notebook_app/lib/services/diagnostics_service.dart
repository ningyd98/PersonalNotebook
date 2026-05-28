import 'dart:io';
import 'package:flutter/foundation.dart';
import '../api/client.dart';

class DiagnosticsService {
  String? _lastErrorSummary;

  String? get lastErrorSummary => _lastErrorSummary;

  void recordError(String summary) {
    if (summary.contains('Bearer') || summary.contains('token=')) return;
    _lastErrorSummary = summary.substring(0, summary.length < 200 ? summary.length : 200);
  }

  String generateReport(String coreUrl, String tenantId, String? deviceId, bool isPaired) {
    final buffer = StringBuffer();
    buffer.writeln('=== PersonalNotebook Diagnostics ===');
    buffer.writeln('App Version: 0.2.0+2');
    buffer.writeln('Platform: ${Platform.operatingSystem} ${Platform.operatingSystemVersion}');
    buffer.writeln('Core URL: $coreUrl');
    buffer.writeln('Tenant ID: $tenantId');
    buffer.writeln('Device ID: ${deviceId != null ? deviceId.substring(0, 8) : "none"}…');
    buffer.writeln('Paired: $isPaired');
    if (_lastErrorSummary != null) {
      buffer.writeln('Last API Error: $_lastErrorSummary');
    }
    buffer.writeln('=== End Diagnostics ===');
    return buffer.toString();
  }
}

final diagnosticsService = DiagnosticsService();
