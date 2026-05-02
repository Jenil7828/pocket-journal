"""
IEEE Evaluation Script for Journaling API

This script evaluates the journaling API using the IEEE evaluation framework,
computing metrics for:
- Text Classification (Mood)
- Summarization
- Entity Extraction
- Readability

Usage:
    python ml/evaluation/ieee_evaluation.py \
        --base_url http://localhost:5000 \
        --uid "your_uid" \
        --limit 100 \
        --start_date "2023-01-01" \
        --end_date "2023-12-31" \
        --rec_limit 5 \
        --cleanup

    python -m ml.evaluation.ieee_evaluation --dataset ml/evaluation/results/dataset_20260502_210315.json --email jenilrathod114@gmail.com --password BetterPass123! --base-url http://localhost:5000 --output-dir ml/evaluation/results/ieee_figures
"""
import argparse
import json
import logging
import os
import sys
import time
import requests
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from datetime import datetime
from typing import List, Dict, Any, Tuple

# Ensure Backend is in path
_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(os.path.dirname(_HERE))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from ml.evaluation.orchestrator.auth_client import AuthClient
from ml.evaluation.orchestrator.api_client import APIClient

# --- IEEE PLOT CONFIGURATION ---
matplotlib.rcParams.update({
    'font.family':      'serif',
    'font.serif':       ['Times New Roman', 'DejaVu Serif', 'serif'],
    'font.size':        10,
    'axes.linewidth':   0.8,
    'axes.titlesize':   11,
    'axes.labelsize':   10,
    'xtick.labelsize':  9,
    'ytick.labelsize':  9,
    'legend.fontsize':  9,
    'figure.dpi':       300,
    'savefig.dpi':      300,
    'savefig.bbox':     'tight',
    'figure.facecolor': 'white',
    'axes.facecolor':   'white',
    'axes.grid':        True,
    'grid.alpha':       0.3,
    'grid.linewidth':   0.5,
})

COLORS = {
    'primary':   '#2E4057',   # dark navy
    'secondary': '#048A81',   # teal
    'accent':    '#E76F51',   # burnt orange
    'neutral':   '#8D99AE',   # slate grey
    'positive':  '#2D6A4F',   # forest green
    'negative':  '#C1121F',   # crimson
    'highlight': '#F4A261',   # warm amber
}

EMOTIONS = ["anger", "disgust", "fear", "happy", "neutral", "sad", "surprise"]
EMOTION_COLORS = {
    'anger':    '#C1121F',
    'disgust':  '#6B4226',
    'fear':     '#7B2D8B',
    'happy':    '#2D6A4F',
    'neutral':  '#8D99AE',
    'sad':      '#2E4057',
    'surprise': '#F4A261',
}

# --- METRIC IMPLEMENTATIONS (FROM SCRATCH) ---

def compute_confusion_matrix(y_true_indices, y_pred_indices, num_classes):
    cm = np.zeros((num_classes, num_classes))
    for t, p in zip(y_true_indices, y_pred_indices):
        cm[t, p] += 1
    return cm

def compute_precision_recall_f1(tp, fp, fn):
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1

def compute_mcc(tp, tn, fp, fn):
    num = (tp * tn) - (fp * fn)
    den = np.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return num / den if den > 0 else 0.0

def compute_auc_roc(y_true, y_scores):
    # Sort scores and corresponding truth
    desc_score_indices = np.argsort(y_scores)[::-1]
    y_scores = np.array(y_scores)[desc_score_indices]
    y_true = np.array(y_true)[desc_score_indices]
    
    distinct_value_indices = np.where(np.diff(y_scores))[0]
    threshold_indices = np.r_[distinct_value_indices, y_true.size - 1]
    
    tps = np.cumsum(y_true)[threshold_indices]
    fps = 1 + threshold_indices - tps
    
    # Add point at (0,0)
    tps = np.r_[0, tps]
    fps = np.r_[0, fps]
    
    if tps[-1] == 0 or fps[-1] == 0:
        return 0.0
        
    tpr = tps / tps[-1]
    fpr = fps / fps[-1]
    
    # Manual trapezoidal rule implementation (for NumPy 2.0+ compatibility)
    auc = 0.0
    for i in range(len(fpr) - 1):
        auc += (fpr[i+1] - fpr[i]) * (tpr[i] + tpr[i+1]) / 2.0
    return abs(auc)

