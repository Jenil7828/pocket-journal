import 'package:diary/Login/login.dart';
import 'package:flutter/material.dart';

class StartScreen extends StatefulWidget {
  const StartScreen({super.key});

  @override
  State<StartScreen> createState() => _StartScreenState();
}

class _StartScreenState extends State<StartScreen> {
  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;

    return Scaffold(
      body: TweenAnimationBuilder<double>(
        tween: Tween(begin: 0.85, end: 1.0), // 👈 Start medium, zoom to full
        duration: const Duration(seconds: 2),
        curve: Curves.easeOutCubic, // Smooth cinematic zoom
        builder: (context, scale, child) {
          return Transform.scale(
            scale: scale,
            child: Stack(
              children: [
                // ✅ Background image with smooth zoom-in effect
                SizedBox(
                  width: size.width,
                  height: size.height,
                  child: Image.asset('assets/home/home.png', fit: BoxFit.cover),
                ),

                // ✅ Gradient overlay for better contrast
                Container(
                  width: size.width,
                  height: size.height,
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [
                        Colors.black.withOpacity(0.2),
                        Colors.transparent,
                        Colors.black.withOpacity(0.35),
                      ],
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                    ),
                  ),
                ),

                // ✅ Center title “Mood Diary”
                Align(
                  alignment: Alignment.center,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: const [
                      Text(
                        'MOOD',
                        style: TextStyle(
                          fontFamily: 'Poppins',
                          fontSize: 48,
                          fontWeight: FontWeight.w800,
                          color: Colors.white,
                          letterSpacing: 1.5,
                        ),
                      ),
                      Text(
                        'DIARY',
                        style: TextStyle(
                          fontFamily: 'Poppins',
                          fontSize: 42,
                          fontWeight: FontWeight.w700,
                          color: Colors.white,
                          letterSpacing: 1.2,
                        ),
                      ),
                    ],
                  ),
                ),

                // ✅ “Start” Button (styled similar to image)
                Align(
                  alignment: Alignment.bottomCenter,
                  child: Padding(
                    padding: const EdgeInsets.only(bottom: 70),
                    child: AnimatedOpacity(
                      opacity: scale > 0.95 ? 1 : 0,
                      duration: const Duration(milliseconds: 600),
                      child: GestureDetector(
                        onTap: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (context) => const LoginScreen(),
                            ),
                          );
                        },
                        child: Container(
                          width: size.width * 0.5,
                          height: 55,
                          decoration: BoxDecoration(
                            color: const Color(0xFFFEF5E4), // pastel cream
                            borderRadius: BorderRadius.circular(30),
                            boxShadow: [
                              BoxShadow(
                                color: Colors.brown.withOpacity(0.2),
                                offset: const Offset(0, 5),
                                blurRadius: 10,
                              ),
                            ],
                            border: Border.all(
                              color: const Color(
                                0xFFF3D9B1,
                              ), // soft border tone
                              width: 1.5,
                            ),
                          ),
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: const [
                              Text(
                                'Start',
                                style: TextStyle(
                                  fontSize: 20,
                                  fontWeight: FontWeight.bold,
                                  color: Color(0xFF744B27), // warm brown text
                                  letterSpacing: 1.1,
                                ),
                              ),
                              SizedBox(width: 6),
                              Icon(
                                Icons.play_arrow_rounded,
                                color: Color(0xFF744B27),
                                size: 26,
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
