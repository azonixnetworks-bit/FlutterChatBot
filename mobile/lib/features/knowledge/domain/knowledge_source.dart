class KnowledgeSource {
  const KnowledgeSource({
    required this.id,
    required this.fileName,
    required this.fileType,
    required this.storagePath,
    required this.status,
    required this.createdAt,
    this.mimeType,
    this.fileSizeBytes,
    this.errorMessage,
  });

  factory KnowledgeSource.fromJson(Map<String, dynamic> json) {
    return KnowledgeSource(
      id: json['id'] as String,
      fileName: json['file_name'] as String,
      fileType: json['file_type'] as String,
      mimeType: json['mime_type'] as String?,
      storagePath: json['storage_path'] as String,
      fileSizeBytes: json['file_size_bytes'] as int?,
      status: json['status'] as String,
      errorMessage: json['error_message'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }

  final String id;
  final String fileName;
  final String fileType;
  final String? mimeType;
  final String storagePath;
  final int? fileSizeBytes;
  final String status;
  final String? errorMessage;
  final DateTime createdAt;
}
