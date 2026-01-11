import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:shared_preferences/shared_preferences.dart';

class GoalPage extends StatefulWidget {
  const GoalPage({super.key});

  @override
  State<GoalPage> createState() => _GoalPageState();
}

class _GoalPageState extends State<GoalPage>
    with SingleTickerProviderStateMixin {
  final _goalController = TextEditingController();
  bool _isSaving = false;
  String? uid;
  late AnimationController _animController;

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    );

    // ✅ FIX #1: Wait until first frame before calling SharedPreferences
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadUserUID());
  }

  // ✅ FIX #2: Safer SharedPreferences call
  Future<void> _loadUserUID() async {
    try {
      await Future.delayed(
        const Duration(milliseconds: 100),
      ); // small safety delay
      final prefs = await SharedPreferences.getInstance();
      final storedUid = prefs.getString('uid');

      if (storedUid != null) {
        uid = storedUid;
      } else {
        uid = FirebaseAuth.instance.currentUser?.uid;
      }

      setState(() {});
    } catch (e) {
      debugPrint("⚠️ Error loading UID: $e");
    }
  }

  Future<void> _saveGoal() async {
    if (_goalController.text.trim().isEmpty || uid == null) return;
    setState(() => _isSaving = true);

    await FirebaseFirestore.instance
        .collection('record')
        .doc(uid)
        .collection('goals')
        .add({
          'goal': _goalController.text.trim(),
          'createdAt': FieldValue.serverTimestamp(),
        });

    _goalController.clear();
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(const SnackBar(content: Text("✅ Goal added successfully!")));

    setState(() => _isSaving = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF3E5F5),
      appBar: AppBar(
        backgroundColor: const Color(0xFF7B1FA2),
        title: const Text(
          "Your Goals",
          style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white),
        ),
      ),
      body:
          uid == null
              ? const Center(child: CircularProgressIndicator())
              : Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                  children: [
                    _buildInputCard(),
                    const SizedBox(height: 20),
                    Expanded(child: _buildGoalList()),
                  ],
                ),
              ),
    );
  }

  Widget _buildInputCard() {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 500),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [Colors.white.withOpacity(0.9), Colors.purple[50]!],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(25),
        boxShadow: [
          BoxShadow(
            color: Colors.purple.withOpacity(0.2),
            blurRadius: 12,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Column(
        children: [
          TextField(
            controller: _goalController,
            maxLines: 3,
            decoration: InputDecoration(
              hintText: "Write your next goal...",
              hintStyle: GoogleFonts.poppins(color: Colors.grey[600]),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(16),
                borderSide: BorderSide(color: Colors.purple.shade300),
              ),
            ),
          ),
          const SizedBox(height: 15),
          _isSaving
              ? const CircularProgressIndicator()
              : ElevatedButton.icon(
                onPressed: _saveGoal,
                icon: const Icon(Icons.add, color: Colors.white),
                label: const Text(
                  "Add Goal",
                  style: TextStyle(color: Colors.white),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF7B1FA2),
                  minimumSize: const Size(double.infinity, 50),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(20),
                  ),
                ),
              ),
        ],
      ),
    );
  }

  Widget _buildGoalList() {
    return StreamBuilder<QuerySnapshot>(
      stream:
          FirebaseFirestore.instance
              .collection('record')
              .doc(uid)
              .collection('goals')
              .orderBy('createdAt', descending: true)
              .snapshots(),
      builder: (context, snapshot) {
        if (!snapshot.hasData) {
          return const Center(child: CircularProgressIndicator());
        }

        final goals = snapshot.data!.docs;
        if (goals.isEmpty) {
          return const Center(
            child: Text(
              "No goals yet 🌱\nStart adding some!",
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 18, color: Colors.grey),
            ),
          );
        }

        return ListView.builder(
          itemCount: goals.length,
          itemBuilder: (context, index) {
            final goal = goals[index]['goal'];
            return TweenAnimationBuilder<double>(
              tween: Tween(begin: 0, end: 1),
              duration: Duration(milliseconds: 500 + (index * 100)),
              builder: (context, value, child) {
                return Opacity(
                  opacity: value,
                  child: Transform.translate(
                    offset: Offset(0, 50 * (1 - value)),
                    child: child,
                  ),
                );
              },
              child: HoverGoalCard(goalText: goal),
            );
          },
        );
      },
    );
  }

  @override
  void dispose() {
    _goalController.dispose();
    _animController.dispose();
    super.dispose();
  }
}

class HoverGoalCard extends StatefulWidget {
  final String goalText;
  const HoverGoalCard({super.key, required this.goalText});

  @override
  State<HoverGoalCard> createState() => _HoverGoalCardState();
}

class _HoverGoalCardState extends State<HoverGoalCard> {
  bool _isHovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 250),
        margin: const EdgeInsets.symmetric(vertical: 10),
        transform:
            Matrix4.identity()
              ..translate(0.0, _isHovered ? -5.0 : 0.0)
              ..scale(_isHovered ? 1.03 : 1.0),
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              Colors.purple.shade400.withOpacity(0.9),
              Colors.purple.shade200.withOpacity(0.8),
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: BorderRadius.circular(20),
          boxShadow: [
            BoxShadow(
              color: Colors.purple.withOpacity(0.3),
              blurRadius: _isHovered ? 12 : 6,
              offset: const Offset(0, 5),
            ),
          ],
        ),
        child: Row(
          children: [
            const Icon(Icons.star, color: Colors.white),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                widget.goalText,
                style: GoogleFonts.poppins(
                  color: Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
