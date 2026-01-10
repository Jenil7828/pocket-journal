import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'dart:developer';

class JournalEntryScreen extends StatefulWidget {
  final DateTime selectedDate;

  const JournalEntryScreen({super.key, required this.selectedDate});

  @override
  State<JournalEntryScreen> createState() => _JournalEntryScreenState();
}

class _JournalEntryScreenState extends State<JournalEntryScreen> {
  late TextEditingController _topicController;
  late TextEditingController _entryController;
  bool _isLoading = false;

  final Dio _dio = Dio(
    BaseOptions(
     baseUrl: "http://10.252.110.242:5000",
      headers: {"Content-Type": "application/json"},
    ),
  );

  final FirebaseAuth _auth = FirebaseAuth.instance;
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;

  @override
  void initState() {
    super.initState();
    _topicController = TextEditingController();
    _entryController = TextEditingController(text: "How is today?\n\n");
  }

  @override
  void dispose() {
    _topicController.dispose();
    _entryController.dispose();
    super.dispose();
  }

  /// 🌸 Custom snackbar (from LoginScreen)
  void _showCustomSnackBar(
    BuildContext context,
    String message, {
    bool isError = false,
  }) {
    final bgColor = isError ? const Color(0xFFE57373) : const Color(0xFFB39DDB);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        behavior: SnackBarBehavior.floating,
        backgroundColor: bgColor,
        elevation: 8,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        content: Text(
          message,
          style: const TextStyle(color: Colors.white, fontSize: 16),
        ),
      ),
    );
  }

  Future<void> _saveEntry() async {
    if (_entryController.text.trim().isEmpty) {
      _showCustomSnackBar(
        context,
        "✏️ Please write something before saving.",
        isError: true,
      );
      return;
    }

    setState(() => _isLoading = true);

    try {
      final user = _auth.currentUser;
      if (user == null) {
        log("⚠️ No user logged in");
        _showCustomSnackBar(context, "⚠️ No user logged in.", isError: true);
        return;
      }

      final prefs = await SharedPreferences.getInstance();
      final token = prefs.getString('idToken');

      // 🔹 Step 1: Save to Firestore
      final docRef = await _firestore.collection('journal_entries').add({
        'uid': user.uid,
        'entry_text': _entryController.text.trim(),
        'topic': _topicController.text.trim(),
        'created_at': widget.selectedDate,
        'updated_at': DateTime.now(),
      });

      log("✅ Entry saved to Firestore: ${docRef.id}");

      // 🔹 Step 2: Send to backend for analysis
      if (token != null) {
        final response = await _dio.post(
          "/process_entry",
          data: {"entry_text": _entryController.text.trim()},
          options: Options(headers: {"Authorization": "Bearer $token"}),
        );

        if (response.statusCode == 200) {
          log("✅ Backend processed successfully: ${response.data}");
          _showCustomSnackBar(
            context,
            "✅ Entry added successfully!",
            isError: false,
          );
          Navigator.pop(context);
        } else {
          log("⚠️ Backend failed: ${response.statusCode}");
          _showCustomSnackBar(
            context,
            "⚠️ Failed to process entry (Code: ${response.statusCode})",
            isError: true,
          );
        }
      } else {
        log("⚠️ No token found in SharedPreferences");
        _showCustomSnackBar(
          context,
          "⚠️ Unable to find login token. Please re-login.",
          isError: true,
        );
      }
    } catch (e) {
      log("❌ Error saving entry: $e");
      _showCustomSnackBar(
        context,
        "❌ Something went wrong. Try again.",
        isError: true,
      );
    } finally {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    String formattedDate = DateFormat.yMMMd().format(widget.selectedDate);

    return Scaffold(
      backgroundColor: const Color(0xFFBCAAA4),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(20.0),
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    Transform.rotate(
                      angle: -0.05,
                      child: _diaryPage(const Color(0xFFD7CCC8)),
                    ),
                    Transform.rotate(
                      angle: 0.03,
                      child: _diaryPage(const Color(0xFFEDE7F6)),
                    ),
                    _mainDiaryPage(formattedDate),
                  ],
                ),
              ),
            ),

            // ---------- Buttons ----------
            Padding(
              padding: const EdgeInsets.only(bottom: 30),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  _roundedButton(
                    label: "Cancel",
                    color: const Color(0xFFD7CCC8),
                    textColor: Colors.brown.shade700,
                    onTap: () => Navigator.pop(context),
                  ),
                  const SizedBox(width: 30),
                  _isLoading
                      ? const CircularProgressIndicator(color: Colors.white)
                      : _roundedButton(
                        label: "Save",
                        color: const Color(0xFFF8F3FF),
                        textColor: Colors.brown.shade700,
                        onTap: _saveEntry,
                      ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _roundedButton({
    required String label,
    required Color color,
    required Color textColor,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 110,
        height: 45,
        decoration: BoxDecoration(
          color: color,
          borderRadius: BorderRadius.circular(25),
          border: Border.all(color: Colors.brown.shade700, width: 1.5),
          boxShadow: [
            BoxShadow(
              color: Colors.brown.withOpacity(0.2),
              blurRadius: 5,
              offset: const Offset(2, 3),
            ),
          ],
        ),
        alignment: Alignment.center,
        child: Text(
          label,
          style: GoogleFonts.poppins(
            fontSize: 15,
            fontWeight: FontWeight.w600,
            color: textColor,
          ),
        ),
      ),
    );
  }

  Widget _diaryPage(Color color) {
    return Container(
      height: 500,
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.brown.withOpacity(0.3),
            blurRadius: 10,
            offset: const Offset(5, 5),
          ),
        ],
      ),
    );
  }

  Widget _mainDiaryPage(String formattedDate) {
    return Container(
      height: 500,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFFF8F3FF),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.brown.withOpacity(0.4),
            blurRadius: 15,
            offset: const Offset(5, 8),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.lightbulb_outline, color: Colors.black54),
              const SizedBox(width: 10),
              Expanded(
                child: TextField(
                  controller: _topicController,
                  decoration: InputDecoration(
                    hintText: "Enter the topic",
                    hintStyle: GoogleFonts.poppins(color: Colors.black54),
                    border: InputBorder.none,
                  ),
                  style: GoogleFonts.poppins(
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
          Padding(
            padding: const EdgeInsets.only(left: 10.0, top: 4),
            child: Text(
              formattedDate,
              style: GoogleFonts.poppins(color: Colors.black54, fontSize: 14),
            ),
          ),
          const SizedBox(height: 10),
          Expanded(
            child: TextField(
              controller: _entryController,
              maxLines: null,
              expands: true,
              keyboardType: TextInputType.multiline,
              decoration: const InputDecoration(
                hintText: "Start writing...",
                border: InputBorder.none,
              ),
              style: GoogleFonts.poppins(fontSize: 16),
            ),
          ),
        ],
      ),
    );
  }
}
