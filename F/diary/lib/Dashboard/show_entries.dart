import 'package:diary/Dashboard/entry_analysis.dart';
import 'package:flutter/material.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:google_fonts/google_fonts.dart';
import 'dart:math';

class JournalEntriesListPage extends StatelessWidget {
  const JournalEntriesListPage({super.key});

  @override
  Widget build(BuildContext context) {
    final FirebaseAuth auth = FirebaseAuth.instance;
    final FirebaseFirestore firestore = FirebaseFirestore.instance;
    final user = auth.currentUser;

    if (user == null) {
      return const Scaffold(
        body: Center(child: Text("Please log in to view your journal.")),
      );
    }

    return Scaffold(
      backgroundColor: const Color(0xFFF3E5F5),
      appBar: AppBar(
        title: Text(
          "My Journal Entries",
          style: GoogleFonts.poppins(fontWeight: FontWeight.w600),
        ),
        centerTitle: true,
        backgroundColor: const Color(0xFF9575CD),
      ),
      body: StreamBuilder<QuerySnapshot>(
        stream:
            firestore
                .collection('journal_entries')
                .where('uid', isEqualTo: user.uid)
                .orderBy('created_at', descending: true)
                .snapshots(),
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (!snapshot.hasData || snapshot.data!.docs.isEmpty) {
            return const Center(
              child: Text(
                "No journal entries yet ✍️\nStart writing your thoughts!",
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 16, color: Colors.black54),
              ),
            );
          }

          final entries = snapshot.data!.docs;

          return ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: entries.length,
            itemBuilder: (context, index) {
              final doc = entries[index];
              final data = doc.data() as Map<String, dynamic>;
              final text = data['entry_text'] ?? 'No text';
              final createdAt = data['created_at']?.toDate();
              final dateText =
                  createdAt != null
                      ? "${createdAt.day}/${createdAt.month}/${createdAt.year}"
                      : "Unknown date";

              // Random emoji + background color
              final emojis = [
                "😊",
                "🌿",
                "💭",
                "🌞",
                "🔥",
                "🌈",
                "🦋",
                "🌸",
                "🍀",
                "✨",
              ];
              final colors = [
                Colors.pink.shade100,
                Colors.lightBlue.shade100,
                Colors.orange.shade100,
                Colors.green.shade100,
                Colors.purple.shade100,
                Colors.teal.shade100,
                Colors.yellow.shade100,
                Colors.red.shade100,
              ];
              final random = Random(index);
              final emoji = emojis[random.nextInt(emojis.length)];
              final color = colors[random.nextInt(colors.length)];

              return GestureDetector(
                onTap: () {
                  // ✅ Navigate to EntryAnalysisPage with this entry’s ID
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => EntryAnalysisPage(entryId: doc.id),
                    ),
                  );
                },
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 400),
                  curve: Curves.easeInOut,
                  margin: const EdgeInsets.only(bottom: 16),
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: color,
                    borderRadius: BorderRadius.circular(20),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black12,
                        blurRadius: 8,
                        offset: const Offset(3, 3),
                      ),
                    ],
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        "$emoji  $dateText",
                        style: GoogleFonts.poppins(
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                          color: Colors.brown.shade700,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        text,
                        maxLines: 3,
                        overflow: TextOverflow.ellipsis,
                        style: GoogleFonts.poppins(
                          fontSize: 16,
                          color: Colors.black87,
                        ),
                      ),
                    ],
                  ),
                ),
              );
            },
          );
        },
      ),
    );
  }
}
