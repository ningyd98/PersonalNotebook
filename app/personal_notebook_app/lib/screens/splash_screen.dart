import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});
  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    final app = context.read<AppState>();
    await app.init();
    if (!mounted) return;
    Navigator.pushReplacementNamed(context, app.paired ? '/dashboard' : '/pairing');
  }

  @override
  Widget build(BuildContext context) => const Scaffold(
    body: Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
      Icon(Icons.menu_book, size: 64, color: Colors.blue),
      SizedBox(height: 16),
      Text('PersonalNotebook', style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
      SizedBox(height: 8),
      CircularProgressIndicator(),
    ])),
  );
}
