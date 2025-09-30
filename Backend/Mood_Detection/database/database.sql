-- Select database
CREATE DATABASE journal_app;
USE journal_app;

-- Journal entries table
CREATE TABLE journal_entries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    entry_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Entry analysis table
CREATE TABLE entry_analysis (
    id INT AUTO_INCREMENT PRIMARY KEY,
    entry_id INT NOT NULL,
    summary TEXT,
    mood JSON, -- store full probabilities (e.g. {"happy": 0.7, "sad": 0.2})
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (entry_id) REFERENCES journal_entries(id)
);

CREATE TABLE goal_feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    entry_ids JSON NOT NULL,
    detected_goals TEXT,
    feedback TEXT,
    suggestions TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
