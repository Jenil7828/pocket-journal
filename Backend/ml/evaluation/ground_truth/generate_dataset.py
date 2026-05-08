import argparse
import json
import logging
import os
import random
import sys
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Ensure Backend is in path
_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from persistence.db_manager import DBManager
from ml.evaluation.orchestrator.firestore_fetcher import FirestoreFetcher
from ml.evaluation.orchestrator.auth_client import AuthClient
from ml.evaluation.ground_truth.gemini_generator import GeminiGTGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger()

# --- SYNTHETIC ENTRIES TEMPLATES ---
# 35 entries — 5 per emotion class
SYNTHETIC_TEMPLATES = [
    # ANGER
    {"hint": "anger", "text": "I am absolutely livid right now. I just found out that my group partners for the final AI project haven't even started their modules, and the submission is tomorrow morning! I've been working my tail off for weeks, attending every lab, debugging my code until 3 AM, and they have the nerve to tell me they were 'too busy' with other stuff. This project determines 40% of our grade. I feel like I'm about to explode. I told them exactly what I think of their laziness in the group chat, but they haven't even replied. It's so unfair that my GPA might suffer because of these incompetent slackers. I'm sitting here in the Monash library, hands shaking with rage, trying to finish their parts myself. I hate being in this position. Why do I always end up doing all the work while others just coast along? It's just disrespectful to my time and effort."},
    {"hint": "anger", "text": "The traffic in Mumbai is getting worse every single day and today was the absolute breaking point. It took me two and a half hours to get from Andheri to Colaba for an important meeting. Some idiot in a rickshaw decided to cut me off without signaling, and then had the audacity to yell at ME when I honked! I was fuming the entire way. By the time I reached the office, I was so angry I could barely speak professionally. Then, to top it all off, the security guard was being difficult about my parking pass which I've had for a year. I'm just sick of people's incompetence and the general chaos of this city sometimes. I just want one day where things work properly and people follow the basic rules of the road. My head is throbbing and I'm just sitting at my desk now, trying to calm down before I start my work."},
    {"hint": "anger", "text": "I can't believe the audacity of my landlord. He just informed me that he's increasing the rent by 25% starting next month, even though the elevator has been broken for three weeks and there's a persistent leak in the bathroom that he refuses to fix. I've been a perfect tenant, always paying on time, and this is how I'm treated? It's pure greed. I spent an hour on the phone arguing with him, but he just kept giving me these vague excuses about 'market rates.' I'm so frustrated I could scream. It's not just about the money; it's the principle of it. He's taking advantage of the housing shortage in Pune, and it makes me sick. I'm already looking for new places, but the whole situation has just ruined my mood. I feel like I'm being backed into a corner and I hate that feeling of being powerless against someone else's unfair decisions."},
    {"hint": "anger", "text": "My manager took credit for my entire backend optimization strategy during the board meeting today. I was sitting right there, and he presented my slides as if he had stayed up all weekend writing them. I am beyond words. I put in so much effort to reduce the latency by 40%, and he just stole the spotlight without even mentioning my name once. I wanted to stand up and call him out right then and there, but I knew it would look unprofessional. Now I'm just sitting at my desk, staring at my computer, and I can't focus on anything because I'm so angry. This isn't the first time he's done something like this, but it's definitely the biggest. I feel completely betrayed and undervalued. What's the point of working so hard if someone else is going to reap the rewards? I'm honestly thinking about updating my resume tonight and looking for a team that actually respects its developers."},
    {"hint": "anger", "text": "I've been waiting for my food delivery for over two hours now. The app says the driver is 'nearby' but he's been in the same spot on the map for forty-five minutes. When I finally reached the restaurant, they told me they gave the order to the wrong person! How does that even happen? I'm starving, I've had a long day, and now I have to wait another hour for a refund or a re-order. The customer support agent was useless, just giving me automated scripts instead of actually solving the problem. I'm so annoyed with the lack of accountability in these services. Everything is supposed to be 'convenient' but it ends up being more stressful than just cooking myself. I ended up canceling everything and I'm just eating cold leftovers now, still fuming about the waste of time and money. Some days it feels like everything is working against you."},
    
    # DISGUST
    {"hint": "disgust", "text": "I had to take the local train during peak hours today and it was a genuinely revolting experience. The compartment was so packed that I was literally pressed against three other people, all of whom were drenched in sweat. The smell was overpowering—a mix of stale perspiration, damp clothes from the rain, and someone's very strong, cheap cologne. I felt like I couldn't breathe. Then, someone behind me started coughing without covering their mouth, and I could actually feel the droplets on the back of my neck. It was absolutely disgusting. I felt so contaminated. As soon as I got home, I threw all my clothes into the washing machine and took a long, hot shower, scrubbing my skin until it was red. I still feel like I can smell that train carriage. I really need to find a way to avoid the local during these hours; it's just not worth the mental toll of feeling that dirty."},
    {"hint": "disgust", "text": "I went to a new cafe in Koregaon Park today because it looked 'aesthetic' on Instagram, but the reality was horrifying. As I was about to take a sip of my coffee, I noticed a small cockroach crawling along the edge of the counter, right near the sugar packets. I looked down at my table and it was covered in a sticky residue that clearly hadn't been wiped in days. The bathroom was even worse—the floor was wet with something I didn't want to identify, and there was no soap or paper towels. It's shocking how a place can charge so much and have such appalling hygiene standards. I left my full coffee on the table and walked out immediately. I still feel a bit nauseous just thinking about it. How do people even work in conditions like that? I'm definitely writing a scathing review on Zomato. No amount of pretty decor can make up for a lack of basic cleanliness. I'm home now, still feeling grossed out."},
    {"hint": "disgust", "text": "I saw someone throw a massive bag of trash right into the Mula-Mutha river this morning while I was crossing the bridge. It wasn't even a small piece of litter; it was a full black garbage bag. The river is already so polluted and choked with plastic, and seeing that just made my stomach turn. It's so disappointing to see how little some people care about the environment we all live in. The water looked dark and greasy, with literal layers of scum on the surface, and that extra bag just floated there like a symbol of everything wrong with our civic sense. It's repulsive. I wanted to shout at them, but they just drove away on their bike like it was nothing. I feel a mix of anger and pure revulsion. We're destroying our own city, and some people are doing it with a smile on their faces. I really wish there were stricter penalties for this kind of behavior. It's just sickening."},
    {"hint": "disgust", "text": "I was at a wedding reception last night and the behavior of some of the guests at the buffet was truly off-putting. People were using their own used spoons to serve themselves from the communal dishes, and I saw one man literally pick up a piece of chicken with his hands, change his mind, and put it back. I was so repulsed that I lost my appetite immediately. I spent the rest of the evening just drinking water and making polite conversation, but inside I was cringing. The whole 'grand' event felt cheapened by such a lack of basic manners and hygiene. It's supposed to be a celebration, but seeing that level of selfishness and sloppiness just made me want to leave. I don't understand how people can be so oblivious to others around them. I'm just staying in tonight and cooking my own dinner where I know exactly who has touched the food. Some social situations are just a test of one's patience and stomach."},
    {"hint": "disgust", "text": "I opened the fridge in the office breakroom today to put my lunch in, and the smell that hit me was like something had died in there. I looked around and found a Tupperware container in the back that was so covered in green and black mold that it was hard to tell what it used to be. It must have been sitting there for months. I can't believe none of my coworkers thought to clean it out. The thought that my fresh sandwich was sitting inches away from that biohazard for even five minutes made me not want to eat it. It's so inconsiderate to leave rotting food in a shared space. I ended up cleaning the shelf myself because I couldn't stand the sight of it, but the whole process was so gross I had to wear a mask and double up on gloves. I'm just going to start keeping my lunch in an insulated bag at my desk from now on. People are genuinely messy and it's exhausting."},

    # FEAR
    {"hint": "fear", "text": "I'm sitting in my room right now and my heart is racing. I just got an email from the university stating that my student visa status is 'under review' due to a clerical error in my documents. If this isn't resolved by next week, I might actually be deported or at least forced to suspend my Master's in AI. I've spent so much money and effort to get here to Monash, and the thought of it all being taken away because of a typo is terrifying. I tried calling the international student office but they're closed for the weekend. I can't stop thinking about the 'what ifs.' What if I have to go back to India with nothing to show for it? What will my parents say? I feel like my whole future is hanging by a thread. Every time my phone pings, I jump, hoping it's an update but also being afraid it's bad news. I tried to do some coding to distract myself, but I can't even focus on a simple loop. I just feel paralyzed by this uncertainty."},
    {"hint": "fear", "text": "The storm outside tonight is absolutely terrifying. The wind is howling so loudly it sounds like a literal monster, and the old trees near my balcony are swaying so much I'm afraid one might crash through the glass. We've already had two power cuts, and sitting here in the pitch black makes every noise sound ten times louder. I heard a loud thud on the roof a few minutes ago and I'm too scared to go out and check what it was. I'm worried about the flooding too; I live on the ground floor and I can see the water level rising in the street. I've moved my laptop and some important documents to the top shelf just in case, but I'm honestly shaking. I'm all alone in the apartment because my roommate is stuck at work due to the rain. I just want the morning to come so I can see the damage and know I'm safe. Every lightning strike makes me flinch. I've never felt this vulnerable in my own home before."},
    {"hint": "fear", "text": "I'm really worried about my health lately. I've been having these weird chest pains for the last few days, and of course, I made the mistake of Googling the symptoms. Now I'm convinced I have some serious heart condition even though I'm only 24. I have an appointment with the doctor tomorrow morning, but I'm absolutely dreading it. I'm scared of what he might find. What if it's something I can't fix? I keep checking my pulse every five minutes and my anxiety is just making the physical sensations worse. I haven't told my family yet because I don't want to panic them, but keeping it to myself is making it feel even more real. I'm trying to tell myself it's just stress from my job, but the fear is always there in the back of my mind, cold and heavy. I just want to feel normal again. Tonight is going to be a very long and sleepless night. I keep thinking about all the things I still want to do with my life."},
    {"hint": "fear", "text": "I had to walk home alone from the library tonight because the last bus was canceled, and it was the most frightening twenty minutes of my life. The streetlights in my neighborhood were mostly out, and it was so dark I could barely see the sidewalk. I felt like someone was following me the entire time. I heard footsteps behind me twice, and when I turned around, I couldn't see anyone. I started walking faster, almost running, with my keys clutched in my hand like a weapon. Every shadow looked like a person waiting to jump out. When I finally reached my building, I was so out of breath I could barely unlock the main door. I'm inside now, with all the doors locked and the lights on, but I'm still trembling. Mumbai is supposed to be safe, but at 2 AM in a dark alley, it feels very different. I'm never staying at the library that late again without a guaranteed ride home. The fear was so physical, like a knot in my stomach that won't go away."},
    {"hint": "fear", "text": "I have my final technical interview with TCS Digital tomorrow, and I'm absolutely terrified of failing. This job means everything to me—it's my chance at financial independence and a real career in AI. I've been preparing for months, but suddenly I feel like I've forgotten everything I ever knew about data structures and algorithms. My mind keeps going blank every time I try to solve a practice problem. I'm scared I'll freeze up during the live coding session and look like a total fraud. The pressure is immense because my parents are expecting so much from me. I can't sleep, I can't eat, and I keep imagining the interviewer's disappointed face when I can't answer a simple question. It feels like my entire identity is tied to this one hour-long call. I just want it to be over, but I'm also terrified of the result. What if I'm just not good enough? The imposter syndrome is hitting me harder than ever before. I'm just a mess of nerves and doubt right now."},

    # HAPPY
    {"hint": "happy", "text": "I am over the moon right now! I just got the official offer letter from TCS Digital for the AI Developer role, and the salary is even higher than I expected—7.5 LPA! All those months of late-night coding, the endless technical rounds, and the anxiety were totally worth it. I immediately called my parents and my mom was actually crying with joy. It's the best feeling in the world to know that I've made them proud and that my career is finally taking off. We're going out for a grand dinner at a fancy place tonight to celebrate. I feel so light and energetic, like I could run a marathon. Even the Mumbai rain looks beautiful today! I keep re-reading the email just to make sure it's real. This is the start of a whole new chapter for me, and I couldn't be more excited. I'm going to work so hard and prove that they made the right choice. Everything feels possible right now. Today is truly a perfect day."},
    {"hint": "happy", "text": "Today was such a wonderful day spent with my old school friends. We all met up at our favorite spot near FC Road after almost a year of not seeing each other. We spent hours just talking, laughing about old memories, and catching up on everyone's lives. It's amazing how even though we've all changed so much, the bond we have is still exactly the same. We had the most delicious misal pav and then went for a long walk on the university campus. The weather was perfect—cool and breezy with a hint of sunshine. I feel so refreshed and full of life. It's so important to have people who really know you and support you. I'm sitting at home now, looking at the photos we took, and I can't stop smiling. It was the perfect break from my stressful project work. I feel so grateful for these friendships. Days like this remind me of what's truly important in life. I'm going to sleep with a very happy heart tonight."},
    {"hint": "happy", "text": "I finally fixed that massive bug in my recommendation engine that's been bothering me for three weeks! It was a simple logic error in the cosine similarity calculation, and when the results finally started making sense, I literally jumped for joy in my room. It feels like such a huge weight has been lifted off my shoulders. I've been working on this project for a year, and this was the last major hurdle before I could say it's 'complete.' I feel so proud of myself for not giving up even when it was frustrating. I celebrated by making myself a really nice cup of coffee and watching an episode of Pokemon without feeling guilty. It's the little victories that make the long hours worth it. I'm so excited to finally demo this to my mentor. I feel so much more confident in my skills as a developer now. Hard work really does pay off! I'm definitely going to have a relaxing evening now and maybe even start planning my next big project. Life is good."},
    {"hint": "happy", "text": "The surprise party we planned for my sister's birthday was a huge success! She had absolutely no idea. When she walked into the room and everyone shouted 'Surprise!', the look of pure shock and then delight on her face was priceless. We spent the whole evening eating cake, dancing to her favorite songs, and just enjoying each other's company. My whole family was there, and seeing everyone so happy and relaxed together was the best part. I put a lot of effort into the decorations and the playlist, and seeing it all come together so perfectly made me feel so satisfied. My sister kept saying it was her best birthday ever. I feel so lucky to have such a close-knit and loving family. It's these moments of connection and joy that I'll cherish forever. I'm tired from all the planning, but it's that good kind of tired where you know you've done something meaningful for someone you love. My heart is very full tonight."},
    {"hint": "happy", "text": "I had the most peaceful and beautiful morning at the park today. I woke up early, which I rarely do, and went for a long walk while the sun was still rising. The air was so crisp and clean, and the sound of the birds was so calming. I found a quiet bench and just sat there for thirty minutes, meditating and observing the world around me. I saw an old couple holding hands, and some kids playing with a puppy, and it just made me feel so optimistic about humanity. I feel so much more centered and ready to tackle my work now. It's amazing what a little bit of nature and silence can do for your mental state. I'm going to try to make this a regular habit. I feel so much more grateful for the small things in life today. It's a beautiful world if you just take the time to look at it. I'm going to keep this feeling of calm with me throughout the rest of the day. Everything feels right."},

    # NEUTRAL
    {"hint": "neutral", "text": "Today was a pretty standard Wednesday. I woke up at my usual time of 7:30 AM, had some tea, and started working on my project code around 9:00. I spent most of the morning doing some routine data cleaning and updating the documentation, which wasn't particularly exciting but needed to be done. For lunch, I had some simple dal and rice that I cooked yesterday. In the afternoon, I attended a two-hour webinar on new trends in NLP, which was informative though some parts were a bit repetitive. I took a short break at 4 PM to walk to the local grocery store and pick up some milk and vegetables for the week. The weather was average—neither too hot nor too cold. I'm just sitting at my desk now, finishing up some final emails before I call it a day. Nothing major happened, but it was a productive enough day. I'll probably just watch some news and go to bed early tonight. It's just one of those normal, quiet days where everything goes according to plan."},
    {"hint": "neutral", "text": "I spent the entire day at the library today, just focusing on my research for the Master's application. I went through several university websites, compared their AI curriculum, and took notes on their admission requirements. It was a lot of reading and data collection. I also spent some time drafting a potential SOP, focusing on my project experience and my long-term goals. The library was quiet and I managed to get a lot done without any major interruptions. I had a quick sandwich for lunch at the campus canteen. The commute back home was also relatively smooth for a change. I don't feel particularly excited or stressed about the process right now; I'm just taking it one step at a time and making sure I have all the information I need. It's a long process and I'm just in the middle of the 'doing' phase. I'll probably just do some light reading tonight and get started on the next set of tasks tomorrow. It's a steady pace."},
    {"hint": "neutral", "text": "My day was mostly occupied with household chores and some basic administrative tasks. I spent the morning cleaning the apartment, doing the laundry, and organizing my desk which had become quite a mess over the last week. After that, I went to the bank to update my passbook and then to the post office to send a document. Both places were moderately busy, but I didn't have to wait for too long. For lunch, I tried a new tiffin service that recently started in my building—the food was okay, nothing special but edible. In the afternoon, I spent some time checking my emails and unsubscribing from a bunch of newsletters I never read. I also made a list of things I need to buy for the upcoming month. Now I'm just relaxing on the sofa, listening to some instrumental music. It's been a very low-key day, just taking care of the small things that tend to pile up. I feel like I've checked a few things off my to-do list, which is fine."},
    {"hint": "neutral", "text": "I attended a series of back-to-back meetings at work today, mostly focused on the quarterly planning. We discussed the budget allocations, the timeline for the next release, and some minor adjustments to the team structure. It was a lot of talking and looking at spreadsheets, but we managed to reach a consensus on most points. I took some notes and sent out a summary to the rest of the team. During the lunch break, I had a brief chat with a coworker about a new movie he saw, but otherwise, I just stayed at my desk. The afternoon was spent responding to a few technical queries from the QA team and doing a quick code review for a colleague. The office was its usual temperature and noise level. I'm just heading home now, thinking about what to have for dinner. It was a completely typical day at the office—no big surprises, just the usual workflow. I'll probably just do some chores and relax tonight."},
    {"hint": "neutral", "text": "I spent the afternoon at a local museum today, just looking at some historical artifacts and reading the descriptions. It was a quiet way to spend a few hours. Some of the exhibits on ancient Indian metallurgy were quite detailed and I found them mildly interesting. The museum wasn't very crowded, so I could walk through at my own pace. After that, I had a cup of tea at a nearby stall and watched the people passing by for a bit. The street was busy as usual. I then took the bus back home, which was about half-full. I didn't really have any strong reactions to anything I saw; it was just a calm and informative way to spend some free time. Now I'm back in my apartment, thinking about starting some light work on my project. It's been a balanced day, neither particularly good nor bad. I'm just in a neutral state of mind, ready to transition into the evening. I'll probably just keep things simple tonight."},

    # SAD
    {"hint": "sad", "text": "I'm feeling really down today. I just received news that my application for the Monash University scholarship was rejected. I knew it was competitive, but I had really hoped that my project work would give me an edge. Without the scholarship, it's going to be much harder for my family to afford the tuition fees, and I feel like I'm a burden on them. I spent most of the afternoon just sitting in my darkened room, feeling like all my hard work has been for nothing. I don't even have the energy to open my laptop. It's hard to stay motivated when you keep hitting these walls. I keep comparing myself to others who seem to be getting everything so easily, and it just makes me feel worse. My mom tried to cheer me up with some of my favorite food, but I couldn't even finish it. I just feel so disappointed in myself. I keep wondering if I'm even cut out for this path. Tonight feels very heavy and quiet, and I just want to disappear for a while."},
    {"hint": "sad", "text": "Today would have been my grandfather's 80th birthday, and the house feels so empty without him. He was always the one who encouraged me the most with my AI project, and I miss his wisdom and his constant support so much. I spent the morning looking at old photo albums and I couldn't stop crying. It's been six months since he passed away, but sometimes it feels like it happened yesterday. The grief just comes in these waves that wash over you when you least expect it. I tried to go for a walk to clear my head, but everywhere I looked, I saw things that reminded me of him—the park where we used to sit, the bakery where he bought his favorite biscuits. I feel a deep sense of loneliness and loss that I can't quite put into words. I wish I could just talk to him one more time and tell him about my job offer. I'm just sitting here now, in his favorite chair, feeling very small and very sad. It's a difficult day for all of us."},
    {"hint": "sad", "text": "I had a really difficult conversation with my best friend today, and it feels like our friendship might be coming to an end. We've been growing apart for a while now, with different priorities and lifestyles, but today we finally acknowledged it. There was no big fight, just a lot of sadness and the realization that we don't really understand each other anymore. It hurts so much to lose someone who has been a part of my life for so many years. I feel like a piece of my history is being erased. I spent the evening just walking around the neighborhood, feeling completely lost. Everything looks so bleak and gray tonight. I tried to listen to some music, but every song just made me want to cry. It's hard to imagine my life without our daily chats and our shared inside jokes. I feel a profound sense of emptiness and I don't know how to fill it. It's just a very lonely and heartbreaking realization. I'm not ready to let go, but I know I have to. The silence in my phone is deafening."},
    {"hint": "sad", "text": "I'm sitting alone in my apartment tonight and the silence is just overwhelming. I've been so busy with my work and my project that I haven't really made an effort to socialize, and now I'm feeling the consequences. All my friends seem to be out at parties or dinners, and I'm just here, staring at my code. I feel so disconnected from everyone and everything. It's like I'm living in a bubble while the rest of the world is moving on without me. I tried to call my sister, but she was busy with her own kids. I feel like I'm becoming a stranger even to my own family. There's this hollow feeling in my chest that won't go away. I keep thinking about how different my life was a few years ago when I was surrounded by people all the time. Now, it's just me and my computer. I'm starting to wonder if the success I'm working so hard for is worth the isolation. I just feel very tired and very, very lonely. Sometimes I just want someone to ask me how my day was and actually mean it. Tonight is particularly hard."},
    {"hint": "sad", "text": "It's a rainy, gloomy day in Pune, and my mood matches the weather perfectly. I feel completely drained and uninspired. I've been staring at the same block of code for hours and I just can't bring myself to care about it. I feel like I'm just going through the motions of life without any real purpose or joy. Everything feels like an effort—getting out of bed, making food, even talking to people. I'm overwhelmed by a general sense of hopelessness and I don't know why. Maybe it's just the accumulated stress of the last few months finally catching up with me. I feel like I'm failing at everything, even though I know logically that's not true. I just want to crawl under my blanket and stay there forever. The world outside feels too loud and demanding, and I just don't have anything left to give. I feel like a ghost in my own life. I'm just going to try to sleep and hope that tomorrow feels a little bit brighter, but right now, everything is just dark and sad. I don't know how to fix this feeling."},

    # SURPRISE
    {"hint": "surprise", "text": "I am absolutely shocked! I just found out that I've been awarded the 'Innovator of the Year' prize at my college for my final year AI project. I didn't even know my professor had nominated me! I was sitting in the cafeteria when my friend ran up to me with the announcement on his phone. I literally dropped my spoon in my plate. I never thought my work would be recognized on such a large scale. I'm still processing it—it feels like a dream. The award includes a cash prize and a chance to present my work at a national conference! I'm so stunned and excited at the same time. I keep checking the official college portal just to make sure they didn't make a mistake and meant someone else with a similar name. This came completely out of the blue. I'm so grateful and happy, but mostly just incredibly surprised. My phone is blowing up with messages from classmates and I don't even know what to say. Today has taken a very unexpected and amazing turn! I'm shaking a little bit from the adrenaline."},
    {"hint": "surprise", "text": "You won't believe what happened today! I was walking through the airport in Mumbai, waiting for my flight to Pune, when I literally bumped into my favorite Bollywood actor! He was just standing there at the bookstore, looking at some magazines. I was so startled I couldn't even speak for a second. He was actually very kind and even agreed to take a quick selfie with me! I'm still in total disbelief. I've been a fan of his for years, and to meet him just like that in a random place was so surreal. I immediately sent the photo to all my family groups and everyone is just as shocked as I am. It's the kind of thing you read about but never think will actually happen to you. My heart was pounding the whole time! I'm sitting on the plane now, still looking at the photo and grinning like an idiot. What are the odds? It's definitely the most unexpected and exciting thing that's happened to me in a long time. Today is a day I'll never forget!"},
    {"hint": "surprise", "text": "I just got a call from an unknown number, and it turned out to be an old childhood friend I haven't spoken to in over fifteen years! He somehow found my number through a common acquaintance and decided to reach out. I was so taken aback I almost didn't recognize his voice at first. We spent an hour on the phone, and it was so strange yet wonderful to hear about his life after all this time. He's actually living in Australia now! It's such a bizarre coincidence because I'm planning to move there for my Master's at Monash. I'm still reeling from the shock of it all. It's amazing how life can suddenly bring back people you thought were gone forever. I'm so surprised and happy to be reconnected with him. We've already planned a video call for next weekend to catch up properly. My mind is just buzzing with memories from our school days. What an incredible and unexpected turn of events. Life is truly full of surprises! I'm still smiling from the call."},
    {"hint": "surprise", "text": "I walked into my apartment tonight and was greeted by a full-blown surprise welcome-home party! My roommates had coordinated with my parents and a few of my close friends to celebrate the completion of my project. I had absolutely no idea they were planning anything. The room was decorated with balloons and there was a huge cake that said 'Project Hero.' I was so startled I almost walked right back out of the door! I'm usually the one who knows everything that's going on, so they really got me this time. I feel so touched and loved that they went to all this effort for me. It was the most unexpected and heartwarming end to a very long day. We spent the whole night celebrating and I'm still feeling the shock of it all. I'm so lucky to have such wonderful people in my life. I really didn't see this coming at all. My heart is still racing a bit from the initial surprise! It was a truly special moment that I'll never forget."},
    {"hint": "surprise", "text": "I was checking my bank account this morning to see if my refund had been processed, and I found a significantly larger balance than I expected. It turns out I received a one-time performance bonus from my company for the work I did on the AI migration project last quarter! I had no idea they were even considering a bonus for junior developers. I had to double-check the transaction details three times to make sure it wasn't a mistake. I'm so surprised and incredibly grateful. It's such a huge boost, both financially and for my morale. It's the first time I've ever received an unexpected bonus like this. I was so stunned I just sat there staring at the screen for a few minutes. This changes my budget for the next few months in a very good way! I'm definitely going to use some of it to buy that new mechanical keyboard I've been eyeing. What a fantastic and completely unexpected start to the day. I'm still in a state of happy shock. Hard work really does get noticed sometimes!"},
]

