import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../processing/domain/processing_job.dart';
import '../../upload/presentation/upload_controller.dart';
import '../data/knowledge_repository.dart';
import '../domain/knowledge_source.dart';

class KnowledgeLibraryScreen extends ConsumerWidget {
  const KnowledgeLibraryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final sources = ref.watch(knowledgeSourcesProvider);
    final jobs = ref.watch(processingJobsProvider);
    final upload = ref.watch(uploadControllerProvider);

    ref.listen(uploadControllerProvider, (previous, next) {
      if (next.message == null || next.message == previous?.message) return;

      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(
          SnackBar(
            content: Text(next.message!),
            backgroundColor:
                next.isError ? Theme.of(context).colorScheme.error : null,
          ),
        );
    });

    return Scaffold(
      appBar: AppBar(
        title: const Text('Knowledge Library'),
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: () {
              ref.invalidate(knowledgeSourcesProvider);
              ref.invalidate(processingJobsProvider);
            },
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: upload.isBusy
            ? null
            : () => ref.read(uploadControllerProvider.notifier).pickAndUpload(),
        icon: const Icon(Icons.upload_file),
        label: const Text('Upload'),
      ),
      body: Column(
        children: [
          if (upload.isBusy || upload.stage != null)
            _UploadProgressCard(state: upload),
          Expanded(
            child: sources.when(
              data: (items) => jobs.when(
                data: (jobMap) => _KnowledgeList(
                  sources: items,
                  jobs: jobMap,
                  onRefresh: () async {
                    ref.invalidate(knowledgeSourcesProvider);
                    ref.invalidate(processingJobsProvider);
                    await ref.read(knowledgeSourcesProvider.future);
                  },
                ),
                loading: () =>
                    const Center(child: CircularProgressIndicator()),
                error: (error, stackTrace) => _ErrorView(
                  message: 'Unable to load processing jobs.',
                  onRetry: () => ref.invalidate(processingJobsProvider),
                ),
              ),
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (error, stackTrace) => _ErrorView(
                message: 'Unable to load your knowledge files.',
                onRetry: () => ref.invalidate(knowledgeSourcesProvider),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _UploadProgressCard extends StatelessWidget {
  const _UploadProgressCard({required this.state});

  final UploadFlowState state;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.fromLTRB(16, 12, 16, 4),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              state.stage ?? 'Preparing upload',
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 10),
            LinearProgressIndicator(
              value: state.isBusy ? state.progress.clamp(0, 1) : 1,
            ),
          ],
        ),
      ),
    );
  }
}

class _KnowledgeList extends StatelessWidget {
  const _KnowledgeList({
    required this.sources,
    required this.jobs,
    required this.onRefresh,
  });

  final List<KnowledgeSource> sources;
  final Map<String, ProcessingJob> jobs;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    if (sources.isEmpty) {
      return RefreshIndicator(
        onRefresh: onRefresh,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          children: const [
            SizedBox(height: 120),
            Icon(Icons.folder_open_outlined, size: 72),
            SizedBox(height: 16),
            Center(
              child: Text(
                'No knowledge files yet.\nUpload your first file.',
                textAlign: TextAlign.center,
              ),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: onRefresh,
      child: ListView.separated(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 96),
        itemCount: sources.length,
        separatorBuilder: (_, __) => const SizedBox(height: 8),
        itemBuilder: (context, index) {
          final source = sources[index];
          final job = jobs[source.id];

          return Card(
            child: ListTile(
              leading: CircleAvatar(
                child: Text(source.fileType.toUpperCase()),
              ),
              title: Text(
                source.fileName,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              subtitle: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SizedBox(height: 4),
                  Text(_formatBytes(source.fileSizeBytes)),
                  const SizedBox(height: 6),
                  _StatusLine(source: source, job: job),
                ],
              ),
              isThreeLine: true,
            ),
          );
        },
      ),
    );
  }

  static String _formatBytes(int? bytes) {
    if (bytes == null) return 'Unknown size';
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) {
      return '${(bytes / 1024).toStringAsFixed(1)} KB';
    }
    return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }
}

class _StatusLine extends StatelessWidget {
  const _StatusLine({
    required this.source,
    required this.job,
  });

  final KnowledgeSource source;
  final ProcessingJob? job;

  @override
  Widget build(BuildContext context) {
    final status = job?.status ?? source.status;
    final progress = job?.progress;

    return Row(
      children: [
        Chip(
          visualDensity: VisualDensity.compact,
          label: Text(status.toUpperCase()),
        ),
        if (progress != null) ...[
          const SizedBox(width: 8),
          Expanded(
            child: LinearProgressIndicator(
              value: progress.clamp(0, 100) / 100,
            ),
          ),
          const SizedBox(width: 8),
          Text('$progress%'),
        ],
      ],
    );
  }
}

class _ErrorView extends StatelessWidget {
  const _ErrorView({
    required this.message,
    required this.onRetry,
  });

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline, size: 48),
            const SizedBox(height: 12),
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 12),
            OutlinedButton(
              onPressed: onRetry,
              child: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }
}
