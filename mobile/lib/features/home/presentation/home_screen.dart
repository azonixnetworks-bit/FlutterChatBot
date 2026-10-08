import 'package:flutter/material.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Multimodal Knowledge AI')),
      body: const Center(
        child: Text(
          'Phase 1 foundation is running.',
          textAlign: TextAlign.center,
        ),
      ),
    );
  }
}
