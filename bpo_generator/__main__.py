"""
CLI entry point.

Usage:
    python -m bpo_generator [OPTIONS]

Options:
    --leads     INT     Number of leads to generate        [default: 500]
    --calls     INT     Number of calls to generate        [default: 2000]
    --days      INT     History window in days             [default: 90]
    --vertical  TEXT    Filter to one vertical (optional)
    --format    TEXT    csv | json | parquet               [default: csv]
    --output    PATH    Output directory                   [default: ./output]
    --seed      INT     Random seed for reproducibility    [default: 42]
"""

import json
import os
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

import click
import pandas as pd
from faker import Faker
from tqdm import tqdm

from .generators import (
    generate_agents,
    generate_agent_daily_performance,
    generate_appointments,
    generate_campaigns,
    generate_clients,
    generate_calls,
    generate_dnc_list,
    generate_insurance_qualifications,
    generate_leads,
    generate_ml_features,
    generate_payment_arrangements,
    generate_pipeline_events,
    generate_qa_reviews,
    generate_realestate_qualifications,
)


def _save(data: list[dict], name: str, output_dir: Path, fmt: str) -> None:
    if not data:
        click.echo(f"  [skip] {name} — no records generated")
        return

    df = pd.DataFrame(data)
    output_dir.mkdir(parents=True, exist_ok=True)

    if fmt == "csv":
        path = output_dir / f"{name}.csv"
        df.to_csv(path, index=False)
    elif fmt == "parquet":
        path = output_dir / f"{name}.parquet"
        df.to_parquet(path, index=False, engine="pyarrow")
    elif fmt == "json":
        path = output_dir / f"{name}.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for row in data:
                f.write(json.dumps(row) + "\n")
    else:
        click.echo(f"Unknown format: {fmt}", err=True)
        sys.exit(1)

    click.echo(f"  {name:<38} {len(df):>7,} rows  →  {path}")


@click.command()
@click.option("--leads", default=500, show_default=True, help="Number of leads")
@click.option("--calls", default=2000, show_default=True, help="Number of calls")
@click.option("--days", default=90, show_default=True, help="History window in days")
@click.option("--vertical", default=None, help="Filter to one vertical (Insurance|Healthcare|RealEstate|AR)")
@click.option("--format", "fmt", default="csv", show_default=True,
              type=click.Choice(["csv", "json", "parquet"]), help="Output format")
