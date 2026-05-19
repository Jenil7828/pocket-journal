import 'dart:convert';

import 'package:diary/Dashboard/entry_analysis.dart';
import 'package:diary/DesignConstraints/api.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:intl/intl.dart';
import 'package:shared_preferences/shared_preferences.dart';

class EntriesPage extends StatefulWidget {
  const EntriesPage({super.key});

  @override
  State<EntriesPage> createState() => _EntriesPageState();
}

class _EntriesPageState extends State<EntriesPage> {
  final Color primaryColor = const Color(0xFF1E2D4C);

  int selectedFilter = 0;
  String searchQuery = "";
  bool isLoading = true;

  final List<String> filters = ["All", "This Week", "This Month"];

  List<Map<String, String>> entries = [];

  @override
  void initState() {
    super.initState();
    fetchJournalEntries();
  }

  /// ✅ FETCH JOURNAL ENTRIES API
  Future<void> fetchJournalEntries() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final token = prefs.getString("token");

      if (token == null) {
        setState(() => isLoading = false);
        return;
      }

      final response = await http.get(
        Uri.parse("${ApiConfig.baseUrl}/journal/all"),
        headers: {
          "Content-Type": "application/json",
          "Authorization": "Bearer $token",
        },
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);

        final List fetchedEntries = data["entries"] ?? [];

