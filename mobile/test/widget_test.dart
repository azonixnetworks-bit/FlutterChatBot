import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:multimodal_knowledge_ai/app/app.dart';

void main() {
  testWidgets('shows Phase 1 home screen', (tester) async {
    await tester.pumpWidget(const ProviderScope(child: KnowledgeAiApp()));
    expect(find.text('Multimodal Knowledge AI'), findsOneWidget);
    expect(find.text('Phase 1 foundation is running.'), findsOneWidget);
  });
}
