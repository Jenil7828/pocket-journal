import json
import csv
import os
import logging
from datetime import datetime
from typing import Dict, Any, List
import numpy as np

logger = logging.getLogger()

class ReportGenerator:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def save_json(self, report: Dict[str, Any], filename: str = None) -> str:
        filename = filename or f"evaluation_report_{self.timestamp}.json"
        path = os.path.join(self.output_dir, filename)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        logger.info("Saved JSON report to %s", path)
        return path

    def save_csv(self, roberta_results: Dict[str, Any], filename: str = None) -> str:
        if not roberta_results or "per_emotion" not in roberta_results:
            return ""
            
        filename = filename or f"roberta_metrics_{self.timestamp}.csv"
        path = os.path.join(self.output_dir, filename)
        
        per_emotion = roberta_results["per_emotion"]
        labels = sorted(per_emotion.keys())
        
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Emotion", "Precision", "Recall", "F1", "AUC-ROC"])
            for label in labels:
                m = per_emotion[label]
                writer.writerow([label, m["precision"], m["recall"], m["f1"], m["auc_roc"]])
                
        logger.info("Saved CSV metrics to %s", path)
        return path

    def _normalize_emotion_results(self, roberta_results: Dict[str, Any]) -> Dict[str, Any]:
        """Translate evaluator output into the schema expected by IEEEPlotter."""
        normalized = dict(roberta_results or {})
        normalized.setdefault("per_emotion", {})
        normalized.setdefault("roc_data", {})
        normalized.setdefault("distribution", normalized.get("class_distribution", {}))
        normalized.setdefault("confusion_matrix", normalized.get("confusion", []))
        normalized.setdefault("raw", {})
        normalized.setdefault("latency_raw", [])
        return normalized

    def _normalize_summarization_results(self, bart_results: Dict[str, Any]) -> Dict[str, Any]:
        """Translate summarization output into the schema expected by IEEEPlotter."""
        normalized = dict(bart_results or {})
        normalized.setdefault("raw", {})
        return normalized

    def generate_plots(self, roberta_results: Dict[str, Any], bart_results: Dict[str, Any]):
        """Delegates to IEEEPlotter for 300-DPI publication-quality plots."""
        from ml.evaluation.ieee_evaluation import IEEEPlotter
        plotter = IEEEPlotter(self.output_dir, self.timestamp)

        emotion_metrics = self._normalize_emotion_results(roberta_results)
        summarization_metrics = self._normalize_summarization_results(bart_results)

        # Format results to match IEEEPlotter expected schema
        combined_results = {
            "emotion_metrics": emotion_metrics,
            "summarization_metrics": summarization_metrics,
            "summarization_raw": summarization_metrics["raw"],
            "latency_raw": emotion_metrics["latency_raw"],
            "run_id": self.timestamp
        }
        return plotter.plot_all(combined_results)

    def save_latex_table(self, report: Dict[str, Any]) -> List[str]:
        """Save LaTeX tables for the evaluation report."""
        output_paths = []
        
        # 1. Emotion Table
        if "emotion_metrics" in report:
            em_metrics = report["emotion_metrics"]
            per_emotion = em_metrics.get("per_emotion", {})
            emotions = sorted(per_emotion.keys())
            
            tex = "\\begin{table}[h]\n\\centering\n\\caption{Per-Emotion Classification Metrics}\n\\label{tab:emotion_metrics}\n\\begin{tabular}{lcccc}\n\\hline\n"
            tex += "\\textbf{Emotion} & \\textbf{Precision} & \\textbf{Recall} & \\textbf{F1-Score} & \\textbf{AUC-ROC} \\\\\n\\hline\n"
            for em in emotions:
                m = per_emotion[em]
                tex += f"{em:<10} & {m['precision']:.3f} & {m['recall']:.3f} & {m['f1']:.3f} & {m['auc_roc']:.3f} \\\\\n"
            
            tex += "\\hline\n"
            macro = em_metrics.get("macro_avg", {})
            weighted = em_metrics.get("weighted_avg", {})
            tex += f"\\textbf{{Macro Avg}}    & {macro.get('precision', 0):.3f} & {macro.get('recall', 0):.3f} & {macro.get('f1', 0):.3f} & {macro.get('auc_roc', 0):.3f} \\\\\n"
            tex += f"\\textbf{{Weighted Avg}} & {weighted.get('precision', 0):.3f} & {weighted.get('recall', 0):.3f} & {weighted.get('f1', 0):.3f} & {weighted.get('auc_roc', 0):.3f} \\\\\n"
            tex += "\\hline\n\\end{tabular}\n\\end{table}"
            
            path = os.path.join(self.output_dir, f"metrics_table_{self.timestamp}.tex")
            with open(path, 'w') as f:
                f.write(tex)
            output_paths.append(path)

        # 2. Summarization Table
        if "summarization_metrics" in report:
            s = report["summarization_metrics"]
            tex = "\\begin{table}[h]\n\\centering\n\\caption{Summarization Quality Metrics}\n\\label{tab:summ_metrics}\n\\begin{tabular}{lc}\n\\hline\n"
            tex += "\\textbf{Metric} & \\textbf{Score} \\\\\n\\hline\n"
            tex += f"ROUGE-1 (F1) & {s.get('rouge1', 0):.3f} \\\\\n"
            tex += f"ROUGE-2 (F1) & {s.get('rouge2', 0):.3f} \\\\\n"
            tex += f"ROUGE-L (F1) & {s.get('rougeL', 0):.3f} \\\\\n"
            tex += f"Avg. Compression Ratio & {s.get('avg_compression_ratio', 0):.3f} \\\\\n"
            tex += f"Avg. Semantic Similarity & {s.get('avg_semantic_similarity', 0):.3f} \\\\\n"
            tex += f"Avg. Readability Grade & {s.get('avg_readability_grade', 0):.2f} \\\\\n"
            tex += "\\hline\n\\end{tabular}\n\\end{table}"
            
            path = os.path.join(self.output_dir, f"summarization_metrics_{self.timestamp}.tex")
            with open(path, 'w') as f:
                f.write(tex)
            output_paths.append(path)
            
        return output_paths
