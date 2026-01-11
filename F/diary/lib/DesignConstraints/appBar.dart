import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class CustomAppBar extends StatelessWidget implements PreferredSizeWidget {
  final String title;
  final bool centerTitle;
  final bool showBack;
  final List<Widget>? actions;
  final Color backgroundColor;
  final Color textColor;

  const CustomAppBar({
    super.key,
    required this.title,
    this.centerTitle = true,
    this.showBack = false, // 👈 Toggle for back button
    this.actions,
    this.backgroundColor = Colors.white,
    this.textColor = Colors.black87,
  });

  @override
  Widget build(BuildContext context) {
    return AppBar(
      elevation: 0,
      backgroundColor: backgroundColor,
      automaticallyImplyLeading: false,
      centerTitle: centerTitle,
      leading:
          showBack
              ? IconButton(
                icon: Icon(
                  Icons.arrow_back_ios_new_rounded,
                  color: textColor,
                  size: 20,
                ),
                onPressed: () => Navigator.of(context).maybePop(),
                tooltip: 'Back',
              )
              : null,
      title: Text(
        title,
        style: GoogleFonts.poppins(
          color: textColor,
          fontSize: 20,
          fontWeight: FontWeight.w600,
        ),
      ),
      actions: actions,
    );
  }

  @override
  Size get preferredSize => const Size.fromHeight(56);
}