        setState(() {
          entries =
              fetchedEntries.map<Map<String, String>>((entry) {
                return {
                  "id": entry["id"] ?? "", // ✅ ENTRY ID ADDED
                  "title": entry["title"] ?? "Untitled",
                  "desc": entry["entry_text"] ?? "",
                  "date": formatDate(entry["created_at"]),
                  "full_date": entry["created_at"] ?? "",
                };
              }).toList();

          isLoading = false;
        });
      } else {
        setState(() => isLoading = false);
      }
    } catch (e) {
      debugPrint("Entries Fetch Error: $e");
      setState(() => isLoading = false);
    }
  }

  /// ✅ FORMAT DATE
  String formatDate(String? rawDate) {
    if (rawDate == null || rawDate.isEmpty) return "";

    try {
      final parsedDate = DateFormat(
        "EEE, dd MMM yyyy HH:mm:ss 'GMT'",
      ).parseUtc(rawDate);

      return DateFormat("MMM d").format(parsedDate);
    } catch (e) {
      return "";
    }
  }

  List<Map<String, String>> get filteredEntries {
    List<Map<String, String>> filtered =
        entries.where((entry) {
          return entry["title"]!.toLowerCase().contains(
                searchQuery.toLowerCase(),
              ) ||
              entry["desc"]!.toLowerCase().contains(searchQuery.toLowerCase());
        }).toList();

    /// FILTER LOGIC
    if (selectedFilter == 1) {
      // This Week
      final now = DateTime.now();
      filtered =
          filtered.where((entry) {
            try {
              final date = DateFormat(
                "EEE, dd MMM yyyy HH:mm:ss 'GMT'",
              ).parseUtc(entry["full_date"]!);
              return now.difference(date).inDays <= 7;
            } catch (_) {
              return false;
            }
          }).toList();
    } else if (selectedFilter == 2) {
      // This Month
      final now = DateTime.now();
      filtered =
          filtered.where((entry) {
            try {
              final date = DateFormat(
                "EEE, dd MMM yyyy HH:mm:ss 'GMT'",
              ).parseUtc(entry["full_date"]!);
              return date.month == now.month && date.year == now.year;
            } catch (_) {
              return false;
            }
          }).toList();
    }

    return filtered;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        leading: GestureDetector(
          onTap: () => Navigator.pop(context),
          child: Container(
            margin: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: primaryColor.withOpacity(0.1),
              shape: BoxShape.circle,
            ),
            child: Icon(Icons.arrow_back, color: primaryColor),
          ),
        ),
        centerTitle: true,
        title: const Text(
          "Your Entries",
          style: TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.w600,
            color: Colors.black,
          ),
        ),
      ),

      body: SafeArea(
        child: Column(
          children: [
            const SizedBox(height: 10),

            /// SUBTITLE
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  "${entries.length} entries · Reflect on your journey",
                  style: TextStyle(color: Colors.grey.shade600),
                ),
              ),
            ),

            const SizedBox(height: 18),

            /// SEARCH
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                decoration: BoxDecoration(
                  color: const Color.fromARGB(255, 235, 233, 233),
                  borderRadius: BorderRadius.circular(30),
                  boxShadow: [
                    BoxShadow(
                      blurRadius: 10,
                      color: primaryColor.withOpacity(0.08),
                    ),
                  ],
                ),
                child: TextField(
                  onChanged: (value) {
                    setState(() => searchQuery = value);
                  },
                  decoration: InputDecoration(
                    icon: Icon(Icons.search, color: primaryColor),
                    hintText: "Search entries...",
                    border: InputBorder.none,
                  ),
                ),
              ),
            ),

            const SizedBox(height: 16),

            /// FILTERS
            SizedBox(
              height: 45,
              child: ListView.builder(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 16),
                itemCount: filters.length,
                itemBuilder: (context, index) {
                  final isSelected = selectedFilter == index;

                  return GestureDetector(
                    onTap: () {
                      setState(() => selectedFilter = index);
                    },
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 250),
                      margin: const EdgeInsets.only(right: 10),
                      padding: const EdgeInsets.symmetric(
                        horizontal: 18,
                        vertical: 10,
                      ),
                      decoration: BoxDecoration(
                        color: isSelected ? primaryColor : Colors.white,
                        borderRadius: BorderRadius.circular(25),
                        border: Border.all(
                          color: primaryColor.withOpacity(0.2),
                        ),
                        boxShadow:
                            isSelected
                                ? [
                                  BoxShadow(
                                    color: primaryColor.withOpacity(0.3),
                                    blurRadius: 10,
                                  ),
                                ]
                                : [],
                      ),
                      child: Text(
                        filters[index],
                        style: TextStyle(
                          color: isSelected ? Colors.white : primaryColor,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  );
                },
              ),
            ),

            const SizedBox(height: 10),

            /// ENTRIES LIST
            Expanded(
              child:
                  isLoading
                      ? Center(
                        child: CircularProgressIndicator(color: primaryColor),
                      )
                      : filteredEntries.isEmpty
                      ? Center(
                        child: Text(
                          "No journal entries found",
                          style: TextStyle(
                            color: Colors.grey.shade600,
                            fontSize: 15,
                          ),
                        ),
                      )
                      : ListView.builder(
                        padding: const EdgeInsets.all(16),
                        itemCount: filteredEntries.length,
                        itemBuilder: (context, index) {
                          final entry = filteredEntries[index];
                          return _entryCard(entry);
                        },
                      ),
            ),
          ],
        ),
      ),
    );
  }

  /// 💎 ENTRY CARD
  Widget _entryCard(Map<String, String> entry) {
    return GestureDetector(
      onTap: () {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder:
                (_) => EntryAnalysisPage(
                  entryId: entry["id"]!, // ✅ PASSING ENTRY ID
                ),
          ),
        );
      },
      child: Container(
        margin: const EdgeInsets.only(bottom: 14),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: const Color(0xFFF5F5F5),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.grey.shade300),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(width: 12),

            /// TEXT
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          entry["title"]!,
                          style: TextStyle(
                            fontSize: 15.5,
                            fontWeight: FontWeight.w600,
                            color: Colors.black87,
                          ),
                        ),
                      ),
                      Text(
                        entry["date"]!,
                        style: TextStyle(
                          color: Colors.grey.shade500,
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(
                    entry["desc"]!,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(color: Colors.grey.shade600, fontSize: 13),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
