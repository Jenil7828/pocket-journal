import 'package:curved_labeled_navigation_bar/curved_navigation_bar.dart';
import 'package:curved_labeled_navigation_bar/curved_navigation_bar_item.dart';
import 'package:diary/Dashboard/calendar.dart';
import 'package:diary/Dashboard/mood_selector.dart';
import 'package:diary/Dashboard/show_entries.dart';
import 'package:diary/Dashboard/statistics.dart';
import 'package:diary/Profile/profile.dart';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:shared_preferences/shared_preferences.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  String? userName;
  bool isLoading = true;

  @override
  void initState() {
    super.initState();
    _fetchUserName();
  }

  Future<void> _fetchUserName() async {
    final prefs = await SharedPreferences.getInstance();
    final uid = prefs.getString('uid');

    if (uid == null) {
      setState(() {
        userName = 'User';
        isLoading = false;
      });
      return;
    }

    final doc =
        await FirebaseFirestore.instance.collection('users').doc(uid).get();

    setState(() {
      userName = doc.data()?['name'] ?? 'User';
      isLoading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      bottomNavigationBar: _buildBottomNavBar(),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
          child:
              isLoading
                  ? const Center(
                    child: Padding(
                      padding: EdgeInsets.only(top: 150),
                      child: CircularProgressIndicator(color: Colors.purple),
                    ),
                  )
                  : Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        "Good Morning, ${userName ?? 'User'} 👋",
                        style: GoogleFonts.poppins(
                          fontSize: 22,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        "Let's begin your day with calm energy",
                        style: GoogleFonts.poppins(
                          fontSize: 14,
                          color: Colors.grey[600],
                        ),
                      ),
                      const SizedBox(height: 20),

                      _featuredCard(),
                      const SizedBox(height: 20),

                      _dailyMoodCard(),
                      const SizedBox(height: 30),
                    ],
                  ),
        ),
      ),
    );
  }

  /* ---------------- FEATURED JOURNAL CARD ---------------- */

  Widget _featuredCard() {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFFFFD6D1),
        borderRadius: BorderRadius.circular(20),
      ),
      padding: const EdgeInsets.all(20),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  "Ready to start your journey?",
                  style: GoogleFonts.poppins(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                Text(
                  "Write your first journal entry today.",
                  style: GoogleFonts.poppins(fontSize: 13),
                ),
                const SizedBox(height: 10),
                ElevatedButton(
                  onPressed: () {
                    showDialog(
                      context: context,
                      builder: (context) => const CalendarPopupCard(),
                    );
                  },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.white,
                    foregroundColor: Colors.black,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(30),
                    ),
                  ),
                  child: const Text("Get Started"),
                ),
              ],
            ),
          ),
          const Icon(Icons.book_outlined, size: 80, color: Colors.white70),
        ],
      ),
    );
  }

  /* ---------------- DAILY MOOD CARD ---------------- */

  Widget _dailyMoodCard() {
    return GestureDetector(
      onTap: () {
        Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => const MoodInputPage()),
        );
      },
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            colors: [Color(0xFFF3E8FF), Color(0xFFFFF1F8)],
          ),
          borderRadius: BorderRadius.circular(24),
          boxShadow: [
            BoxShadow(color: Colors.purple.withOpacity(0.1), blurRadius: 10),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.wb_sunny, color: Colors.purple),
                const SizedBox(width: 6),
                Text(
                  "Daily Journal",
                  style: GoogleFonts.poppins(
                    fontWeight: FontWeight.w600,
                    color: Colors.purple,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              "How are you feeling today?",
              style: GoogleFonts.poppins(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                _moodChip("😊", "Great"),
                _moodChip("🙂", "Good"),
                _moodChip("😐", "Okay"),
                _moodChip("😕", "Not Great"),
                _moodChip("😢", "Bad"),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _moodChip(String emoji, String label) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(emoji, style: const TextStyle(fontSize: 18)),
          const SizedBox(width: 6),
          Text(label),
        ],
      ),
    );
  }

  /* ---------------- BOTTOM NAV ---------------- */

  Widget _buildBottomNavBar() {
    return CurvedNavigationBar(
      backgroundColor: Colors.transparent,
      color: Colors.black,
      buttonBackgroundColor: const Color(0xFF6A1B9A),
      height: 65,
      items: const [
        CurvedNavigationBarItem(
          child: Icon(Icons.home, color: Colors.white),
          label: 'Home',
        ),
        CurvedNavigationBarItem(
          child: Icon(Icons.access_time, color: Colors.white),
          label: 'Journal',
        ),
        CurvedNavigationBarItem(
          child: Icon(Icons.bar_chart, color: Colors.white),
          label: 'Stats',
        ),
        CurvedNavigationBarItem(
          child: Icon(Icons.person, color: Colors.white),
          label: 'Profile',
        ),
      ],
      onTap: (index) {
        if (index == 1) {
          Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => const JournalEntriesListPage()),
          );
        } else if (index == 2) {
          Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => const StatisticsScreen()),
          );
        } else if (index == 3) {
          Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => const ProfileScreen()),
          );
        }
      },
    );
  }
}
