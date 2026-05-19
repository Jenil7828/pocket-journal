import 'dart:convert';
import 'package:diary/Dashboard/dashboard.dart';
import 'package:diary/DesignConstraints/api.dart';
import 'package:diary/DesignConstraints/navbar.dart';
import 'package:diary/Login/login.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class LangSelect extends StatefulWidget {
  final Map<String, List<String>> preferencesData; // ✅ ADDED

  const LangSelect({super.key, required this.preferencesData}); // ✅ UPDATED

  @override
  State<LangSelect> createState() => _LangSelectState();
}

class _LangSelectState extends State<LangSelect> {
  final Color navyBlue = const Color(0xFF1E2D4C);

  /// ✅ MULTI SELECT (no default)
  Set<String> selectedMedia = {};

  String selectedLanguage = "English";
  final TextEditingController languageCtrl = TextEditingController();

  bool isEditing = true;

  final List<String> languages = [
    "English",
    "Hindi",
    "Marathi",
    "Spanish",
    "French",
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF4F6FB),
      appBar: AppBar(
        title: const Text("Preferences"),
        backgroundColor: Colors.transparent,
        elevation: 0,
        foregroundColor: Colors.black,

        /// 🔥 BACK BUTTON
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () {
            Navigator.pop(context);
          },
        ),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            /// TITLE
            const Text(
              "Preferred Media Type",
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 4),
            const Text(
              "Choose what you'd like to track",
              style: TextStyle(color: Colors.grey),
            ),

            const SizedBox(height: 20),

            /// MEDIA OPTIONS
            Row(
              children: [
                _mediaButton("Movies", Icons.movie),
                const SizedBox(width: 10),
                _mediaButton("Songs", Icons.music_note),
              ],
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                _mediaButton("Books", Icons.menu_book),
                const SizedBox(width: 10),
                _mediaButton("Podcasts", Icons.mic),
              ],
            ),

            const SizedBox(height: 30),

            /// LANGUAGE
            const Text(
              "Preferred Language",
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),

            TextField(
              controller: languageCtrl,
              enabled: isEditing,
              decoration: InputDecoration(
                hintText: "Enter language",
                filled: true,
                fillColor: Colors.white,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(14),
                  borderSide: BorderSide.none,
                ),
              ),
            ),

            const SizedBox(height: 12),

            DropdownButtonFormField<String>(
              value: selectedLanguage,
              items:
                  languages
                      .map(
                        (lang) =>
                            DropdownMenuItem(value: lang, child: Text(lang)),
                      )
                      .toList(),
              onChanged:
                  isEditing
                      ? (value) {
                        setState(() {
                          selectedLanguage = value!;
                          languageCtrl.text = value;
                        });
                      }
                      : null,
              decoration: InputDecoration(
                filled: true,
                fillColor: Colors.white,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(14),
                  borderSide: BorderSide.none,
                ),
              ),
            ),

            const Spacer(),

            /// BUTTONS
            Row(
              children: [
                Expanded(
                  child: ElevatedButton(
                    onPressed: _savePreferences,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: navyBlue,
                      minimumSize: const Size(double.infinity, 50),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(14),
                      ),
                    ),
                    child: const Text(
                      "Save",
                      style: TextStyle(color: Colors.white),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: ElevatedButton(
                    onPressed: _toggleEdit,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: navyBlue,
                      minimumSize: const Size(double.infinity, 50),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(14),
                      ),
                    ),
                    child: Text(
                      isEditing ? "Disable Edit" : "Edit",
                      style: const TextStyle(color: Colors.white),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  /// ✅ MULTI SELECT BUTTON
  Widget _mediaButton(String title, IconData icon) {
    final bool isSelected = selectedMedia.contains(title);

    return Expanded(
      child: GestureDetector(
        onTap:
            isEditing
                ? () {
                  setState(() {
                    if (isSelected) {
                      selectedMedia.remove(title);
                    } else {
                      selectedMedia.add(title);
                    }
                  });
                }
                : null,
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 14),
          decoration: BoxDecoration(
            color: isSelected ? navyBlue : Colors.grey.shade200,
            borderRadius: BorderRadius.circular(20),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, color: isSelected ? Colors.white : Colors.black54),
              const SizedBox(width: 6),
              Text(
                title,
                style: TextStyle(
                  color: isSelected ? Colors.white : Colors.black54,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// 🔥 SAVE + API INTEGRATION
  void _savePreferences() async {
    setState(() {
      isEditing = false;
    });

    print("🚀 SAVE BUTTON CLICKED");

    final prefs = await SharedPreferences.getInstance();
    String? token = prefs.getString("token");

    print("🔑 TOKEN: $token");

    if (token == null) {
      print("❌ ERROR: Token is NULL");
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Token missing, login again")),
      );
      return;
    }

    /// 🔥 PREPARE BODY
    final body = {
      "preferred_media_type":
          selectedMedia.isEmpty ? "" : selectedMedia.first.toLowerCase(),
      "languages": [
        languageCtrl.text.isEmpty ? selectedLanguage : languageCtrl.text,
      ],
      "music": widget.preferencesData["songs"] ?? [],
      "movies": widget.preferencesData["movies"] ?? [],
      "books": widget.preferencesData["books"] ?? [],
      "podcasts": widget.preferencesData["podcasts"] ?? [],
      "content_intensity": "Balanced",
    };

    print("📦 REQUEST BODY: ${jsonEncode(body)}");

    try {
      final url = "${ApiConfig.baseUrl}/me/preferences";
      print("🌐 API URL: $url");

      final response = await http.put(
        Uri.parse(url),
        headers: {
          "Content-Type": "application/json",
          "Authorization": "Bearer $token",
        },
        body: jsonEncode(body),
      );

      print("📥 STATUS CODE: ${response.statusCode}");
      print("📥 RESPONSE BODY: ${response.body}");

      if (response.statusCode == 200 || response.statusCode == 204) {
        print("✅ SUCCESS: Preferences saved");

        // ✅ ADD THIS (MOST IMPORTANT)
        await prefs.setBool("hasPreferences", true);

        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("Preferences Saved Successfully")),
        );

        Future.delayed(const Duration(milliseconds: 800), () {
          Navigator.pushReplacement(
            context,
            MaterialPageRoute(builder: (_) => const CustomBottomNavBar()),
          );
        });
      } else {
        print("❌ API FAILED");

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text("Error ${response.statusCode}: ${response.body}"),
          ),
        );
      }
    } catch (e, stackTrace) {
      print("🔥 EXCEPTION OCCURRED");
      print("ERROR: $e");
      print("STACKTRACE: $stackTrace");

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text("Exception: $e")));
    }
  }

  /// TOGGLE EDIT
  void _toggleEdit() {
    setState(() {
      isEditing = !isEditing;
    });

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(isEditing ? "Edit Enabled" : "Edit Disabled")),
    );
  }
}
