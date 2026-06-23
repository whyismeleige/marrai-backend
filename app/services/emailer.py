import html
from typing import Any

import resend

from app.core.orchestrator import OrchestrationResult
from app.config import get_settings
from app.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)

resend.api_key = settings.RESEND_API_KEY


def _escape(value: object) -> str:
    return html.escape(str(value))


def _top_items(items: list[str], limit: int = 5) -> list[str]:
    return items[:limit] if items else []


def _render_list(title: str, items: list[str]) -> str:
    if not items:
        return f"""
            <section style="margin-top: 24px;">
                <h3 style="margin-bottom: 8px;">{_escape(title)}</h3>
                <p style="color: #666; margin-top: 0;">No items found.</p>
            </section>
        """

    list_items = "".join(f"""
        <li style="margin-bottom: 10px; line-height: 1.5;">
            {_escape(item)}
        </li>
        """ for item in items)

    return f"""
        <section style="margin-top: 24px;">
            <h3 style="margin-bottom: 8px;">{_escape(title)}</h3>
            <ol style="padding-left: 20px; margin-top: 0;">
                {list_items}
            </ol>
        </section>
    """


def _build_report_url(job_id: str) -> str:
    base_url = "https://marrai.tech"
    return f"{base_url}/audit/{job_id}"


def _build_audit_complete_html(job_id: str, result: OrchestrationResult) -> str:
    report_url = _build_report_url(job_id)

    top_findings = _top_items(result.findings)
    top_semantic_findings = _top_items(result.semantic_findings)
    top_recommendations = _top_items(result.recommendations)
    top_semantic_recommendations = _top_items(result.semantic_recommendations)

    return f"""
    <!doctype html>
    <html>
      <body style="
        margin: 0;
        padding: 0;
        background-color: #f6f7f9;
        font-family: Arial, sans-serif;
        color: #111827;
      ">
        <div style="
          max-width: 680px;
          margin: 0 auto;
          padding: 32px 20px;
        ">
          <div style="
            background: #ffffff;
            border-radius: 14px;
            padding: 32px;
            border: 1px solid #e5e7eb;
          ">
            <h1 style="margin-top: 0; margin-bottom: 8px;">
              Your AEO audit is complete
            </h1>

            <p style="margin-top: 0; color: #4b5563; line-height: 1.5;">
              We finished auditing:
              <strong>{_escape(result.url)}</strong>
            </p>

            <div style="
              display: block;
              margin-top: 24px;
              padding: 20px;
              border-radius: 12px;
              background-color: #f9fafb;
              border: 1px solid #e5e7eb;
            ">
              <p style="margin: 0 0 6px 0; color: #6b7280; font-size: 14px;">
                Overall Score
              </p>

              <p style="margin: 0; font-size: 36px; font-weight: 700;">
                {_escape(result.overall_score)} / 100
              </p>

              <p style="margin: 14px 0 0 0; color: #6b7280; font-size: 14px;">
                Semantic Score: <strong>{_escape(result.semantic_score)} / 100</strong>
              </p>

              <p style="margin: 6px 0 0 0; color: #6b7280; font-size: 14px;">
                Pages crawled: <strong>{_escape(result.pages_crawled)}</strong>
              </p>

              <p style="margin: 6px 0 0 0; color: #6b7280; font-size: 14px;">
                Crawl duration:
                <strong>{_escape(round(result.crawl_duration_seconds, 2))} seconds</strong>
              </p>
            </div>

            {_render_list("Top 5 Findings", top_findings)}
            {_render_list("Top 5 Semantic Findings", top_semantic_findings)}
            {_render_list("Top 5 Recommendations", top_recommendations)}
            {_render_list("Top 5 Semantic Recommendations", top_semantic_recommendations)}

            <div style="margin-top: 32px;">
              <a href="{_escape(report_url)}"
                 style="
                   display: inline-block;
                   background-color: #111827;
                   color: #ffffff;
                   text-decoration: none;
                   padding: 12px 18px;
                   border-radius: 8px;
                   font-weight: 600;
                 ">
                Open full report
              </a>
            </div>

            <p style="
              margin-top: 32px;
              color: #6b7280;
              font-size: 13px;
              line-height: 1.5;
            ">
              This is an automated audit summary from Marrai.
            </p>
          </div>
        </div>
      </body>
    </html>
    """


def send_audit_complete_mail(
    to_email: str,
    job_id: str,
    result: OrchestrationResult,
) -> dict[str, Any] | None:

    try:
        html_body = _build_audit_complete_html(job_id=job_id, result=result)

        return resend.Emails.send(
            {
                "from": "Marrai <onboarding@resend.dev>",
                "to": [to_email],
                "subject": "Your AEO audit is complete",
                "html": html_body,
            }
        )

    except Exception:
        logger.exception("Error sending audit completion email to %s", to_email)
        return None
