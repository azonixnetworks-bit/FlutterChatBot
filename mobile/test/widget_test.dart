import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:multimodal_knowledge_ai/app/app.dart';

void main() {
  testWidgets('shows Supabase configuration guidance when not configured',
      (tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: KnowledgeAiApp(),
      ),
    );

    expect(find.text('Supabase setup required'), findsOneWidget);
    expect(find.textContaining('SUPABASE_URL'), findsOneWidget);
  });
}
