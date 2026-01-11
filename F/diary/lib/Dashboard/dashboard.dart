import 'package:curved_labeled_navigation_bar/curved_navigation_bar.dart';
import 'package:curved_labeled_navigation_bar/curved_navigation_bar_item.dart';
import 'package:diary/Dashboard/calendar.dart';
import 'package:diary/Dashboard/show_entries.dart';
import 'package:diary/Dashboard/statistics.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
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
    try {
      // ✅ Try from SharedPreferences first
      final prefs = await SharedPreferences.getInstance();
      final uid = prefs.getString('uid');

      if (uid == null) {
        setState(() {
          userName = 'User';
          isLoading = false;
        });
        return;
      }

      // ✅ Fetch from Firestore
      final doc =
          await FirebaseFirestore.instance.collection('users').doc(uid).get();

      if (doc.exists) {
        setState(() {
          userName = doc.data()?['name'] ?? 'User';
          isLoading = false;
        });
      } else {
        setState(() {
          userName = 'User';
          isLoading = false;
        });
      }
    } catch (e) {
      debugPrint('⚠️ Error fetching user name: $e');
      setState(() {
        userName = 'User';
        isLoading = false;
      });
    }
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
                      // ✅ Dynamic Greeting Header
                      Text(
                        "Good Morning, ${userName ?? 'User'} 👋",
                        style: GoogleFonts.poppins(
                          fontSize: 22,
                          fontWeight: FontWeight.bold,
                          color: Colors.black87,
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

                      // Featured Card
                      _featuredCard(),

                      const SizedBox(height: 30),
                    ],
                  ),
        ),
      ),
    );
  }

  // Featured Top Card
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
                  style: GoogleFonts.poppins(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  "Write your first journal entry today.",
                  style: GoogleFonts.poppins(fontSize: 13),
                ),
                const SizedBox(height: 10),
                ElevatedButton(
                  onPressed: () {
                    // ✅ CHANGED: Show the calendar dialog
                    showDialog(
                      context: context,
                      builder: (context) => const CalendarPopupCard(),
                    );
                  },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.white,
                    foregroundColor: Colors.black87,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(30),
                    ),
                  ),
                  child: const Text("Get Started"),
                ),
              ],
            ),
          ),
          const SizedBox(width: 10),
          const Icon(Icons.book_outlined, size: 80, color: Colors.white70),
        ],
      ),
    );
  }

  // Bottom Navigation Bar

  Widget _buildBottomNavBar() {
  return CurvedNavigationBar(
    backgroundColor: Colors.transparent, // keeps body background visible
    color: Colors.black, // main bar color
    buttonBackgroundColor: const Color(0xFF6A1B9A), // purple highlight
    height: 65,
    animationDuration: const Duration(milliseconds: 400),
    index: 0,
    items: const [
      CurvedNavigationBarItem(
        child: Icon(Icons.home, color: Colors.white),
        label: 'Home',
        labelStyle: TextStyle(color: Colors.white, fontSize: 12), // ✅ white label
      ),
      CurvedNavigationBarItem(
        child: Icon(Icons.access_time, color: Colors.white),
        label: 'Journal',
        labelStyle: TextStyle(color: Colors.white, fontSize: 12), // ✅ white label
      ),
      CurvedNavigationBarItem(
        child: Icon(Icons.bar_chart, color: Colors.white),
        label: 'Stats',
        labelStyle: TextStyle(color: Colors.white, fontSize: 12), // ✅ white label
      ),
      CurvedNavigationBarItem(
        child: Icon(Icons.person, color: Colors.white),
        label: 'Profile',
        labelStyle: TextStyle(color: Colors.white, fontSize: 12), // ✅ white label
      ),
    ],
    onTap: (index) {
      switch (index) {
        case 0:
          // Home
          break;
        case 1:
          // Journal
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => const JournalEntriesListPage(),
            ),
          );
          break;
        case 2:
          // ✅ Navigate to Statistics Page
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => const StatisticsScreen(),
            ),
          );
          break;
        case 3:
          // Profile
          break;
      }
    },
  );
}

}
