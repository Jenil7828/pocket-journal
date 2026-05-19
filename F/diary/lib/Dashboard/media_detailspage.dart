import 'package:flutter/material.dart';

class RecommendationDetailsPage extends StatelessWidget {
  final Map<String, dynamic> data;

  const RecommendationDetailsPage({super.key, required this.data});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF7F7F7),

      appBar: AppBar(
        title: Text(data['title']),
        elevation: 0,
        backgroundColor: Colors.white,
        foregroundColor: Colors.black,
      ),

      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            /// IMAGE CARD
            ClipRRect(
              borderRadius: BorderRadius.circular(16),
              child: Image.network(
                data['image_url'],
                height: 260,
                width: double.infinity,
                fit: BoxFit.cover,
              ),
            ),

            const SizedBox(height: 16),

            /// TITLE + META
            Text(
              data['title'],
              style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
            ),

            const SizedBox(height: 10),

            Row(
              children: [
                _chip("⭐ ${data['rating']}"),
                const SizedBox(width: 8),
                _chip("${data['duration']} sec"),
              ],
            ),

            const SizedBox(height: 20),

            /// CREATOR CARD
            _infoCard(title: "Creator", content: data['creator']),

            /// CONTRIBUTORS CARD
            _infoCard(
              title: "Contributors",
              content: (data['contributors'] as List).join(", "),
            ),

            /// GENRES CARD
            _infoCard(
              title: "Genres",
              content: (data['genres'] as List).join(", "),
            ),

            /// DESCRIPTION CARD
            _infoCard(title: "Description", content: data['description']),

            /// EXTRA DETAILS ROW
            Row(
              children: [
                Expanded(
                  child: _infoCard(
                    title: "Popularity",
                    content: data['popularity'].toString(),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: _infoCard(
                    title: "Language",
                    content: data['language'] ?? "N/A",
                  ),
                ),
              ],
            ),

            const SizedBox(height: 10),

            /// LINK CARD
            _infoCard(
              title: "External Link",
              content: data['external_url'],
              isLink: true,
            ),
          ],
        ),
      ),
    );
  }

  /// 🔹 REUSABLE CARD
  Widget _infoCard({
    required String title,
    required String content,
    bool isLink = false,
  }) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        boxShadow: [
          BoxShadow(
            color: Colors.grey.shade200,
            blurRadius: 8,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              fontWeight: FontWeight.bold,
              color: Colors.grey,
              fontSize: 13,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            content,
            style: TextStyle(
              fontSize: 15,
              color: isLink ? Colors.blue : Colors.black87,
              decoration:
                  isLink ? TextDecoration.underline : TextDecoration.none,
            ),
          ),
        ],
      ),
    );
  }

  /// 🔹 SMALL CHIP
  Widget _chip(String text) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.black,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        text,
        style: const TextStyle(color: Colors.white, fontSize: 12),
      ),
    );
  }
}
