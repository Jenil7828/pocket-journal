import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:diary/DesignConstraints/appBar.dart';

class WeaknessPage extends StatefulWidget {
  const WeaknessPage({super.key});

  @override
  State<WeaknessPage> createState() => _WeaknessPageState();
}

class _WeaknessPageState extends State<WeaknessPage> {
  final _weaknessController = TextEditingController();
  bool _isSaving = false;

  Future<void> _saveWeakness() async {
    setState(() => _isSaving = true);
    final uid = FirebaseAuth.instance.currentUser!.uid;

    await FirebaseFirestore.instance.collection('user_weaknesses').doc(uid).set({
      'weakness': _weaknessController.text.trim(),
      'updatedAt': FieldValue.serverTimestamp(),
    });

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text("⚡ Weakness saved successfully!")),
    );

    setState(() => _isSaving = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: const CustomAppBar(title: "Your Weaknesses", showBack: true),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            TextField(
              controller: _weaknessController,
              maxLines: 4,
              decoration: InputDecoration(
                hintText: "Mention areas where you want to improve...",
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
              ),
            ),
            const SizedBox(height: 20),
            _isSaving
                ? const CircularProgressIndicator()
                : ElevatedButton.icon(
                    onPressed: _saveWeakness,
                    icon: const Icon(Icons.save),
                    label: const Text("Save Weaknesses"),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFFFF7043),
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
