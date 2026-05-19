import 'dart:io';
import 'dart:convert';
import 'package:diary/DesignConstraints/api.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:diary/DesignConstraints/navbar.dart';
import 'package:diary/DesignConstraints/snackbar.dart';
import 'package:diary/Profile/accountsettings.dart';
import 'package:diary/Profile/profildetails.dart';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

class ProfilePage extends StatefulWidget {
  const ProfilePage({super.key});

  @override
  State<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends State<ProfilePage> {
  // 🌿 COLORS
  Color primaryColor = const Color(0xFFCEC0BB);
  final Color accentColor = const Color(0xFF1E2D4C);
  final Color bgColor = const Color(0xFFACBDAA);

  final Color textGrey = const Color(0xFF858585);

  bool moodTracking = false;
  bool journalReminder = false;

  bool savedMoodTracking = false;
  bool savedJournalReminder = false;

  bool isEditing = true;

  File? _image;
  final ImagePicker _picker = ImagePicker();

  // ✅ PICK IMAGE
  Future<void> _pickImage() async {
    final picked = await _picker.pickImage(source: ImageSource.gallery);
    if (picked != null) {
      setState(() => _image = File(picked.path));
    }
  }

  // ✅ SAVE PREFERENCES (API INTEGRATED)
  Future<void> _savePreferences() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      String? token = prefs.getString("token");

      if (token == null) {
        AppSnackbar.show(context, "User not logged in");
        return;
      }

      final response = await http.put(
        Uri.parse("${ApiConfig.baseUrl}/me/settings"),
        headers: {
          "Content-Type": "application/json",
          "Authorization": "Bearer $token",
        },
        body: jsonEncode({
          "mood_tracking_enabled": moodTracking,
          "daily_journal_reminders": journalReminder,
        }),
      );

      print("SETTINGS RESPONSE: ${response.body}");

      if (response.statusCode == 200) {
        setState(() {
          savedMoodTracking = moodTracking;
          savedJournalReminder = journalReminder;
          isEditing = false;
        });

        await prefs.setBool("hasPreferences", true);

        AppSnackbar.show(context, "Preferences Saved Successfully");
      } else {
        final error = jsonDecode(response.body);
        AppSnackbar.show(context, error["message"] ?? "Failed to save");
      }
    } catch (e) {
      print("ERROR: $e");
      AppSnackbar.show(context, "Something went wrong");
    }
  }

  // ✅ EDIT MODE
  void _editPreferences() {
    setState(() {
      moodTracking = savedMoodTracking;
      journalReminder = savedJournalReminder;
      isEditing = true;
    });
  }

  @override
  Widget build(BuildContext context) {
    final displayMood = isEditing ? moodTracking : savedMoodTracking;
    final displayJournal = isEditing ? journalReminder : savedJournalReminder;

    return Container(
      color: Colors.white,
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
                        colors: [accentColor, accentColor.withOpacity(0.8)],
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
                                color: accentColor.withOpacity(0.3),
                                blurRadius: 15,
                              ),
                            ],
                          ),
                          child: CircleAvatar(
                            radius: 50,
                            backgroundColor: primaryColor,
                            backgroundImage:
                                _image != null ? FileImage(_image!) : null,
                            child:
                                _image == null
                                    ? Icon(Icons.camera_alt, color: accentColor)
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
                      children: [
                        Icon(Icons.email, size: 16, color: textGrey),
                        const SizedBox(width: 6),
                        Text(
                          "stefani.wong@example.com",
                          style: TextStyle(color: textGrey),
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
                          color: primaryColor.withOpacity(0.2),
                          borderRadius: BorderRadius.circular(30),
                          border: Border.all(color: accentColor),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              "View Full Profile",
                              style: TextStyle(
                                color: accentColor,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            const SizedBox(width: 6),
                            Icon(
                              Icons.arrow_forward,
                              size: 16,
                              color: accentColor,
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 20),

              /// 🌿 PREFERENCES CARD
              _buildCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      "PREFERENCES",
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        color: textGrey,
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

                    Row(
                      children: [
                        Expanded(
                          child: ElevatedButton(
                            onPressed: isEditing ? _savePreferences : null,
                            style: ElevatedButton.styleFrom(
                              backgroundColor: accentColor,
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
                              foregroundColor: accentColor,
                              side: BorderSide(color: accentColor),
                            ),
                            child: const Text("Edit"),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 20),

              /// 🌿 ACCOUNT & SETTINGS + LOGOUT
              _buildAccountSettingsCard(),

              const SizedBox(height: 30),
            ],
          ),
        ),
      ),
    );
  }

  /// ✅ ACCOUNT SETTINGS CARD
  Widget _buildAccountSettingsCard() {
    return Column(
      children: [
        _buildCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                "ACCOUNT & SETTINGS",
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: textGrey,
                  letterSpacing: 1,
                ),
              ),
              const SizedBox(height: 20),

              _settingsTile(
                Icons.lock_outline,
                "Account Settings",
                onTap: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => const AccountSettingsPage(),
                    ),
                  );
                },
              ),

              _settingsTile(Icons.shield_outlined, "Privacy Policy"),
              _settingsTile(Icons.description_outlined, "Terms & Conditions"),
              _settingsTile(Icons.info_outline, "About Pocket Journal"),
            ],
          ),
        ),

        const SizedBox(height: 16),

        Container(
          margin: const EdgeInsets.symmetric(horizontal: 20),
          width: double.infinity,
          child: ElevatedButton(
            onPressed: () {},
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.white,
              elevation: 2,
              padding: const EdgeInsets.symmetric(vertical: 14),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16),
              ),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: const [
                Icon(Icons.logout, color: Colors.red),
                SizedBox(width: 8),
                Text(
                  "Logout",
                  style: TextStyle(
                    color: Colors.red,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _settingsTile(IconData icon, String title, {VoidCallback? onTap}) {
    return Column(
      children: [
        ListTile(
          contentPadding: EdgeInsets.zero,
          leading: Icon(icon, color: accentColor),
          title: Text(title),
          trailing: const Icon(Icons.arrow_forward_ios, size: 16),
          onTap: onTap,
        ),
        const Divider(),
      ],
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
              Text(subtitle, style: TextStyle(color: textGrey)),
            ],
          ),
        ),
        Switch(
          value: value,
          onChanged: (val) {
            if (enabled) onChanged(val);
          },
          activeColor: accentColor,
          inactiveTrackColor: accentColor.withOpacity(0.3),
          inactiveThumbColor: accentColor,
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
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: accentColor.withOpacity(0.2), width: 1.2),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: child,
    );
  }
}
