import 'dart:html' as html;
import 'package:js/js_util.dart' as js_util;
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:crypto/crypto.dart';

class AuthService extends ChangeNotifier {
  static const _tokenKey = 'auth_token';
  static String get baseUrl {
    try {
      final url = js_util.getProperty(html.window,'JOGOBORG_URL') as String?;
      if (url != null && url.isNotEmpty) {
        return url;
      } else {
        print('JOGOBORG_URL environment variable not defined. Falling back to the default backend URL.');
      }
    } catch (e) {
      print('An error occurred when trying to acccess the value of the JOGOBORG_URL environment variable not defined. Falling back to the default backend URL.');
    }
    return 'http://localhost:8080'; // fallback
  }

  String? _token;
  bool _isAuthenticated = false;

  bool get isAuthenticated => _isAuthenticated;
  String? get token => _token;

  // Method to login
  Future<bool> login(String username, String password) async {
    try {
      final url = Uri.parse('${AuthService.baseUrl}/api/login');
      final response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'username': username,
          'password': password,
        }),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        _token = data['token'];
        _isAuthenticated = true;
        notifyListeners();
        return true;
      } else {
        return false;
      }
    } catch (e) {
      return false;
    }
  }

  // Method to logout
  Future<void> logout() async {
    // if (_token != null) {
    //   try {
    //     // Optional: Call server to invalidate token
    //     final url = Uri.parse('${AuthService.baseUrl}/api/logout');
    //     await http.post(
    //       url,
    //       headers: getAuthHeaders(),
    //     );
    //   } catch (e) {
    //     // Log error but continue with local logout
    //     debugPrint('Error during server logout: $e');
    //   }
    // }

    _token = null;
    _isAuthenticated = false;
    notifyListeners();
  }

  // Method to get authorization header for API requests
  Map<String, String> getAuthHeaders() {
    if (_token != null) {
      return {
        'Authorization': 'Bearer $_token',
        'Content-Type': 'application/json',
      };
    }
    return {
      'Content-Type': 'application/json',
    };
  }
}
