import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:diary/DesignConstraints/appBar.dart';

class StrengthPage extends StatefulWidget {
  const StrengthPage({super.key});

  @override
  State<StrengthPage> createState() => _StrengthPageState();
}

class _StrengthPageState extends State<StrengthPage> {
  final _strengthController = TextEditingController();
  bool _isSaving = false;

  Future<void> _saveStrength() async {
    setState(() => _isSaving = true);
    final uid = FirebaseAuth.instance.currentUser!.uid;

    await FirebaseFirestore.instance.collection('user_strengths').doc(uid).set({
      'strength': _strengthController.text.trim(),
      'updatedAt': FieldValue.serverTimestamp(),
    });

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text("💪 Strength saved successfully!")),
    );

    setState(() => _isSaving = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: const CustomAppBar(title: "Your Strengths", showBack: true),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            TextField(
              controller: _strengthController,
              maxLines: 4,
              decoration: InputDecoration(
                hintText: "List your top qualities or strengths...",
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
              ),
            ),
            const SizedBox(height: 20),
            _isSaving
                ? const CircularProgressIndicator()
                : ElevatedButton.icon(
                    onPressed: _saveStrength,
                    icon: const Icon(Icons.save),
                    label: const Text("Save Strengths"),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF26A69A),
                      minimumSize: const Size(double.infinity, 50),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(30),
                      ),
                    ),
                  ),
          ],
        ),
      ),
    );
  }
}
