import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import pytz

# -----------------------------
# CONFIG: Replace with your Firebase Auth UID
# -----------------------------
USER_UID = "t6xSqQyHIEQzeDsL16qdKlDPQU42"  # Example Firebase UID

# -----------------------------
# Initialize Firebase
# -----------------------------
cred = credentials.Certificate("D:\\B.E._Project\\pocket_journal\\pocket-journal-be-firebase-adminsdk-fbsvc-b311d88edc.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# -----------------------------
# Journal Entries (actual values from MySQL dump)
# -----------------------------
journal_entries_data = [
    {"entry_text":"Woke up early and did a 30-minute morning run. Felt energized.","created_at":"2025-08-31 18:30:00"},
    {"entry_text":"Had a busy day at work, felt stressed but managed tasks efficiently.","created_at":"2025-09-01 18:30:00"},
    {"entry_text":"Lunch with colleagues was enjoyable. Shared jokes and felt happy.","created_at":"2025-09-02 18:30:00"},
    {"entry_text":"Felt lonely and missed friends. Spent evening reading.","created_at":"2025-09-03 18:30:00"},
    {"entry_text":"Went for a walk in the park. Appreciated nature and calmness.","created_at":"2025-09-04 18:30:00"},
    {"entry_text":"Felt anxious about upcoming project deadline.","created_at":"2025-09-05 18:30:00"},
    {"entry_text":"Had a relaxing coffee break and talked to a friend.","created_at":"2025-09-06 18:30:00"},
    {"entry_text":"Overwhelmed by workload but took short mindfulness breaks.","created_at":"2025-09-07 18:30:00"},
    {"entry_text":"Watched a movie but found it uninteresting. Felt regret for wasting time.","created_at":"2025-09-08 18:30:00"},
    {"entry_text":"Completed a small personal project. Felt accomplished and proud.","created_at":"2025-09-09 18:30:00"},
    {"entry_text":"Feeling tired and sleepy after a long workday.","created_at":"2025-09-10 18:30:00"},
    {"entry_text":"Had a nice surprise visit from a friend. Felt joyful.","created_at":"2025-09-11 18:30:00"},
    {"entry_text":"Practiced meditation for 10 minutes. Felt calm and focused.","created_at":"2025-09-12 18:30:00"},
    {"entry_text":"Skipped lunch and felt low energy.","created_at":"2025-09-13 18:30:00"},
    {"entry_text":"Attended a workshop and learned new skills. Felt motivated.","created_at":"2025-09-14 18:30:00"},
    {"entry_text":"Felt frustrated with traffic. Practiced deep breathing to stay calm.","created_at":"2025-09-15 18:30:00"},
    {"entry_text":"Cooked a healthy dinner and enjoyed the process.","created_at":"2025-09-16 18:30:00"},
    {"entry_text":"Had a video call with family. Felt connected and happy.","created_at":"2025-09-17 18:30:00"},
    {"entry_text":"Procrastinated on work and felt guilty.","created_at":"2025-09-18 18:30:00"},
    {"entry_text":"Went for a short run. Mood improved.","created_at":"2025-09-19 18:30:00"},
    {"entry_text":"Felt anxious about finances. Planned budget to reduce stress.","created_at":"2025-09-20 18:30:00"},
    {"entry_text":"Spent time on a hobby I enjoy. Felt satisfied.","created_at":"2025-09-21 18:30:00"},
    {"entry_text":"Felt lonely but reached out to a friend. Conversation helped.","created_at":"2025-09-22 18:30:00"},
    {"entry_text":"Had a productive workday. Felt confident and energetic.","created_at":"2025-09-23 18:30:00"},
    {"entry_text":"Skipped exercise. Felt low motivation.","created_at":"2025-09-24 18:30:00"},
    {"entry_text":"Went to a new coffee shop. Enjoyed the new experience.","created_at":"2025-09-25 18:30:00"},
    {"entry_text":"Felt stressed by emails. Took breaks and focused on priorities.","created_at":"2025-09-26 18:30:00"},
    {"entry_text":"Watched a motivational talk. Felt inspired.","created_at":"2025-09-27 18:30:00"},
    {"entry_text":"Had a calm evening. Practiced gratitude for small joys.","created_at":"2025-09-28 18:30:00"},
    {"entry_text":"Finished a project ahead of deadline. Felt proud.","created_at":"2025-09-29 18:30:00"}
]

# -----------------------------
# Entry Analysis (actual JSON values)
# -----------------------------
entry_analysis_data = [
	{"summary": "Woke up early and did a 30-minute morning run. Felt energized.",
	 "mood": {"sad": 0.016773831099271774, "fear": 0.007715207990258932, "anger": 0.0533609576523304,
			  "happy": 0.7336307168006897, "disgust": 0.01225358620285988, "neutral": 0.15442080795764923,
			  "surprise": 0.009560473263263702},
	 "created_at": "2025-10-01 18:00:02"},

	{"summary": "Had a busy day at work, felt stressed but managed tasks efficiently.",
	 "mood": {"sad": 0.17028926312923431, "fear": 0.011108558624982834, "anger": 0.7559499740600586,
			  "happy": 0.051793619990348816, "disgust": 0.024039098992943764, "neutral": 0.04791782051324845,
			  "surprise": 0.004675835836678743},
	 "created_at": "2025-10-01 18:00:02"},

	{"summary": "Lunch with colleagues was enjoyable. Shared jokes and felt happy.",
	 "mood": {"sad": 0.024357343092560768, "fear": 0.01734195090830326, "anger": 0.033784788101911545,
			  "happy": 0.918743133544922, "disgust": 0.01657884381711483, "neutral": 0.03380206972360611,
			  "surprise": 0.021215450018644333},
	 "created_at": "2025-10-01 18:00:03"},

	{"summary": "Felt lonely and missed friends. Spent evening reading.",
	 "mood": {"sad": 0.9764425158500672, "fear": 0.017839662730693817, "anger": 0.013310611248016356,
			  "happy": 0.02257399819791317, "disgust": 0.01972658559679985, "neutral": 0.02614760771393776,
			  "surprise": 0.020930703729391095},
	 "created_at": "2025-10-01 18:00:03"},

	{"summary": "Went for a walk in the park. Appreciated nature and calmness.",
	 "mood": {"sad": 0.015237413346767426, "fear": 0.003912938758730888, "anger": 0.034812409430742264,
			  "happy": 0.34148213267326355, "disgust": 0.015009980648756027, "neutral": 0.5183740854263306,
			  "surprise": 0.007200200110673904},
	 "created_at": "2025-10-01 18:00:03"},

	{"summary": "Felt anxious about upcoming project deadline.",
	 "mood": {"sad": 0.023389948531985283, "fear": 0.9467912912368774, "anger": 0.020128998905420303,
			  "happy": 0.017865672707557678, "disgust": 0.015738239511847496, "neutral": 0.02100289426743984,
			  "surprise": 0.008195720613002777},
	 "created_at": "2025-10-01 18:00:03"},

	{"summary": "Had a relaxing coffee break and talked to a friend.",
	 "mood": {"sad": 0.0392327792942524, "fear": 0.009074114263057709, "anger": 0.017678722739219666,
			  "happy": 0.03838702663779259, "disgust": 0.017166618257761, "neutral": 0.9350869655609132,
			  "surprise": 0.01042560674250126},
	 "created_at": "2025-10-01 18:00:03"},

	{"summary": "Overwhelmed by workload but took short mindfulness breaks.",
	 "mood": {"sad": 0.04361799359321594, "fear": 0.01591736078262329, "anger": 0.07739271223545074,
			  "happy": 0.0773095116019249, "disgust": 0.00621293717995286, "neutral": 0.7137840986251831,
			  "surprise": 0.006689855828881264},
	 "created_at": "2025-10-01 18:00:03"},

	{"summary": "Watched a movie but found it uninteresting. Felt regret for wasting time.",
	 "mood": {"sad": 0.9244129061698914, "fear": 0.008278297260403633, "anger": 0.0463792085647583,
			  "happy": 0.041861217468976974, "disgust": 0.013971901498734953, "neutral": 0.040114838629961014,
			  "surprise": 0.009680583141744137},
	 "created_at": "2025-10-01 18:00:03"},

	{"summary": "Completed a small personal project. Felt accomplished and proud.",
	 "mood": {"sad": 0.05384603887796402, "fear": 0.023952968418598175, "anger": 0.20606955885887143,
			  "happy": 0.5033878684043884, "disgust": 0.005216571036726236, "neutral": 0.007569156121462584,
			  "surprise": 0.024938492104411125},
	 "created_at": "2025-10-01 18:00:03"},

	{"summary": "Feeling tired and sleepy after a long workday.",
	 "mood": {"sad": 0.8682569265365601, "fear": 0.008664182387292385, "anger": 0.02361416071653366,
			  "happy": 0.03218592330813408, "disgust": 0.0153369577601552, "neutral": 0.06219097226858139,
			  "surprise": 0.006742893718183041},
	 "created_at": "2025-10-01 18:00:03"},

	{"summary": "Had a nice surprise visit from a friend. Felt joyful.",
	 "mood": {"sad": 0.02670827880501747, "fear": 0.033132705837488174, "anger": 0.05314413458108902,
			  "happy": 0.9238151907920836, "disgust": 0.019977957010269165, "neutral": 0.016074122861027718,
			  "surprise": 0.032482292503118515},
	 "created_at": "2025-10-01 18:00:03"},

	{"summary": "Practiced meditation for 10 minutes. Felt calm and focused.",
	 "mood": {"sad": 0.026021748781204224, "fear": 0.022576160728931427, "anger": 0.02228816039860249,
			  "happy": 0.036797553300857544, "disgust": 0.012897881679236887, "neutral": 0.9250431656837464,
			  "surprise": 0.007553858682513237},
	 "created_at": "2025-10-01 18:00:03"},

	{"summary": "Skipped lunch and felt low energy.",
	 "mood": {"sad": 0.9507270455360411, "fear": 0.011300044134259224, "anger": 0.017431512475013733,
			  "happy": 0.021938515827059742, "disgust": 0.021338410675525665, "neutral": 0.03600914403796196,
			  "surprise": 0.008397267200052738},
	 "created_at": "2025-10-01 18:00:04"},

	{"summary": "Attended a workshop and learned new skills. Felt motivated.",
	 "mood": {"sad": 0.05203280597925186, "fear": 0.0291050486266613, "anger": 0.2646641135215759,
			  "happy": 0.2440491020679474, "disgust": 0.006007293239235878, "neutral": 0.23164549469947815,
			  "surprise": 0.00524568697437644},
	 "created_at": "2025-10-01 18:00:04"},

	{"summary": "Felt frustrated with traffic. Practiced deep breathing to stay calm.",
	 "mood": {"sad": 0.03671380132436752, "fear": 0.020403601229190823, "anger": 0.8289282321929932,
			  "happy": 0.031480059027671814, "disgust": 0.016815263777971268, "neutral": 0.16788989305496216,
			  "surprise": 0.00766716618090868},
	 "created_at": "2025-10-01 18:00:04"},

	{"summary": "Cooked a healthy dinner and enjoyed the process.",
	 "mood": {"sad": 0.017170608043670654, "fear": 0.012438204139471054, "anger": 0.03585215285420418,
			  "happy": 0.8975556492805481, "disgust": 0.02361868880689144, "neutral": 0.0716887041926384,
			  "surprise": 0.01197124645113945},
	 "created_at": "2025-10-01 18:00:04"},

	{"summary": "Had a video call with family. Felt connected and happy.",
	 "mood": {"sad": 0.0927700325846672, "fear": 0.007294607348740101, "anger": 0.03333384543657303,
			  "happy": 0.6012692451477051, "disgust": 0.009958584792912006, "neutral": 0.2332720309495926,
			  "surprise": 0.005555812269449234},
	 "created_at": "2025-10-01 18:00:04"},

	{"summary": "Procrastinated on work and felt guilty.",
	 "mood": {"sad": 0.7468488216400146, "fear": 0.0044713569805026054, "anger": 0.10910730808973312,
			  "happy": 0.03401188552379608, "disgust": 0.06323419511318207, "neutral": 0.050538692623376846,
			  "surprise": 0.004250704310834408},
	 "created_at": "2025-10-01 18:00:04"},

	{"summary": "Went for a short run. Mood improved.",
	 "mood": {"sad": 0.02632862888276577, "fear": 0.008926080539822578, "anger": 0.014406527392566204,
			  "happy": 0.03636318817734718, "disgust": 0.012193828821182253, "neutral": 0.9073809385299684,
			  "surprise": 0.01334210392087698},
	 "created_at": "2025-10-01 18:00:04"},

	{"summary": "Felt anxious about finances. Planned budget to reduce stress.",
	 "mood": {"sad": 0.028544824570417404, "fear": 0.9437557458877563, "anger": 0.02062080055475235,
			  "happy": 0.01561441645026207, "disgust": 0.01564743183553219, "neutral": 0.019808439537882805,
			  "surprise": 0.006101609207689762},
	 "created_at": "2025-10-01 18:00:04"},

	{"summary": "Spent time on a hobby I enjoy. Felt satisfied.",
	 "mood": {"sad": 0.06157644093036651, "fear": 0.0054273526184260845, "anger": 0.19400180876255035,
			  "happy": 0.29365888237953186, "disgust": 0.014305743388831615, "neutral": 0.03551851212978363,
			  "surprise": 0.016378462314605713},
	 "created_at": "2025-10-01 18:00:04"},

	{"summary": "Felt lonely but reached out to a friend. Conversation helped.",
	 "mood": {"sad": 0.9677791595458984, "fear": 0.015474147163331509, "anger": 0.012702737003564836,
			  "happy": 0.02164706587791443, "disgust": 0.01991957984864712, "neutral": 0.04389167949557304,
			  "surprise": 0.015284198336303234},
	 "created_at": "2025-10-01 18:00:04"},

	{"summary": "Had a productive workday. Felt confident and energetic.",
	 "mood": {"sad": 0.037373363971710205, "fear": 0.4363050162792206, "anger": 0.038638826459646225,
			  "happy": 0.17473313212394714, "disgust": 0.004087330307811499, "neutral": 0.0976785123348236,
			  "surprise": 0.0029833719599992037},
	 "created_at": "2025-10-01 18:00:04"},

	{"summary": "Skipped exercise. Felt low motivation.",
	 "mood": {"sad": 0.9212666153907776, "fear": 0.018940245732665065, "anger": 0.029216637834906575,
			  "happy": 0.040013376623392105, "disgust": 0.011856583878397942, "neutral": 0.04634639248251915,
			  "surprise": 0.004323207773268223},
	 "created_at": "2025-10-01 18:00:05"},

	{"summary": "Went to a new coffee shop. Enjoyed the new experience.",
	 "mood": {"sad": 0.01413376536220312, "fear": 0.01224167924374342, "anger": 0.03188513591885567,
			  "happy": 0.783656120300293, "disgust": 0.01016133278608322, "neutral": 0.023114515468478203,
			  "surprise": 0.16376496851444244},
	 "created_at": "2025-10-01 18:00:05"},

	{"summary": "Felt stressed by emails. Took breaks and focused on priorities.",
	 "mood": {"sad": 0.2283881902694702, "fear": 0.005062188021838665, "anger": 0.2844354510307312,
			  "happy": 0.05983879417181015, "disgust": 0.03411710262298584, "neutral": 0.3337303102016449,
			  "surprise": 0.0037163393571972847},
	 "created_at": "2025-10-01 18:00:05"},

	{"summary": "Watched a motivational talk. Felt inspired.",
	 "mood": {"sad": 0.027340300381183624, "fear": 0.0033209375105798244, "anger": 0.04053952172398567,
			  "happy": 0.6602674722671509, "disgust": 0.01377052627503872, "neutral": 0.2508108913898468,
			  "surprise": 0.01442726794630289},
	 "created_at": "2025-10-01 18:00:05"},

	{"summary": "Had a calm evening. Practiced gratitude for small joys.",
	 "mood": {"sad": 0.02873235009610653, "fear": 0.01620589755475521, "anger": 0.04458308219909668,
			  "happy": 0.2575978934764862, "disgust": 0.011454658582806587, "neutral": 0.3857360780239105,
			  "surprise": 0.005274312105029821},
	 "created_at": "2025-10-01 18:00:05"},

	{"summary": "Finished a project ahead of deadline. Felt proud.",
	 "mood": {"sad": 0.03710303083062172, "fear": 0.02227074094116688, "anger": 0.16713714599609375,
			  "happy": 0.6962985396385193, "disgust": 0.005418557208031416, "neutral": 0.015310135670006275,
			  "surprise": 0.017242809757590294},
	 "created_at": "2025-10-01 18:00:05"}
]

# -----------------------------
# MIGRATION SCRIPT
# -----------------------------
IST = pytz.timezone("Asia/Kolkata")
entry_ids = []

# Upload Journal Entries
for entry in journal_entries_data:
    doc_ref = db.collection("journal_entries").document()
    # Convert to IST timezone
    created_at_naive = datetime.fromisoformat(entry["created_at"])
    created_at = IST.localize(created_at_naive)
    doc_ref.set({
        "user_id": USER_UID,
        "entry_text": entry["entry_text"],
        "created_at": created_at
    })
    entry_ids.append(doc_ref.id)

# Upload Entry Analysis
for idx, analysis in enumerate(entry_analysis_data):
    # Convert to IST timezone
    analysis_created_at_naive = datetime.fromisoformat(analysis["created_at"])
    analysis_created_at = IST.localize(analysis_created_at_naive)
    db.collection("entry_analysis").document().set({
        "entry_id": entry_ids[idx],
        "summary": analysis["summary"],
        "mood": analysis["mood"],
        "created_at": analysis_created_at
    })

print("✅ Migration completed: all 30 entries + analyses uploaded.")
