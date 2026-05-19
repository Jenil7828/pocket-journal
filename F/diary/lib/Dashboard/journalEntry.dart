import 'dart:convert';
import 'package:diary/DesignConstraints/api.dart';
import 'package:http/http.dart' as http;
import 'package:intl/intl.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:diary/DesignConstraints/navbar.dart';
import 'package:diary/DesignConstraints/snackbar.dart';

import 'package:flutter/material.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;

class Journalentry extends StatefulWidget {
  const Journalentry({super.key});

  @override
  State<Journalentry> createState() => _JournalentryState();
}

class _JournalentryState extends State<Journalentry> {
  final TextEditingController titleController = TextEditingController();
  final TextEditingController contentController = TextEditingController();

  final Color primaryColor = const Color(0xFFCEC0BB);
  final Color accentColor = const Color(0xFF1E2D4C);

  late stt.SpeechToText _speech;
  bool isListening = false;

  @override
  void initState() {
    super.initState();
    _speech = stt.SpeechToText();
  }

  void _listen() async {
    if (!isListening) {
      bool available = await _speech.initialize();

      if (available) {
        setState(() => isListening = true);

        _speech.listen(
          onResult: (result) {
            setState(() {
              contentController.text = result.recognizedWords;
            });
          },
        );
      }
    } else {
      setState(() => isListening = false);
      _speech.stop();
    }
  }

  // ✅ API CALL
  Future<void> _saveEntry() async {
    final title = titleController.text.trim();
    final content = contentController.text.trim();

    if (title.isEmpty || content.isEmpty) {
      AppSnackbar.show(context, "Please fill all fields");
      return;
    }

    try {
      final prefs = await SharedPreferences.getInstance();
      String? token = prefs.getString("token");

      if (token == null) {
        AppSnackbar.show(context, "User not logged in");
        return;
      }

      final response = await http.post(
        Uri.parse("${ApiConfig.baseUrl}/journal"),
        headers: {
          "Content-Type": "application/json",
          "Authorization": "Bearer $token",
        },
        body: jsonEncode({"title": title, "entry_text": content}),
      );

      print("JOURNAL RESPONSE: ${response.body}");

      if (response.statusCode == 200 || response.statusCode == 201) {
        AppSnackbar.show(context, "Entry Saved Successfully");

        // ✅ Clear fields after success
        titleController.clear();
        contentController.clear();

        // OPTIONAL: Navigate back
        // Navigator.pop(context);
      } else {
        final error = jsonDecode(response.body);
        AppSnackbar.show(context, error["message"] ?? "Failed to save entry");
      }
    } catch (e) {
      print("ERROR: $e");
      AppSnackbar.show(context, "Something went wrong");
    }
  }

  @override
  Widget build(BuildContext context) {
    final String currentDate = DateFormat(
      "MMMM dd, yyyy",
    ).format(DateTime.now());
    return Scaffold(
      backgroundColor: primaryColor.withOpacity(0.98),

      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        leading: GestureDetector(
          onTap: () => Navigator.pop(context),
          child: Container(
            margin: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: primaryColor.withOpacity(0.4),
              shape: BoxShape.circle,
            ),
            child: Icon(Icons.arrow_back, color: accentColor),
          ),
        ),
        centerTitle: true,
        title: Text(
          "New Entry",
          style: TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.w600,
            color: accentColor,
          ),
        ),
      ),

      body: Column(
        children: [
          Expanded(
            child: SingleChildScrollView(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Container(
                  margin: const EdgeInsets.all(3),
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(27),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const SizedBox(height: 10),

                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            currentDate,
                            style: const TextStyle(color: Colors.grey),
                          ),
                          SizedBox(height: 5),
                          Text(
                            "Today's Story",
                            style: TextStyle(
                              fontSize: 22,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),

                      const SizedBox(height: 20),

                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: primaryColor.withOpacity(0.2),
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: TextField(
                          controller: titleController,
                          decoration: const InputDecoration(
                            hintText: "Title",
                            border: InputBorder.none,
                          ),
                        ),
                      ),

                      const SizedBox(height: 15),

                      Container(
                        height: 180,
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: primaryColor.withOpacity(0.2),
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Stack(
                          children: [
                            TextField(
                              controller: contentController,
                              maxLines: null,
                              decoration: const InputDecoration(
                                hintText: "What's on your mind?",
                                border: InputBorder.none,
                              ),
                            ),

                            Positioned(
                              right: 0,
                              bottom: 0,
                              child: GestureDetector(
                                onTap: _listen,
                                child: CircleAvatar(
                                  radius: 22,
                                  backgroundColor:
                                      isListening ? Colors.red : accentColor,
                                  child: Icon(
                                    isListening ? Icons.mic : Icons.mic_none,
                                    color: Colors.white,
                                  ),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),

                      const SizedBox(height: 20),

                      Row(
                        children: [
                          Icon(Icons.flash_on, color: accentColor),
                          const SizedBox(width: 8),
                          Text(
                            "Need a Spark?",
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                              color: accentColor,
                            ),
                          ),
                        ],
                      ),

                      const SizedBox(height: 10),

                      _sparkButton("What made you smile today?"),
                      _sparkButton("One thing you're grateful for..."),
                      _sparkButton("A lesson you learned lately"),
                    ],
                  ),
                ),
              ),
            ),
          ),

          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                SizedBox(
                  width: double.infinity,
                  height: 50,
                  child: ElevatedButton(
                    onPressed: _saveEntry, // ✅ API CONNECTED HERE
                    style: ElevatedButton.styleFrom(
                      backgroundColor: accentColor,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(15),
                      ),
                    ),
                    child: const Text(
                      "Save Entry",
                      style: TextStyle(fontSize: 16, color: Colors.white),
                    ),
                  ),
                ),

                const SizedBox(height: 10),

                const Text(
                  "Your mood will be automatically detected when you save",
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 13, color: Colors.grey),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _sparkButton(String text) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.symmetric(vertical: 12),
      decoration: BoxDecoration(
        color: primaryColor.withOpacity(0.3),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Center(
        child: Text(
          text,
          style: TextStyle(color: accentColor, fontWeight: FontWeight.w600),
        ),
      ),
    );
  }
}