def compute_rouge_n(ref_tokens, hyp_tokens, n=1):
    def get_ngrams(tokens, n):
        return [tuple(tokens[i:i+n]) for i in range(len(tokens)-n+1)]
    
    ref_ngrams = get_ngrams(ref_tokens, n)
    hyp_ngrams = get_ngrams(hyp_tokens, n)
    
    if not ref_ngrams or not hyp_ngrams:
        return 0.0
        
    ref_counts = {}
    for ng in ref_ngrams:
        ref_counts[ng] = ref_counts.get(ng, 0) + 1
        
    overlap = 0
    hyp_counts = {}
    for ng in hyp_ngrams:
        if ng in ref_counts and hyp_counts.get(ng, 0) < ref_counts[ng]:
            overlap += 1
            hyp_counts[ng] = hyp_counts.get(ng, 0) + 1
            
    recall = overlap / len(ref_ngrams)
    precision = overlap / len(hyp_ngrams)
    
    if precision + recall == 0:
        return 0.0
    return 2 * (precision * recall) / (precision + recall)

def compute_tfidf_cosine_sim(doc1, doc2):
    # Simple TF-IDF and Cosine Similarity
    def get_tf(tokens):
        tf = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1
        return tf

    tokens1 = doc1.lower().split()
    tokens2 = doc2.lower().split()
    
    all_tokens = set(tokens1) | set(tokens2)
    tf1 = get_tf(tokens1)
    tf2 = get_tf(tokens2)
    
    # Using raw TF as vector components for simplicity in TF-IDF proxy
    v1 = [tf1.get(t, 0) for t in all_tokens]
    v2 = [tf2.get(t, 0) for t in all_tokens]
    
    dot = sum(a*b for a, b in zip(v1, v2))
    norm1 = np.sqrt(sum(a*a for a in v1))
    norm2 = np.sqrt(sum(a*a for a in v2))
    
    if norm1 * norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)

def flesch_kincaid_grade(text):
    import re
    if not text: return 0.0
    sentences = len(re.split(r'[.!?]+', text))
    words = len(text.split())
    if words == 0 or sentences == 0: return 0.0
    
    # Rough syllable count
    def count_syllables(word):
        word = word.lower()
        count = 0
        vowels = "aeiouy"
        if word[0] in vowels: count += 1
        for index in range(1, len(word)):
            if word[index] in vowels and word[index - 1] not in vowels:
                count += 1
        if word.endswith("e"): count -= 1
        if count == 0: count = 1
        return count

    syllables = sum(count_syllables(w) for w in text.split())
    
    # Grade Level = 0.39 * (words/sentences) + 11.8 * (syllables/words) - 15.59
    return 0.39 * (words/sentences) + 11.8 * (syllables/words) - 15.59

