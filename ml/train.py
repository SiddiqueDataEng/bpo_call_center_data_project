"""
ML Training Pipeline — BPO Platform
=====================================
Trains per-vertical lead conversion propensity models + a global model.
Outputs:
  ml/models/model_{vertical}.pkl   — scikit-learn pipeline per vertical
  ml/models/model_global.pkl       — global cross-vertical model
  ml/reports/model_report.json     — metrics: AUC-ROC, precision, recall, F1
  ml/reports/feature_importance.csv
  lakehouse/gold/gold_ml_feature_store.parquet — with predicted scores attached
"""

from __future__ import annotations

import json
import pickle
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, classification_report, f1_score,
    precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, OneHotEncoder, StandardScaler

warnings.filterwarnings("ignore")

GOLD_DIR = Path("lakehouse/gold")
MODEL_DIR = Path("ml/models")
REPORT_DIR = Path("ml/reports")
MODEL_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Feature configuration per vertical
# ---------------------------------------------------------------------------

VERTICAL_FEATURES = {
    "Insurance": {
        "numeric": [
            "lead_score", "n_call_attempts", "avg_sentiment_score",
            "ins_household_size", "ins_annual_income",
            "feat_n_calls", "feat_avg_duration", "feat_n_callbacks",
            "feat_max_sentiment", "feat_min_sentiment",
        ],
        "categorical": [
            "state", "ins_product_type", "has_consent",
            "ins_aca_eligible", "ins_tobacco_user",
        ],
    },
    "Healthcare": {
        "numeric": [
            "lead_score", "n_call_attempts", "avg_sentiment_score",
            "feat_n_calls", "feat_avg_duration", "feat_n_callbacks",
            "feat_max_sentiment",
        ],
        "categorical": [
            "state", "hc_specialty", "hc_payer_id", "has_consent",
        ],
    },
    "RealEstate": {
        "numeric": [
            "lead_score", "n_call_attempts", "avg_sentiment_score",
            "re_budget_min", "re_budget_max", "re_timeline_months",
            "feat_n_calls", "feat_avg_duration",
        ],
        "categorical": [
            "state", "re_interest_type", "re_pre_approval", "has_consent",
        ],
    },
    "AR": {
        "numeric": [
            "lead_score", "n_call_attempts", "avg_sentiment_score",
            "ar_original_balance", "ar_current_balance", "ar_account_age_days",
            "feat_n_calls", "feat_avg_duration", "feat_n_dnc_dispositions",
        ],
        "categorical": [
            "state", "ar_debt_type", "ar_sol_expired", "has_consent",
        ],
    },
}

GLOBAL_NUMERIC = [
    "lead_score", "n_call_attempts", "avg_sentiment_score",
    "feat_n_calls", "feat_avg_duration", "feat_n_callbacks",
    "feat_max_sentiment", "feat_min_sentiment",
    "feat_n_dnc_dispositions", "feat_n_no_answers",
]
GLOBAL_CATEGORICAL = ["state", "vertical", "has_consent", "dnc_flagged"]


# ---------------------------------------------------------------------------
# Build sklearn pipeline
# ---------------------------------------------------------------------------

def build_pipeline(numeric_cols: list[str], categorical_cols: list[str],
                   model_type: str = "gbm") -> Pipeline:
    num_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    cat_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="constant", fill_value="unknown")),
        ("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])
    preprocessor = ColumnTransformer([
        ("num", num_transformer, numeric_cols),
        ("cat", cat_transformer, categorical_cols),
    ], remainder="drop")

    if model_type == "gbm":
        clf = GradientBoostingClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.05,
            subsample=0.8, random_state=42,
        )
    elif model_type == "rf":
        clf = RandomForestClassifier(
            n_estimators=150, max_depth=6, random_state=42, n_jobs=-1,
        )
    else:
        clf = LogisticRegression(max_iter=500, random_state=42)

    return Pipeline([("preprocessor", preprocessor), ("classifier", clf)])


# ---------------------------------------------------------------------------
# Evaluate and report
# ---------------------------------------------------------------------------

def evaluate(pipe: Pipeline, X_test: pd.DataFrame,
             y_test: pd.Series, label: str) -> dict:
    y_pred = pipe.predict(X_test)
    y_prob = pipe.predict_proba(X_test)[:, 1]
    metrics = {
        "model": label,
        "n_test": len(y_test),
        "positive_rate": round(float(y_test.mean()), 4),
        "auc_roc": round(roc_auc_score(y_test, y_prob), 4),
        "accuracy": round(accuracy_score(y_test, y_pred), 4),
        "precision": round(precision_score(y_test, y_pred, zero_division=0), 4),
        "recall": round(recall_score(y_test, y_pred, zero_division=0), 4),
        "f1": round(f1_score(y_test, y_pred, zero_division=0), 4),
    }
    print(f"  [{label}] AUC={metrics['auc_roc']}  F1={metrics['f1']}  "
          f"Prec={metrics['precision']}  Rec={metrics['recall']}")
    return metrics


def feature_importances(pipe: Pipeline, numeric_cols: list[str],
                         categorical_cols: list[str]) -> pd.DataFrame:
    clf = pipe.named_steps["classifier"]
    preprocessor = pipe.named_steps["preprocessor"]
    if not hasattr(clf, "feature_importances_"):
        return pd.DataFrame()
    # Get OHE feature names
    ohe = preprocessor.named_transformers_["cat"].named_steps["ohe"]
    cat_feat_names = list(ohe.get_feature_names_out(categorical_cols))
    all_names = numeric_cols + cat_feat_names
    imps = clf.feature_importances_
    n = min(len(all_names), len(imps))
    return pd.DataFrame({
        "feature": all_names[:n],
        "importance": imps[:n],
    }).sort_values("importance", ascending=False)


