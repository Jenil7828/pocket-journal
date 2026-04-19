import 'dart:io';
import 'package:diary/DesignConstraints/navbar.dart';
import 'package:diary/Profile/profildetails.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

class ProfilePage extends StatefulWidget {
  const ProfilePage({super.key});

  @override
  State<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends State<ProfilePage> {
  // 🌿 NEW THEME COLORS
  final Color primaryColor = const Color(0xFF266533); // Basil
  final Color bgColor = const Color(0xFFF6F4DC); // Cream
  final Color cardColor = Colors.white;

  bool moodTracking = false;
  bool journalReminder = false;
  List<String> selectedMedia = [];

  bool savedMoodTracking = false;
  bool savedJournalReminder = false;
  List<String> savedMedia = [];

  bool isEditing = true;

  File? _image;
  final ImagePicker _picker = ImagePicker();

  Future<void> _pickImage() async {
    final picked = await _picker.pickImage(source: ImageSource.gallery);
    if (picked != null) {
      setState(() => _image = File(picked.path));
    }
  }

  void _savePreferences() {
    setState(() {
      savedMoodTracking = moodTracking;
      savedJournalReminder = journalReminder;
      savedMedia = List.from(selectedMedia);
      isEditing = false;
    });
  }

  void _editPreferences() {
    setState(() {
      moodTracking = savedMoodTracking;
      journalReminder = savedJournalReminder;
      selectedMedia = List.from(savedMedia);
      isEditing = true;
    });
  }

  @override
  Widget build(BuildContext context) {
    final displayMood = isEditing ? moodTracking : savedMoodTracking;
    final displayJournal = isEditing ? journalReminder : savedJournalReminder;
    final displayMedia = isEditing ? selectedMedia : savedMedia;

    return Container(
      color: bgColor,
      child: SafeArea(
        child: SingleChildScrollView(
          child: Column(
            children: [
              /// 🌿 HEADER
              Stack(
                clipBehavior: Clip.none,
                children: [
                  Container(
                    height: 150,
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: [primaryColor, primaryColor.withOpacity(0.85)],
                      ),
                      borderRadius: const BorderRadius.only(
                        bottomLeft: Radius.circular(60),
                        bottomRight: Radius.circular(60),
                      ),
                    ),
                  ),

                  Positioned(
                    top: 20,
                    left: 16,
                    right: 16,
                    child: Stack(
                      alignment: Alignment.center,
                      children: [
                        Row(
                          children: [
                            _iconButton(
                              Icons.arrow_back,
                              onTap: () {
                                CustomBottomNavBar.of(context)?.changeTab(0);
                              },
                            ),
                          ],
                        ),
                        const Text(
                          "Profile",
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 20,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                  ),

                  Positioned(
                    bottom: -50,
                    left: 0,
                    right: 0,
                    child: Center(
                      child: GestureDetector(
                        onTap: _pickImage,
                        child: Container(
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            border: Border.all(color: Colors.white, width: 4),
                            boxShadow: [
                              BoxShadow(
                                color: primaryColor.withOpacity(0.3),
                                blurRadius: 15,
                              ),
                            ],
                          ),
                          child: CircleAvatar(
                            radius: 50,
                            backgroundImage:
                                _image != null ? FileImage(_image!) : null,
                            child:
                                _image == null
                                    ? Icon(
                                      Icons.camera_alt,
                                      color: primaryColor,
                                    )
                                    : null,
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),

              const SizedBox(height: 70),

              /// 🌿 PROFILE CARD
              _buildCard(
                child: Column(
                  children: [
                    const Text(
                      "Stefani Wong",
                      style: TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 8),

                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: const [
                        Icon(Icons.email, size: 16, color: Colors.grey),
                        SizedBox(width: 6),
                        Text(
                          "stefani.wong@example.com",
                          style: TextStyle(color: Colors.grey),
                        ),
                      ],
                    ),

                    const SizedBox(height: 16),

                    GestureDetector(
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(builder: (_) => FullProfilePage()),
                        );
                      },
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          vertical: 10,
                          horizontal: 20,
                        ),
                        decoration: BoxDecoration(
                          color: primaryColor.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(30),
                          border: Border.all(color: primaryColor),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              "View Full Profile",
                              style: TextStyle(
                                color: primaryColor,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            const SizedBox(width: 6),
                            Icon(
                              Icons.arrow_forward,
                              size: 16,
                              color: primaryColor,
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 20),

              /// 🌿 SETTINGS CARD
              _buildCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      "PREFERENCES",
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        color: Colors.grey,
                      ),
                    ),

                    const SizedBox(height: 20),

                    _buildToggleTile(
                      title: "Mood Tracking",
                      subtitle: "Track your daily emotional state",
                      value: displayMood,
                      enabled: isEditing,
                      onChanged: (val) => setState(() => moodTracking = val),
                    ),

                    const Divider(),

                    _buildToggleTile(
                      title: "Daily Journal Reminders",
                      subtitle: "Get reminded to write each day",
                      value: displayJournal,
                      enabled: isEditing,
                      onChanged: (val) => setState(() => journalReminder = val),
                    ),

                    const SizedBox(height: 20),

                    const Text(
                      "Preferred Media Type",
                      style: TextStyle(fontWeight: FontWeight.bold),
                    ),

                    const SizedBox(height: 16),

                    Row(
                      children: [
                        Expanded(
                          child: _buildMediaButton(
                            "Movies",
                            Icons.movie,
                            displayMedia,
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: _buildMediaButton(
                            "Songs",
                            Icons.music_note,
                            displayMedia,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        Expanded(
                          child: _buildMediaButton(
                            "Books",
                            Icons.menu_book,
                            displayMedia,
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: _buildMediaButton(
                            "Podcasts",
                            Icons.mic,
                            displayMedia,
                          ),
                        ),
                      ],
                    ),

                    const SizedBox(height: 20),

                    Row(
                      children: [
                        Expanded(
                          child: ElevatedButton(
                            onPressed: isEditing ? _savePreferences : null,
                            style: ElevatedButton.styleFrom(
                              backgroundColor: primaryColor,
                              foregroundColor: Colors.white,
                            ),
                            child: const Text("Save"),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: OutlinedButton(
                            onPressed: !isEditing ? _editPreferences : null,
                            style: OutlinedButton.styleFrom(
                              foregroundColor: primaryColor,
                              side: BorderSide(color: primaryColor),
                            ),
                            child: const Text("Edit"),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildMediaButton(
    String title,
    IconData icon,
    List<String> displayMedia,
  ) {
    final isSelected = displayMedia.contains(title);

    return GestureDetector(
      onTap:
          isEditing
              ? () {
                setState(() {
                  if (selectedMedia.contains(title)) {
                    selectedMedia.remove(title);
                  } else {
                    selectedMedia.add(title);
                  }
                });
              }
              : null,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 250),
        padding: const EdgeInsets.symmetric(vertical: 14),
        decoration: BoxDecoration(
          color: isSelected ? primaryColor : const Color(0xFFF1F1F1),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              icon,
              size: 18,
              color: isSelected ? Colors.white : Colors.black54,
            ),
            const SizedBox(width: 6),
            Text(
              title,
              style: TextStyle(
                color: isSelected ? Colors.white : Colors.black54,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildToggleTile({
    required String title,
    required String subtitle,
    required bool value,
    required bool enabled,
    required Function(bool) onChanged,
  }) {
    return Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
              const SizedBox(height: 4),
              Text(subtitle, style: const TextStyle(color: Colors.grey)),
            ],
          ),
        ),
        Switch(
          value: value,
          onChanged: enabled ? onChanged : null,
          activeColor: primaryColor,
        ),
      ],
    );
  }

  Widget _iconButton(IconData icon, {VoidCallback? onTap}) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.3),
          shape: BoxShape.circle,
        ),
        child: Icon(icon, color: Colors.white),
      ),
    );
  }

  Widget _buildCard({required Widget child}) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: cardColor,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 10),
        ],
      ),
      child: child,
    );
  }
}