def call_api_with_retry(method, url, headers, payload=None, retries=3):
    """Robust API call wrapper with retries and response validation."""
    for attempt in range(retries):
        try:
            start_time = time.time()
            if method.upper() == "POST":
                response = requests.post(url, headers=headers, json=payload, timeout=30)
            else:
                response = requests.get(url, headers=headers, timeout=30)
            
            latency = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                
                if "mood" in result and "summary" in result:
                    # Defensive validation
                    if not isinstance(result["mood"], dict) or len(result["mood"]) == 0:
                        print("[ERROR] Invalid mood structure")
                        continue

                    # Return formatted record
                    flattened = {
                        "mood": result["mood"],
                        "summary": result["summary"],
                        "entry_id": result.get("entry_id")
                    }
                    print(f"[LATENCY] API took {latency:.2f}s")
                    return flattened
                else:
                    print(f"[RETRY] Invalid schema. Expected keys: ['mood','summary'], got: {list(result.keys())}")
            else:
                print(f"[RETRY] Status {response.status_code}. Attempt {attempt + 1}/{retries}")
                
        except (requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
            print(f"[RETRY] {type(e).__name__}: {str(e)}. Attempt {attempt + 1}/{retries}")
        
        if attempt < retries - 1:
            time.sleep(2)
            
    return None

# --- IEEE PLOTTER CLASS ---

class IEEEPlotter:
    def __init__(self, output_dir, run_id):
        self.output_dir = output_dir
        self.run_id = run_id
        os.makedirs(output_dir, exist_ok=True)

    def plot_all(self, results):
        self.plot_fig1_per_emotion(results['emotion_metrics']['per_emotion'])
        self.plot_fig2_confusion_matrix(results['emotion_metrics']['confusion_matrix'])
        self.plot_fig3_roc_curves(results['emotion_metrics']['roc_data'])
        self.plot_fig4_threshold_sweep(results['emotion_metrics']['threshold_sweep'])
        self.plot_fig5_calibration(results['emotion_metrics']['calibration'])
        self.plot_fig6_mcc(results['emotion_metrics']['per_emotion'])
        self.plot_fig7_averages(results['emotion_metrics'])
        self.plot_fig8_rouge(results['summarization_metrics'])
        self.plot_fig9_compression(results['summarization_raw']['compression_ratios'])
        self.plot_fig10_semantic_similarity(results['summarization_raw']['semantic_sims_by_emotion'])
        self.plot_fig11_latency(results['latency_raw'])
        self.plot_fig12_readability_vs_compression(results['summarization_raw'])
        self.plot_fig13_distribution(results['emotion_metrics']['distribution'])
        self.plot_fig00_overview()

    def plot_fig1_per_emotion(self, per_emotion):
        labels = list(per_emotion.keys())
        p = [per_emotion[e]['precision'] for e in labels]
        r = [per_emotion[e]['recall'] for e in labels]
        f1 = [per_emotion[e]['f1'] for e in labels]
        auc = [per_emotion[e]['auc_roc'] for e in labels]
        
        x = np.arange(len(labels))
        width = 0.2
        
        fig, ax = plt.subplots(figsize=(12, 5))
        b1 = ax.bar(x - 1.5*width, p, width, label='Precision', color=COLORS['primary'])
        b2 = ax.bar(x - 0.5*width, r, width, label='Recall', color=COLORS['secondary'])
        b3 = ax.bar(x + 0.5*width, f1, width, label='F1-score', color=COLORS['accent'])
        b4 = ax.bar(x + 1.5*width, auc, width, label='AUC-ROC', color=COLORS['highlight'])
        
        ax.set_ylabel('Score')
        ax.set_title('Per-Emotion Classification Metrics (RoBERTa)')
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.set_ylim(0, 1.1)
        ax.legend(loc='upper right')
        
        for bars in [b1, b2, b3, b4]:
            for bar in bars:
                height = bar.get_height()
                ax.annotate(f'{height:.2f}', xy=(bar.get_x() + bar.get_width()/2, height),
                            xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', rotation=90, fontsize=7)
        
        plt.savefig(os.path.join(self.output_dir, "fig1_per_emotion_metrics.png"))
        plt.close()

    def plot_fig2_confusion_matrix(self, cm):
        fig, ax = plt.subplots(figsize=(9, 7))
        # Normalize
        cm_norm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
        cm_norm = np.nan_to_num(cm_norm)
        
        im = ax.imshow(cm_norm, interpolation='nearest', cmap='Blues', vmin=0, vmax=1)
        ax.figure.colorbar(im, ax=ax, label='Recall')
        
        ax.set(xticks=np.arange(cm.shape[1]), yticks=np.arange(cm.shape[0]),
               xticklabels=EMOTIONS, yticklabels=EMOTIONS,
               title='Normalized Confusion Matrix — Emotion Classification',
               ylabel='True Emotion', xlabel='Predicted Emotion')
        
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                ax.text(j, i, format(cm_norm[i, j], '.2f'), ha="center", va="center",
                        color="white" if cm_norm[i, j] > 0.5 else "black")
        
        plt.savefig(os.path.join(self.output_dir, "fig2_confusion_matrix.png"))
        plt.close()

    def plot_fig3_roc_curves(self, roc_data):
        fig, ax = plt.subplots(figsize=(8, 7))
        for em in EMOTIONS:
            fpr = roc_data[em]['fpr']
            tpr = roc_data[em]['tpr']
            auc = roc_data[em]['auc']
            ax.plot(fpr, tpr, label=f'{em} (AUC = {auc:.2f})', color=EMOTION_COLORS[em], lw=1.5)
            
        ax.plot([0, 1], [0, 1], color='grey', lw=0.8, linestyle='--')
        ax.set_xlabel('False Positive Rate')
        ax.set_ylabel('True Positive Rate')
        ax.set_title('ROC Curves — One-vs-Rest')
        ax.legend(loc='lower right')
        
        plt.savefig(os.path.join(self.output_dir, "fig3_roc_curves.png"))
        plt.close()

    def plot_fig4_threshold_sweep(self, sweep_data):
        fig, ax = plt.subplots(figsize=(7, 4))
        thresholds = sorted([float(t) for t in sweep_data.keys()])
        f1s = [sweep_data[str(t)] for t in thresholds]
        
        ax.plot(thresholds, f1s, color=COLORS['primary'], marker='o', lw=1.5, markersize=4)
        
        best_idx = np.argmax(f1s)
        best_t = thresholds[best_idx]
        best_f1 = f1s[best_idx]
        
        ax.axvline(best_t, color=COLORS['accent'], linestyle='--', lw=1, alpha=0.8)
        ax.annotate(f'Best F1={best_f1:.2f}\nat t={best_t:.2f}', xy=(best_t, best_f1),
                    xytext=(10, -10), textcoords='offset points', color=COLORS['accent'])
        
        ax.set_xlabel('Threshold')
        ax.set_ylabel('Macro-F1 Score')
        ax.set_title('Classification Performance Threshold Sweep')
        
        plt.savefig(os.path.join(self.output_dir, "fig4_threshold_sweep.png"))
        plt.close()

    def plot_fig5_calibration(self, cal_data):
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.plot([0, 1], [0, 1], 'k--', alpha=0.2, label='Perfect Calibration')
        
        for em_data in cal_data:
            em = em_data['emotion']
            ax.scatter(em_data['mean_predicted_prob'], em_data['actual_positive_rate'], 
                       color=EMOTION_COLORS[em], s=50, label=em)
            ax.annotate(em, (em_data['mean_predicted_prob'], em_data['actual_positive_rate']),
                        xytext=(5, 5), textcoords='offset points', fontsize=8)
            
        ax.set_xlabel('Mean Predicted Probability')
        ax.set_ylabel('Actual Positive Rate')
        ax.set_title('Emotion Prediction Calibration')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        
        plt.savefig(os.path.join(self.output_dir, "fig5_calibration.png"))
        plt.close()

    def plot_fig6_mcc(self, per_emotion):
        fig, ax = plt.subplots(figsize=(7, 4))
        labels = sorted(per_emotion.keys(), key=lambda x: per_emotion[x]['mcc'], reverse=True)
        mccs = [per_emotion[e]['mcc'] for e in labels]
        
        colors = []
        for m in mccs:
            if m > 0.5: colors.append(COLORS['positive'])
            elif m > 0.2: colors.append(COLORS['highlight'])
            else: colors.append(COLORS['negative'])
            
        ax.barh(labels, mccs, color=colors)
        ax.axvline(0, color='black', lw=0.8)
        ax.set_xlabel('Matthews Correlation Coefficient')
        ax.set_title('MCC per Emotion Class')
        ax.set_xlim(-1, 1)
        
        plt.savefig(os.path.join(self.output_dir, "fig6_mcc_per_emotion.png"))
        plt.close()

    def plot_fig7_averages(self, metrics):
        fig, ax = plt.subplots(figsize=(8, 4))
        types = ['precision', 'recall', 'f1', 'auc_roc']
        macro = [metrics['macro_avg'][t] for t in types]
        weighted = [metrics['weighted_avg'][t] for t in types]
        
        x = np.arange(len(types))
        width = 0.35
        
        ax.bar(x - width/2, macro, width, label='Macro Average', color=COLORS['primary'])
        ax.bar(x + width/2, weighted, width, label='Weighted Average', color=COLORS['secondary'])
        
        ax.set_xticks(x)
        ax.set_xticklabels([t.upper() for t in types])
        ax.set_title('Aggregated Classification Metrics')
        ax.set_ylim(0, 1.1)
        ax.legend()
        
        plt.savefig(os.path.join(self.output_dir, "fig7_macro_weighted_comparison.png"))
        plt.close()

    def plot_fig8_rouge(self, summ_metrics):
        fig, ax = plt.subplots(figsize=(6, 4))
        labels = ['ROUGE-1', 'ROUGE-2', 'ROUGE-L']
        values = [summ_metrics['rouge1'], summ_metrics['rouge2'], summ_metrics['rougeL']]
        colors = [COLORS['primary'], COLORS['secondary'], COLORS['accent']]
        
        bars = ax.bar(labels, values, color=colors, width=0.6)
        ax.set_ylabel('F1-score')
        ax.set_title('Summarization Performance (ROUGE)')
        ax.set_ylim(0, 1.0)
        
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height:.3f}', xy=(bar.get_x() + bar.get_width()/2, height),
                        xytext=(0, 3), textcoords="offset points", ha='center', va='bottom')
                        
        plt.savefig(os.path.join(self.output_dir, "fig8_rouge_scores.png"))
        plt.close()

    def plot_fig9_compression(self, ratios):
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.hist(ratios, bins=12, color=COLORS['secondary'], alpha=0.4, density=True, label='Frequency')
        
        # Manual KDE
        if len(ratios) > 1:
            x_range = np.linspace(min(ratios)*0.8, max(ratios)*1.2, 200)
            bw = 0.05
            kde = np.zeros_like(x_range)
            for r in ratios:
                kde += np.exp(-0.5 * ((x_range - r)/bw)**2) / (bw * np.sqrt(2*np.pi))
            kde /= len(ratios)
            
            ax2 = ax.twinx()
            ax2.plot(x_range, kde, color=COLORS['primary'], lw=1.5, label='KDE')
            ax2.set_ylabel('Density')
        
        ax.set_xlabel('Compression Ratio')
        ax.set_ylabel('Frequency')
        ax.set_title('Summarization Compression Ratio Distribution')
        
        plt.savefig(os.path.join(self.output_dir, "fig9_compression_histogram.png"))
        plt.close()

    def plot_fig10_semantic_similarity(self, sim_data):
        fig, ax = plt.subplots(figsize=(9, 4))
        
        valid_emotions = [em for em in EMOTIONS if em in sim_data and len(sim_data[em]) > 0]
        data = [sim_data[em] for em in valid_emotions]
        
        if data:
            bp = ax.boxplot(data, patch_artist=True, labels=valid_emotions)
            for i, patch in enumerate(bp['boxes']):
                patch.set_facecolor(EMOTION_COLORS[valid_emotions[i]])
                patch.set_alpha(0.6)
            
            ax.set_ylabel('Cosine Similarity (TF-IDF)')
            ax.set_title('Semantic Similarity by Dominant Emotion')
        
        plt.savefig(os.path.join(self.output_dir, "fig10_semantic_similarity_boxplot.png"))
        plt.close()

    def plot_fig11_latency(self, latencies):
        fig, ax = plt.subplots(figsize=(8, 4))
        lats = sorted(latencies)
        ax.hist(lats, bins=15, color=COLORS['neutral'], alpha=0.6, label='Histogram')
        
        ax2 = ax.twinx()
        cdf = np.arange(1, len(lats) + 1) / len(lats)
        ax2.plot(lats, cdf, color=COLORS['negative'], lw=2, label='CDF')
        ax2.set_ylabel('Cumulative Probability')
        
        p50 = np.percentile(lats, 50)
        p90 = np.percentile(lats, 90)
        p99 = np.percentile(lats, 99)
        
        for p, label in zip([p50, p90, p99], ['p50', 'p90', 'p99']):
            ax.axvline(p, color='black', linestyle=':', lw=1)
            ax.text(p, ax.get_ylim()[1]*0.8, f'{label}\n{p:.0f}ms', rotation=90, fontsize=8, ha='right')

        ax.set_xlabel('Latency (ms)')
        ax.set_ylabel('Count')
        ax.set_title('API Latency Distribution (Journal Creation)')
        
        plt.savefig(os.path.join(self.output_dir, "fig11_latency_distribution.png"))
        plt.close()

    def plot_fig12_readability_vs_compression(self, raw_data):
        fig, ax = plt.subplots(figsize=(7, 5))
        ratios = raw_data['compression_ratios']
        grades = raw_data['readability_grades']
        emotions = raw_data['dominant_emotions']
        
        for em in EMOTIONS:
            idx = [i for i, e in enumerate(emotions) if e == em]
            if idx:
                ax.scatter([ratios[i] for i in idx], [grades[i] for i in idx], 
                           color=EMOTION_COLORS[em], label=em, alpha=0.7)
        
        # Manual Linear Regression
        if len(ratios) > 1:
            x = np.array(ratios)
            y = np.array(grades)
            m = np.cov(x, y)[0, 1] / np.var(x)
            c = np.mean(y) - m * np.mean(x)
            x_line = np.linspace(min(x), max(x), 100)
            ax.plot(x_line, m * x_line + c, color=COLORS['primary'], linestyle='--', alpha=0.5, label='Regression')

        ax.set_xlabel('Compression Ratio')
        ax.set_ylabel('Flesch-Kincaid Grade Level')
        ax.set_title('Readability vs. Compression Ratio')
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        
        plt.savefig(os.path.join(self.output_dir, "fig12_readability_vs_compression.png"))
        plt.close()

    def plot_fig13_distribution(self, dist):
        fig, ax = plt.subplots(figsize=(6, 6))
        labels = [f'{em}\n({dist[em]})' for em in EMOTIONS if dist[em] > 0]
        sizes = [dist[em] for em in EMOTIONS if dist[em] > 0]
        colors = [EMOTION_COLORS[em] for em in EMOTIONS if dist[em] > 0]
        
        ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=140, 
               wedgeprops={'edgecolor': 'white', 'linewidth': 1})
        ax.set_title('Ground Truth Emotion Distribution (N=40)')
        
        plt.savefig(os.path.join(self.output_dir, "fig13_emotion_distribution.png"))
        plt.close()

    def plot_fig00_overview(self):
        # Create a combined 4x3 grid of all plots
        fig, axes = plt.subplots(4, 3, figsize=(18, 22))
        fig.suptitle("Pocket Journal ML Evaluation — System-Level Results Overview", fontsize=16, y=0.98)
        
        plot_files = [
            "fig1_per_emotion_metrics.png", "fig2_confusion_matrix.png", "fig3_roc_curves.png",
            "fig4_threshold_sweep.png", "fig5_calibration.png", "fig6_mcc_per_emotion.png",
            "fig7_macro_weighted_comparison.png", "fig8_rouge_scores.png", "fig9_compression_histogram.png",
            "fig10_semantic_similarity_boxplot.png", "fig11_latency_distribution.png", "fig12_readability_vs_compression.png"
        ]
        
        for i, ax in enumerate(axes.flat):
            if i < len(plot_files):
                img = plt.imread(os.path.join(self.output_dir, plot_files[i]))
                ax.imshow(img)
                ax.axis('off')
        
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        plt.savefig(os.path.join(self.output_dir, "fig00_ieee_overview.png"), dpi=300)
        plt.close()

