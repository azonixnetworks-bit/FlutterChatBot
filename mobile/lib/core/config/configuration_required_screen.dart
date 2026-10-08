import 'package:flutter/material.dart';

class ConfigurationRequiredScreen extends StatelessWidget {
  const ConfigurationRequiredScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Multimodal Knowledge AI')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 640),
            child: const Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.settings_suggest_outlined, size: 56),
                SizedBox(height: 16),
                Text(
                  'Supabase setup required',
                  style: TextStyle(fontSize: 24, fontWeight: FontWeight.w600),
                ),
                SizedBox(height: 12),
                Text(
                  'Run the app with SUPABASE_URL and '
                  'SUPABASE_PUBLISHABLE_KEY using --dart-define. '
                  'Never place a Supabase secret/service-role key '
                  'inside the Flutter app.',
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
