import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'providers/app_state.dart';
import 'screens/splash_screen.dart';
import 'screens/pairing_screen.dart';
import 'screens/dashboard_screen.dart';
import 'screens/kb_list_screen.dart';
import 'screens/kb_detail_screen.dart';
import 'screens/document_upload_screen.dart';
import 'screens/document_list_screen.dart';
import 'screens/document_detail_screen.dart';
import 'screens/chat_screen.dart';
import 'screens/debug_trace_screen.dart';
import 'screens/eval_screen.dart';
import 'screens/system_status_screen.dart';
import 'screens/settings_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(
    ChangeNotifierProvider(
      create: (_) => AppState(),
      child: const PersonalNotebookApp(),
    ),
  );
}

String? _routeStringArg(BuildContext context, [String? key]) {
  final args = ModalRoute.of(context)?.settings.arguments;
  if (args is String) return args;
  if (args is Map && key != null) return args[key]?.toString();
  return null;
}

class PersonalNotebookApp extends StatelessWidget {
  const PersonalNotebookApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'PersonalNotebook',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorSchemeSeed: const Color(0xFF2563EB),
        useMaterial3: true,
        brightness: Brightness.light,
      ),
      darkTheme: ThemeData(
        colorSchemeSeed: const Color(0xFF3B82F6),
        useMaterial3: true,
        brightness: Brightness.dark,
      ),
      home: const SplashScreen(),
      routes: {
        '/pairing': (_) => const PairingScreen(),
        '/dashboard': (_) => const DashboardScreen(),
        '/kb-list': (_) => const KbListScreen(),
        '/kb-detail': (context) => KbDetailScreen(kbId: _routeStringArg(context, 'kb_id')),
        '/document-upload': (context) => DocumentUploadScreen(kbId: _routeStringArg(context, 'kb_id')),
        '/document-list': (context) => DocumentListScreen(kbId: _routeStringArg(context, 'kb_id')),
        '/document-detail': (context) => DocumentDetailScreen(docId: _routeStringArg(context, 'doc_id')),
        '/chat': (context) => ChatScreen(kbId: _routeStringArg(context, 'kb_id')),
        '/debug-trace': (context) => DebugTraceScreen(kbId: _routeStringArg(context, 'kb_id')),
        '/eval': (_) => const EvalScreen(),
        '/system-status': (_) => const SystemStatusScreen(),
        '/settings': (_) => const SettingsScreen(),
      },
    );
  }
}
