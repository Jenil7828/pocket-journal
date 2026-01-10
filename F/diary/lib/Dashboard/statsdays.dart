import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';

class MoodTrendsPage extends StatefulWidget {
  final int days;
  const MoodTrendsPage({super.key, required this.days});

  @override
  State<MoodTrendsPage> createState() => _MoodTrendsPageState();
}

class _MoodTrendsPageState extends State<MoodTrendsPage> {
  final Dio _dio = Dio(BaseOptions(baseUrl: "http://10.156.57.242:5000"));
  final PageController _pageController = PageController();

  bool _isLoading = true;
  List<dynamic> moodData = [];
  int _currentPage = 0;

  @override
  void initState() {
    super.initState();
    _fetchMoodTrends();
  }

  Future<void> _fetchMoodTrends() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final token = prefs.getString('idToken');
      if (token == null) throw Exception("No token found");

      final response = await _dio.get(
        '/mood-trends?days=${widget.days}',
        options: Options(headers: {"Authorization": "Bearer $token"}),
      );

      if (response.statusCode == 200 && response.data != null) {
        final data = response.data;

        setState(() {
          // Safely extract list
          if (data is List) {
            moodData = data;
          } else if (data is Map && data['trends'] is List) {
            moodData = data['trends'];
          } else if (data is Map && data['data'] is List) {
            moodData = data['data'];
          } else {
            moodData = [];
          }
          _isLoading = false;
        });
      }
    } on DioException catch (e) {
      print("❌ Dio error: ${e.message}");
    } catch (e) {
      print("⚠️ Unexpected error: $e");
      setState(() => _isLoading = false);
    }
  }

  String _getEmoji(String mood) {
    switch (mood.toLowerCase()) {
      case "happy":
        return "😊";
      case "sad":
        return "😢";
      case "anger":
        return "😠";
      case "calm":
        return "😌";
      case "fear":
        return "😨";
      case "tired":
        return "🥱";
      case "excited":
        return "🤩";
      default:
        return "🙂";
    }
  }

  Color _getMoodColor(String mood) {
    switch (mood.toLowerCase()) {
      case "happy":
        return const Color(0xFF00C853);
      case "sad":
        return const Color(0xFF2979FF);
      case "anger":
        return const Color(0xFFFF1744);
      case "calm":
        return const Color(0xFF00BCD4);
      case "fear":
        return const Color(0xFF9C27B0);
      case "tired":
        return const Color(0xFF757575);
      case "excited":
        return const Color(0xFFFFC107);
      default:
        return Colors.grey;
    }
  }

  void _goToNextPage() {
    if (_currentPage < moodData.length - 1) {
      _pageController.nextPage(
        duration: const Duration(milliseconds: 500),
        curve: Curves.easeInOut,
      );
    } else {
      // Optionally show a toast or finish message
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("End of mood trends 😊"),
          duration: Duration(seconds: 1),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8F9FF),
      appBar: AppBar(
        elevation: 0,
        backgroundColor: Colors.transparent,
        centerTitle: true,
        title: Text(
          "Mood Trends (${widget.days} Days)",
          style: GoogleFonts.poppins(
            color: Colors.black87,
            fontWeight: FontWeight.w600,
          ),
        ),
        leading: const BackButton(color: Colors.black87),
      ),
      body:
          _isLoading
              ? const Center(child: CircularProgressIndicator())
              : moodData.isEmpty
              ? const Center(child: Text("No mood data available"))
              : Column(
                children: [
                  Expanded(
                    child: PageView.builder(
                      controller: _pageController,
                      scrollDirection: Axis.horizontal,
                      onPageChanged: (index) {
                        setState(() => _currentPage = index);
                      },
                      itemCount: moodData.length,
                      itemBuilder: (context, index) {
                        final moodItem = moodData[index];
                        final emoji = _getEmoji(moodItem['mood']);
                        final color = _getMoodColor(moodItem['mood']);
                        final confidence = ((moodItem['confidence'] ?? 0.0) *
                                100)
                            .toStringAsFixed(0);
                        final date = moodItem['date'] ?? "Unknown";

                        return Padding(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 20,
                            vertical: 25,
                          ),
                          child: Container(
                            decoration: BoxDecoration(
                              gradient: LinearGradient(
                                colors: [
                                  color.withOpacity(0.15),
                                  color.withOpacity(0.4),
                                ],
                                begin: Alignment.topCenter,
                                end: Alignment.bottomCenter,
                              ),
                              borderRadius: BorderRadius.circular(25),
                              boxShadow: [
                                BoxShadow(
                                  color: color.withOpacity(0.3),
                                  blurRadius: 12,
                                  offset: const Offset(0, 6),
                                ),
                              ],
                            ),
                            padding: const EdgeInsets.symmetric(
                              horizontal: 24,
                              vertical: 30,
                            ),
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Container(
                                  padding: const EdgeInsets.all(22),
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    color: color.withOpacity(0.2),
                                  ),
                                  child: Text(
                                    emoji,
                                    style: const TextStyle(fontSize: 90),
                                  ),
                                ),
                                const SizedBox(height: 18),
                                Text(
                                  moodItem['mood'].toString().toUpperCase(),
                                  style: GoogleFonts.poppins(
                                    fontSize: 26,
                                    fontWeight: FontWeight.bold,
                                    color: color,
                                  ),
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  "$confidence% confidence",
                                  style: GoogleFonts.poppins(
                                    fontSize: 16,
                                    color: Colors.black54,
                                  ),
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  date,
                                  style: GoogleFonts.poppins(
                                    fontSize: 15,
                                    color: Colors.grey[700],
                                  ),
                                ),
                                const SizedBox(height: 30),
                                Container(
                                  height: 140,
                                  width: double.infinity,
                                  margin: const EdgeInsets.symmetric(
                                    horizontal: 10,
                                  ),
                                  decoration: BoxDecoration(
                                    color: Colors.white,
                                    borderRadius: BorderRadius.circular(20),
                                    boxShadow: [
                                      BoxShadow(
                                        color: Colors.black.withOpacity(0.1),
                                        blurRadius: 10,
                                        offset: const Offset(0, 4),
                                      ),
                                    ],
                                  ),
                                  child: const Center(
                                    child: Icon(
                                      Icons.bar_chart_rounded,
                                      color: Colors.grey,
                                      size: 60,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        );
                      },
                    ),
                  ),

                  // 🔘 Next Button
                  Padding(
                    padding: const EdgeInsets.symmetric(
                      vertical: 20,
                      horizontal: 20,
                    ),
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: _getMoodColor(
                          moodData[_currentPage]['mood'],
                        ),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(30),
                        ),
                        padding: const EdgeInsets.symmetric(
                          horizontal: 60,
                          vertical: 14,
                        ),
                      ),
                      onPressed: _goToNextPage,
                      child: Text(
                        _currentPage == moodData.length - 1 ? "Finish" : "Next",
                        style: GoogleFonts.poppins(
                          color: Colors.white,
                          fontWeight: FontWeight.w600,
                          fontSize: 16,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
    );
  }
}
