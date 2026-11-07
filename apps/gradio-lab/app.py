"""Gradio AI Engineering & Prompt Evaluation Laboratory.

Provides an interactive GUI for testing recruitment data extraction,
evaluating prompt injection defenses, tuning fuzzy deduplication thresholds,
and monitoring zero-cost cloud quotas.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Tuple
from rapidfuzz import fuzz

from packages.core.quota_manager import global_quota_manager
from packages.intelligence.ai_gateway import global_ai_gateway, sanitize_input_text
from packages.intelligence.deduplicator import OpportunityDeduplicator
from packages.intelligence.eligibility import EligibilityAnalyzer
from packages.intelligence.verifier import SourceVerifier

logger = logging.getLogger("GradioLab")

try:
    import gradio as gr
except ImportError:
    gr = None


def run_extraction_analysis(raw_text: str, source_url: str, force_deterministic: bool) -> Tuple[str, str, str, str]:
    """Runs extraction on raw text and returns formatted JSON, batches, and safety audit."""
    if not raw_text.strip():
        return "{}", "None", "None", "Empty input provided."

    # 1. Prompt Injection Audit
    sanitized = sanitize_input_text(raw_text)
    injection_detected = sanitized != raw_text
    safety_verdict = "⚠️ Potential prompt injection detected and neutralized!" if injection_detected else "✅ Clean input (no adversarial instructions detected)."

    # 2. Synchronous deterministic extraction
    extracted = global_ai_gateway._deterministic_extract(sanitized, source_url if source_url.strip() else None)

    # 3. Batch & Degree extraction
    batches = EligibilityAnalyzer.extract_batches(sanitized)
    degrees = EligibilityAnalyzer.extract_degrees(sanitized)

    formatted_json = json.dumps(extracted, indent=2)
    batches_str = ", ".join(batches) if batches else "None detected"
    degrees_str = ", ".join(degrees) if degrees else "None detected"

    return formatted_json, batches_str, degrees_str, safety_verdict


def compare_deduplication(title1: str, company1: str, title2: str, company2: str) -> Tuple[str, float, str]:
    """Compares two opportunities for semantic and fuzzy similarity."""
    dedup = OpportunityDeduplicator()

    norm1 = dedup.normalize_title(title1)
    norm2 = dedup.normalize_title(title2)

    comp_ratio = fuzz.token_sort_ratio(company1.lower(), company2.lower())
    title_ratio = fuzz.token_sort_ratio(norm1, norm2)

    composite_score = (comp_ratio * 0.4) + (title_ratio * 0.6)

    verdict = "DISTINCT OPPORTUNITY"
    if composite_score >= 85.0:
        verdict = "HIGH CONFIDENCE DUPLICATE"
    elif composite_score >= 70.0:
        verdict = "POTENTIAL NEW VERSION / VARIANT"

    details = (
        f"Normalized 1: '{norm1}' ({company1.strip()})\n"
        f"Normalized 2: '{norm2}' ({company2.strip()})\n"
        f"Company Similarity: {comp_ratio:.1f}%\n"
        f"Title Similarity: {title_ratio:.1f}%"
    )

    return verdict, round(composite_score, 1), details


def get_live_quota_status() -> str:
    """Returns human-readable quota audit from QuotaManager."""
    summary = global_quota_manager.get_summary()
    lines = ["📊 LIVE ZERO-COST QUOTA TELEMETRY", "━" * 40]
    for metric, data in summary.items():
        used = data["current_usage"]
        limit = data["limit"]
        pct = data["usage_percent"] * 100
        status_sym = "🚨" if data["is_critical"] else ("⚠️" if data["is_warning"] else "✅")
        lines.append(f"{status_sym} {metric}: {used:,} / {limit:,} ({pct:.1f}%)")
    lines.append("━" * 40)
    lines.append("Infrastructure Cost Invariant: ₹0.00 / month")
    return "\n".join(lines)


def build_app():
    if gr is None:
        raise RuntimeError("Gradio is not installed in the environment. Install via pip install gradio.")

    theme = gr.themes.Soft(
        primary_hue="blue",
        neutral_hue="slate",
    )

    with gr.Blocks(title="Placement Hub — AI Lab", theme=theme) as demo:
        gr.Markdown(
            "# 🔬 Placement Intelligence Hub — AI & Extraction Laboratory\n"
            "Diagnostic workbench for recruitment data extraction, adversarial prompt injection defense, "
            "and fuzzy deduplication calibration."
        )

        with gr.Tab("🧪 Opportunity Extraction & Sanitization"):
            with gr.Row():
                with gr.Column(scale=1):
                    input_text = gr.Textbox(
                        label="Raw Opportunity Text / Forwarded Post",
                        placeholder="Paste WhatsApp forward, LinkedIn post, or career page HTML snippet here...",
                        lines=10,
                        value=(
                            "🔥 Hevo Freshers Hiring 2026/2027\n"
                            "Role: Associate Software Developer\n"
                            "Eligibility: BE/B.Tech (CS, IT, EC & AI)\n"
                            "Eligible batches: 2026 & 2027\n"
                            "Location: Pune\n"
                            "CTC: 6 - 8 LPA\n"
                            "Apply: https://go.acciojob.com/pP8wXz"
                        )
                    )
                    source_url = gr.Textbox(label="Source URL (Optional)", placeholder="https://...")
                    deterministic_chk = gr.Checkbox(label="Force 100% Deterministic Regex Parser", value=True)
                    extract_btn = gr.Button("🚀 Run Extraction & Safety Audit", variant="primary")

                with gr.Column(scale=1):
                    safety_out = gr.Textbox(label="Prompt Injection & Security Audit", interactive=False)
                    with gr.Row():
                        batches_out = gr.Textbox(label="Detected Batches", interactive=False)
                        degrees_out = gr.Textbox(label="Detected Degrees", interactive=False)
                    json_out = gr.Code(label="Extracted Structured JSON", language="json")

            extract_btn.click(
                run_extraction_analysis,
                inputs=[input_text, source_url, deterministic_chk],
                outputs=[json_out, batches_out, degrees_out, safety_out]
            )

        with gr.Tab("⚖️ Deduplication & Fuzzy Similarity Inspector"):
            gr.Markdown("### Test Semantic & Token-Sort Similarity Between Two Jobs")
            with gr.Row():
                with gr.Column():
                    gr.Markdown("#### Job Posting A")
                    comp_a = gr.Textbox(label="Company A", value="Amazon")
                    title_a = gr.Textbox(label="Role Title A", value="Software Development Engineer Intern - 2027")

                with gr.Column():
                    gr.Markdown("#### Job Posting B")
                    comp_b = gr.Textbox(label="Company B", value="Amazon Development Centre India")
                    title_b = gr.Textbox(label="Role Title B", value="SDE Intern (May 2027)")

            compare_btn = gr.Button("🔍 Compute Similarity Score", variant="secondary")

            with gr.Row():
                verdict_out = gr.Textbox(label="Deduplication Verdict", interactive=False)
                score_out = gr.Number(label="Composite Similarity Score (%)", interactive=False)

            details_out = gr.Textbox(label="Algorithm Breakdown", lines=4, interactive=False)

            compare_btn.click(
                compare_deduplication,
                inputs=[title_a, comp_a, title_b, comp_b],
                outputs=[verdict_out, score_out, details_out]
            )

        with gr.Tab("🛡️ Infrastructure Quota & Telemetry"):
            gr.Markdown("### Real-Time Zero-Cost Cloud Resource Monitor")
            quota_text = gr.Textbox(label="Current Usage vs Hard Ceilings", lines=12, interactive=False, value=get_live_quota_status)
            refresh_quota_btn = gr.Button("🔄 Refresh Quota Counts")
            refresh_quota_btn.click(get_live_quota_status, outputs=[quota_text])

    return demo


if __name__ == "__main__":
    if gr is not None:
        app = build_app()
        app.launch(server_name="127.0.0.1", server_port=7860, share=False)
    else:
        print("Gradio is not installed. To run the lab: pip install gradio")
