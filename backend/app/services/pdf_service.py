"""
Renders the Jinja2 HTML template to a PDF file using WeasyPrint.

Kept separate from report_service.py so the "turn data into a PDF" step
is independently testable/replaceable — e.g. swapping WeasyPrint for
another renderer later only touches this file.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html"]),
)


def render_report_pdf(*, context: dict, output_path: Path) -> None:
    """
    Renders app/templates/report_template.html with `context` and writes
    the resulting PDF to `output_path`, creating parent directories as
    needed.
    """
    template = _env.get_template("report_template.html")
    html_string = template.render(**context)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html_string, base_url=str(TEMPLATE_DIR)).write_pdf(str(output_path))
