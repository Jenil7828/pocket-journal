
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class MoodInputPage extends StatefulWidget {
  const MoodInputPage({super.key});

  @override
  State<MoodInputPage> createState() => _MoodInputPageState();
}

class _MoodInputPageState extends State<MoodInputPage>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  final Random _random = Random();
  String _currentMood = "Spin to find out!";
  Color _moodColor = Colors.white;

  final List<Map<String, dynamic>> _moods = [
    {'name': 'Happy', 'color': const Color(0xFFFFD54F)}, // Yellow
    {'name': 'Sad', 'color': const Color(0xFF64B5F6)}, // Blue
    {'name': 'Angry', 'color': const Color(0xFFEF5350)}, // Red
    {'name': 'Calm', 'color': const Color(0xFF81C784)}, // Green
    {'name': 'Energetic', 'color': const Color(0xFFFF8A65)}, // Orange
    {'name': 'Anxious', 'color': const Color(0xFFBA68C8)}, // Purple
  ];

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 4),
    );
  }


  
  // Revised Spin Logic
  double _rotation = 0.0;

  void _spin() {
     if (_controller.isAnimating) return;

     double randomAngle = _random.nextDouble() * 2 * pi;
     double newTarget = _rotation + (5 * 2 * pi) + randomAngle;
    
     // We need to animate from _rotation to newTarget.
     _controller.duration = const Duration(seconds: 4);
     
     Animation<double> curve = CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic);
     Animation<double> rotationAnimation = Tween<double>(begin: _rotation, end: newTarget).animate(curve);

     rotationAnimation.addListener(() {
       setState(() {
         _rotation = rotationAnimation.value;
       });
     });

     rotationAnimation.addStatusListener((status) {
       if (status == AnimationStatus.completed) {
         _calculateMood(normalizeAngle(_rotation));
       }
     });

     _controller.reset();
     _controller.forward();
  }

  double normalizeAngle(double angle) {
    return angle % (2 * pi);
  }

  void _calculateMood(double finalAngle) {
    // Top is 0/2pi (or -pi/2 depending on drawing). 
    // Our arrow points UP.
    // Wheel rotates clockwise.
    // The segment at the TOP is the one that "wins".
    
    // Angle 0 is usually 3 o'clock in Flutter CustomPaint.
    // We will rotate the canvas by -pi/2 so 0 is at 12 o'clock.
    // But verify CustomPaint coords.
    
    // Let's assume standard unit circle: 0 is Right, pi/2 is Bottom, pi is Left, 3pi/2 is Top.
    // If we rotate the Canvas by -90deg (-pi/2), then 0 is Top.
    
    // Segment calculation:
    // Segment ARC = 2*pi / count.
    
    // If pointer is static at TOP (0 radians after canvas rotation),
    // and wheel rotates by `finalAngle`.
    // The segment under the pointer is determined by:
    // (Total Rotation) mod (2*pi).
    
    // Wait, if I rotate 10 degrees clockwise, the segment at -10 degrees comes to the top.
    // So effective angle to check is (2*pi - (finalAngle % 2*pi)) % 2*pi.
    
    double normalized = finalAngle % (2 * pi);
    double effectiveAngle = (2 * pi - normalized) % (2 * pi);
    
    double segmentSize = (2 * pi) / _moods.length;
    int index = (effectiveAngle / segmentSize).floor();
    
    // Safety check
    if (index >= _moods.length) index = 0;
    
    setState(() {
      _currentMood = _moods[index]['name'];
      _moodColor = _moods[index]['color'];
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      // Background handled by global theme (Dark Faint Violet)
      appBar: AppBar(
        title: Text("Mood Input", style: GoogleFonts.poppins()),
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new, color: Colors.white),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              "Let's capture your\nmood for today.",
              textAlign: TextAlign.center,
              style: GoogleFonts.poppins(
                fontSize: 24,
                fontWeight: FontWeight.bold,
                color: Colors.white,
              ),
            ),
            const SizedBox(height: 10),
             AnimatedOpacity(
              duration: const Duration(milliseconds: 500),
              opacity: _currentMood == "Spinning..." ? 0.5 : 1.0,
              child: Column(
                children: [
                   // Mood Icon/Emoji placeholder (optional) or just text
                   Text(
                    "Mood Indicator",
                    style: GoogleFonts.poppins(color: Colors.white70),
                  ),
                   Text(
                    _currentMood,
                    style: GoogleFonts.poppins(
                      fontSize: 28,
                      fontWeight: FontWeight.w600,
                      color: _moodColor,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 30),
            
            // WHEEL
            SizedBox(
              height: 320,
              width: 300,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  // The Rotating Wheel
                  Transform.rotate(
                    angle: _rotation,
                    child: CustomPaint(
                      size: const Size(300, 300),
                      painter: WheelPainter(moods: _moods),
                    ),
                  ),
                  // The Pointer/Indicator (Static)
                  Positioned(
                    top: 0,
                    child: Icon(Icons.arrow_drop_down, size: 50, color: Colors.white),
                  ),
                  // Center Button to Spin
                  GestureDetector(
                    onTap: _spin,
                    child: Container(
                      width: 60,
                      height: 60,
                      decoration: BoxDecoration(
                        color: Colors.white,
                        shape: BoxShape.circle,
                        boxShadow: [
                          BoxShadow(color: Colors.black26, blurRadius: 10)
                        ],
                      ),
                      child: Center(
                        child: Text(
                          "SPIN",
                          style: GoogleFonts.poppins(
                            fontWeight: FontWeight.bold,
                            color: Colors.black87
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            
            const SizedBox(height: 40),
            
            // Save Button
             ElevatedButton(
              onPressed: () {
                if (_currentMood == "Spin to find out!" || _currentMood == "Spinning...") {
                   ScaffoldMessenger.of(context).showSnackBar(
                     const SnackBar(content: Text("Please spin the wheel first!")),
                   );
                   return;
                }
                // Save Logic Here (Mock)
                ScaffoldMessenger.of(context).showSnackBar(
                   SnackBar(content: Text("Saved mood: $_currentMood")),
                );
                Navigator.pop(context);
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: _moodColor == Colors.white ? const Color(0xFF7B1FA2) : _moodColor,
                padding: const EdgeInsets.symmetric(horizontal: 50, vertical: 15),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
              ),
              child: Text(
                "Save My Feeling",
                style: GoogleFonts.poppins(
                  fontSize: 16, 
                  fontWeight: FontWeight.bold,
                  color: Colors.black87, // Contrast against bright mood colors
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class WheelPainter extends CustomPainter {
  final List<Map<String, dynamic>> moods;

  WheelPainter({required this.moods});

  @override
  void paint(Canvas canvas, Size size) {
    Offset center = Offset(size.width / 2, size.height / 2);
    double radius = min(size.width, size.height) / 2;
    
    // Rotate canvas so 0 is at top (-pi/2)
    // Actually, let's just accept 0 is at Right (standard) and handle indicator placement.
    // If indicator is at TOP, that corresponds to -pi/2 (or 3pi/2).
    // Let's draw segments starting from -pi/2.
    
    double startAngle = -pi / 2;
    double sweepAngle = (2 * pi) / moods.length;
    
    final paint = Paint()..style = PaintingStyle.fill;
    
    for (var mood in moods) {
      paint.color = mood['color'];
      canvas.drawArc(
        Rect.fromCircle(center: center, radius: radius),
        startAngle,
        sweepAngle,
        true, // useCenter
        paint,
      );
      
      // Draw Text? (Complex to rotate text, keeping it simple for now)
      
      startAngle += sweepAngle;
    }
    
    // Draw Border
    final borderPaint = Paint()
      ..color = Colors.white
      ..style = PaintingStyle.stroke
      ..strokeWidth = 4;
      
     canvas.drawCircle(center, radius, borderPaint);
     
     // Draw Center Hub Border
     canvas.drawCircle(center, 10, Paint()..color = Colors.white);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
