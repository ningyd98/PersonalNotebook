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
        '/kb-detail': (_) => const KbDetailScreen(),
        '/document-upload': (_) => const DocumentUploadScreen(),
        '/document-list': (_) => const DocumentListScreen(),
        '/document-detail': (_) => const DocumentDetailScreen(),
        '/chat': (_) => const ChatScreen(),
        '/debug-trace': (_) => const DebugTraceScreen(),
        '/eval': (_) => const EvalScreen(),
        '/system-status': (_) => const SystemStatusScreen(),
        '/settings': (_) => const SettingsScreen(),
      },
    );
  }
}
