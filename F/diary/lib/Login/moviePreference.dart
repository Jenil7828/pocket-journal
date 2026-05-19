import 'package:diary/DesignConstraints/navbar.dart';
import 'package:diary/Login/langSelect.dart';
import 'package:diary/Login/login.dart';
import 'package:flutter/material.dart';

class PreferencesPage extends StatefulWidget {
  const PreferencesPage({super.key});

  @override
  State<PreferencesPage> createState() => _PreferencesPageState();
}

class _PreferencesPageState extends State<PreferencesPage> {
  final Color navyBlue = const Color(0xFF1E2D4C);

  /// 🔥 steps flow
  final List<String> steps = ["movies", "songs", "books", "podcasts"];

  int currentStep = 0;

  Map<String, List<String>> selectedData = {};
  Set<String> selectedGenres = {};

  late Map<String, dynamic> config;

  @override
  void initState() {
    super.initState();
    loadStep();
  }

  /// 🔥 load current step config
  void loadStep() {
    String currentType = steps[currentStep];
    config = getConfig(currentType);

    selectedGenres = selectedData[currentType]?.toSet() ?? {};
  }

  /// 🔥 CONFIG (same)
  Map<String, dynamic> getConfig(String type) {
    switch (type) {
      case "songs":
        return {
          "title": "Song Preferences",
          "subtitle": "Choose music genres that resonate with you.",
          "icon": Icons.music_note,
          "genres": [
            {"name": "Pop", "emoji": "🎤"},
            {"name": "Rock", "emoji": "🎸"},
            {"name": "Bollywood", "emoji": "🎬"},
            {"name": "Romantic", "emoji": "💕"},
            {"name": "Instrumental", "emoji": "🎹"},
            {"name": "Classical", "emoji": "🎻"},
            {"name": "Jazz", "emoji": "🎷"},
            {"name": "EDM", "emoji": "🎧"},
            {"name": "Indie", "emoji": "🌿"},
            {"name": "Hip-Hop", "emoji": "🎵"},
            {"name": "Ambient", "emoji": "🌌"},
            {"name": "Folk", "emoji": "🪕"},
          ],
        };

      case "books":
        return {
          "title": "Book Preferences",
          "subtitle": "Select genres you love.",
          "icon": Icons.menu_book,
          "genres": [
            {"name": "Fiction", "emoji": "📖"},
            {"name": "Self-Help", "emoji": "🌟"},
            {"name": "Motivational", "emoji": "💪"},
            {"name": "Biography", "emoji": "👤"},
            {"name": "Philosophy", "emoji": "🧠"},
            {"name": "Psychology", "emoji": "🔬"},
            {"name": "Business", "emoji": "💼"},
            {"name": "Science", "emoji": "🔭"},
            {"name": "History", "emoji": "🏛️"},
            {"name": "Spirituality", "emoji": "🕉️"},
            {"name": "Poetry", "emoji": "✍️"},
            {"name": "Creativity", "emoji": "🎨"},
          ],
        };

      case "podcasts":
        return {
          "title": "Podcast Preferences",
          "subtitle": "Choose topics you enjoy.",
          "icon": Icons.mic,
          "genres": [
            {"name": "Wellness", "emoji": "🌸"},
            {"name": "Mindfulness", "emoji": "🧘"},
            {"name": "Personal Growth", "emoji": "🌱"},
            {"name": "Mental Health", "emoji": "💚"},
            {"name": "Motivation", "emoji": "🔥"},
            {"name": "Science", "emoji": "🔬"},
            {"name": "True Crime", "emoji": "🔎"},
            {"name": "Comedy", "emoji": "😂"},
            {"name": "Business", "emoji": "💼"},
            {"name": "Technology", "emoji": "💻"},
            {"name": "Storytelling", "emoji": "📚"},
            {"name": "Interviews", "emoji": "🎙️"},
          ],
        };

      default:
        return {
          "title": "Movie Preferences",
          "subtitle":
              "Select movie genres you enjoy. We'll use this to recommend content.",
          "icon": Icons.movie,
          "genres": [
            {"name": "Action", "emoji": "💥"},
            {"name": "Comedy", "emoji": "😂"},
            {"name": "Drama", "emoji": "🎭"},
            {"name": "Sci-Fi", "emoji": "🚀"},
            {"name": "Horror", "emoji": "😱"},
            {"name": "Romance", "emoji": "💕"},
            {"name": "Thriller", "emoji": "🔪"},
            {"name": "Fantasy", "emoji": "🧙"},
            {"name": "Documentary", "emoji": "📹"},
            {"name": "Animation", "emoji": "🎨"},
            {"name": "Adventure", "emoji": "🗺️"},
            {"name": "Mystery", "emoji": "🔍"},
          ],
        };
    }
  }

