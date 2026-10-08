import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../data/auth_repository.dart';

final authControllerProvider =
    StateNotifierProvider.autoDispose<AuthController, AuthFormState>((ref) {
  return AuthController(ref.watch(authRepositoryProvider));
});

class AuthFormState {
  const AuthFormState({
    this.isLoading = false,
    this.errorMessage,
  });

  final bool isLoading;
  final String? errorMessage;

  AuthFormState copyWith({
    bool? isLoading,
    String? errorMessage,
    bool clearError = false,
  }) {
    return AuthFormState(
      isLoading: isLoading ?? this.isLoading,
      errorMessage: clearError ? null : errorMessage ?? this.errorMessage,
    );
  }
}

class AuthController extends StateNotifier<AuthFormState> {
  AuthController(this._repository) : super(const AuthFormState());

  final AuthRepository _repository;

  Future<bool> signIn({
    required String email,
    required String password,
  }) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      await _repository.signIn(email: email, password: password);
      state = const AuthFormState();
      return true;
    } on AuthException catch (error) {
      state = AuthFormState(errorMessage: error.message);
      return false;
    } catch (_) {
      state = const AuthFormState(
        errorMessage: 'Unable to sign in. Please try again.',
      );
      return false;
    }
  }

  Future<bool?> signUp({
    required String email,
    required String password,
  }) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final response = await _repository.signUp(
        email: email,
        password: password,
      );
      state = const AuthFormState();
      return response.session == null;
    } on AuthException catch (error) {
      state = AuthFormState(errorMessage: error.message);
      return null;
    } catch (_) {
      state = const AuthFormState(
        errorMessage: 'Unable to create the account. Please try again.',
      );
      return null;
    }
  }

  Future<void> signOut() async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      await _repository.signOut();
      state = const AuthFormState();
    } on AuthException catch (error) {
      state = AuthFormState(errorMessage: error.message);
    } catch (_) {
      state = const AuthFormState(
        errorMessage: 'Unable to sign out. Please try again.',
      );
    }
  }
}
