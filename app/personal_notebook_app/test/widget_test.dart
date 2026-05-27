import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:personal_notebook_app/screens/chat_screen.dart';

void main() {
  testWidgets('Chat screen renders KB input', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: ChatScreen(kbId: 'kb-test')));
    expect(find.text('知识库 ID'), findsOneWidget);
  });
}
