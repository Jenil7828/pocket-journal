import time
import logging
from flask import jsonify
from utils.logging_utils import log_request, log_response
from datetime import datetime

logger = logging.getLogger()


def register(app, deps: dict):
    @app.route("/api/v1/app/about", methods=["GET"])
    def app_about():
        """Get app information, version, and mission."""
        start_time = time.time()
        log_request()
        
        try:
            response = {
                "app_name": "Pocket Journal",
                "version": "1.0.0",
                "mission": "Empower users to understand themselves better through AI-powered emotional insights and personalized media recommendations.",
                "features": [
                    "AI-powered mood detection from journal entries",
                    "Personalized insights and behavioral patterns",
                    "Emotion-driven media recommendations (movies, music, books, podcasts)",
                    "Privacy-first architecture with end-to-end encryption",
                    "Weekly emotional summaries and progress tracking",
                    "Customizable notification preferences",
                    "Journal search and filtering capabilities"
                ],
                "privacy_highlight": "Your journal entries are encrypted and stored securely. AI processing happens on-device or on secure servers. We never sell your data.",
                "contact": {
                    "email": "support@pocketjournal.app",
                    "website": "https://pocketjournal.app"
                }
            }
            log_response(200, start_time)
            return jsonify(response), 200
        except Exception as e:
            logger.exception("Failed to retrieve app info: %s", str(e))
            log_response(500, start_time)
            return jsonify({"error": "failed_to_fetch_app_info", "details": str(e)}), 500

    @app.route("/api/v1/app/privacy", methods=["GET"])
    def app_privacy():
        """Get comprehensive privacy policy."""
        start_time = time.time()
        log_request()
        
        try:
            response = {
                "last_updated": "2024-01-01",
                "sections": [
                    {
                        "title": "Data Collection",
                        "content": "Pocket Journal collects the following data: journal entries you write, mood detection results from AI analysis, user preferences (media types, genres, languages), activity metadata (timestamps, interaction history), and device information (app version, OS version). We do NOT collect: payment information, precise location data, browsing history unrelated to Pocket Journal, or biometric data beyond emotion detection."
                    },
                    {
                        "title": "Data Security",
                        "content": "All journal entries are encrypted at rest using AES-256 encryption. Data in transit is protected via TLS 1.3. Your data is stored in Firebase Firestore with enterprise-grade security, including intrusion detection, DDoS protection, and regular security audits. API access is restricted to authenticated users via JWT tokens with expiration."
                    },
                    {
                        "title": "AI and Machine Learning",
                        "content": "Your journal entries are analyzed using fine-tuned RoBERTa models for emotion detection and BART models for summarization. This processing may occur on-device or on secure cloud servers. AI models do NOT perform persistent learning on your data. Sentiment analysis is used solely to provide you with insights and recommendations. Your emotional data is NEVER used to train new models without explicit consent."
                    },
                    {
                        "title": "Third-Party Services",
                        "content": "Pocket Journal integrates with: Google Firebase (authentication, database, hosting), TMDB (The Movie Database - movie recommendations), Spotify API (music recommendations), Google Generative AI (Gemini - optional insights generation). Each third party has its own privacy policy which we encourage you to review."
                    },
                    {
                        "title": "Data Retention",
                        "content": "Your journal entries, mood data, and insights are retained indefinitely until you delete them. You can delete individual entries or request full account deletion anytime. Deleted data is permanently removed from our systems within 30 days. Backup copies older than 90 days are also purged."
                    },
                    {
                        "title": "Your Rights",
                        "content": "You have the right to: access all personal data we hold about you, download your data in machine-readable format (JSON export), delete your account and associated data at any time, opt-out of optional features (e.g., AI insights, recommendations), and request clarification on how your data is used. We comply with GDPR, CCPA, and other privacy regulations."
                    },
                    {
                        "title": "Contact Us",
                        "content": "If you have concerns about your privacy or how we handle your data, please contact us at privacy@pocketjournal.app. We aim to respond to all privacy inquiries within 7 business days."
                    }
                ]
            }
            log_response(200, start_time)
            return jsonify(response), 200
        except Exception as e:
            logger.exception("Failed to retrieve privacy policy: %s", str(e))
            log_response(500, start_time)
            return jsonify({"error": "failed_to_fetch_privacy", "details": str(e)}), 500

    @app.route("/api/v1/app/terms", methods=["GET"])
    def app_terms():
        """Get comprehensive terms of service."""
        start_time = time.time()
        log_request()
        
        try:
            response = {
                "last_updated": "2024-01-01",
                "sections": [
                    {
                        "title": "Service Description",
                        "content": "Pocket Journal is an AI-powered journaling and recommendation platform designed to help users track emotions, gain behavioral insights, and discover personalized media. The service includes journal entry storage, emotion detection via machine learning, weekly insights generation, and media recommendations tailored to user mood and preferences."
                    },
                    {
                        "title": "User Responsibilities",
                        "content": "You are responsible for: maintaining the confidentiality of your login credentials, being truthful in your journal entries and preference settings, using the service lawfully and in compliance with all applicable laws, not attempting to reverse-engineer or hack the service, and respecting other users' privacy. You agree not to use the service to harass, defame, abuse, or threaten other users."
                    },
                    {
                        "title": "Acceptable Use",
                        "content": "Pocket Journal must NOT be used for: illegal activities, generating content that violates intellectual property rights, transmitting malware or harmful code, creating fake or misleading entries, or sharing account access with unauthorized third parties. Violation of these terms may result in account suspension or permanent deletion without refund."
                    },
                    {
                        "title": "Intellectual Property",
                        "content": "Journal entries you create remain YOUR intellectual property. You grant Pocket Journal a non-exclusive license to store, process, and analyze your entries for your own use and to provide AI insights. Pocket Journal respects all copyrights and intellectual property. Do not post copyrighted material without permission. Media recommendations from TMDB, Spotify, or other providers remain the property of those services."
                    },
                    {
                        "title": "Limitation of Liability",
                        "content": "Pocket Journal is provided 'AS IS' without warranties. We are not liable for: data loss due to user error or third-party breaches (we use industry-standard security, but no system is 100% secure), emotional distress from insights or recommendations, third-party service outages (Firebase, TMDB, Spotify), or indirect damages resulting from your use of the service. Our liability is capped at the amount you paid to use Pocket Journal in the past 12 months."
                    },
                    {
                        "title": "Disclaimer",
                        "content": "Pocket Journal's AI insights are NOT a substitute for professional mental health advice. If you are experiencing a mental health crisis, please contact a licensed mental health professional or call a crisis hotline. The insights generated by AI are for self-reflection only and should not be used for clinical diagnosis or treatment decisions."
                    },
                    {
                        "title": "Termination",
                        "content": "We reserve the right to suspend or terminate your account if you violate these Terms of Service. You can request account deletion anytime through your profile settings. Upon termination, we will delete your data in accordance with our privacy policy and applicable law (within 30-90 days)."
                    },
                    {
                        "title": "Changes to Terms",
                        "content": "We may update these Terms of Service from time to time. Continued use of Pocket Journal after changes are posted constitutes your acceptance of new terms. We will notify you of material changes via email or in-app notification."
                    }
                ]
            }
            log_response(200, start_time)
            return jsonify(response), 200
        except Exception as e:
            logger.exception("Failed to retrieve terms of service: %s", str(e))
            log_response(500, start_time)
            return jsonify({"error": "failed_to_fetch_terms", "details": str(e)}), 500
