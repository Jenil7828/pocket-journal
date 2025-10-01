-- MySQL dump for journal_app with IDs starting from 1

DROP DATABASE IF EXISTS journal_app;
CREATE DATABASE journal_app CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE journal_app;

-- ------------------------------------------------------
-- Table structure for table `journal_entries`
-- ------------------------------------------------------
CREATE TABLE `journal_entries` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `entry_text` text NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Insert data into `journal_entries`
INSERT INTO `journal_entries` (`id`,`user_id`,`entry_text`,`created_at`) VALUES
(1,1,'Woke up early and did a 30-minute morning run. Felt energized.','2025-08-31 18:30:00'),
(2,1,'Had a busy day at work, felt stressed but managed tasks efficiently.','2025-09-01 18:30:00'),
(3,1,'Lunch with colleagues was enjoyable. Shared jokes and felt happy.','2025-09-02 18:30:00'),
(4,1,'Felt lonely and missed friends. Spent evening reading.','2025-09-03 18:30:00'),
(5,1,'Went for a walk in the park. Appreciated nature and calmness.','2025-09-04 18:30:00'),
(6,1,'Felt anxious about upcoming project deadline.','2025-09-05 18:30:00'),
(7,1,'Had a relaxing coffee break and talked to a friend.','2025-09-06 18:30:00'),
(8,1,'Overwhelmed by workload but took short mindfulness breaks.','2025-09-07 18:30:00'),
(9,1,'Watched a movie but found it uninteresting. Felt regret for wasting time.','2025-09-08 18:30:00'),
(10,1,'Completed a small personal project. Felt accomplished and proud.','2025-09-09 18:30:00'),
(11,1,'Feeling tired and sleepy after a long workday.','2025-09-10 18:30:00'),
(12,1,'Had a nice surprise visit from a friend. Felt joyful.','2025-09-11 18:30:00'),
(13,1,'Practiced meditation for 10 minutes. Felt calm and focused.','2025-09-12 18:30:00'),
(14,1,'Skipped lunch and felt low energy.','2025-09-13 18:30:00'),
(15,1,'Attended a workshop and learned new skills. Felt motivated.','2025-09-14 18:30:00'),
(16,1,'Felt frustrated with traffic. Practiced deep breathing to stay calm.','2025-09-15 18:30:00'),
(17,1,'Cooked a healthy dinner and enjoyed the process.','2025-09-16 18:30:00'),
(18,1,'Had a video call with family. Felt connected and happy.','2025-09-17 18:30:00'),
(19,1,'Procrastinated on work and felt guilty.','2025-09-18 18:30:00'),
(20,1,'Went for a short run. Mood improved.','2025-09-19 18:30:00'),
(21,1,'Felt anxious about finances. Planned budget to reduce stress.','2025-09-20 18:30:00'),
(22,1,'Spent time on a hobby I enjoy. Felt satisfied.','2025-09-21 18:30:00'),
(23,1,'Felt lonely but reached out to a friend. Conversation helped.','2025-09-22 18:30:00'),
(24,1,'Had a productive workday. Felt confident and energetic.','2025-09-23 18:30:00'),
(25,1,'Skipped exercise. Felt low motivation.','2025-09-24 18:30:00'),
(26,1,'Went to a new coffee shop. Enjoyed the new experience.','2025-09-25 18:30:00'),
(27,1,'Felt stressed by emails. Took breaks and focused on priorities.','2025-09-26 18:30:00'),
(28,1,'Watched a motivational talk. Felt inspired.','2025-09-27 18:30:00'),
(29,1,'Had a calm evening. Practiced gratitude for small joys.','2025-09-28 18:30:00'),
(30,1,'Finished a project ahead of deadline. Felt proud.','2025-09-29 18:30:00');

