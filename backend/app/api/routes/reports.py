"""
Report routes: generate a PDF from selected articles, list your own
reports, and download a previously generated one.
"""

from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.database import get_db
from app.models.user import User
from app.schemas.report import GenerateReportRequest, ReportOut
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["Reports"])


def _to_report_out(report) -> ReportOut:
    return ReportOut(
        id=report.id,
        title=report.title,
        keyword=report.keyword,
        language=report.language,
        newspaper=report.newspaper,
        edition=report.edition,
        article_count=report.article_count,
        generated_at=report.generated_at,
        download_url=f"{settings.API_V1_PREFIX}/reports/{report.id}/download",
    )


@router.post("/generate", response_model=ReportOut)
def generate(
    payload: GenerateReportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = report_service.generate_report(db, current_user, payload)
    return _to_report_out(report)


@router.get("", response_model=list[ReportOut])
def list_my_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reports = report_service.list_reports(db, current_user.id)
    return [_to_report_out(r) for r in reports]


@router.get("/{report_id}/download")
def download(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = report_service.get_owned_report(db, current_user.id, report_id)
    file_path = Path(report.file_path)
    filename = f"{report_service.slugify(report.keyword)}-report.pdf"
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=filename,
    )
