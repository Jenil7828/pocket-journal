import 'dart:convert';
import 'dart:math';

import 'package:diary/DesignConstraints/api.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class EntryAnalysisPage extends StatefulWidget {
  final String entryId;

  const EntryAnalysisPage({super.key, required this.entryId});

  @override
  State<EntryAnalysisPage> createState() => _EntryAnalysisPageState();
}

class _EntryAnalysisPageState extends State<EntryAnalysisPage>
    with SingleTickerProviderStateMixin {
  Map<String, double> moodData = {};

  String title = "";
  String entryText = "";
  String summary = "";

  bool isLoading = true;

  late AnimationController _controller;

  final Color primaryColor = const Color(0xFF6E6E9E);

  @override
  void initState() {
    super.initState();

    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 1),
    );

    fetchEntryAnalysis();
  }

  /// ✅ FETCH ENTRY ANALYSIS API
  Future<void> fetchEntryAnalysis() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final token = prefs.getString("token");

      if (token == null) {
        setState(() => isLoading = false);
        return;
      }

      final response = await http.get(
        Uri.parse("${ApiConfig.baseUrl}/journal/${widget.entryId}"),
        headers: {
          "Content-Type": "application/json",
          "Authorization": "Bearer $token",
        },
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);

        final analysis = data["analysis"] ?? {};
        final mood = analysis["mood"] ?? {};

        setState(() {
          /// ✅ FIXED TITLE EXTRACTION
          title = (data["title"] ?? "").toString().trim();
          entryText = (data["entry_text"] ?? "").toString().trim();
          summary = (analysis["summary"] ?? "").toString().trim();

          /// Fallbacks
          if (title.isEmpty) title = "Untitled";
          if (entryText.isEmpty) entryText = "No entry content available.";
          if (summary.isEmpty) {
            summary = "No AI summary available for this journal entry.";
          }

          moodData = {
            "anger": (mood["anger"] ?? 0).toDouble(),
            "disgust": (mood["disgust"] ?? 0).toDouble(),
            "fear": (mood["fear"] ?? 0).toDouble(),
            "happy": (mood["happy"] ?? 0).toDouble(),
            "neutral": (mood["neutral"] ?? 0).toDouble(),
            "sad": (mood["sad"] ?? 0).toDouble(),
            "surprise": (mood["surprise"] ?? 0).toDouble(),
          };

          isLoading = false;
        });

        _controller.forward();
      } else {
        debugPrint("Failed: ${response.body}");
        setState(() => isLoading = false);
      }
    } catch (e) {
      debugPrint("Analysis Error: $e");
      setState(() => isLoading = false);
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  /// 🎭 Emoji
  String getEmoji(String mood) {
    switch (mood) {
      case "happy":
        return "😊";
      case "sad":
        return "😢";
      case "anger":
        return "😡";
      case "fear":
        return "😨";
      case "surprise":
        return "😲";
      case "disgust":
        return "🤢";
      default:
        return "😐";
    }
  }

  /// 🎨 Mood Color
  Color getMoodColor(String mood) {
    switch (mood) {
      case "happy":
        return Colors.green;
      case "sad":
        return Colors.blue;
      case "anger":
        return Colors.red;
      case "fear":
        return Colors.purple;
      case "surprise":
        return Colors.orange;
      case "disgust":
        return Colors.brown;
      default:
        return Colors.grey;
    }
  }

  /// 🏷️ Mood Label
  String getFullMoodName(String mood) {
    switch (mood) {
      case "anger":
        return "Anger";
      case "disgust":
        return "Disgust";
      case "fear":
        return "Fear";
      case "happy":
        return "Happy";
      case "neutral":
        return "Neutral";
      case "sad":
        return "Sad";
      case "surprise":
        return "Surprise";
      default:
        return mood;
    }
  }

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return Scaffold(
        backgroundColor: const Color(0xFFF5F6FA),
        body: Center(child: CircularProgressIndicator(color: primaryColor)),
      );
    }

    if (moodData.isEmpty) {
      return Scaffold(
        backgroundColor: const Color(0xFFF5F6FA),
        appBar: AppBar(title: const Text("Entry Analysis")),
        body: const Center(child: Text("No analysis found")),
      );
    }

    final highest = moodData.entries.reduce(
      (a, b) => a.value > b.value ? a : b,
    );

    return Scaffold(
      backgroundColor: const Color(0xFFF5F6FA),

      /// 🔥 APPBAR
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        leading: GestureDetector(
          onTap: () => Navigator.pop(context),
          child: Container(
            margin: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: primaryColor.withOpacity(0.1),
              shape: BoxShape.circle,
            ),
            child: Icon(Icons.arrow_back, color: primaryColor),
          ),
        ),
        centerTitle: true,
        title: const Text(
          "Entry Analysis",
          style: TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.w600,
            color: Colors.black,
          ),
        ),
      ),

      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            /// 📄 ENTRY TITLE + TEXT
            _card(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 10),
                  const Divider(),
                  const SizedBox(height: 10),
                  Text(
                    entryText,
                    style: const TextStyle(height: 1.6, fontSize: 15),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 16),

            /// 🧠 SUMMARY CARD
            _card(
              color: const Color(0xFFEDEBFF),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.psychology, color: Colors.deepPurple),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      summary,
                      style: const TextStyle(height: 1.5, fontSize: 14),
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 16),

            /// 🎭 TOP MOOD
            _card(
              child: Row(
                children: [
                  Text(
                    getEmoji(highest.key),
                    style: const TextStyle(fontSize: 32),
                  ),
                  const SizedBox(width: 10),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        "Top Mood",
                        style: TextStyle(color: Colors.grey),
                      ),
                      Text(
                        getFullMoodName(highest.key),
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                          color: getMoodColor(highest.key),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),

            const SizedBox(height: 20),

            /// 📊 MOOD CHART
            _card(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    "Mood Analysis",
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 20),

                  SizedBox(
                    height: 220,
                    child: AnimatedBuilder(
                      animation: _controller,
                      builder: (context, child) {
                        return Row(
                          crossAxisAlignment: CrossAxisAlignment.end,
                          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                          children:
                              moodData.entries.map((entry) {
                                final isHighest = entry.key == highest.key;
                                double animatedValue =
                                    entry.value * _controller.value;

                                return Column(
                                  mainAxisAlignment: MainAxisAlignment.end,
                                  children: [
                                    Text(
                                      "${(entry.value * 100).toStringAsFixed(1)}%",
                                      style: TextStyle(
                                        fontSize: 10,
                                        fontWeight:
                                            isHighest
                                                ? FontWeight.bold
                                                : FontWeight.normal,
                                      ),
                                    ),
                                    const SizedBox(height: 4),

                                    Container(
                                      height: max(8, animatedValue * 180),
                                      width: isHighest ? 22 : 16,
                                      decoration: BoxDecoration(
                                        color: getMoodColor(entry.key),
                                        borderRadius: BorderRadius.circular(6),
                                      ),
                                    ),

                                    const SizedBox(height: 6),

                                    Text(
                                      getFullMoodName(entry.key),
                                      style: const TextStyle(fontSize: 10),
                                    ),
                                  ],
                                );
                              }).toList(),
                        );
                      },
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// 💎 REUSABLE CARD
  Widget _card({required Widget child, Color? color}) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color ?? Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            blurRadius: 12,
            offset: const Offset(0, 4),
            color: Colors.black.withOpacity(0.06),
          ),
        ],
      ),
      child: child,
    );
  }
}
