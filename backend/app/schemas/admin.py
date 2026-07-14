"""
Response schemas for the admin dashboard. Everything here is read-only
aggregate data — there's no request body for any admin endpoint in this
module beyond query params.
"""

from datetime import datetime

from pydantic import BaseModel


class OverviewStats(BaseModel):
    total_users: int
    active_users: int  # logged in within ACTIVE_USER_WINDOW_DAYS
    total_searches: int
    total_reports: int


class RecentSearchOut(BaseModel):
    id: int
    user_full_name: str
    keyword: str
    language: str
    newspaper: str | None
    result_count: int
    searched_at: datetime


class RecentReportOut(BaseModel):
    id: int
    user_full_name: str
    title: str
    article_count: int
    generated_at: datetime


class UserActivityOut(BaseModel):
    id: int
    full_name: str
    email: str
    is_admin: bool
    is_active: bool
    search_count: int
    report_count: int
    last_login_at: datetime | None
    created_at: datetime


class CountByLabel(BaseModel):
    label: str
    count: int


class DateCount(BaseModel):
    period: str  # "2026-07-04" for daily, "2026-07" for monthly
    count: int


class AdminDashboardOut(BaseModel):
    overview: OverviewStats
    recent_searches: list[RecentSearchOut]
    recent_reports: list[RecentReportOut]
    most_searched_keywords: list[CountByLabel]
    most_selected_language: list[CountByLabel]
    most_selected_newspaper: list[CountByLabel]
    most_selected_edition: list[CountByLabel]
    daily_reports: list[DateCount]
    monthly_reports: list[DateCount]


class UsersListOut(BaseModel):
    users: list[UserActivityOut]


class CleanupResult(BaseModel):
    retention_days: int
    cutoff: str
    deleted_cached_searches: int
    deleted_articles: int
