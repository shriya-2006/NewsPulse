"""Tests for app/api/routes/auth.py."""


def test_register_returns_token(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Shriya Reddy", "email": "shriya@vizagsteel.com", "password": "Steel1234"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["access_token"]
    assert body["user"]["email"] == "shriya@vizagsteel.com"
    assert body["user"]["is_admin"] is False


def test_register_duplicate_email_conflicts(client, register_user):
    register_user(email="shriya@vizagsteel.com")
    response = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Someone Else", "email": "shriya@vizagsteel.com", "password": "Other1234"},
    )
    assert response.status_code == 409


def test_register_rejects_weak_password(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Bob", "email": "bob@vizagsteel.com", "password": "weak"},
    )
    assert response.status_code == 422


def test_login_with_correct_password(client, register_user):
    register_user(email="shriya@vizagsteel.com", password="Steel1234")
    response = client.post(
        "/api/v1/auth/login", json={"email": "shriya@vizagsteel.com", "password": "Steel1234"}
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_login_with_wrong_password_rejected(client, register_user):
    register_user(email="shriya@vizagsteel.com", password="Steel1234")
    response = client.post(
        "/api/v1/auth/login", json={"email": "shriya@vizagsteel.com", "password": "WrongPass1"}
    )
    assert response.status_code == 401


def test_login_sets_last_login_at(client, register_user, db_session_factory):
    register_user(email="shriya@vizagsteel.com", password="Steel1234")
    client.post("/api/v1/auth/login", json={"email": "shriya@vizagsteel.com", "password": "Steel1234"})

    from app.models.user import User

    db = db_session_factory()
    user = db.query(User).filter(User.email == "shriya@vizagsteel.com").first()
    assert user.last_login_at is not None
    db.close()


def test_me_requires_auth(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_returns_profile(client, register_user):
    _, headers = register_user()
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == "shriya@vizagsteel.com"


def test_forgot_password_same_response_whether_or_not_email_exists(client, register_user):
    register_user(email="shriya@vizagsteel.com")

    existing = client.post("/api/v1/auth/forgot-password", json={"email": "shriya@vizagsteel.com"})
    missing = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@vizagsteel.com"})

    assert existing.status_code == 200
    assert missing.status_code == 200
    assert existing.json()["message"] == missing.json()["message"]


def test_reset_password_with_invalid_token_rejected(client):
    response = client.post(
        "/api/v1/auth/reset-password", json={"token": "not-a-real-token", "new_password": "NewPass1234"}
    )
    assert response.status_code == 400


def test_logout_is_idempotent_and_requires_auth(client, register_user):
    _, headers = register_user()
    response = client.post("/api/v1/auth/logout", headers=headers)
    assert response.status_code == 200

    unauth_response = client.post("/api/v1/auth/logout")
    assert unauth_response.status_code == 401
