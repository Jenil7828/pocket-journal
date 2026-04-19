import 'package:diary/DesignConstraints/snackbar.dart';
import 'package:diary/Login/login.dart';

import 'package:flutter/material.dart';

class SignupPage extends StatefulWidget {
  const SignupPage({super.key});

  @override
  State<SignupPage> createState() => _SignupPageState();
}

class _SignupPageState extends State<SignupPage> {
  final TextEditingController emailController = TextEditingController();
  final TextEditingController passwordController = TextEditingController();
  final TextEditingController confirmPasswordController =
      TextEditingController();

  bool obscurePassword = true;
  bool obscureConfirmPassword = true;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      resizeToAvoidBottomInset: true,
      body: SafeArea(
        child: Container(
          width: double.infinity,
          decoration: const BoxDecoration(color: Color(0xFF6E6E9E)),
          child: SingleChildScrollView(
            padding: EdgeInsets.only(
              bottom: MediaQuery.of(context).viewInsets.bottom,
            ),
            child: Column(
              children: [
                // Top UI
                Container(
                  height: 160,
                  width: double.infinity,
                  decoration: const BoxDecoration(
                    color: Color(0xFFF5F5F5),
                    borderRadius: BorderRadius.only(
                      bottomLeft: Radius.circular(140),
                      bottomRight: Radius.circular(140),
                    ),
                  ),
                  child: Column(
                    children: [
                      const SizedBox(height: 30),
                      Image.asset('assets/home/logo.png', height: 60),
                      const Text(
                        'POCKET JOURNAL',
                        style: TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                          color: Color(0xFF5A5A85),
                        ),
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 20),

                const Text(
                  'Sign Up',
                  style: TextStyle(
                    fontSize: 22,
                    color: Colors.white,
                    fontWeight: FontWeight.w600,
                  ),
                ),

                const SizedBox(height: 20),

                // Fields
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 30),
                  child: Column(
                    children: [
                      buildTextField(
                        controller: emailController,
                        icon: Icons.person,
                        hint: 'Email Address',
                      ),
                      const SizedBox(height: 15),
                      buildTextField(
                        controller: passwordController,
                        icon: Icons.star,
                        hint: 'Password',
                        obscure: obscurePassword,
                        isPassword: true,
                        toggle: () {
                          setState(() {
                            obscurePassword = !obscurePassword;
                          });
                        },
                      ),
                      const SizedBox(height: 15),
                      buildTextField(
                        controller: confirmPasswordController,
                        icon: Icons.star,
                        hint: 'Confirm Password',
                        obscure: obscureConfirmPassword,
                        isPassword: true,
                        toggle: () {
                          setState(() {
                            obscureConfirmPassword = !obscureConfirmPassword;
                          });
                        },
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 10),

                GestureDetector(
                  onTap: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => const LoginPage(),
                      ),
                    );
                  },
                  child: const Text(
                    'Already have an account? Log in',
                    style: TextStyle(color: Colors.white70, fontSize: 12),
                  ),
                ),

                const SizedBox(height: 20),

                // BUTTON WITH SNACKBAR VALIDATION
                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.orange,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(25),
                    ),
                    padding: const EdgeInsets.symmetric(
                      horizontal: 40,
                      vertical: 12,
                    ),
                  ),
                  onPressed: () {
                    final email = emailController.text.trim();
                    final password = passwordController.text.trim();
                    final confirmPassword =
                        confirmPasswordController.text.trim();

                    // EMAIL
                    if (email.isEmpty) {
                      AppSnackbar.show(context, 'Email is required');
                      return;
                    }

                    final emailRegex = RegExp(r'^[^@]+@[^@]+\.[^@]+');
                    if (!emailRegex.hasMatch(email)) {
                      AppSnackbar.show(context, 'Enter a valid email');
                      return;
                    }

                    // PASSWORD
                    if (password.isEmpty) {
                      AppSnackbar.show(context, 'Password is required');
                      return;
                    }

                    if (password.length < 6) {
                      AppSnackbar.show(
                        context,
                        'Password must be at least 6 characters',
                      );
                      return;
                    }

                    // CONFIRM PASSWORD
                    if (confirmPassword.isEmpty) {
                      AppSnackbar.show(context, 'Confirm your password');
                      return;
                    }

                    if (confirmPassword != password) {
                      AppSnackbar.show(context, 'Passwords do not match');
                      return;
                    }

                    // SUCCESS
                    AppSnackbar.show(context, 'Signup Successful');

                    // Navigate to Login
                    Future.delayed(const Duration(milliseconds: 800), () {
                      Navigator.pushReplacement(
                        context,
                        MaterialPageRoute(builder: (_) => const LoginPage()),
                      );
                    });
                  },
                  child: const Text('Sign Up'),
                ),

                const SizedBox(height: 20),

                // Image
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 20),
                  child: Image.asset('assets/home/hello.png', height: 190),
                ),

                const SizedBox(height: 20),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // TEXTFIELD
  Widget buildTextField({
    required TextEditingController controller,
    required IconData icon,
    required String hint,
    bool obscure = false,
    bool isPassword = false,
    VoidCallback? toggle,
  }) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(25),
      ),
      child: TextField(
        controller: controller,
        obscureText: obscure,
        decoration: InputDecoration(
          prefixIcon: Icon(icon, color: Colors.orange),
          hintText: hint,
          border: InputBorder.none,
          contentPadding: const EdgeInsets.symmetric(vertical: 15),
          suffixIcon:
              isPassword
                  ? IconButton(
                    icon: Icon(
                      obscure ? Icons.visibility_off : Icons.visibility,
                    ),
                    onPressed: toggle,
                  )
                  : null,
        ),
      ),
    );
  }
}