  /// 🔥 NEXT STEP
  void goToNext() {
    String currentType = steps[currentStep];

    selectedData[currentType] = selectedGenres.toList();

    if (currentStep < steps.length - 1) {
      setState(() {
        currentStep++;
        loadStep();
      });
    } else {
      /// ✅ ONLY CHANGE HERE (pass data)
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (_) => LangSelect(preferencesData: selectedData),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final List genres = config["genres"];

    return Scaffold(
      backgroundColor: const Color(0xFFF4F6FA),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 20),

              /// 🔥 PROGRESS BAR
              Row(
                children: List.generate(
                  steps.length,
                  (index) => Expanded(
                    child: Container(
                      margin: const EdgeInsets.symmetric(horizontal: 4),
                      height: 6,
                      decoration: BoxDecoration(
                        color:
                            index <= currentStep
                                ? navyBlue
                                : Colors.grey.shade300,
                        borderRadius: BorderRadius.circular(10),
                      ),
                    ),
                  ),
                ),
              ),

              const SizedBox(height: 25),

              /// ICON
              Container(
                height: 70,
                width: 70,
                decoration: BoxDecoration(
                  color: const Color(0xFFE8EAF3),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Icon(config["icon"], size: 35),
              ),

              const SizedBox(height: 20),

              Text(
                config["title"],
                style: const TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                ),
              ),

              const SizedBox(height: 8),

              Text(
                config["subtitle"],
                style: const TextStyle(color: Colors.grey),
              ),

              const SizedBox(height: 20),

              /// GRID
              Expanded(
                child: GridView.builder(
                  itemCount: genres.length,
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 2,
                    mainAxisSpacing: 14,
                    crossAxisSpacing: 14,
                    childAspectRatio: 1.8,
                  ),
                  itemBuilder: (context, index) {
                    final genre = genres[index];
                    final isSelected = selectedGenres.contains(genre['name']);

                    return GestureDetector(
                      onTap: () {
                        setState(() {
                          if (isSelected) {
                            selectedGenres.remove(genre['name']);
                          } else {
                            selectedGenres.add(genre['name']);
                          }
                        });
                      },
                      child: Container(
                        decoration: BoxDecoration(
                          color:
                              isSelected
                                  ? navyBlue.withOpacity(0.1)
                                  : Colors.white,
                          borderRadius: BorderRadius.circular(18),
                          border: Border.all(
                            color: isSelected ? navyBlue : Colors.grey.shade300,
                          ),
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(
                              genre['emoji'],
                              style: const TextStyle(fontSize: 22),
                            ),
                            const SizedBox(width: 10),
                            Text(
                              genre['name'],
                              style: TextStyle(
                                fontWeight: FontWeight.w600,
                                color: isSelected ? navyBlue : Colors.black,
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ),

              const SizedBox(height: 10),

              /// CONTINUE
              ElevatedButton(
                onPressed: selectedGenres.isEmpty ? null : goToNext,
                style: ElevatedButton.styleFrom(
                  backgroundColor: navyBlue,
                  minimumSize: const Size(double.infinity, 55),
                ),
                child: const Text(
                  "Continue",
                  style: TextStyle(color: Colors.black),
                ),
              ),

              const SizedBox(height: 10),

              /// SKIP
              OutlinedButton(
                onPressed: goToNext,
                style: OutlinedButton.styleFrom(
                  minimumSize: const Size(double.infinity, 55),
                ),
                child: const Text(
                  "Skip for now",
                  style: TextStyle(color: Colors.black),
                ),
              ),

              const SizedBox(height: 20),
            ],
          ),
        ),
      ),
    );
  }
}