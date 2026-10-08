import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../knowledge/data/knowledge_repository.dart';
import '../../processing/data/processing_job_api.dart';

final uploadControllerProvider =
    StateNotifierProvider.autoDispose<UploadController, UploadFlowState>((ref) {
  return UploadController(
    ref,
    ref.watch(knowledgeRepositoryProvider),
    ref.watch(processingJobApiProvider),
  );
});

class UploadFlowState {
  const UploadFlowState({
    this.isBusy = false,
    this.progress = 0,
    this.stage,
    this.message,
    this.isError = false,
  });

  final bool isBusy;
  final double progress;
  final String? stage;
  final String? message;
  final bool isError;

  UploadFlowState copyWith({
    bool? isBusy,
    double? progress,
    String? stage,
    String? message,
    bool? isError,
    bool clearMessage = false,
  }) {
    return UploadFlowState(
      isBusy: isBusy ?? this.isBusy,
      progress: progress ?? this.progress,
      stage: stage ?? this.stage,
      message: clearMessage ? null : message ?? this.message,
      isError: isError ?? this.isError,
    );
  }
}

class UploadController extends StateNotifier<UploadFlowState> {
  UploadController(
    this._ref,
    this._repository,
    this._jobApi,
  ) : super(const UploadFlowState());

  final Ref _ref;
  final KnowledgeRepository _repository;
  final ProcessingJobApi _jobApi;

  Future<void> pickAndUpload() async {
    if (state.isBusy) return;

    state = const UploadFlowState(
      isBusy: true,
      progress: 0.02,
      stage: 'Choose a file',
    );

    try {
      final file = await _repository.pickSupportedFile();
      if (file == null) {
        state = const UploadFlowState();
        return;
      }

      final source = await _repository.uploadSource(
        file,
        onProgress: (progress, stage) {
          state = UploadFlowState(
            isBusy: true,
            progress: progress,
            stage: stage,
          );
        },
      );

      state = const UploadFlowState(
        isBusy: true,
        progress: 0.95,
        stage: 'Queueing processing job',
      );

      try {
        await _jobApi.queueSource(source.id);
        state = UploadFlowState(
          progress: 1,
          stage: 'Queued',
          message: '${source.fileName} uploaded and queued successfully.',
        );
      } catch (error) {
        state = UploadFlowState(
          progress: 1,
          stage: 'Uploaded',
          message:
              '${source.fileName} was uploaded, but processing could not be queued. $error',
          isError: true,
        );
      }

      _refreshLists();
    } catch (error) {
      state = UploadFlowState(
        stage: 'Upload failed',
        message: _friendlyError(error),
        isError: true,
      );
      _refreshLists();
    }
  }

  void clearMessage() {
    state = state.copyWith(clearMessage: true, isError: false);
  }

  void _refreshLists() {
    _ref.invalidate(knowledgeSourcesProvider);
    _ref.invalidate(processingJobsProvider);
  }

  static String _friendlyError(Object error) {
    if (error is DuplicateKnowledgeFileException ||
        error is UnsupportedKnowledgeFileException ||
        error is KnowledgeUploadTooLargeException ||
        error is StateError) {
      return error.toString().replaceFirst('Bad state: ', '');
    }

    return 'Upload failed. Please try again.';
  }
}
