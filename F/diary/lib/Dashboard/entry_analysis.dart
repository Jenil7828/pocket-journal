import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'dart:developer';

class EntryAnalysisPage extends StatefulWidget {
  final String entryId; // passed from tapped entry
  const EntryAnalysisPage({super.key, required this.entryId});

  @override
  State<EntryAnalysisPage> createState() => _EntryAnalysisPageState();
}

class _EntryAnalysisPageState extends State<EntryAnalysisPage> {
  bool isLoading = true;
  Map<String, dynamic>? moodData;
  String? summary;

  @override
  void initState() {
    super.initState();
    fetchAnalysisFromFirestore();
  }

  Future<void> fetchAnalysisFromFirestore() async {
    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user == null) {
        log("⚠️ No logged-in user found");
        setState(() => isLoading = false);
        return;
      }

      final userId = user.uid;
      log(
        "🔹 Fetching Firestore analysis for user: $userId, entry: ${widget.entryId}",
      );

      // Fetch from top-level collection `entry_analysis`
      final snapshot =
          await FirebaseFirestore.instance
              .collection('entry_analysis')
              .where('entry_id', isEqualTo: widget.entryId)
              .get();

      if (snapshot.docs.isNotEmpty) {
        final doc = snapshot.docs.first;
        final data = doc.data();

        setState(() {
          moodData = data['mood'] ?? {};
          summary = data['summary'] ?? "No summary available.";
          isLoading = false;
        });

        log(
          "✅ Analysis loaded successfully from Firestore: ${data['entry_id']}",
        );
      } else {
        log("⚠️ No matching entry found for ID: ${widget.entryId}");
        setState(() => isLoading = false);
      }
    } catch (e) {
      log("❌ Firestore fetch error: $e");
      setState(() => isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFFFF8F6),
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 1,
        title: Text(
          "Mood Analysis",
          style: GoogleFonts.poppins(
            color: Colors.black87,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      body:
          isLoading
              ? const Center(
                child: CircularProgressIndicator(color: Colors.pink),
              )
              : Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    if (summary != null)
                      Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: Colors.pink[50],
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Text(
                          "📝 $summary",
                          style: GoogleFonts.poppins(
                            fontSize: 14,
                            color: Colors.black87,
                          ),
                        ),
                      ),
                    const SizedBox(height: 20),
                    Expanded(
                      child: GridView.builder(
                        gridDelegate:
                            const SliverGridDelegateWithFixedCrossAxisCount(
                              crossAxisCount: 2,
                              crossAxisSpacing: 16,
                              mainAxisSpacing: 16,
                              childAspectRatio: 0.9,
                            ),
                        itemCount: moodData?.length ?? 0,
                        itemBuilder: (context, index) {
                          final moodName = moodData!.keys.elementAt(index);
                          final moodValue = moodData![moodName];
                          return MoodCard(
                            mood: moodName,
                            accuracy: (moodValue * 100).toStringAsFixed(
                              1,
                            ), // percent
                          );
                        },
                      ),
                    ),
                  ],
                ),
              ),
    );
  }
}

class MoodCard extends StatelessWidget {
  final String mood;
  final String accuracy;

  const MoodCard({super.key, required this.mood, required this.accuracy});

  String get imagePath {
    switch (mood.toLowerCase()) {
      case 'happy':
        return 'Assets/home/happy.png';
      case 'sad':
        return 'Assets/home/sad.png';
      case 'angry':
        return 'Assets/home/angry.png';
      case 'fear':
        return 'Assets/home/fear.png';
      case 'disgust':
        return 'Assets/home/disgust.png';
      case 'surprise':
        return 'Assets/home/shocked.png';
      default:
        return 'Assets/home/normal.png';
    }
  }

  Color get backgroundColor {
    switch (mood.toLowerCase()) {
      case 'happy':
        return const Color(0xFFFFD6D1);
      case 'sad':
        return const Color(0xFFBFD7ED);
      case 'angry':
        return const Color(0xFFFFB3B3);
      case 'fear':
        return const Color(0xFFFFE4B5);
      case 'disgust':
        return const Color(0xFFD1F7C4);
      case 'surprise':
        return const Color(0xFFFFE0F0);
      default:
        return const Color(0xFFEAEAEA);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: BorderRadius.circular(25),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 20),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Expanded(child: Image.asset(imagePath, fit: BoxFit.contain)),
          const SizedBox(height: 10),
          Text(
            mood[0].toUpperCase() + mood.substring(1),
            style: GoogleFonts.poppins(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: Colors.black87,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            "$accuracy%",
            style: GoogleFonts.poppins(fontSize: 14, color: Colors.black54),
          ),
        ],
      ),
    );
  }
}
