import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'dart:developer';
import 'login.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _nameController = TextEditingController();
  bool _isLoading = false;

  Future<void> _registerUser() async {
    setState(() => _isLoading = true);
    log('🔹 Starting registration...');

    try {
      final auth = FirebaseAuth.instance;
      final firestore = FirebaseFirestore.instance;

      log('📨 Creating user with email: ${_emailController.text}');
      UserCredential userCredential = await auth.createUserWithEmailAndPassword(
        email: _emailController.text.trim(),
        password: _passwordController.text.trim(),
      );

      final user = userCredential.user;
      log('✅ Firebase user created successfully! UID: ${user?.uid}');

      if (user == null) {
        throw FirebaseAuthException(
          code: 'unknown',
          message: 'User creation failed',
        );
      }

      await firestore.collection('users').doc(user.uid).set({
        'uid': user.uid,
        'name': _nameController.text.trim(),
        'email': _emailController.text.trim(),
        'createdAt': FieldValue.serverTimestamp(),
      });

      log('🗄️ User data stored in Firestore (collection: users)');
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('✅ Account created successfully!')),
      );

      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => const LoginScreen()),
      );
    } on FirebaseAuthException catch (e) {
      log('⚠️ FirebaseAuthException: ${e.code} — ${e.message}');
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('⚠️ ${e.message}')));
    } catch (e, stack) {
      log('💥 Unexpected error: $e', stackTrace: stack);
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('💥 Error: $e')));
    } finally {
      setState(() => _isLoading = false);
      log('🔸 Registration process finished.');
    }
  }

  @override
  Widget build(BuildContext context) {
    final lavender = const Color(0xFFD1C4E9);

    return Scaffold(
      backgroundColor: Colors.white,
      body: Stack(
        children: [
          // Lavender wave background
          CustomPaint(
            size: Size(
              MediaQuery.of(context).size.width,
              MediaQuery.of(context).size.height * 0.45,
            ),
            painter: WavePainter(),
          ),

          // Foreground UI
          SingleChildScrollView(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 30, vertical: 80),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SizedBox(height: 40),
                  const Text(
                    "Create Account",
                    style: TextStyle(
                      fontSize: 32,
                      fontWeight: FontWeight.bold,
                      color: Colors.black87,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    "Sign up to get started!",
                    style: TextStyle(color: Colors.grey[600], fontSize: 15),
                  ),
                  const SizedBox(height: 150),

                  _buildTextField(
                    "Full Name",
                    Icons.person_outline,
                    controller: _nameController,
                  ),
                  const SizedBox(height: 20),
                  _buildTextField(
                    "Email",
                    Icons.email_outlined,
                    controller: _emailController,
                  ),
                  const SizedBox(height: 20),
                  _buildTextField(
                    "Password",
                    Icons.lock_outline,
                    controller: _passwordController,
                    isPassword: true,
                  ),

                  const SizedBox(height: 35),

                  _isLoading
                      ? const Center(child: CircularProgressIndicator())
                      : ElevatedButton(
                        onPressed: _registerUser,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: lavender,
                          foregroundColor: Colors.white,
                          minimumSize: const Size(double.infinity, 55),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(15),
                          ),
                        ),
                        child: const Text(
                          "Sign Up",
                          style: TextStyle(fontSize: 18),
                        ),
                      ),

                  const SizedBox(height: 20),
                  Center(
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Text("Already have an account? "),
                        GestureDetector(
                          onTap: () {
                            Navigator.pushReplacement(
                              context,
                              MaterialPageRoute(
                                builder: (_) => const LoginScreen(),
                              ),
                            );
                          },
                          child: const Text(
                            "Log In",
                            style: TextStyle(
                              color: Colors.purple,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTextField(
    String label,
    IconData icon, {
    required TextEditingController controller,
    bool isPassword = false,
  }) {
    return TextField(
      controller: controller,
      obscureText: isPassword,
      decoration: InputDecoration(
        prefixIcon: Icon(icon, color: Colors.purple[300]),
        labelText: label,
        filled: true,
        fillColor: Colors.grey[100],
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(15),
          borderSide: BorderSide.none,
        ),
      ),
    );
  }
}

/// 🌊 Lavender wave background painter
class WavePainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    Paint paint = Paint()..color = const Color(0xFFC5A3FF);
    Path path = Path();

    path.lineTo(0, size.height * 0.8);
    path.quadraticBezierTo(
      size.width * 0.25,
      size.height * 0.9,
      size.width * 0.5,
      size.height * 0.75,
    );
    path.quadraticBezierTo(
      size.width * 0.75,
      size.height * 0.6,
      size.width,
      size.height * 0.7,
    );
    path.lineTo(size.width, 0);
    path.close();

    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
