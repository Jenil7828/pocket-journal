import 'dart:async';
import 'package:diary/Dashboard/journalEntry.dart';
import 'package:diary/DesignConstraints/profile_service.dart';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

class DashboardPage extends StatefulWidget {
  const DashboardPage({super.key});

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  final Color primaryColor = const Color.fromARGB(255, 250, 250, 249);
  final Color accentColor = const Color(0xFF1E2D4C);
  final Color textGrey = const Color(0xFF858585);

  final List<String> messages = [
    "You're doing an amazing job showing up for yourself. Even a few words each day can bring clarity and peace.",
    "Your thoughts deserve a safe space to exist and be understood.",
    "You don’t have to write perfectly, just write honestly.",
    "Small reflections can lead to big transformations.",
  ];

  int currentMessageIndex = 0;
  Timer? timer;

  String userName = "User";

  final List<Map<String, String>> recentEntries = [
    {
      "title": "A beautiful morning walk in the park today",
      "date": "Jan 11, 2026",
    },
    {
      "title": "Reflections on growth and personal change",
      "date": "Jan 10, 2026",
    },
    {"title": "Gratitude practice made me feel calm", "date": "Jan 9, 2026"},
    {"title": "Evening thoughts about life and purpose", "date": "Jan 8, 2026"},
  ];

  final List<Map<String, String>> mediaEntries = [
    {
      "title": "Shape of You",
      "desc": "A romantic upbeat song by Ed Sheeran",
      "type": "song",
    },
    {
      "title": "Inception",
      "desc": "A mind bending sci-fi thriller movie",
      "type": "movie",
    },
    {
      "title": "Believer",
      "desc": "Motivational energetic song by Imagine Dragons",
      "type": "song",
    },
  ];

  @override
  void initState() {
    super.initState();

    loadUserProfile();

    timer = Timer.periodic(const Duration(seconds: 3), (timer) {
      if (mounted) {
        setState(() {
          currentMessageIndex = (currentMessageIndex + 1) % messages.length;
        });
      }
    });
  }

  /// ✅ LOAD USER PROFILE FROM API + CACHE
  Future<void> loadUserProfile() async {
    try {
      // Load cached name instantly
      userName = await ProfileService.getCachedUserName();

      if (mounted) {
        setState(() {});
      }

      // Fetch latest profile from API
      final profile = await ProfileService.fetchUserProfile();

      if (profile != null && mounted) {
        setState(() {
          userName = profile["name"] ?? userName;
        });
      }
    } catch (e) {
      debugPrint("Dashboard Profile Load Error: $e");
    }
  }

  @override
  void dispose() {
    timer?.cancel();
    super.dispose();
  }

  String getShortTitle(String text) {
    final words = text.split(' ');
    if (words.length <= 5) return text;
    return '${words.take(5).join(' ')}...';
  }

  String getShortDescription(String text) {
    if (text.length <= 25) return text;
    return '${text.substring(0, 25)}...';
  }

  String getCurrentDate() {
    return DateFormat('EEEE, MMMM d').format(DateTime.now()).toUpperCase();
  }

