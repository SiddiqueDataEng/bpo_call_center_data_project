# BPO Platform Data Generator

Generates realistic, randomized, contextually accurate synthetic data for the Pakistan BPO Platform
covering all four verticals (Insurance, Healthcare, Real Estate, AR Sales) with full relational
integrity across all entities. Output is suitable for data engineering pipelines, ML/AI model
training, and dashboard development.

## Install

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Generate default dataset (500 leads, 2000 calls, all verticals)
python -m bpo_generator

# Generate large ML training dataset
python -m bpo_generator --leads 5000 --calls 20000 --days 180 --output ./output

# Generate single vertical
python -m bpo_generator --vertical insurance --leads 1000 --calls 4000

# Generate as JSON (for Event Hubs / pipeline testing)
python -m bpo_generator --format json --output ./output

# Generate as Parquet (for Data Mesh / OneLake)
python -m bpo_generator --format parquet --output ./output
```

## Output Files

| File | Description |
|---|---|
| `clients.csv` | BPO client companies |
| `agents.csv` | Call center agents with roles and performance profiles |
| `campaigns.csv` | Campaigns per vertical with dialing modes |
| `leads.csv` | Lead records with vertical-specific data, DNC flags, scores |
| `calls.csv` | Call records with dispositions, durations, sentiment scores |
| `qa_reviews.csv` | QA scoring records for sampled calls |
| `payment_arrangements.csv` | AR vertical payment arrangements |
| `appointments.csv` | Healthcare appointment records |
| `insurance_qualifications.csv` | Insurance qualification form submissions |
| `realestate_qualifications.csv` | Real estate buyer/seller qualification records |
| `pipeline_events.jsonl` | Kafka/Event Hubs event stream (JSONL format) |
| `dnc_list.csv` | Internal DNC registry sample |
| `ml_features.csv` | Flattened ML feature matrix for model training |
| `agent_daily_performance.csv` | Daily agent KPI time series for drift/retraining |



