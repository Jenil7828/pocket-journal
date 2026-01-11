import 'package:diary/Dashboard/journalEntry.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';

class CalendarPopupCard extends StatefulWidget {
  const CalendarPopupCard({super.key});

  @override
  State<CalendarPopupCard> createState() => _CalendarPopupCardState();
}

class _CalendarPopupCardState extends State<CalendarPopupCard> {
  DateTime currentMonth = DateTime.now();

  void _nextMonth() {
    setState(() {
      currentMonth = DateTime(currentMonth.year, currentMonth.month + 1);
    });
  }

  void _prevMonth() {
    setState(() {
      currentMonth = DateTime(currentMonth.year, currentMonth.month - 1);
    });
  }

  @override
  Widget build(BuildContext context) {
    final daysInMonth = DateUtils.getDaysInMonth(
      currentMonth.year,
      currentMonth.month,
    );
    // ✅ FIXED: This logic correctly finds the first day for a Sunday-start week
    final firstDayOffset =
        DateTime(currentMonth.year, currentMonth.month, 1).weekday % 7;

    return Dialog(
      backgroundColor: Colors.transparent,
      insetPadding: const EdgeInsets.all(20),
      child: Center(
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: const Color(0xFFF8F6FB),
            borderRadius: BorderRadius.circular(24),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.1),
                blurRadius: 10,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Header
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  IconButton(
                    icon: const Icon(
                      Icons.arrow_back_ios_new_rounded,
                      color: Color(0xFF5E548E),
                    ),
                    onPressed: _prevMonth,
                  ),
                  Text(
                    DateFormat.yMMMM().format(currentMonth),
                    style: GoogleFonts.poppins(
                      fontSize: 18,
                      color: const Color(0xFF5E548E),
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  IconButton(
                    icon: const Icon(
                      Icons.arrow_forward_ios_rounded,
                      color: Color(0xFF5E548E),
                    ),
                    onPressed: _nextMonth,
                  ),
                ],
              ),
              const SizedBox(height: 10),

              // Week Days Row
              Row(
                mainAxisAlignment:
                    MainAxisAlignment.spaceAround, // Better spacing
                children:
                    ['S', 'M', 'T', 'W', 'T', 'F', 'S']
                        .map(
                          (d) => Text(
                            d,
                            style: GoogleFonts.poppins(
                              color: const Color(0xFF9C89B8),
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        )
                        .toList(),
              ),
              const SizedBox(height: 10),

              // Calendar Grid
              GridView.builder(
                shrinkWrap: true,
                // ✅ CHANGED: Use the correct offset
                itemCount: daysInMonth + firstDayOffset,
                physics: const NeverScrollableScrollPhysics(),
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 7,
                  mainAxisSpacing: 10,
                  crossAxisSpacing: 8,
                ),
                itemBuilder: (context, index) {
                  // ✅ CHANGED: Use the correct offset
                  if (index < firstDayOffset) return const SizedBox();

                  // ✅ CHANGED: Calculate the day
                  int day = index - firstDayOffset + 1;

                  final date = DateTime(
                    currentMonth.year,
                    currentMonth.month,
                    day,
                  );
                  final isToday = _isSameDay(date, DateTime.now());

                  // ✅ CHANGED: Pass the date to the build function
                  return _buildDayCircle(day, isToday, date);
                },
              ),

              const SizedBox(height: 10),
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: Text(
                  "Close",
                  style: GoogleFonts.poppins(
                    color: const Color(0xFF5E548E),
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ✅ CHANGED: Added 'date' parameter and InkWell wrapper
  Widget _buildDayCircle(int day, bool isToday, DateTime date) {
    return InkWell(
      onTap: () {
        // ✅ ACTION: Pop the calendar first
        Navigator.pop(context);

        // ✅ ACTION: Then push the new journal page
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (context) => JournalEntryScreen(selectedDate: date),
          ),
        );
      },
      customBorder: const CircleBorder(),
      child: Container(
        decoration: BoxDecoration(
          color:
              isToday
                  ? const Color.fromARGB(255, 197, 136, 244)
                  : const Color(0xFFEDE1F5), // lavender tone
          shape: BoxShape.circle,
          border: Border.all(
            color: isToday ? const Color(0xFF7B6D8D) : const Color(0xFFB799A5),
            width: 1,
          ),
        ),
        child: Center(
          child: Text(
            "$day",
            style: GoogleFonts.poppins(
              color: const Color(0xFF4B3F72),
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      ),
    );
  }

  bool _isSameDay(DateTime a, DateTime B) {
    return a.year == B.year && a.month == B.month && a.day == B.day;
  }
}
