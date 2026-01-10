import 'package:diary/Dashboard/statsdays.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';

class StatisticsScreen extends StatefulWidget {
  const StatisticsScreen({super.key});

  @override
  State<StatisticsScreen> createState() => _StatisticsScreenState();
}

class _StatisticsScreenState extends State<StatisticsScreen> {
  final Dio _dio = Dio(
    BaseOptions(
      baseUrl: "http://10.252.110.242:5000",
      headers: {"Content-Type": "application/json"},
    ),
  );

  bool _isLoading = true;
  Map<String, dynamic>? statsData;
  String selectedTrend = '7 Days'; // Default selected toggle

  @override
  void initState() {
    super.initState();
    _fetchStats();
  }

  Future<void> _fetchStats() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final token = prefs.getString('idToken');
      if (token == null) throw Exception("No token found");

      final response = await _dio.get(
        '/stats',
        options: Options(headers: {"Authorization": "Bearer $token"}),
      );

      if (response.statusCode == 200 && response.data != null) {
        setState(() {
          statsData = response.data;
          _isLoading = false;
        });
      } else {
        setState(() {
          statsData = null;
          _isLoading = false;
        });
      }
    } on DioException catch (e) {
      print("❌ Error fetching stats: $e");
    } catch (e) {
      print("⚠️ Unexpected error: $e");
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8F9FF),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: Text(
          "My Journal Insights",
          style: GoogleFonts.poppins(
            color: Colors.black87,
            fontWeight: FontWeight.w600,
          ),
        ),
        centerTitle: true,
        leading: const BackButton(color: Colors.black87),
      ),
      body:
          _isLoading
              ? const Center(child: CircularProgressIndicator())
              : statsData == null
              ? const Center(child: Text("No data found"))
              : _buildStatsContent(),
    );
  }

  Widget _buildStatsContent() {
    final rawMoods = statsData!['mood_distribution'] as Map<String, dynamic>;
    final totalEntries = statsData!['total_entries'];

    final moods = rawMoods.map((key, value) {
      final normalizedKey =
          key.toString().substring(0, 1).toUpperCase() +
          key.toString().substring(1).toLowerCase();
      return MapEntry(normalizedKey, value);
    });

    final moodColors = {
      "Happy": const Color(0xFFFFC107),
      "Sad": const Color(0xFF6C63FF),
      "Calm": const Color(0xFF4CAF50),
      "Anxious": const Color(0xFFEF5350),
      "Anger": const Color(0xFFFF7043),
      "Excited": const Color(0xFFFF6F91),
      "Tired": const Color(0xFF90A4AE),
      "Fear": const Color(0xFF9C27B0),
      "Neutral": const Color(0xFF607D8B),
    };

    return SingleChildScrollView(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
        child: Column(
          children: [
            const SizedBox(height: 10),

            // 🔘 Horizontal Scrollable Buttons
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  _buildGradientToggleButton(
                    label: "Mood Trends (7 Days)",
                    isSelected: selectedTrend == '7 Days',
                    gradientColors: const [
                      Color(0xFFDA4453),
                      Color(0xFF89216B),
                    ],
                    onTap: () {
                      setState(() => selectedTrend = '7 Days');
                      Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (_) => const MoodTrendsPage(days: 7),
                        ),
                      );
                    },
                    icon: Icons.bar_chart_rounded,
                  ),
                  const SizedBox(width: 15),
                  _buildGradientToggleButton(
                    label: "Mood Trends (30 Days)",
                    isSelected: selectedTrend == '30 Days',
                    gradientColors: const [
                      Color(0xFF6A11CB),
                      Color(0xFF2575FC),
                    ],
                    onTap: () {
                      setState(() => selectedTrend = '30 Days');
                      Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (_) => const MoodTrendsPage(days: 30),
                        ),
                      );
                    },
                    icon: Icons.timeline_rounded,
                  ),
                ],
              ),
            ),

            const SizedBox(height: 30),

            // 🩵 Total Entries Card
            Container(
              padding: const EdgeInsets.all(22),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFF74ABE2), Color(0xFF5563DE)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(20),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.1),
                    blurRadius: 10,
                    offset: const Offset(0, 5),
                  ),
                ],
              ),
              child: Column(
                children: [
                  Text(
                    "$totalEntries",
                    style: GoogleFonts.poppins(
                      fontSize: 72,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),
                  Text(
                    "Moments captured in your journal",
                    style: GoogleFonts.poppins(
                      color: Colors.white.withOpacity(0.9),
                      fontSize: 16,
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 35),

            // 🌈 Mood Tracker Section
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(22),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(25),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.07),
                    blurRadius: 12,
                    offset: const Offset(0, 6),
                  ),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    "Mood Tracker",
                    style: GoogleFonts.poppins(
                      fontSize: 20,
                      fontWeight: FontWeight.w600,
                      color: Colors.black87,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    "Your emotions over time",
                    style: GoogleFonts.poppins(
                      fontSize: 13,
                      color: Colors.black54,
                    ),
                  ),
                  const SizedBox(height: 25),
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children:
                          moods.entries.map((entry) {
                            final mood = entry.key;
                            final percent = (entry.value as num).toDouble();
                            final color = moodColors[mood] ?? Colors.grey;
                            return Padding(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 8,
                              ),
                              child: _buildEmotionBar(mood, percent, color),
                            );
                          }).toList(),
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 30),

            // 🌤️ Reflection Section
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFFFFD194), Color(0xFFD1913C)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(20),
                boxShadow: [
                  BoxShadow(
                    color: Colors.orange.withOpacity(0.3),
                    blurRadius: 10,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: Text(
                "“Each day you write is another page of strength, reflection, and growth.”",
                textAlign: TextAlign.center,
                style: GoogleFonts.poppins(
                  color: Colors.white,
                  fontSize: 15,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
            const SizedBox(height: 25),

            // 💡 Quick Stats
            Container(
              padding: const EdgeInsets.all(18),
              width: double.infinity,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFFB993D6), Color(0xFF8CA6DB)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(20),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.1),
                    blurRadius: 8,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: Text(
                "You’ve been consistent and mindful 🌿\nKeep journaling to see your emotional growth over time!",
                textAlign: TextAlign.center,
                style: GoogleFonts.poppins(color: Colors.white, fontSize: 14),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// 🔘 Gradient Toggle Button
  Widget _buildGradientToggleButton({
    required String label,
    required bool isSelected,
    required List<Color> gradientColors,
    required VoidCallback onTap,
    required IconData icon,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 250),
        height: 52,
        width: 160,
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: gradientColors,
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: BorderRadius.circular(30),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.15),
              blurRadius: 8,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Padding(
          padding: const EdgeInsets.all(10),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, color: Colors.white, size: 20),
              const SizedBox(width: 8),
              Flexible(
                child: Text(
                  label,
                  textAlign: TextAlign.center,
                  style: GoogleFonts.poppins(
                    color: Colors.white,
                    fontWeight: FontWeight.w600,
                    fontSize: 12.5,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// 📊 Mood Bar Widget
  Widget _buildEmotionBar(String mood, double percent, Color color) {
    final barHeight = (percent / 100) * 180;
    return Column(
      mainAxisAlignment: MainAxisAlignment.end,
      children: [
        Stack(
          alignment: Alignment.bottomCenter,
          children: [
            Container(
              height: 180,
              width: 50,
              decoration: BoxDecoration(
                color: color.withOpacity(0.15),
                borderRadius: BorderRadius.circular(30),
              ),
            ),
            AnimatedContainer(
              duration: const Duration(milliseconds: 800),
              curve: Curves.easeOut,
              height: barHeight,
              width: 50,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(30),
                color: color,
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        Text(
          "${percent.toStringAsFixed(0)}%",
          style: GoogleFonts.poppins(
            fontSize: 15,
            fontWeight: FontWeight.bold,
            color: Colors.black87,
          ),
        ),
        Text(
          mood,
          style: GoogleFonts.poppins(fontSize: 14, color: Colors.black87),
        ),
      ],
    );
  }
}