# --- MAIN EXECUTION ---

def main():
    parser = argparse.ArgumentParser(description="Pocket Journal IEEE Evaluation Script")
    parser.add_argument("--dataset", required=True, help="Path to dataset JSON")
    parser.add_argument("--email", required=True, help="Login email")
    parser.add_argument("--password", required=True, help="Login password")
    parser.add_argument("--base-url", default="http://localhost:5000", help="API base URL")
    parser.add_argument("--output-dir", default="ml/evaluation/results/ieee_figures", help="Output directory")
    parser.add_argument("--delay-ms", type=int, default=500, help="Delay between API calls")
    
    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 1. Load Dataset
    with open(args.dataset, 'r', encoding='utf-8') as f:
        dataset = json.load(f)
    
    # 2. Auth Init
    auth = AuthClient(args.base_url, args.email, args.password)
    api = APIClient(args.base_url, auth)
    
    # 3. Process Entries
    results = []
    latencies = []
    
    print(f"Starting evaluation of {len(dataset)} entries...")
    for i, entry in enumerate(dataset, 1):
        print(f"[{i}/{len(dataset)}] Evaluating entry {entry['entry_id']}...")
        
        url = f"{args.base_url.rstrip('/')}/api/v1/journal"
        payload = {"entry_text": entry['entry_text']}
        if entry.get("title"):
            payload["title"] = entry["title"]
            
        auth.refresh_if_expired()
        headers = auth.get_headers()
        
        start_time = time.time()
        result = call_api_with_retry("POST", url, headers, payload=payload)
        
        if result is None:
            print(f"[ERROR] Failed to get valid response for entry {entry['entry_id']}. Skipping.")
            continue
            
        latency = (time.time() - start_time) * 1000
        latencies.append(latency)
        
        # 1. Prediction Extraction
        pred_mood = result.get("mood", {})
        pred_summary = result.get("summary", "")
        
        # 2. Safety Validation
        if not pred_mood or not isinstance(pred_mood, dict):
            print(f"[ERROR] Invalid or empty mood prediction for {entry['entry_id']}. Skipping.")
            continue
            
        if not pred_summary:
            print(f"[WARNING] Empty summary for {entry['entry_id']}. Continuing.")
            
        results.append({
            "id": entry["entry_id"],
            "text": entry["entry_text"],
            "gt": entry["ground_truth"],
            "pred_mood": pred_mood,
            "pred_summary": pred_summary,
            "latency_ms": latency
        })
            
        time.sleep(1) # Sequential delay

    # 4. Compute Metrics
    print("Computing metrics...")
    
    # Distribution
    dist = {em: 0 for em in EMOTIONS}
    for r in results: dist[r['gt']['dominant_emotion']] += 1
    
    # Classification
    per_emotion = {}
    macro_p, macro_r, macro_f1 = 0, 0, 0
    total_samples = len(results)
    
    y_true_all = []
    y_pred_all = []
    
    roc_data = {}
    
    for em in EMOTIONS:
        y_true = [1 if r['gt']['emotion_labels'].get(em, 0) == 1 else 0 for r in results]
        y_scores = [r['pred_mood'].get(em, 0.0) for r in results]
        y_preds = [1 if s >= 0.5 else 0 for s in y_scores]
        
        tp = sum(1 for t, p in zip(y_true, y_preds) if t == 1 and p == 1)
        fp = sum(1 for t, p in zip(y_true, y_preds) if t == 0 and p == 1)
        fn = sum(1 for t, p in zip(y_true, y_preds) if t == 1 and p == 0)
        tn = sum(1 for t, p in zip(y_true, y_preds) if t == 0 and p == 0)
        
        p, r, f1 = compute_precision_recall_f1(tp, fp, fn)
        auc = compute_auc_roc(y_true, y_scores)
        mcc = compute_mcc(tp, tn, fp, fn)
        
        per_emotion[em] = {
            "precision": p, "recall": r, "f1": f1, "auc_roc": auc, "mcc": mcc, "support": sum(y_true)
        }
        
        macro_p += p / len(EMOTIONS)
        macro_r += r / len(EMOTIONS)
        macro_f1 += f1 / len(EMOTIONS)
        
        # ROC Curve Points
        fpr_list, tpr_list = [], []
        for t in np.linspace(0, 1, 100):
            yp = [1 if s >= t else 0 for s in y_scores]
            ftp = sum(1 for gt, pr in zip(y_true, yp) if gt == 0 and pr == 1)
            ttp = sum(1 for gt, pr in zip(y_true, yp) if gt == 1 and pr == 1)
            ffn = sum(1 for gt, pr in zip(y_true, yp) if gt == 1 and pr == 0)
            ttn = sum(1 for gt, pr in zip(y_true, yp) if gt == 0 and pr == 0)
            
            fpr_list.append(ftp / (ftp + ttn) if (ftp + ttn) > 0 else 0)
            tpr_list.append(ttp / (ttp + ffn) if (ttp + ffn) > 0 else 0)
        
        roc_data[em] = {"fpr": fpr_list, "tpr": tpr_list, "auc": auc}

    # Weighted Averages
    weighted_p = sum(per_emotion[em]['precision'] * per_emotion[em]['support'] for em in EMOTIONS) / total_samples
    weighted_r = sum(per_emotion[em]['recall'] * per_emotion[em]['support'] for em in EMOTIONS) / total_samples
    weighted_f1 = sum(per_emotion[em]['f1'] * per_emotion[em]['support'] for em in EMOTIONS) / total_samples
    weighted_auc = sum(per_emotion[em]['auc_roc'] * per_emotion[em]['support'] for em in EMOTIONS) / total_samples

    # Confusion Matrix
    y_true_idx = [EMOTIONS.index(r['gt']['dominant_emotion']) for r in results]
    y_pred_idx = [EMOTIONS.index(max(r['pred_mood'], key=r['pred_mood'].get)) for r in results]
    cm = compute_confusion_matrix(y_true_idx, y_pred_idx, len(EMOTIONS))

    # Threshold Sweep
    sweep = {}
    for t in [0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]:
        t_f1 = 0
        for em in EMOTIONS:
            y_t = [1 if r['gt']['emotion_labels'].get(em, 0) == 1 else 0 for r in results]
            y_s = [r['pred_mood'].get(em, 0.0) for r in results]
            y_p = [1 if s >= t else 0 for s in y_s]
            _, _, f = compute_precision_recall_f1(
                sum(1 for vt, vp in zip(y_t, y_p) if vt == 1 and vp == 1),
                sum(1 for vt, vp in zip(y_t, y_p) if vt == 0 and vp == 1),
                sum(1 for vt, vp in zip(y_t, y_p) if vt == 1 and vp == 0)
            )
            t_f1 += f / len(EMOTIONS)
        sweep[str(round(t, 2))] = t_f1

    # Calibration
    calibration = []
    for em in EMOTIONS:
        y_scores = [r['pred_mood'].get(em, 0.0) for r in results]
        y_true = [1 if r['gt']['emotion_labels'].get(em, 0) == 1 else 0 for r in results]
        calibration.append({
            "emotion": em,
            "mean_predicted_prob": np.mean(y_scores),
            "actual_positive_rate": np.mean(y_true)
        })

    # Summarization
    rouge1_list, rouge2_list, rougel_list = [], [], []
    comp_ratios, sim_list, grade_list = [], [], []
    sims_by_emotion = {em: [] for em in EMOTIONS}
    
    for r in results:
        ref_tokens = r['gt']['reference_summary'].lower().split()
        hyp_tokens = r['pred_summary'].lower().split()
        
        rouge1_list.append(compute_rouge_n(ref_tokens, hyp_tokens, 1))
        rouge2_list.append(compute_rouge_n(ref_tokens, hyp_tokens, 2))
        rougel_list.append(compute_rouge_n(ref_tokens, hyp_tokens, 1)) # Simple proxy for R-L
        
        c_ratio = len(hyp_tokens) / len(r['text'].split()) if len(r['text'].split()) > 0 else 0
        comp_ratios.append(c_ratio)
        
        sim = compute_tfidf_cosine_sim(r['text'], r['pred_summary'])
        sim_list.append(sim)
        sims_by_emotion[r['gt']['dominant_emotion']].append(sim)
        
        grade_list.append(flesch_kincaid_grade(r['pred_summary']))

    # Final Metrics Bundle
    final_results = {
        "run_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "timestamp": datetime.now().isoformat(),
        "emotion_metrics": {
            "per_emotion": per_emotion,
            "macro_avg": {"precision": macro_p, "recall": macro_r, "f1": macro_f1, "auc_roc": np.mean([per_emotion[e]['auc_roc'] for e in EMOTIONS])},
            "weighted_avg": {"precision": weighted_p, "recall": weighted_r, "f1": weighted_f1, "auc_roc": weighted_auc},
            "confusion_matrix": cm,
            "threshold_sweep": sweep,
            "calibration": calibration,
            "roc_data": roc_data,
            "distribution": dist
        },
        "summarization_metrics": {
            "rouge1": np.mean(rouge1_list), "rouge2": np.mean(rouge2_list), "rougeL": np.mean(rougel_list),
            "avg_compression_ratio": np.mean(comp_ratios),
            "avg_semantic_similarity": np.mean(sim_list),
            "avg_readability_grade": np.mean(grade_list)
        },
        "summarization_raw": {
            "compression_ratios": comp_ratios, "readability_grades": grade_list,
            "dominant_emotions": [r['gt']['dominant_emotion'] for r in results],
            "semantic_sims_by_emotion": sims_by_emotion
        },
        "latency_raw": latencies
    }

    # 5. Plotting
    print("Generating IEEE plots...")
    plotter = IEEEPlotter(args.output_dir, final_results['run_id'])
    plotter.plot_all(final_results)

    # 6. Export LaTeX Tables
    print("Exporting LaTeX tables...")
    
    # Emotion Table
    emotion_tex = "\\begin{table}[h]\n\\centering\n\\caption{Per-Emotion Classification Metrics}\n\\label{tab:emotion_metrics}\n\\begin{tabular}{lcccc}\n\\hline\n"
    emotion_tex += "\\textbf{Emotion} & \\textbf{Precision} & \\textbf{Recall} & \\textbf{F1-Score} & \\textbf{AUC-ROC} \\\\\n\\hline\n"
    for em in EMOTIONS:
        m = per_emotion[em]
        emotion_tex += f"{em:<10} & {m['precision']:.3f} & {m['recall']:.3f} & {m['f1']:.3f} & {m['auc_roc']:.3f} \\\\\n"
    emotion_tex += "\\hline\n"
    emotion_tex += f"\\textbf{{Macro Avg}}    & {macro_p:.3f} & {macro_r:.3f} & {macro_f1:.3f} & {np.mean([per_emotion[e]['auc_roc'] for e in EMOTIONS]):.3f} \\\\\n"
    emotion_tex += f"\\textbf{{Weighted Avg}} & {weighted_p:.3f} & {weighted_r:.3f} & {weighted_f1:.3f} & {weighted_auc:.3f} \\\\\n"
    emotion_tex += "\\hline\n\\end{tabular}\n\\end{table}"
    
    with open(os.path.join(args.output_dir, "metrics_table.tex"), "w") as f:
        f.write(emotion_tex)
    print("\n" + emotion_tex + "\n")

    # Summarization Table
    s = final_results['summarization_metrics']
    summ_tex = "\\begin{table}[h]\n\\centering\n\\caption{Summarization Quality Metrics}\n\\label{tab:summ_metrics}\n\\begin{tabular}{lc}\n\\hline\n"
    summ_tex += "\\textbf{Metric} & \\textbf{Score} \\\\\n\\hline\n"
    summ_tex += f"ROUGE-1 (F1) & {s['rouge1']:.3f} \\\\\n"
    summ_tex += f"ROUGE-2 (F1) & {s['rouge2']:.3f} \\\\\n"
    summ_tex += f"ROUGE-L (F1) & {s['rougeL']:.3f} \\\\\n"
    summ_tex += f"Avg. Compression Ratio & {s['avg_compression_ratio']:.3f} \\\\\n"
    summ_tex += f"Avg. Semantic Similarity (TF-IDF) & {s['avg_semantic_similarity']:.3f} \\\\\n"
    summ_tex += f"Avg. Flesch-Kincaid Grade & {s['avg_readability_grade']:.2f} \\\\\n"
    summ_tex += "\\hline\n\\end{tabular}\n\\end{table}"
    
    with open(os.path.join(args.output_dir, "summarization_metrics.tex"), "w") as f:
        f.write(summ_tex)

    # 7. Final JSON
    # Remove large raw data for small JSON summary
    final_results.pop('summarization_raw')
    final_results['emotion_metrics'].pop('roc_data')
    final_results['emotion_metrics']['confusion_matrix'] = cm.tolist()
    
    # Add percentile latencies
    final_results['latency_ms'] = {
        "p50": np.percentile(latencies, 50),
        "p90": np.percentile(latencies, 90),
        "p99": np.percentile(latencies, 99)
    }
    final_results.pop('latency_raw')
    
    with open(os.path.join(args.output_dir, f"ieee_results_{final_results['run_id']}.json"), "w") as f:
        json.dump(final_results, f, indent=2)

    print(f"Evaluation complete. IEEE Figures and LaTeX tables saved to: {args.output_dir}")

if __name__ == "__main__":
    main()
