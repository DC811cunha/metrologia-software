from app.workers import email_tasks


def test_send_password_reset_email_task_delegates_to_email_service(monkeypatch):
    captured = {}

    def fake_send(to_email, reset_link):
        captured["to_email"] = to_email
        captured["reset_link"] = reset_link

    monkeypatch.setattr(email_tasks, "send_password_reset_email", fake_send)

    email_tasks.send_password_reset_email_task.run(
        "user@example.com", "http://localhost:3000/reset-password?token=abc"
    )

    assert captured == {
        "to_email": "user@example.com",
        "reset_link": "http://localhost:3000/reset-password?token=abc",
    }
