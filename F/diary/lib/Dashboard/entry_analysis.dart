import 'package:flutter/material.dart';
import 'dart:math';

class EntryAnalysisPage extends StatefulWidget {
  const EntryAnalysisPage({super.key});

  @override
  State<EntryAnalysisPage> createState() => _EntryAnalysisPageState();
}

class _EntryAnalysisPageState extends State<EntryAnalysisPage>
    with SingleTickerProviderStateMixin {
  final Map<String, double> moodData = {
    "anger": 0.015,
    "disgust": 0.057,
    "fear": 0.009,
    "happy": 0.011,
    "neutral": 0.396,
    "sad": 0.321,
    "surprise": 0.002,
  };

  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 1),
    );
    _controller.forward();
  }

  @override
  void dispose() {
    _controller.dispose(); // ✅ IMPORTANT
    super.dispose();
  }

  // 🔥 BACK FUNCTION (MAIN FIX)
  void handleBack() {
    Navigator.pop(context);
  }

  // 🎭 Emoji
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

  // 🎨 Color
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

  // 🏷️ Full Name
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
    final Color primaryColor = const Color(0xFF6E6E9E);
    final highest = moodData.entries.reduce(
      (a, b) => a.value > b.value ? a : b,
    );

    return Scaffold(
      backgroundColor: const Color(0xFFF5F6FA),

      // 🔥 CUSTOM APPBAR WITH BACK BUTTON
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
            _card(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: const [
                  Text(
                    "A beautiful morning walk",
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                  ),
                  SizedBox(height: 10),
                  Divider(),
                  SizedBox(height: 10),
                  Text(
                    "This morning I went for a walk in the park. The fresh air made me feel peaceful...",
                    style: TextStyle(height: 1.5),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 16),

            _card(
              color: const Color(0xFFEDEBFF),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: const [
                  Icon(Icons.psychology, color: Colors.deepPurple),
                  SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      "This entry shows a positive and reflective mindset. You're appreciating small joys.",
                      style: TextStyle(height: 1.5),
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 16),

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