  String getGreeting() {
    final hour = DateTime.now().hour;

    if (hour < 12) {
      return "Good morning";
    } else if (hour < 17) {
      return "Good afternoon";
    } else {
      return "Good evening";
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: SingleChildScrollView(
        child: Column(
          children: [
            /// HEADER
            Container(
              width: double.infinity,
              padding: const EdgeInsets.fromLTRB(20, 50, 20, 25),
              decoration: BoxDecoration(
                color: accentColor,
                borderRadius: const BorderRadius.only(
                  bottomLeft: Radius.circular(60),
                  bottomRight: Radius.circular(60),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        getCurrentDate(),
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w900,
                          color: Color.fromARGB(179, 245, 132, 39),
                        ),
                      ),
                      Container(
                        height: 40,
                        width: 40,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          border: Border.all(color: Colors.white, width: 2),
                        ),
                        child: const Icon(
                          Icons.person,
                          color: Colors.white,
                          size: 22,
                        ),
                      ),
                    ],
                  ),

                  const SizedBox(height: 15),

                  Text(
                    '${getGreeting()}, $userName',
                    style: const TextStyle(
                      fontSize: 22,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),

                  const SizedBox(height: 10),

                  Row(
                    children: [
                      const Icon(
                        Icons.auto_awesome,
                        color: Colors.white,
                        size: 18,
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: AnimatedSwitcher(
                          duration: const Duration(milliseconds: 500),
                          child: Text(
                            messages[currentMessageIndex],
                            key: ValueKey(currentMessageIndex),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontSize: 13,
                              color: Colors.white70,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),

            const SizedBox(height: 50),

            /// JOURNAL CARD
            Stack(
              clipBehavior: Clip.none,
              children: [
                Card(
                  elevation: 6,
                  margin: const EdgeInsets.symmetric(horizontal: 16),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Container(
                    decoration: BoxDecoration(
                      color: primaryColor,
                      borderRadius: BorderRadius.circular(20),
                    ),
                    height: 140,
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Text(
                                'Start Journaling',
                                style: TextStyle(
                                  fontSize: 18,
                                  fontWeight: FontWeight.bold,
                                  color: accentColor,
                                ),
                              ),
                              const SizedBox(height: 8),
                              Text(
                                'Write your thoughts and reflect on your day.',
                                style: TextStyle(fontSize: 12, color: textGrey),
                              ),
                              const SizedBox(height: 10),
                              GestureDetector(
                                onTap: () {
                                  Navigator.push(
                                    context,
                                    MaterialPageRoute(
                                      builder: (_) => const Journalentry(),
                                    ),
                                  );
                                },
                                child: Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 12,
                                    vertical: 6,
                                  ),
                                  decoration: BoxDecoration(
                                    color: accentColor,
                                    borderRadius: BorderRadius.circular(20),
                                  ),
                                  child: const Text(
                                    'Start Now',
                                    style: TextStyle(
                                      fontSize: 12,
                                      color: Colors.white,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 80),
                      ],
                    ),
                  ),
                ),

                Positioned(
                  right: 10,
                  top: -40,
                  child: Container(
                    height: 120,
                    width: 120,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border: Border.all(color: Colors.grey, width: 3),
                    ),
                    child: Icon(
                      Icons.menu_book_rounded,
                      size: 50,
                      color: accentColor,
                    ),
                  ),
                ),
              ],
            ),

            const SizedBox(height: 30),

            /// RECENT ACTIVITY
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 16),
              child: Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  "Recent Activity",
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
              ),
            ),

            const SizedBox(height: 16),

            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 10),
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: recentEntries.map((e) => _recentCard(e)).toList(),
                ),
              ),
            ),

            const SizedBox(height: 10),

            /// MEDIA ACTIVITY
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 16),
              child: Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  "Media Activity",
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
              ),
            ),

            const SizedBox(height: 16),

            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 10),
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: mediaEntries.map((e) => _mediaCard(e)).toList(),
                ),
              ),
            ),

            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }

  /// RECENT CARD
  Widget _recentCard(Map<String, String> entry) {
    return Card(
      elevation: 6,
      margin: const EdgeInsets.only(right: 16, bottom: 8),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(22)),
      child: Container(
        width: 190,
        height: 170,
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Icon(Icons.auto_stories, color: accentColor),
            Text(
              getShortTitle(entry["title"]!),
              style: TextStyle(fontWeight: FontWeight.bold, color: accentColor),
            ),
            Text(
              entry["date"]!,
              style: TextStyle(color: textGrey, fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }

  /// MEDIA CARD
  Widget _mediaCard(Map<String, String> media) {
    return Card(
      elevation: 6,
      margin: const EdgeInsets.only(right: 16, bottom: 8),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(22)),
      child: Container(
        width: 190,
        height: 170,
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Icon(
              media["type"] == "movie" ? Icons.movie : Icons.music_note,
              color: accentColor,
            ),
            Text(
              media["title"]!,
              style: TextStyle(fontWeight: FontWeight.bold, color: accentColor),
            ),
            Text(
              getShortDescription(media["desc"]!),
              style: TextStyle(color: textGrey, fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }
}
