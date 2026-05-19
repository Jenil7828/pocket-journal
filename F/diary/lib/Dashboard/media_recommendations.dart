import 'package:diary/Dashboard/media_detailspage.dart';
import 'package:flutter/material.dart';

class RecommendationPage extends StatefulWidget {
  const RecommendationPage({super.key});

  @override
  State<RecommendationPage> createState() => _RecommendationPageState();
}

class _RecommendationPageState extends State<RecommendationPage> {
  final Color primaryColor = const Color(0xFFCEC0BB);
  final Color accentColor = const Color(0xFF1E2D4C);

  int selectedTab = 0;

  final List<String> tabs = ["Movies", "Songs", "Books", "Podcasts"];

  String getActionText() {
    switch (selectedTab) {
      case 0:
        return "Watch";
      case 1:
        return "Listen";
      case 2:
        return "Read";
      case 3:
        return "Listen";
      default:
        return "Explore";
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,

      body: SafeArea(
        child: Column(
          children: [
            const SizedBox(height: 10),

            /// HEADER
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(
                children: [
                  const Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          "Media Recommendations",
                          style: TextStyle(
                            fontSize: 22,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        SizedBox(height: 4),
                        Text(
                          "Curated for your mood",
                          style: TextStyle(color: Colors.grey),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 20),

            /// TABS
            SizedBox(
              height: 45,
              child: ListView.builder(
                scrollDirection: Axis.horizontal,
                itemCount: tabs.length,
                padding: const EdgeInsets.symmetric(horizontal: 12),
                itemBuilder: (context, index) {
                  bool isSelected = selectedTab == index;

                  return GestureDetector(
                    onTap: () {
                      setState(() {
                        selectedTab = index;
                      });
                    },
                    child: Container(
                      margin: const EdgeInsets.symmetric(horizontal: 6),
                      padding: const EdgeInsets.symmetric(horizontal: 18),
                      decoration: BoxDecoration(
                        color:
                            isSelected
                                ? accentColor
                                : primaryColor.withOpacity(0.4),
                        borderRadius: BorderRadius.circular(14),
                      ),
                      alignment: Alignment.center,
                      child: Text(
                        tabs[index],
                        style: TextStyle(
                          color: isSelected ? Colors.white : accentColor,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  );
                },
              ),
            ),

            const SizedBox(height: 20),

            /// SEARCH
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: TextField(
                decoration: InputDecoration(
                  hintText: "Search...",
                  prefixIcon: Icon(Icons.search, color: accentColor),
                  filled: true,
                  fillColor: primaryColor.withOpacity(0.2),
                  contentPadding: const EdgeInsets.symmetric(vertical: 0),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(16),
                    borderSide: BorderSide.none,
                  ),
                ),
              ),
            ),

            const SizedBox(height: 20),

            /// GRID
            Expanded(
              child: GridView.builder(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 2,
                  childAspectRatio: 0.52,
                ),
                itemCount: 6,
                itemBuilder: (context, index) {
                  return RecommendationCard(
                    primaryColor: primaryColor,
                    accentColor: accentColor,
                    actionText: getActionText(),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class RecommendationCard extends StatefulWidget {
  final Color primaryColor;
  final Color accentColor;
  final String actionText;

  const RecommendationCard({
    super.key,
    required this.primaryColor,
    required this.accentColor,
    required this.actionText,
  });

  @override
  State<RecommendationCard> createState() => _RecommendationCardState();
}

class _RecommendationCardState extends State<RecommendationCard> {
  bool isHovered = false;
  bool isWishlisted = false;

  final Map<String, dynamic> sampleData = {
    "title": "The Foghorn Leghorn",
    "creator": "Robert McKimson",
    "contributors": ["Mel Blanc"],
    "description":
        "Little Henery the Chicken Hawk wants to prove he's big enough to hunt chickens...",
    "duration": 420,
    "genres": ["Animation", "Comedy"],
    "popularity": 0.5326,
    "rating": 6.9,
    "external_url": "https://www.themoviedb.org/movie/100364",
    "image_url":
        "https://image.tmdb.org/t/p/w500/tOLph1YIulhLxpPblq6jdatAJyU.jpg",
  };

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => isHovered = true),
      onExit: (_) => setState(() => isHovered = false),
      child: GestureDetector(
        onTap: () {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (_) => RecommendationDetailsPage(data: sampleData),
            ),
          );
        },
        child: Container(
          margin: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(18),
            color: Colors.white,
            boxShadow: [
              BoxShadow(
                blurRadius: 10,
                color: Colors.grey.shade300,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: Column(
            children: [
              /// IMAGE
              Stack(
                children: [
                  ClipRRect(
                    borderRadius: const BorderRadius.vertical(
                      top: Radius.circular(18),
                    ),
                    child: AspectRatio(
                      aspectRatio: 3 / 3.2,
                      child: Image.network(
                        sampleData['image_url'],
                        fit: BoxFit.cover,
                      ),
                    ),
                  ),

                  /// ❤️ WISHLIST
                  Positioned(
                    top: 10,
                    left: 10,
                    child: GestureDetector(
                      onTap: () {
                        setState(() {
                          isWishlisted = !isWishlisted;
                        });
                      },
                      child: CircleAvatar(
                        radius: 14,
                        backgroundColor: Colors.white,
                        child: Icon(
                          isWishlisted ? Icons.favorite : Icons.favorite_border,
                          color: Colors.red,
                          size: 18,
                        ),
                      ),
                    ),
                  ),

                  /// HOVER
                  if (isHovered)
                    Positioned.fill(
                      child: Container(
                        decoration: BoxDecoration(
                          color: Colors.black.withOpacity(0.4),
                          borderRadius: const BorderRadius.vertical(
                            top: Radius.circular(18),
                          ),
                        ),
                        child: Center(
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                            children: [
                              _actionButton("Skip", Icons.close),
                              _actionButton("Save", Icons.favorite_border),
                            ],
                          ),
                        ),
                      ),
                    ),
                ],
              ),

              /// CONTENT
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.all(10),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            sampleData['title'],
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 16,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            "${sampleData['genres'].join(', ')}",
                            style: TextStyle(color: Colors.grey.shade600),
                          ),
                        ],
                      ),

                      /// BUTTON
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.symmetric(vertical: 10),
                        decoration: BoxDecoration(
                          color: widget.accentColor,
                          borderRadius: BorderRadius.circular(10),
                        ),
                        alignment: Alignment.center,
                        child: Text(
                          widget.actionText,
                          style: const TextStyle(color: Colors.white),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _actionButton(String text, IconData icon) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        children: [Icon(icon, size: 18), const SizedBox(width: 6), Text(text)],
      ),
    );
  }
}
