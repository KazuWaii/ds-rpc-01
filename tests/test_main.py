from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_login_valid_credentials():
    resp = client.get("/login", auth=("Sam", "financepass"))
    assert resp.status_code == 200
    assert resp.json() == {"message": "Welcome Sam!", "role": "finance"}


def test_login_invalid_password():
    resp = client.get("/login", auth=("Sam", "wrongpassword"))
    assert resp.status_code == 401


def test_login_unknown_user():
    resp = client.get("/login", auth=("NotAUser", "whatever"))
    assert resp.status_code == 401


def test_login_natasha_regression():
    # Regression test: Natasha's record used to have a typo'd "passwoed" key
    # instead of "password", causing an unhandled KeyError (500 error)
    # instead of a clean login/401.
    resp = client.get("/login", auth=("Natasha", "hrpass123"))
    assert resp.status_code == 200
    assert resp.json()["role"] == "hr"


def test_chat_requires_authentication():
    resp = client.post("/chat", json={"message": "hello"})
    assert resp.status_code == 401


def test_chat_wires_role_and_message_to_answer_question():
    with patch(
        "app.main.answer_question",
        return_value={"answer": "the answer", "sources": ["finance/doc.md"]},
    ) as mock_answer:
        resp = client.post(
            "/chat",
            json={"message": "What drove vendor expenses up?"},
            auth=("Sam", "financepass"),
        )

    assert resp.status_code == 200
    assert resp.json() == {"answer": "the answer", "sources": ["finance/doc.md"], "role": "finance"}
    mock_answer.assert_called_once_with("What drove vendor expenses up?", role="finance")


def test_chat_rejects_malformed_body():
    resp = client.post("/chat", json={"not_message": "oops"}, auth=("Sam", "financepass"))
    assert resp.status_code == 422