@click.option("--output", default="./output", show_default=True, help="Output directory")
@click.option("--seed", default=42, show_default=True, help="Random seed")
def main(leads: int, calls: int, days: int, vertical: str,
         fmt: str, output: str, seed: int) -> None:
    """BPO Platform Synthetic Data Generator."""
    random.seed(seed)
    Faker.seed(seed)

    output_dir = Path(output)
    start = datetime.utcnow() - timedelta(days=days)

    click.echo("\n=== BPO Platform Data Generator ===")
    click.echo(f"  Leads: {leads:,}   Calls: {calls:,}   Days: {days}   Format: {fmt}")
    click.echo(f"  Output: {output_dir.resolve()}\n")

    steps = [
        "Clients", "Agents", "Campaigns", "DNC List", "Leads", "Calls",
        "QA Reviews", "Insurance Quals", "Appointments",
        "Real Estate Quals", "Payment Arrangements",
        "Pipeline Events", "Agent Daily KPIs", "ML Features",
    ]

    with tqdm(total=len(steps), desc="Generating", unit="step") as bar:

        bar.set_description("Clients")
        clients = generate_clients(n=8)
        bar.update(1)

        bar.set_description("Agents")
        agents = generate_agents(n=60)
        bar.update(1)

        bar.set_description("Campaigns")
        campaigns = generate_campaigns(clients, n_per_vertical=3, start=start)
        if vertical:
            campaigns = [c for c in campaigns if c["vertical"] == vertical]
        bar.update(1)

        bar.set_description("DNC List")
        dnc_records = generate_dnc_list(n=200)
        dnc_phones = {d["phone_e164"] for d in dnc_records}
        bar.update(1)

        bar.set_description("Leads")
        lead_data = generate_leads(campaigns, dnc_phones, n=leads, start=start)
        bar.update(1)

        bar.set_description("Calls")
        call_data = generate_calls(lead_data, agents, n=calls, start=start)
        bar.update(1)

        bar.set_description("QA Reviews")
        qa_data = generate_qa_reviews(call_data, agents, sample_rate=0.15)
        bar.update(1)

        bar.set_description("Insurance Quals")
        ins_quals = generate_insurance_qualifications(call_data, lead_data)
        bar.update(1)

        bar.set_description("Appointments")
        appts = generate_appointments(call_data, lead_data)
        bar.update(1)

        bar.set_description("Real Estate Quals")
        re_quals = generate_realestate_qualifications(call_data, lead_data)
        bar.update(1)

        bar.set_description("Payment Arrangements")
        arrangements = generate_payment_arrangements(call_data, lead_data)
        bar.update(1)

        bar.set_description("Pipeline Events")
        events = generate_pipeline_events(call_data)
        bar.update(1)

        bar.set_description("Agent Daily KPIs")
        daily_perf = generate_agent_daily_performance(agents, call_data, days=days)
        bar.update(1)

        bar.set_description("ML Features")
        ml_feats = generate_ml_features(lead_data, call_data)
        bar.update(1)

    click.echo("\n--- Writing output ---")
    _save(clients,      "clients",                    output_dir, fmt)
    _save(agents,       "agents",                     output_dir, fmt)
    _save(campaigns,    "campaigns",                  output_dir, fmt)
    _save(dnc_records,  "dnc_list",                   output_dir, fmt)
    _save(lead_data,    "leads",                      output_dir, fmt)
    _save(call_data,    "calls",                      output_dir, fmt)
    _save(qa_data,      "qa_reviews",                 output_dir, fmt)
    _save(ins_quals,    "insurance_qualifications",   output_dir, fmt)
    _save(appts,        "appointments",               output_dir, fmt)
    _save(re_quals,     "realestate_qualifications",  output_dir, fmt)
    _save(arrangements, "payment_arrangements",       output_dir, fmt)
    _save(daily_perf,   "agent_daily_performance",    output_dir, fmt)
    _save(ml_feats,     "ml_features",                output_dir, fmt)

    # Pipeline events always written as JSONL regardless of format
    events_path = output_dir / "pipeline_events.jsonl"
    with open(events_path, "w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")
    click.echo(f"  {'pipeline_events':<38} {len(events):>7,} rows  →  {events_path}")

    # Summary stats
    converted = sum(1 for r in ml_feats if r["converted"])
    compliance_flags = sum(1 for c in call_data if c["compliance_flagged"])
    dnc_leads = sum(1 for l in lead_data if l["dnc_flagged"])

    click.echo("\n--- Summary ---")
    click.echo(f"  Campaigns:          {len(campaigns):>6,}")
    click.echo(f"  Leads:              {len(lead_data):>6,}  (DNC flagged: {dnc_leads:,})")
    click.echo(f"  Calls:              {len(call_data):>6,}  (Compliance flagged: {compliance_flags:,})")
    click.echo(f"  QA Reviews:         {len(qa_data):>6,}")
    click.echo(f"  Appointments:       {len(appts):>6,}")
    click.echo(f"  Ins. Qualifications:{len(ins_quals):>6,}")
    click.echo(f"  RE Qualifications:  {len(re_quals):>6,}")
    click.echo(f"  Payment Arrngmnts:  {len(arrangements):>6,}")
    click.echo(f"  Pipeline Events:    {len(events):>6,}")
    click.echo(f"  ML Feature Rows:    {len(ml_feats):>6,}  (Converted: {converted:,})")
    click.echo(f"\nDone. All files written to: {output_dir.resolve()}\n")


if __name__ == "__main__":
    main()
