"""Model Training and Evaluation Pipeline for Predictive Maintenance.

Trains baseline models (Logistic Regression vs. Random Forest) on balanced-class features,
evaluates precision, recall, F1, and ROC-AUC on unseen test aircraft, ranks feature importances,
and serializes the winning model and metadata to disk.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Dict, Tuple
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from config.settings import (
    METADATA_PATH,
    MODEL_PATH,
    MODELS_DIR,
    PROCESSED_DATA_DIR,
    RANDOM_SEED,
)
from src.ml.preprocessor import FEATURE_COLUMNS, TARGET_COLUMN


def load_processed_splits() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load train and test feature splits from disk."""
    train_path = PROCESSED_DATA_DIR / "train_features.csv"
    test_path = PROCESSED_DATA_DIR / "test_features.csv"

    if not train_path.exists() or not test_path.exists():
        from src.ml.preprocessor import run_preprocessing_pipeline
        return run_preprocessing_pipeline()

    train_df = pd.read_csv(train_path)
    test_df = pd.read_csv(test_path)
    return train_df, test_df


def train_and_evaluate_models() -> Dict:
    """Train candidate models, select best performer, and save artifacts."""
    train_df, test_df = load_processed_splits()

    X_train = train_df[FEATURE_COLUMNS]
    y_train = train_df[TARGET_COLUMN]

    X_test = test_df[FEATURE_COLUMNS]
    y_test = test_df[TARGET_COLUMN]

    print(f"Training on {len(X_train)} samples ({y_train.sum()} positive)")
    print(f"Testing on {len(X_test)} samples ({y_test.sum()} positive)")

    # 1. Candidate 1: Logistic Regression (with Scaler)
    lr_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", LogisticRegression(class_weight="balanced", max_iter=1000, random_state=RANDOM_SEED))
    ])
    lr_pipeline.fit(X_train, y_train)
    lr_probs = lr_pipeline.predict_proba(X_test)[:, 1]
    lr_preds = (lr_probs >= 0.5).astype(int)

    lr_f1 = f1_score(y_test, lr_preds, zero_division=0)
    lr_auc = roc_auc_score(y_test, lr_probs) if len(np.unique(y_test)) > 1 else 0.5
    print(f"Logistic Regression -> Test F1: {lr_f1:.3f}, ROC-AUC: {lr_auc:.3f}")

    # 2. Candidate 2: Random Forest Classifier
    rf_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=6,
        min_samples_split=4,
        class_weight="balanced",
        random_state=RANDOM_SEED,
        n_jobs=-1,
    )
    rf_model.fit(X_train, y_train)
    rf_probs = rf_model.predict_proba(X_test)[:, 1]
    rf_preds = (rf_probs >= 0.5).astype(int)

    rf_precision = precision_score(y_test, rf_preds, zero_division=0)
    rf_recall = recall_score(y_test, rf_preds, zero_division=0)
    rf_f1 = f1_score(y_test, rf_preds, zero_division=0)
    rf_auc = roc_auc_score(y_test, rf_probs) if len(np.unique(y_test)) > 1 else 0.5
    rf_acc = accuracy_score(y_test, rf_preds)
    cm = confusion_matrix(y_test, rf_preds).tolist()

    print(f"Random Forest       -> Test Precision: {rf_precision:.3f}, Recall: {rf_recall:.3f}, F1: {rf_f1:.3f}, ROC-AUC: {rf_auc:.3f}")

    # Feature Importance ranking
    importances = rf_model.feature_importances_
    feature_ranking = [
        {"feature": feat, "importance": round(float(imp), 4)}
        for feat, imp in sorted(zip(FEATURE_COLUMNS, importances), key=lambda x: x[1], reverse=True)
    ]

    # Save Best Model (Random Forest selected for robust non-linear thresholding & feature interactions)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(rf_model, MODEL_PATH)
    print(f"Saved trained Random Forest model to: {MODEL_PATH}")

    metadata = {
        "model_name": "RandomForestClassifier",
        "trained_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "random_seed": RANDOM_SEED,
        "hyperparameters": {
            "n_estimators": 100,
            "max_depth": 6,
            "min_samples_split": 4,
            "class_weight": "balanced",
        },
        "dataset_summary": {
            "train_samples": len(train_df),
            "train_aircraft_count": int(train_df["aircraft_id"].nunique()),
            "train_positive_rate": round(float(y_train.mean()), 4),
            "test_samples": len(test_df),
            "test_aircraft_count": int(test_df["aircraft_id"].nunique()),
            "test_positive_rate": round(float(y_test.mean()), 4),
        },
        "evaluation_metrics": {
            "accuracy": round(float(rf_acc), 4),
            "precision": round(float(rf_precision), 4),
            "recall": round(float(rf_recall), 4),
            "f1_score": round(float(rf_f1), 4),
            "roc_auc": round(float(rf_auc), 4),
            "confusion_matrix": {
                "tn": cm[0][0] if len(cm) > 0 else 0,
                "fp": cm[0][1] if len(cm) > 0 and len(cm[0]) > 1 else 0,
                "fn": cm[1][0] if len(cm) > 1 else 0,
                "tp": cm[1][1] if len(cm) > 1 and len(cm[1]) > 1 else 0,
            },
        },
        "top_features": feature_ranking[:8],
        "all_feature_importances": feature_ranking,
        "feature_columns": FEATURE_COLUMNS,
    }

    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"Saved evaluation metadata to: {METADATA_PATH}")
    return metadata


if __name__ == "__main__":
    train_and_evaluate_models()
