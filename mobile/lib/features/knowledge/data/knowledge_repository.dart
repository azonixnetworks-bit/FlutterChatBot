import 'package:crypto/crypto.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:uuid/uuid.dart';

import '../../../core/supabase/supabase_provider.dart';
import '../../processing/domain/processing_job.dart';
import '../domain/knowledge_source.dart';

final knowledgeRepositoryProvider = Provider<KnowledgeRepository>((ref) {
  return KnowledgeRepository(ref.watch(supabaseClientProvider));
});

final knowledgeSourcesProvider =
    FutureProvider.autoDispose<List<KnowledgeSource>>((ref) {
  return ref.watch(knowledgeRepositoryProvider).listSources();
});

final processingJobsProvider =
    FutureProvider.autoDispose<Map<String, ProcessingJob>>((ref) {
  return ref.watch(knowledgeRepositoryProvider).latestJobsBySource();
});

class DuplicateKnowledgeFileException implements Exception {
  const DuplicateKnowledgeFileException(this.fileName);

  final String fileName;

  @override
  String toString() => 'This file content is already uploaded as $fileName.';
}

class UnsupportedKnowledgeFileException implements Exception {
  const UnsupportedKnowledgeFileException(this.extension);

  final String extension;

  @override
  String toString() => 'Unsupported file type: .$extension';
}

class KnowledgeUploadTooLargeException implements Exception {
  const KnowledgeUploadTooLargeException(this.maxBytes);

  final int maxBytes;

  @override
  String toString() {
    final megabytes = (maxBytes / (1024 * 1024)).round();
    return 'File is larger than the configured $megabytes MB upload limit.';
  }
}

class KnowledgeRepository {
  KnowledgeRepository(this._client);

  static const _bucket = 'knowledge-files';
  static const _uuid = Uuid();

  static const supportedExtensions = <String>[
    'txt',
    'pdf',
    'docx',
    'csv',
    'xls',
    'xlsx',
    'jpg',
    'jpeg',
    'png',
    'webp',
  ];

  final SupabaseClient _client;

  int get maxUploadBytes {
    const value = String.fromEnvironment(
      'UPLOAD_MAX_BYTES',
      defaultValue: '52428800',
    );
    return int.tryParse(value) ?? 52428800;
  }

  Future<PlatformFile?> pickSupportedFile() {
    return FilePicker.pickFile(
      dialogTitle: 'Choose a knowledge file',
      type: FileType.custom,
      allowedExtensions: supportedExtensions,
    );
  }

  Future<KnowledgeSource> uploadSource(
    PlatformFile file, {
    void Function(double progress, String stage)? onProgress,
  }) async {
    final user = _client.auth.currentUser;
    if (user == null) {
      throw const AuthException('You must be signed in to upload files.');
    }

    final extension = (file.extension ?? '').toLowerCase();
    if (!supportedExtensions.contains(extension)) {
      throw UnsupportedKnowledgeFileException(extension);
    }

    onProgress?.call(0.1, 'Checking file');
    final length = file.lengthSync() ?? await file.length();
    if (length == null || length <= 0) {
      throw StateError('The selected file is empty or unreadable.');
    }
    if (length > maxUploadBytes) {
      throw KnowledgeUploadTooLargeException(maxUploadBytes);
    }

    onProgress?.call(0.2, 'Reading file');
    final bytes = await file.readAsBytes();
    final contentHash = sha256.convert(bytes).toString();

    final existing = await _client
        .from('knowledge_sources')
        .select('id,file_name')
        .eq('user_id', user.id)
        .eq('content_hash', contentHash)
        .limit(1);

    if (existing.isNotEmpty) {
      throw DuplicateKnowledgeFileException(
        existing.first['file_name'] as String,
      );
    }

    final sourceId = _uuid.v4();
    final safeName = _sanitizeFileName(file.name);
    final storagePath = '${user.id}/$sourceId/$safeName';
    final mimeType = _mimeTypeFor(extension);

    onProgress?.call(0.45, 'Uploading to private storage');
    await _client.storage.from(_bucket).uploadBinary(
          storagePath,
          bytes,
          fileOptions: FileOptions(
            contentType: mimeType,
            upsert: false,
          ),
        );

    try {
      onProgress?.call(0.8, 'Registering knowledge source');
      final row = await _client
          .from('knowledge_sources')
          .insert({
            'id': sourceId,
            'user_id': user.id,
            'file_name': file.name,
            'file_type': extension,
            'mime_type': mimeType,
            'storage_bucket': _bucket,
            'storage_path': storagePath,
            'file_size_bytes': length,
            'content_hash': contentHash,
            'status': 'uploaded',
            'metadata': {
              'original_file_name': file.name,
            },
          })
          .select()
          .single();

      onProgress?.call(0.9, 'Upload registered');
      return KnowledgeSource.fromJson(row);
    } catch (_) {
      try {
        await _client.storage.from(_bucket).remove([storagePath]);
      } catch (_) {
        // Best-effort rollback. The source row was not created.
      }
      rethrow;
    }
  }

  Future<List<KnowledgeSource>> listSources() async {
    final rows = await _client
        .from('knowledge_sources')
        .select()
        .order('created_at', ascending: false);

    return rows
        .map((row) => KnowledgeSource.fromJson(row))
        .toList(growable: false);
  }

  Future<Map<String, ProcessingJob>> latestJobsBySource() async {
    final rows = await _client
        .from('processing_jobs')
        .select()
        .order('created_at', ascending: false);

    final jobs = <String, ProcessingJob>{};
    for (final row in rows) {
      final job = ProcessingJob.fromJson(row);
      jobs.putIfAbsent(job.sourceId, () => job);
    }
    return jobs;
  }

  static String _sanitizeFileName(String name) {
    final sanitized = name.replaceAll(
      RegExp(r"[^A-Za-z0-9._-]"),
      '_',
    );
    return sanitized.isEmpty ? 'knowledge_file' : sanitized;
  }

  static String _mimeTypeFor(String extension) {
    return switch (extension) {
      'txt' => 'text/plain',
      'pdf' => 'application/pdf',
      'docx' =>
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'csv' => 'text/csv',
      'xls' => 'application/vnd.ms-excel',
      'xlsx' =>
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'jpg' || 'jpeg' => 'image/jpeg',
      'png' => 'image/png',
      'webp' => 'image/webp',
      _ => 'application/octet-stream',
    };
  }
}