# ---------------------------------------------------------------------------
# Per-vertical training
# ---------------------------------------------------------------------------

def train_vertical(df: pd.DataFrame, vertical: str) -> dict | None:
    vdf = df[df["vertical"] == vertical].copy()
    if len(vdf) < 40:
        print(f"  [{vertical}] insufficient data ({len(vdf)} rows) — skip")
        return None

    cfg = VERTICAL_FEATURES[vertical]
    num_cols = [c for c in cfg["numeric"] if c in vdf.columns]
    cat_cols = [c for c in cfg["categorical"] if c in vdf.columns]

    # Encode bool-like categoricals as strings
    for c in cat_cols:
        vdf[c] = vdf[c].astype(str)

    X = vdf[num_cols + cat_cols]
    y = vdf["converted"].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=42,
    )
    pipe = build_pipeline(num_cols, cat_cols, model_type="gbm")
    pipe.fit(X_train, y_train)

    metrics = evaluate(pipe, X_test, y_test, vertical)

    # Cross-validation AUC
    cv_scores = cross_val_score(pipe, X, y, cv=StratifiedKFold(3),
                                scoring="roc_auc")
    metrics["cv_auc_mean"] = round(float(cv_scores.mean()), 4)
    metrics["cv_auc_std"] = round(float(cv_scores.std()), 4)

    # Save model
    model_path = MODEL_DIR / f"model_{vertical.lower()}.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(pipe, f)

    # Feature importance
    fi = feature_importances(pipe, num_cols, cat_cols)
    fi["vertical"] = vertical

    # Score full vertical dataset
    vdf["predicted_score"] = (pipe.predict_proba(X)[:, 1] * 100).round(1)
    vdf["predicted_label"] = pipe.predict(X)

    return {
        "metrics": metrics,
        "feature_importance": fi,
        "scored_df": vdf[["lead_id", "vertical", "predicted_score",
                           "predicted_label", "converted"]],
    }


# ---------------------------------------------------------------------------
# Global model
# ---------------------------------------------------------------------------

def train_global(df: pd.DataFrame) -> dict:
    print("\n  [Global] Training cross-vertical model...")
    for c in GLOBAL_CATEGORICAL:
        if c in df.columns:
            df[c] = df[c].astype(str)

    num_cols = [c for c in GLOBAL_NUMERIC if c in df.columns]
    cat_cols = [c for c in GLOBAL_CATEGORICAL if c in df.columns]

    X = df[num_cols + cat_cols]
    y = df["converted"].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=42,
    )
    pipe = build_pipeline(num_cols, cat_cols, model_type="rf")
    pipe.fit(X_train, y_train)
    metrics = evaluate(pipe, X_test, y_test, "Global")

    with open(MODEL_DIR / "model_global.pkl", "wb") as f:
        pickle.dump(pipe, f)

    df["global_predicted_score"] = (pipe.predict_proba(X)[:, 1] * 100).round(1)
    fi = feature_importances(pipe, num_cols, cat_cols)
    fi["vertical"] = "Global"

    return {"metrics": metrics, "feature_importance": fi,
            "scored_df": df[["lead_id", "vertical", "global_predicted_score", "converted"]]}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_ml() -> None:
    print("\n" + "=" * 60)
    print("  ML TRAINING PIPELINE — BPO Platform")
    print("=" * 60)

    feat_path = GOLD_DIR / "gold_ml_feature_store.parquet"
    if not feat_path.exists():
        print("  ERROR: gold_ml_feature_store.parquet not found. Run pipeline first.")
        return

    df = pd.read_parquet(feat_path)
    print(f"  Loaded {len(df):,} feature rows  |  "
          f"conversion rate: {df['converted'].mean():.1%}\n")

    all_metrics = []
    all_fi = []
    all_scores = []

    # Per-vertical models
    for vertical in ["Insurance", "Healthcare", "RealEstate", "AR"]:
        result = train_vertical(df.copy(), vertical)
        if result:
            all_metrics.append(result["metrics"])
            all_fi.append(result["feature_importance"])
            all_scores.append(result["scored_df"])

    # Global model
    g = train_global(df.copy())
    all_metrics.append(g["metrics"])
    all_fi.append(g["feature_importance"])

    # Merge scores back to feature store
    scores_df = pd.concat(all_scores, ignore_index=True)
    df = df.merge(
        scores_df[["lead_id", "predicted_score", "predicted_label"]],
        on="lead_id", how="left",
    )
    df = df.merge(
        g["scored_df"][["lead_id", "global_predicted_score"]],
        on="lead_id", how="left",
    )
    df.to_parquet(GOLD_DIR / "gold_ml_feature_store.parquet", index=False)

    # Save reports
    report = {"models": all_metrics}
    (REPORT_DIR / "model_report.json").write_text(
        json.dumps(report, indent=2))

    fi_df = pd.concat(all_fi, ignore_index=True)
    fi_df.to_csv(REPORT_DIR / "feature_importance.csv", index=False)

    print(f"\n  Models saved → {MODEL_DIR}")
    print(f"  Reports saved → {REPORT_DIR}")
    print("\n  ╔══ Final Model Summary ═══════════════════════════════╗")
    for m in all_metrics:
        print(f"  ║  {m['model']:<12} AUC={m['auc_roc']}  F1={m['f1']}  "
              f"Prec={m['precision']}  Rec={m['recall']}")
    print("  ╚══════════════════════════════════════════════════════╝")


if __name__ == "__main__":
    run_ml()
