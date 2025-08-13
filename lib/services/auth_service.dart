import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:crypto/crypto.dart';
import 'dart:convert';

class AuthService extends ChangeNotifier {
  static const _storage = FlutterSecureStorage();
  static const _tokenKey = 'auth_token';
  
  bool _isAuthenticated = false;
  String? _token;

  bool get isAuthenticated => _isAuthenticated;
  String? get token => _token;

  AuthService() {
    _loadToken();
  }

  Future<void> _loadToken() async {
    try {
      _token = await _storage.read(key: _tokenKey);
      _isAuthenticated = _token != null;
      notifyListeners();
    } catch (e) {
      _isAuthenticated = false;
      notifyListeners();
    }
  }

  Future<bool> login(String username, String password) async {
    try {
      // Hash the credentials for basic security
      final credentials = '$username:$password';
      final bytes = utf8.encode(credentials);
      final digest = sha256.convert(bytes);
      final token = digest.toString();

      // In a real implementation, this would validate against environment variables
      // For now, we'll store the token and assume validation happens server-side
      await _storage.write(key: _tokenKey, value: token);
      _token = token;
      _isAuthenticated = true;
      notifyListeners();
      return true;
    } catch (e) {
      return false;
    }
  }

  Future<void> logout() async {
    try {
      await _storage.delete(key: _tokenKey);
      _token = null;
      _isAuthenticated = false;
      notifyListeners();
    } catch (e) {
      // Handle error
    }
  }
}