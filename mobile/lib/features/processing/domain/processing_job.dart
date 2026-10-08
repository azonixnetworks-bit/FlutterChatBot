class ProcessingJob {
  const ProcessingJob({
    required this.id,
    required this.sourceId,
    required this.status,
    required this.progress,
    required this.jobType,
    required this.createdAt,
    this.currentStep,
    this.errorMessage,
  });

  factory ProcessingJob.fromJson(Map<String, dynamic> json) {
    return ProcessingJob(
      id: json['id'] as String,
      sourceId: json['source_id'] as String,
      status: json['status'] as String,
      progress: json['progress'] as int,
      jobType: json['job_type'] as String,
      currentStep: json['current_step'] as String?,
      errorMessage: json['error_message'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }

  final String id;
  final String sourceId;
  final String status;
  final int progress;
  final String jobType;
  final String? currentStep;
  final String? errorMessage;
  final DateTime createdAt;
}
