"""Tests for app/api/routes/admin.py."""

from tests.test_reports import SAMPLE_ARTICLES


def test_admin_dashboard_requires_admin(client, register_user):
    _, headers = register_user()
    response = client.get("/api/v1/admin/dashboard", headers=headers)
    assert response.status_code == 403


def test_admin_dashboard_requires_auth(client):
    response = client.get("/api/v1/admin/dashboard")
    assert response.status_code == 401


def test_admin_dashboard_accessible_to_admin(client, admin_headers):
    response = client.get("/api/v1/admin/dashboard", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert "overview" in body
    assert "most_searched_keywords" in body
    assert "daily_reports" in body
    assert "monthly_reports" in body


def test_admin_overview_counts_are_accurate(client, register_user, admin_headers, mock_rss):
    _, user_headers = register_user(email="worker@vizagsteel.com")

    client.get(
        "/api/v1/news/search",
        params={"keyword": "steel", "language": "en", "newspaper": "the_hindu"},
        headers=user_headers,
    )
    client.post(
        "/api/v1/reports/generate",
        json={"keyword": "steel", "language": "en", "articles": SAMPLE_ARTICLES},
        headers=user_headers,
    )

    response = client.get("/api/v1/admin/dashboard", headers=admin_headers)
    overview = response.json()["overview"]
    # admin_headers fixture registers one admin user, register_user registers
    # a second regular user in this test -> 2 total.
    assert overview["total_users"] == 2
    assert overview["total_searches"] == 1
    assert overview["total_reports"] == 1


def test_admin_daily_reports_zero_filled(client, admin_headers):
    response = client.get("/api/v1/admin/dashboard", headers=admin_headers)
    daily = response.json()["daily_reports"]
    assert len(daily) == 14
    assert all("period" in d and "count" in d for d in daily)


def test_admin_monthly_reports_zero_filled(client, admin_headers):
    response = client.get("/api/v1/admin/dashboard", headers=admin_headers)
    monthly = response.json()["monthly_reports"]
    assert len(monthly) == 12


def test_admin_users_endpoint_requires_admin(client, register_user):
    _, headers = register_user()
    response = client.get("/api/v1/admin/users", headers=headers)
    assert response.status_code == 403


def test_admin_users_endpoint_shows_activity_counts(client, admin_headers, mock_rss):
    client.get(
        "/api/v1/news/search", params={"keyword": "steel", "language": "en"}, headers=admin_headers
    )
    response = client.get("/api/v1/admin/users", headers=admin_headers)
    assert response.status_code == 200
    users = response.json()["users"]
    assert len(users) == 1
    assert users[0]["search_count"] == 1
    assert users[0]["is_admin"] is True
