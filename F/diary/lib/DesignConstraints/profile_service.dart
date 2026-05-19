import 'dart:convert';
import 'dart:developer';

import 'package:diary/DesignConstraints/api.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ProfileService {
  /// ✅ Fetch logged-in user profile using saved token
  static Future<Map<String, dynamic>?> fetchUserProfile() async {
    try {
      final prefs = await SharedPreferences.getInstance();

      // ✅ Get saved JWT token
      final token = prefs.getString("token");

      if (token == null || token.isEmpty) {
        log("No token found. User may not be logged in.");
        return null;
      }

      final response = await http.get(
        Uri.parse("${ApiConfig.baseUrl}/me"),
        headers: {
          "Content-Type": "application/json",
          "Authorization": "Bearer $token",
        },
      );

      log("PROFILE RESPONSE: ${response.body}");

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);

        // ✅ Optional local caching
        if (data["name"] != null) {
          await prefs.setString("user_name", data["name"]);
        }

        if (data["email"] != null) {
          await prefs.setString("user_email", data["email"]);
        }

        return data;
      } else {
        log("Profile fetch failed: ${response.statusCode}");

        try {
          final error = jsonDecode(response.body);
          log("Error: ${error["message"]}");
        } catch (_) {}

        return null;
      }
    } catch (e) {
      log("Profile API Error: $e");
      return null;
    }
  }

  /// ✅ Get cached user name instantly
  static Future<String> getCachedUserName() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString("user_name") ?? "User";
  }

  /// ✅ Get cached email instantly
  static Future<String> getCachedEmail() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString("user_email") ?? "";
  }

  /// ✅ Clear profile cache on logout
  static Future<void> clearProfileCache() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove("user_name");
    await prefs.remove("user_email");
  }
}