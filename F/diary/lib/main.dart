import 'package:diary/Dashboard/dashboard.dart';
import 'package:diary/Dashboard/entry_analysis.dart';
import 'package:diary/DesignConstraints/navbar.dart';
import 'package:diary/Login/Splash.dart';
import 'package:diary/Login/langSelect.dart';
import 'package:diary/Login/login.dart';
import 'package:diary/Login/moviePreference.dart';
import 'package:diary/Login/signup.dart';
import 'package:diary/Profile/profile.dart';
import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'dart:developer';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  try {
    await Firebase.initializeApp();
    log('✅ Firebase initialized successfully!');
  } catch (e, stack) {
    log('❌ Firebase initialization failed: $e', stackTrace: stack);
  }

  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return const MaterialApp(
      debugShowCheckedModeBanner: false,
      home: SignupPage(),
     
    );
  }
}
