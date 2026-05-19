import 'dart:convert';
import 'dart:developer';
import 'package:diary/DesignConstraints/api.dart';
import 'package:diary/DesignConstraints/navbar.dart';
import 'package:diary/DesignConstraints/snackbar.dart';
import 'package:diary/Login/moviePreference.dart';
import 'package:diary/Login/signup.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final TextEditingController emailController = TextEditingController();
  final TextEditingController passwordController = TextEditingController();

  bool obscurePassword = true;
  bool isLoading = false; // ✅ loader

  // ✅ LOGIN API FUNCTION
  Future<void> loginUser() async {
    final email = emailController.text.trim();
    final password = passwordController.text.trim();

    setState(() => isLoading = true);

    try {
      final response = await http.post(
        Uri.parse("${ApiConfig.baseUrl}/auth/login"),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({"email": email, "password": password}),
      );

      log("RESPONSE: ${response.body}");

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);

        String token = data["id_token"];
        String refreshToken = data["refresh_token"];

        // ✅ STORE TOKEN
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString("token", token);
        await prefs.setString("refresh_token", refreshToken);
        bool hasPreferences = prefs.getBool("hasPreferences") ?? false;
        log("TOKEN SAVED");

        AppSnackbar.show(context, "Login Successful");

        Future.delayed(const Duration(milliseconds: 500), () {
          if (hasPreferences) {
            // ✅ OLD USER → Dashboard
            Navigator.pushReplacement(
              context,
              MaterialPageRoute(
                builder: (context) => const CustomBottomNavBar(),
              ),
            );
          } else {
            // ✅ NEW USER → Preferences
            Navigator.pushReplacement(
              context,
              MaterialPageRoute(builder: (context) => const PreferencesPage()),
            );
          }
        });
      } else {
        final error = jsonDecode(response.body);
        AppSnackbar.show(context, error["message"] ?? "Login failed");
      }
    } catch (e) {
      print("ERROR: $e");
      AppSnackbar.show(context, e.toString());
    }

    setState(() => isLoading = false);
  }

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
                // Top Curve
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

                const SizedBox(height: 60),

                const Text(
                  'Login',
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
                    ],
                  ),
                ),

                const SizedBox(height: 10),

                GestureDetector(
                  onTap: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => const SignupPage(),
                      ),
                    );
                  },
                  child: const Text(
                    'Don’t have an account? Sign up',
                    style: TextStyle(color: Colors.white70, fontSize: 12),
                  ),
                ),

                const SizedBox(height: 40),

                // ✅ BUTTON (UPDATED)
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
                  onPressed:
                      isLoading
                          ? null
                          : () {
                            final email = emailController.text.trim();
                            final password = passwordController.text.trim();

                            // VALIDATIONS (same as yours)
                            if (email.isEmpty) {
                              AppSnackbar.show(context, 'Email is required');
                              return;
                            }

                            final emailRegex = RegExp(r'^[^@]+@[^@]+\.[^@]+');
                            if (!emailRegex.hasMatch(email)) {
                              AppSnackbar.show(context, 'Enter a valid email');
                              return;
                            }

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

                            // ✅ CALL API
                            loginUser();
                          },
                  child:
                      isLoading
                          ? const CircularProgressIndicator(color: Colors.white)
                          : const Text('Login'),
                ),

                const SizedBox(height: 20),

                // Image
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 20),
                  child: Image.asset(
                    'assets/home/hello.png',
                    height: 190,
                    fit: BoxFit.contain,
                  ),
                ),

                const SizedBox(height: 20),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // TEXTFIELD (UNCHANGED)
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
