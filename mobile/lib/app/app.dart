import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/config/configuration_required_screen.dart';
import '../core/router/app_router.dart';

class KnowledgeAiApp extends ConsumerWidget {
  const KnowledgeAiApp({
    super.key,
    this.supabaseReady = false,
  });

  final bool supabaseReady;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = ThemeData(
      colorScheme: ColorScheme.fromSeed(seedColor: Colors.indigo),
      useMaterial3: true,
    );

    if (!supabaseReady) {
      return MaterialApp(
        title: 'Multimodal Knowledge AI',
        debugShowCheckedModeBanner: false,
        theme: theme,
        home: const ConfigurationRequiredScreen(),
      );
    }

    final router = ref.watch(appRouterProvider);

    return MaterialApp.router(
      title: 'Multimodal Knowledge AI',
      debugShowCheckedModeBanner: false,
      routerConfig: router,
      theme: theme,
    );
  }
}
