import 'package:diary/Login/login.dart';
import 'package:flutter/material.dart';
import 'package:smooth_page_indicator/smooth_page_indicator.dart';


class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final PageController _controller = PageController();
  bool _isLastPage = false;

  // Data for the three screens
  final List<OnboardData> _screens = [
    OnboardData(
      title: "Use Journal\nSummaries",
      subtitle: "Access session notes easily",
      color: const Color(0xFFF7E6D4), // Cream
      image: 'assets/home/cartoon1.jpeg',
    ),
    OnboardData(
      title: "De-clutter Your\nThinking",
      subtitle: "One step at a time, with the 2 column technique",
      color: const Color(0xFFE2D7F5), // Light Purple
      image: 'assets/home/cartoon2.jpeg',
    ),
    OnboardData(
      title: "Revisit Your\nPlans",
      subtitle:
          "Use the diary to continue working on your path even after finishing a session",
      color: const Color(0xFFF1E1B9), // Pale Yellow
      image: 'assets/home/cartoon3.jpeg',
    ),
  ];

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          // 1. The Sliding Pages
          PageView.builder(
            controller: _controller,
            itemCount: _screens.length,
            onPageChanged: (index) {
              setState(() {
                _isLastPage = (index == _screens.length - 1);
              });
            },
            // Detection for swiping past the last page
            physics: const BouncingScrollPhysics(),
            itemBuilder: (context, index) {
              return OnboardPage(data: _screens[index]);
            },
          ),

          // 2. The Smooth Indicator & Navigation Trigger
          Positioned(
            bottom: 60,
            left: 0,
            right: 0,
            child: Column(
              children: [
                Center(
                  child: SmoothPageIndicator(
                    controller: _controller,
                    count: _screens.length,
                    effect: const ExpandingDotsEffect(
                      activeDotColor: Color(0xFF7B4D9E), // Purple
                      dotColor: Colors.black26,
                      dotHeight: 8,
                      dotWidth: 8,
                      expansionFactor: 3,
                      spacing: 6,
                    ),
                  ),
                ),
                const SizedBox(height: 20),
                // Optional: "Done" button that appears only on the last page
                if (_isLastPage)
                  TextButton(
                    onPressed: () {
                      Navigator.pushReplacement(
                        context,
                        MaterialPageRoute(
                          builder: (context) => const LoginPage(),
                        ),
                      );
                    },
                    child: const Text(
                      "Done",
                      style: TextStyle(
                        color: Color(0xFF7B4D9E),
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
              ],
            ),
          ),

          // 3. Invisible detector for swiping off the last page
          NotificationListener<ScrollNotification>(
            onNotification: (notification) {
              if (notification is ScrollEndNotification &&
                  _isLastPage &&
                  _controller.position.pixels ==
                      _controller.position.maxScrollExtent) {
                // If user swipes again at the very end
                Navigator.pushReplacement(
                  context,
                  MaterialPageRoute(builder: (context) => const LoginPage()),
                );
              }
              return false;
            },
            child: const SizedBox.shrink(),
          ),
        ],
      ),
    );
  }
}

// Widget for individual page content
class OnboardPage extends StatelessWidget {
  final OnboardData data;

  const OnboardPage({super.key, required this.data});

  @override
  Widget build(BuildContext context) {
    return Container(
      color: data.color,
      padding: const EdgeInsets.symmetric(horizontal: 40),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: Container(
              height: 300,
              decoration: BoxDecoration(
                image: DecorationImage(
                  image: AssetImage(data.image),
                  fit: BoxFit.contain,
                ),
              ),
            ),
          ),
          const SizedBox(height: 50),
          Text(
            data.title,
            style: const TextStyle(
              fontSize: 28,
              fontWeight: FontWeight.bold,
              color: Color(0xFF2E2E5D),
              height: 1.2,
            ),
          ),
          const SizedBox(height: 16),
          Text(
            data.subtitle,
            style: TextStyle(
              fontSize: 14,
              color: Colors.black.withOpacity(0.6),
              height: 1.5,
            ),
          ),
        ],
      ),
    );
  }
}

// Data Model
class OnboardData {
  final String title, subtitle, image;
  final Color color;

  OnboardData({
    required this.title,
    required this.subtitle,
    required this.color,
    required this.image,
  });
}
