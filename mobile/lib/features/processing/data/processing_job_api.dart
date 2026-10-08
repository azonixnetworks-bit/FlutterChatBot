import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../domain/processing_job.dart';

final processingJobApiProvider = Provider<ProcessingJobApi>((ref) {
  return ProcessingJobApi(ref.watch(apiClientProvider));
});

class ProcessingJobApi {
  ProcessingJobApi(this._dio);

  final Dio _dio;

  Future<ProcessingJob> queueSource(String sourceId) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/knowledge/jobs',
        data: {
          'source_id': sourceId,
          'job_type': 'ingest',
        },
      );

      final data = response.data;
      if (data == null) {
        throw StateError('Processing API returned an empty response.');
      }

      return ProcessingJob.fromJson(data);
    } on DioException catch (error) {
      final detail = error.response?.data;
      if (detail is Map<String, dynamic> && detail['detail'] is String) {
        throw StateError(detail['detail'] as String);
      }
      throw StateError(
        'Unable to queue processing. Check that FastAPI is running.',
      );
    }
  }
}
