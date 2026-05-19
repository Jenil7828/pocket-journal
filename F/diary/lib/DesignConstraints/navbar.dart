import 'package:diary/Dashboard/dashboard.dart';
import 'package:diary/Dashboard/entries.dart';
import 'package:diary/Dashboard/media_recommendations.dart';
import 'package:diary/Profile/profile.dart';
import 'package:flutter/material.dart';

class CustomBottomNavBar extends StatefulWidget {
  const CustomBottomNavBar({super.key});

  // 🔥 IMPORTANT: Access navbar state from anywhere
  static _CustomBottomNavBarState? of(BuildContext context) {
    return context.findAncestorStateOfType<_CustomBottomNavBarState>();
  }

  @override
  State<CustomBottomNavBar> createState() => _CustomBottomNavBarState();
}

class _CustomBottomNavBarState extends State<CustomBottomNavBar> {
  int currentIndex = 0;

  // 🔥 CHANGE TAB METHOD
  void changeTab(int index) {
    setState(() {
      currentIndex = index;
    });
  }

  final List<Widget> pages = const [
    DashboardPage(),
    EntriesPage(),
    RecommendationPage(),
    ProfilePage(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(index: currentIndex, children: pages),
      bottomNavigationBar: Container(
        margin: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(30),
          boxShadow: [
            BoxShadow(color: Colors.black.withOpacity(0.1), blurRadius: 20),
          ],
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(30),
          child: BottomNavigationBar(
            backgroundColor: const Color(0xFF1E2D4C), // Navy
            currentIndex: currentIndex,
            onTap: changeTab, // 🔥 simplified
            type: BottomNavigationBarType.fixed,
            elevation: 0,
            selectedItemColor: const Color(0xFFCEC0BB),
            unselectedItemColor: Colors.grey,
            items: const [
              BottomNavigationBarItem(icon: Icon(Icons.home), label: 'Home'),
              BottomNavigationBarItem(icon: Icon(Icons.edit), label: 'Entries'),
              BottomNavigationBarItem(icon: Icon(Icons.photo), label: 'Media'),
              BottomNavigationBarItem(
                icon: Icon(Icons.person),
                label: 'Profile',
              ),
            ],
          ),
        ),
      ),
    );
  }
}
