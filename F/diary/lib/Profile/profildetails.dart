import 'package:flutter/material.dart';

class FullProfilePage extends StatelessWidget {
  const FullProfilePage({super.key});

  static const Color primaryColor = Color(0xFF5A5A85);
  static const Color accentColor = Color(0xFF7B61FF);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF6F5FF),
      body: SafeArea(
        child: SingleChildScrollView(
          child: Column(
            children: [
              _buildHeader(context),
              const SizedBox(height: 10),
              _buildProfileCard(),
              const SizedBox(height: 16),
              _buildStatsRow(),
              const SizedBox(height: 16),
              _buildWellnessCard(),
              const SizedBox(height: 30),
            ],
          ),
        ),
      ),
    );
  }

  // 🔝 HEADER
  Widget _buildHeader(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      child: Stack(
        alignment: Alignment.center,
        children: [
          // 🔙 Back button aligned left
          Align(alignment: Alignment.centerLeft, child: _circleButton(context)),

          // 🎯 Perfect center title
          const Text(
            "Full Profile",
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
        ],
      ),
    );
  }

  // 👤 PROFILE CARD
  Widget _buildProfileCard() {
    return _card(
      child: Column(
        children: [
          CircleAvatar(
            radius: 45,
            backgroundColor: Colors.grey.shade300,
            child: const Icon(Icons.person, size: 40),
          ),
          const SizedBox(height: 12),
          const Text(
            "Saloni",
            style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 4),
          const Text("saloni@gmail.com", style: TextStyle(color: Colors.grey)),
          const SizedBox(height: 10),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: const [
              Icon(Icons.calendar_month, size: 16, color: accentColor),
              SizedBox(width: 6),
              Text(
                "Member since January 2026",
                style: TextStyle(color: Colors.grey),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // 📊 STATS
  Widget _buildStatsRow() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: const [
          Expanded(
            child: SmallCard(
              icon: Icons.menu_book,
              iconColor: Colors.blue,
              title: "Total Entries",
              value: "47",
              subtitle: "Since joining",
            ),
          ),
          SizedBox(width: 12),
          Expanded(
            child: SmallCard(
              icon: Icons.trending_up,
              iconColor: accentColor,
              title: "Current Streak",
              value: "12 days",
              subtitle: "Keep it up!",
            ),
          ),
        ],
      ),
    );
  }

  // 😊 WELLNESS
  Widget _buildWellnessCard() {
    return _card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: const [
          Text(
            "Emotional Wellness",
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
          ),
          SizedBox(height: 16),
          InfoRow("Most Common Mood", "😊 Happy"),
          InfoRow("Avg. Entries per Week", "5.2"),
          InfoRow("Longest Streak", "18 days"),
        ],
      ),
    );
  }

  // 🔘 COMMON CARD
  Widget _card({required Widget child}) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            blurRadius: 15,
            offset: const Offset(0, 5),
            color: Colors.black.withOpacity(0.06),
          ),
        ],
      ),
      child: child,
    );
  }

  // 🔙 BACK BUTTON
  Widget _circleButton(BuildContext context) {
    return GestureDetector(
      onTap: () => Navigator.pop(context),
      child: Container(
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: Colors.white,
          shape: BoxShape.circle,
          boxShadow: [
            BoxShadow(blurRadius: 8, color: Colors.black.withOpacity(0.08)),
          ],
        ),
        child: const Icon(Icons.arrow_back),
      ),
    );
  }
}

// 📦 REUSABLE SMALL CARD
class SmallCard extends StatelessWidget {
  final IconData icon;
  final Color iconColor;
  final String title;
  final String value;
  final String subtitle;

  const SmallCard({
    super.key,
    required this.icon,
    required this.iconColor,
    required this.title,
    required this.value,
    required this.subtitle,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        boxShadow: [
          BoxShadow(blurRadius: 12, color: Colors.black.withOpacity(0.05)),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: iconColor),
          const SizedBox(height: 10),
          Text(title, style: const TextStyle(color: Colors.grey)),
          const SizedBox(height: 6),
          Text(
            value,
            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 4),
          Text(subtitle, style: const TextStyle(color: Colors.grey)),
        ],
      ),
    );
  }
}

// 📊 INFO ROW
class InfoRow extends StatelessWidget {
  final String title;
  final String value;

  const InfoRow(this.title, this.value, {super.key});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(title, style: const TextStyle(color: Colors.grey)),
          Text(
            value,
            style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
          ),
        ],
      ),
    );
  }
}
