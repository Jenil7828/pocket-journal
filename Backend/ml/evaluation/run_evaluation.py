import argparse
import logging
import os
import sys
from datetime import datetime

# Ensure Backend is in path
_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(os.path.dirname(_HERE))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from config_loader import get_config
from ml.utils.model_loader import resolve_model_path
from persistence.db_manager import DBManager
from services.embeddings.embedding_service import get_embedding_service

from ml.evaluation.data.data_loader import DataLoader
from ml.evaluation.evaluators.roberta_evaluator import RobertaEvaluator
from ml.evaluation.evaluators.bart_evaluator import BartEvaluator
from ml.evaluation.evaluators.pipeline_evaluator import PipelineEvaluator
from ml.evaluation.reporting.report_generator import ReportGenerator

# Use root logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

def main():
    parser = argparse.ArgumentParser(description="Pocket Journal ML Evaluation Pipeline")
    parser.add_argument("--task", type=str, default="all", choices=["all", "roberta", "bart", "pipeline"], help="Evaluation task to run")
    parser.add_argument("--data-source", type=str, default="synthetic", choices=["synthetic", "file", "firestore"], help="Data source for evaluation")
    parser.add_argument("--data-path", type=str, help="Path to JSON data file (required for 'file' source)")
    parser.add_argument("--uid", type=str, help="User ID for Firestore data loading")
    parser.add_argument("--output-dir", type=str, default="ml/evaluation/results", help="Directory to save evaluation results")
    parser.add_argument("--roberta-version", type=str, default=None, help="Version of RoBERTa model to evaluate")
    parser.add_argument("--bart-version", type=str, default=None, help="Version of BART model to evaluate")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    cfg = get_config()
    roberta_v = args.roberta_version or cfg["ml"]["mood_detection"].get("model_version", "v1")
    bart_v = args.bart_version or cfg["ml"]["summarization"].get("model_version", "v1")

    # 1. Load Data
    db_manager = None
    if args.data_source == "firestore":
        if not args.uid:
            logger.error("--uid is required for firestore data source")
            sys.exit(1)
        try:
            db_manager = DBManager()
        except Exception as e:
            logger.warning("Firestore unavailable: %s. Falling back to synthetic data.", str(e))
            args.data_source = "synthetic"

    data_loader = DataLoader(db_manager)
    if args.data_source == "synthetic":
        data = data_loader.load_synthetic_data(num_samples=50)
    elif args.data_source == "file":
        if not args.data_path:
            logger.error("--data-path is required for file data source")
            sys.exit(1)
        data = data_loader.load_from_file(args.data_path)
    else: # firestore
        data = data_loader.load_from_firestore(args.uid)

    if not data:
        logger.error("No data loaded for evaluation. Exiting.")
        sys.exit(1)

    # 2. Initialize Models
    roberta_predictor = None
    bart_predictor = None
    embedding_service = None

    if args.task in ["all", "roberta", "pipeline"]:
        try:
            from ml.inference.mood_detection.roberta.predictor import SentencePredictor
            path = resolve_model_path("mood_detection", "roberta", roberta_v)
            roberta_predictor = SentencePredictor(model_path=path)
        except Exception as e:
            logger.error("Failed to load RoBERTa model: %s", str(e))

    if args.task in ["all", "bart", "pipeline"]:
        try:
            from ml.inference.summarization.bart.predictor import SummarizationPredictor
            path = resolve_model_path("summarization", "bart", bart_v)
            bart_predictor = SummarizationPredictor(model_path=path)
            embedding_service = get_embedding_service()
        except Exception as e:
            logger.error("Failed to load BART model: %s", str(e))

    # 3. Run Evaluation Tasks
    report = {
        "evaluation_timestamp": datetime.now().isoformat(),
        "config": {
            "roberta_version": roberta_v,
            "bart_version": bart_v,
            "data_source": args.data_source,
            "num_samples": len(data)
        }
    }

    roberta_results = {}
    bart_results = {}

    if args.task in ["all", "roberta"] and roberta_predictor:
        logger.info("Running RoBERTa Emotion Detection Evaluation...")
        evaluator = RobertaEvaluator(roberta_predictor)
        roberta_results = evaluator.evaluate(data)
        report["roberta"] = roberta_results
        # Add labels to results for plotting
        roberta_results["labels"] = roberta_predictor.labels

    if args.task in ["all", "bart"] and bart_predictor:
        logger.info("Running BART Summarization Evaluation...")
        evaluator = BartEvaluator(bart_predictor, embedding_service)
        bart_results = evaluator.evaluate(data)
        report["bart"] = bart_results

    if args.task in ["all", "pipeline"] and roberta_predictor and bart_predictor:
        logger.info("Running Combined Pipeline Evaluation...")
        evaluator = PipelineEvaluator(roberta_predictor, bart_predictor)
        report["pipeline"] = evaluator.evaluate(data)

    # 4. Generate and Save Reports
    report_gen = ReportGenerator(args.output_dir)
    
    # Generate plots
    plot_paths = report_gen.generate_plots(roberta_results, bart_results)
    if "roberta" in report and "confusion_matrix_png" in plot_paths:
        report["roberta"]["confusion_matrix_png"] = plot_paths["confusion_matrix_png"]
    if "bart" in report and "histogram_png" in plot_paths:
        report["bart"]["histogram_png"] = plot_paths["histogram_png"]

    # Save JSON and CSV
    json_path = report_gen.save_json(report)
    csv_path = report_gen.save_csv(roberta_results)

    logger.info("Evaluation Complete.")
    logger.info("Results saved to: %s", args.output_dir)
    logger.info("Main report: %s", json_path)

if __name__ == "__main__":
    main()