-- ------------------------------------------------------
-- Table structure for table `entry_analysis`
-- ------------------------------------------------------
CREATE TABLE `entry_analysis` (
  `id` int NOT NULL AUTO_INCREMENT,
  `entry_id` int NOT NULL,
  `summary` text,
  `mood` json DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `entry_id` (`entry_id`),
  CONSTRAINT `entry_analysis_ibfk_1` FOREIGN KEY (`entry_id`) REFERENCES `journal_entries` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Insert data into `entry_analysis`
INSERT INTO `entry_analysis` VALUES 
(1,1,'Woke up early and did a 30-minute morning run. Felt energized.','{\"sad\": 0.016773831099271774, \"fear\": 0.007715207990258932, \"anger\": 0.0533609576523304, \"happy\": 0.7336307168006897, \"disgust\": 0.01225358620285988, \"neutral\": 0.15442080795764923, \"surprise\": 0.009560473263263702}','2025-10-01 18:00:02'),
(2,2,'Had a busy day at work, felt stressed but managed tasks efficiently.','{\"sad\": 0.17028926312923431, \"fear\": 0.011108558624982834, \"anger\": 0.7559499740600586, \"happy\": 0.051793619990348816, \"disgust\": 0.024039098992943764, \"neutral\": 0.04791782051324845, \"surprise\": 0.004675835836678743}','2025-10-01 18:00:02'),
(3,3,'Lunch with colleagues was enjoyable. Shared jokes and felt happy.','{\"sad\": 0.024357343092560768, \"fear\": 0.01734195090830326, \"anger\": 0.033784788101911545, \"happy\": 0.918743133544922, \"disgust\": 0.01657884381711483, \"neutral\": 0.03380206972360611, \"surprise\": 0.021215450018644333}','2025-10-01 18:00:03'),
(4,4,'Felt lonely and missed friends. Spent evening reading.','{\"sad\": 0.9764425158500672, \"fear\": 0.017839662730693817, \"anger\": 0.013310611248016356, \"happy\": 0.02257399819791317, \"disgust\": 0.01972658559679985, \"neutral\": 0.02614760771393776, \"surprise\": 0.020930703729391095}','2025-10-01 18:00:03'),
(5,5,'Went for a walk in the park. Appreciated nature and calmness.','{\"sad\": 0.015237413346767426, \"fear\": 0.003912938758730888, \"anger\": 0.034812409430742264, \"happy\": 0.34148213267326355, \"disgust\": 0.015009980648756027, \"neutral\": 0.5183740854263306, \"surprise\": 0.007200200110673904}','2025-10-01 18:00:03'),
(6,6,'Felt anxious about upcoming project deadline.','{\"sad\": 0.023389948531985283, \"fear\": 0.9467912912368774, \"anger\": 0.020128998905420303, \"happy\": 0.017865672707557678, \"disgust\": 0.015738239511847496, \"neutral\": 0.02100289426743984, \"surprise\": 0.008195720613002777}','2025-10-01 18:00:03'),
(7,7,'Had a relaxing coffee break and talked to a friend.','{\"sad\": 0.0392327792942524, \"fear\": 0.009074114263057709, \"anger\": 0.017678722739219666, \"happy\": 0.03838702663779259, \"disgust\": 0.017166618257761, \"neutral\": 0.9350869655609132, \"surprise\": 0.01042560674250126}','2025-10-01 18:00:03'),
(8,8,'Overwhelmed by workload but took short mindfulness breaks.','{\"sad\": 0.04361799359321594, \"fear\": 0.01591736078262329, \"anger\": 0.07739271223545074, \"happy\": 0.0773095116019249, \"disgust\": 0.00621293717995286, \"neutral\": 0.7137840986251831, \"surprise\": 0.006689855828881264}','2025-10-01 18:00:03'),
(9,9,'Watched a movie but found it uninteresting. Felt regret for wasting time.','{\"sad\": 0.9244129061698914, \"fear\": 0.008278297260403633, \"anger\": 0.0463792085647583, \"happy\": 0.041861217468976974, \"disgust\": 0.013971901498734953, \"neutral\": 0.040114838629961014, \"surprise\": 0.009680583141744137}','2025-10-01 18:00:03'),
(10,10,'Completed a small personal project. Felt accomplished and proud.','{\"sad\": 0.05384603887796402, \"fear\": 0.023952968418598175, \"anger\": 0.20606955885887143, \"happy\": 0.5033878684043884, \"disgust\": 0.005216571036726236, \"neutral\": 0.007569156121462584, \"surprise\": 0.024938492104411125}','2025-10-01 18:00:03'),
(11,11,'Feeling tired and sleepy after a long workday.','{\"sad\": 0.8682569265365601, \"fear\": 0.008664182387292385, \"anger\": 0.02361416071653366, \"happy\": 0.03218592330813408, \"disgust\": 0.0153369577601552, \"neutral\": 0.06219097226858139, \"surprise\": 0.006742893718183041}','2025-10-01 18:00:03'),
(12,12,'Had a nice surprise visit from a friend. Felt joyful.','{\"sad\": 0.02670827880501747, \"fear\": 0.033132705837488174, \"anger\": 0.05314413458108902, \"happy\": 0.9238151907920836, \"disgust\": 0.019977957010269165, \"neutral\": 0.016074122861027718, \"surprise\": 0.032482292503118515}','2025-10-01 18:00:03'),
(13,13,'Practiced meditation for 10 minutes. Felt calm and focused.','{\"sad\": 0.026021748781204224, \"fear\": 0.022576160728931427, \"anger\": 0.02228816039860249, \"happy\": 0.036797553300857544, \"disgust\": 0.012897881679236887, \"neutral\": 0.9250431656837464, \"surprise\": 0.007553858682513237}','2025-10-01 18:00:03'),
(14,14,'Skipped lunch and felt low energy.','{\"sad\": 0.9507270455360411, \"fear\": 0.011300044134259224, \"anger\": 0.017431512475013733, \"happy\": 0.021938515827059742, \"disgust\": 0.021338410675525665, \"neutral\": 0.03600914403796196, \"surprise\": 0.008397267200052738}','2025-10-01 18:00:04'),
(15,15,'Attended a workshop and learned new skills. Felt motivated.','{\"sad\": 0.05203280597925186, \"fear\": 0.0291050486266613, \"anger\": 0.2646641135215759, \"happy\": 0.2440491020679474, \"disgust\": 0.006007293239235878, \"neutral\": 0.23164549469947815, \"surprise\": 0.00524568697437644}','2025-10-01 18:00:04'),
(16,16,'Felt frustrated with traffic. Practiced deep breathing to stay calm.','{\"sad\": 0.03671380132436752, \"fear\": 0.020403601229190823, \"anger\": 0.8289282321929932, \"happy\": 0.031480059027671814, \"disgust\": 0.016815263777971268, \"neutral\": 0.16788989305496216, \"surprise\": 0.00766716618090868}','2025-10-01 18:00:04'),
(17,17,'Cooked a healthy dinner and enjoyed the process.','{\"sad\": 0.017170608043670654, \"fear\": 0.012438204139471054, \"anger\": 0.03585215285420418, \"happy\": 0.8975556492805481, \"disgust\": 0.02361868880689144, \"neutral\": 0.0716887041926384, \"surprise\": 0.01197124645113945}','2025-10-01 18:00:04'),
(18,18,'Had a video call with family. Felt connected and happy.','{\"sad\": 0.0927700325846672, \"fear\": 0.007294607348740101, \"anger\": 0.03333384543657303, \"happy\": 0.6012692451477051, \"disgust\": 0.009958584792912006, \"neutral\": 0.2332720309495926, \"surprise\": 0.005555812269449234}','2025-10-01 18:00:04'),
(19,19,'Procrastinated on work and felt guilty.','{\"sad\": 0.7468488216400146, \"fear\": 0.0044713569805026054, \"anger\": 0.10910730808973312, \"happy\": 0.03401188552379608, \"disgust\": 0.06323419511318207, \"neutral\": 0.050538692623376846, \"surprise\": 0.004250704310834408}','2025-10-01 18:00:04'),
(20,20,'Went for a short run. Mood improved.','{\"sad\": 0.02632862888276577, \"fear\": 0.008926080539822578, \"anger\": 0.014406527392566204, \"happy\": 0.03636318817734718, \"disgust\": 0.012193828821182253, \"neutral\": 0.9073809385299684, \"surprise\": 0.01334210392087698}','2025-10-01 18:00:04'),
(21,21,'Felt anxious about finances. Planned budget to reduce stress.','{\"sad\": 0.028544824570417404, \"fear\": 0.9437557458877563, \"anger\": 0.02062080055475235, \"happy\": 0.01561441645026207, \"disgust\": 0.01564743183553219, \"neutral\": 0.019808439537882805, \"surprise\": 0.006101609207689762}','2025-10-01 18:00:04'),
(22,22,'Spent time on a hobby I enjoy. Felt satisfied.','{\"sad\": 0.06157644093036651, \"fear\": 0.0054273526184260845, \"anger\": 0.19400180876255035, \"happy\": 0.29365888237953186, \"disgust\": 0.014305743388831615, \"neutral\": 0.03551851212978363, \"surprise\": 0.016378462314605713}','2025-10-01 18:00:04'),
(23,23,'Felt lonely but reached out to a friend. Conversation helped.','{\"sad\": 0.9677791595458984, \"fear\": 0.015474147163331509, \"anger\": 0.012702737003564836, \"happy\": 0.02164706587791443, \"disgust\": 0.01991957984864712, \"neutral\": 0.04389167949557304, \"surprise\": 0.015284198336303234}','2025-10-01 18:00:04'),
(24,24,'Had a productive workday. Felt confident and energetic.','{\"sad\": 0.037373363971710205, \"fear\": 0.4363050162792206, \"anger\": 0.038638826459646225, \"happy\": 0.17473313212394714, \"disgust\": 0.004087330307811499, \"neutral\": 0.0976785123348236, \"surprise\": 0.0029833719599992037}','2025-10-01 18:00:04'),
(25,25,'Skipped exercise. Felt low motivation.','{\"sad\": 0.9212666153907776, \"fear\": 0.018940245732665065, \"anger\": 0.029216637834906575, \"happy\": 0.040013376623392105, \"disgust\": 0.011856583878397942, \"neutral\": 0.04634639248251915, \"surprise\": 0.004323207773268223}','2025-10-01 18:00:05'),
(26,26,'Went to a new coffee shop. Enjoyed the new experience.','{\"sad\": 0.01413376536220312, \"fear\": 0.01224167924374342, \"anger\": 0.03188513591885567, \"happy\": 0.783656120300293, \"disgust\": 0.01016133278608322, \"neutral\": 0.023114515468478203, \"surprise\": 0.16376496851444244}','2025-10-01 18:00:05'),
(27,27,'Felt stressed by emails. Took breaks and focused on priorities.','{\"sad\": 0.2283881902694702, \"fear\": 0.005062188021838665, \"anger\": 0.2844354510307312, \"happy\": 0.05983879417181015, \"disgust\": 0.03411710262298584, \"neutral\": 0.3337303102016449, \"surprise\": 0.0037163393571972847}','2025-10-01 18:00:05'),
(28,28,'Watched a motivational talk. Felt inspired.','{\"sad\": 0.027340300381183624, \"fear\": 0.0033209375105798244, \"anger\": 0.04053952172398567, \"happy\": 0.6602674722671509, \"disgust\": 0.01377052627503872, \"neutral\": 0.2508108913898468, \"surprise\": 0.01442726794630289}','2025-10-01 18:00:05'),
(29,29,'Had a calm evening. Practiced gratitude for small joys.','{\"sad\": 0.02873235009610653, \"fear\": 0.01620589755475521, \"anger\": 0.04458308219909668, \"happy\": 0.2575978934764862, \"disgust\": 0.011454658582806587, \"neutral\": 0.3857360780239105, \"surprise\": 0.005274312105029821}','2025-10-01 18:00:05'),
(30,30,'Finished a project ahead of deadline. Felt proud.','{\"sad\": 0.03710303083062172, \"fear\": 0.02227074094116688, \"anger\": 0.16713714599609375, \"happy\": 0.6962985396385193, \"disgust\": 0.005418557208031416, \"neutral\": 0.015310135670006275, \"surprise\": 0.017242809757590294}','2025-10-01 18:00:05');

-- ------------------------------------------------------
-- Table structure for table `insights`
-- ------------------------------------------------------
CREATE TABLE `insights` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `start_date` date NOT NULL,
  `end_date` date NOT NULL,
  `goals` json DEFAULT NULL,
  `progress` json DEFAULT NULL,
  `negative_behaviors` text,
  `remedies` text,
  `appreciation` text,
  `conflicts` text,
  `raw_response` text,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ------------------------------------------------------
-- Table structure for table `insight_entry_mapping`
-- ------------------------------------------------------
CREATE TABLE `insight_entry_mapping` (
  `id` int NOT NULL AUTO_INCREMENT,
  `insight_id` int NOT NULL,
  `entry_id` int NOT NULL,
  `relation_type` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `insight_id` (`insight_id`),
  KEY `entry_id` (`entry_id`),
  CONSTRAINT `insight_entry_mapping_ibfk_1` FOREIGN KEY (`insight_id`) REFERENCES `insights` (`id`),
  CONSTRAINT `insight_entry_mapping_ibfk_2` FOREIGN KEY (`entry_id`) REFERENCES `journal_entries` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

