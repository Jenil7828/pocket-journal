import 'package:diary/Profile/goal.dart';
import 'package:diary/Profile/habbits.dart';
import 'package:diary/Profile/strength.dart';
import 'package:diary/Profile/weakness.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:diary/DesignConstraints/appBar.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF9F9FF),
      appBar: const CustomAppBar(title: "Profile", showBack: true),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 15),
        child: Column(
          children: [
            _buildProfileHeader(),
            const SizedBox(height: 25),

            
            _buildInsightCard(
              context,
              title: "🎯 Your Goals",
              color: const Color(0xFF7C4DFF),
              icon: Icons.flag_outlined,
              page: const GoalPage(),
            ),
            _buildInsightCard(
              context,
              title: "💪 Strengths",
              color: const Color(0xFF26A69A),
              icon: Icons.star_outline,
              page: const StrengthPage(),
            ),
            _buildInsightCard(
              context,
              title: "⚡ Weaknesses",
              color: const Color(0xFFFF7043),
              icon: Icons.warning_amber_rounded,
              page: const WeaknessPage(),
            ),
            _buildInsightCard(
              context,
              title: "🕒 Habits",
              color: const Color(0xFFFFCA28),
              icon: Icons.repeat_rounded,
              page: const HabitPage(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildProfileHeader() {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF7B68EE),
        borderRadius: BorderRadius.circular(20),
      ),
      padding: const EdgeInsets.all(20),
      child: Column(
        children: [
          const CircleAvatar(
            radius: 45,
            backgroundColor: Colors.white,
            child: Icon(Icons.person, color: Color(0xFF7B68EE), size: 50),
          ),
          const SizedBox(height: 12),
          Text(
            "Jenil Rathod",
            style: GoogleFonts.poppins(
              fontSize: 20,
              color: Colors.white,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            "jenilrathod117@gmail.com",
            style: GoogleFonts.poppins(fontSize: 14, color: Colors.white70),
          ),
        ],
      ),
    );
  }

  Widget _buildInsightCard(
    BuildContext context, {
    required String title,
    required Color color,
    required IconData icon,
    required Widget page,
  }) {
    return GestureDetector(
      onTap:
          () =>
              Navigator.push(context, MaterialPageRoute(builder: (_) => page)),
      child: Container(
        margin: const EdgeInsets.only(bottom: 16),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(
              color: Colors.grey.shade300,
              blurRadius: 6,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: ListTile(
          leading: CircleAvatar(
            radius: 25,
            backgroundColor: color.withOpacity(0.1),
            child: Icon(icon, color: color, size: 26),
          ),
          title: Text(
            title,
            style: GoogleFonts.poppins(
              fontSize: 16,
              fontWeight: FontWeight.w600,
              color: Colors.black87,
            ),
          ),
          trailing: const Icon(
            Icons.arrow_forward_ios_rounded,
            size: 16,
            color: Colors.grey,
          ),
        ),
      ),
    );
  }
}
