import 'package:diary/Profile/chnagepassword.dart';
import 'package:flutter/material.dart';

class AccountSettingsPage extends StatelessWidget {
  const AccountSettingsPage({super.key});

  @override
  Widget build(BuildContext context) {
    final Color accentColor = const Color(0xFF1E2D4C);
    final Color primaryColor = const Color(0xFFCEC0BB);
    final Color textGrey = const Color(0xFF858585);

    return Scaffold(
      backgroundColor: primaryColor,
      body: SafeArea(
        child: SingleChildScrollView(
          child: Column(
            children: [
              /// 🔹 HEADER
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 10,
                ),
                child: Row(
                  children: [
                    GestureDetector(
                      onTap: () => Navigator.pop(context),
                      child: Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(Icons.arrow_back),
                      ),
                    ),
                    const SizedBox(width: 16),
                    const Text(
                      "Account Settings",
                      style: TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 20),

              /// 🔹 ACCOUNT INFO CARD
              _card(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      "ACCOUNT INFORMATION",
                      style: TextStyle(
                        color: textGrey,
                        fontWeight: FontWeight.bold,
                      ),
                    ),

                    const SizedBox(height: 16),

                    _textField("Full Name", "saloni"),
                    const SizedBox(height: 12),
                    _textField("Email Address", "s@gmail.com"),

                    const SizedBox(height: 20),

                    ElevatedButton(
                      onPressed: () {},
                      style: ElevatedButton.styleFrom(
                        backgroundColor: accentColor,
                        minimumSize: const Size(double.infinity, 50),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(16),
                        ),
                      ),
                      child: const Text("Save Changes"),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 20),

              /// 🔹 PASSWORD CARD
              _card(
                child: ListTile(
                  leading: const Icon(Icons.lock_outline),
                  title: const Text("Change Password"),
                  subtitle: const Text("Update your account password"),
                  trailing: const Icon(Icons.arrow_forward_ios, size: 16),
                  onTap: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => const ChangePasswordPage(),
                      ),
                    );
                  },
                ),
              ),

              const SizedBox(height: 30),

              /// 🔹 DATA MANAGEMENT CARD
              _card(
                child: ListTile(
                  leading: const Icon(Icons.download_outlined),
                  title: const Text("Export My Data"),
                  subtitle: const Text("Download all your journal entries"),
                  trailing: const Icon(Icons.arrow_forward_ios, size: 16),
                  onTap: () {
                    _showExportOptions(context);
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _textField(String label, String hint) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label),
        const SizedBox(height: 6),
        TextField(
          decoration: InputDecoration(
            hintText: hint,
            filled: true,
            fillColor: Colors.white,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
              borderSide: BorderSide.none,
            ),
          ),
        ),
      ],
    );
  }

  void _showExportOptions(BuildContext context) {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (context) {
        return Container(
          padding: const EdgeInsets.all(20),
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(25)),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.download, size: 40, color: Colors.blue),
              const SizedBox(height: 10),
              const Text(
                "Export Your Data",
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 6),
              const Text(
                "Choose the format for your journal entries export",
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.grey),
              ),

              const SizedBox(height: 20),

              /// OPTIONS
              _exportOption(
                context: context,
                icon: Icons.description,
                color: Colors.blue,
                title: "Export as DOC",
                subtitle: "Microsoft Word document",
              ),
              _exportOption(
                context: context,
                icon: Icons.table_chart,
                color: Colors.green,
                title: "Export as CSV",
                subtitle: "Comma-separated values file",
              ),
              _exportOption(
                context: context,
                icon: Icons.picture_as_pdf,
                color: Colors.red,
                title: "Export as PDF",
                subtitle: "Portable document format",
              ),

              const SizedBox(height: 20),

              /// CANCEL BUTTON
              GestureDetector(
                onTap: () => Navigator.pop(context),
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  decoration: BoxDecoration(
                    color: const Color(0xFFEDEDED),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: const Center(
                    child: Text(
                      "Cancel",
                      style: TextStyle(fontWeight: FontWeight.w600),
                    ),
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _exportOption({
    required BuildContext context,
    required IconData icon,
    required Color color,
    required String title,
    required String subtitle,
  }) {
    return GestureDetector(
      onTap: () async {
        /// ✅ STORE SAFE CONTEXT
        final scaffoldMessenger = ScaffoldMessenger.of(context);

        /// CLOSE BOTTOM SHEET
        Navigator.pop(context);

        /// SHOW LOADING MESSAGE
        scaffoldMessenger.showSnackBar(
          const SnackBar(
            content: Text("Data is being exported..."),
            duration: Duration(seconds: 2),
          ),
        );

        /// WAIT 2 SEC
        await Future.delayed(const Duration(seconds: 2));

        /// SHOW SUCCESS
        scaffoldMessenger.showSnackBar(
          const SnackBar(content: Text("Export completed ✅")),
        );
      },
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.grey.shade300),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: color.withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon, color: color),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                  Text(
                    subtitle,
                    style: const TextStyle(color: Colors.grey, fontSize: 12),
                  ),
                ],
              ),
            ),
            const Icon(Icons.arrow_forward_ios, size: 16),
          ],
        ),
      ),
    );
  }

  Widget _card({required Widget child}) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 10),
        ],
      ),
      child: child,
    );
  }
}