def generate_firestore_id() -> str:
    """Generate a random 20-character Firestore-style ID."""
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    return "".join(random.choice(chars) for _ in range(20))

def main():
    parser = argparse.ArgumentParser(description="Pocket Journal Dataset Generator")
    parser.add_argument("--email", required=True, help="Login email")
    parser.add_argument("--password", required=True, help="Login password")
    parser.add_argument("--uid", required=True, help="Firestore user UID")
    parser.add_argument("--entry-ids", required=True, help="Comma-separated real Firestore doc IDs")
    parser.add_argument("--output-dir", default="ml/evaluation/results", help="Output directory")
    parser.add_argument("--base-url", default="http://localhost:5000", help="API base URL")
    
    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(args.output_dir, f"dataset_{timestamp}.json")
    checkpoint_path = os.path.join(args.output_dir, "dataset_checkpoint.jsonl")
    
    # 1. Initialize Auth and Fetcher
    try:
        db_manager = DBManager()
        fetcher = FirestoreFetcher(db_manager)
        real_ids = [eid.strip() for eid in args.entry_ids.split(",") if eid.strip()]
        real_entries = fetcher.fetch_entries_by_ids(args.uid, real_ids)
    except Exception as e:
        logger.error("Failed to fetch real entries: %s", str(e))
        sys.exit(1)
        
    # 2. Prepare all entries list
    all_entries_to_process = []
    
    # Real entries
    for entry in real_entries:
        all_entries_to_process.append({
            "entry_id": entry["entry_id"],
            "title": entry.get("title") or "Real Entry",
            "entry_text": entry["entry_text"],
            "created_at": entry["created_at"] or datetime.now().isoformat()
        })
        
    # Synthetic entries
    ist_tz = timedelta(hours=5, minutes=30)
    for i, template in enumerate(SYNTHETIC_TEMPLATES):
        synthetic_id = generate_firestore_id()
        created_at = (datetime.utcnow() + ist_tz).isoformat()
        all_entries_to_process.append({
            "entry_id": synthetic_id,
            "title": f"Synthetic {template['hint'].capitalize()} {i%5 + 1}",
            "entry_text": template["text"],
            "created_at": created_at
        })
        
    # 3. Load Checkpoint
    processed_data = []
    processed_ids = set()
    if os.path.exists(checkpoint_path):
        logger.info("Loading checkpoint from %s", checkpoint_path)
        with open(checkpoint_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    processed_data.append(record)
                    processed_ids.add(record["entry_id"])
        logger.info("Resuming from %d already processed entries", len(processed_data))

    # 4. Initialize Gemini Generator
    # Note: Using the modified GeminiGTGenerator with internal rate-limiting and retries
    generator = GeminiGTGenerator(model_name="gemini-2.5-flash")
    
    # 5. Process Entries
    total = len(all_entries_to_process)
    for i, entry in enumerate(all_entries_to_process, 1):
        if entry["entry_id"] in processed_ids:
            continue
            
        logger.info("[%d/%d] Generating GT for entry %s", i, total, entry["entry_id"])
        
        # Gemini call with built-in retries and 20s mandatory sleep
        gt_result = generator.generate_ground_truth(entry["entry_text"])
        
        if gt_result:
            # Format record as per requirements
            dominant = gt_result.get("primary_emotion", "neutral")
            emotions_binary = {k: 1 if k == dominant else 0 for k in ["anger", "disgust", "fear", "happy", "neutral", "sad", "surprise"]}
            
            full_record = {
                "entry_id": entry["entry_id"],
                "title": entry["title"],
                "entry_text": entry["entry_text"],
                "created_at": entry["created_at"],
                "ground_truth": {
                    "dominant_emotion": dominant,
                    "emotion_labels": emotions_binary,
                    "mood": gt_result.get("emotions", {}),
                    "reference_summary": gt_result.get("summary", "")
                }
            }
            
            processed_data.append(full_record)
            
            # Save checkpoint
            with open(checkpoint_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(full_record) + "\n")
        else:
            logger.error("Failed to generate GT for entry %s after all retries", entry["entry_id"])
            # Optional: write a placeholder or skip
            
    # 6. Final Write
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(processed_data, f, indent=2)
        
    logger.info("="*50)
    logger.info("Dataset Generation Complete!")
    logger.info("Output: %s", output_path)
    logger.info("Total Records: %d", len(processed_data))
    logger.info("="*50)

if __name__ == "__main__":
    main()
