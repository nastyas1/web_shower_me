import json
from unittest.mock import patch
from django.test import TestCase, Client
from django.urls import reverse

from app.models import FeedbackMessage


class FeedbackViewsTestCase(TestCase):
    """Тесты для представлений feedback-service."""

    def setUp(self):
        self.client = Client()
        self.submit_feedback_url = reverse('submit_feedback')

    def test_submit_feedback_success(self):
        """Тест успешной отправки обратной связи."""
        data = {
            "name": "Иван Иванов",
            "email": "ivan@example.com",
            "subject": "booking",
            "message": "Проблема с бронированием"
        }
        response = self.client.post(
            self.submit_feedback_url,
            data=json.dumps(data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertTrue(json_response["success"])
        self.assertIn("message", json_response)
        
        # Проверяем, что сообщение сохранено в БД
        self.assertEqual(FeedbackMessage.objects.count(), 1)
        saved_message = FeedbackMessage.objects.first()
        self.assertEqual(saved_message.name, "Иван Иванов")
        self.assertEqual(saved_message.email, "ivan@example.com")
        self.assertEqual(saved_message.subject, "booking")

    def test_submit_feedback_missing_fields(self):
        """Тест отправки обратной связи с отсутствующими полями."""
        data = {
            "name": "Иван",
            "email": "ivan@example.com"
            # Отсутствуют subject и message
        }
        response = self.client.post(
            self.submit_feedback_url,
            data=json.dumps(data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        json_response = response.json()
        self.assertIn("error", json_response)

    def test_submit_feedback_invalid_subject(self):
        """Тест отправки обратной связи с неверной темой."""
        data = {
            "name": "Иван",
            "email": "ivan@example.com",
            "subject": "invalid_subject",
            "message": "Сообщение"
        }
        response = self.client.post(
            self.submit_feedback_url,
            data=json.dumps(data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        json_response = response.json()
        self.assertIn("error", json_response)

    def test_submit_feedback_empty_name(self):
        """Тест отправки обратной связи с пустым именем."""
        data = {
            "name": "",
            "email": "ivan@example.com",
            "subject": "booking",
            "message": "Сообщение"
        }
        response = self.client.post(
            self.submit_feedback_url,
            data=json.dumps(data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_submit_feedback_invalid_email(self):
        """Тест отправки обратной связи с невалидным email."""
        data = {
            "name": "Иван",
            "email": "invalid-email",
            "subject": "booking",
            "message": "Сообщение"
        }
        response = self.client.post(
            self.submit_feedback_url,
            data=json.dumps(data),
            content_type="application/json"
        )
        # Django EmailField должен отклонить невалидный email
        self.assertEqual(response.status_code, 400)

    @patch('app.views.requests.post')
    def test_submit_feedback_sends_telegram_notification(self, mock_post):
        """Тест отправки уведомления в Telegram."""
        # Настраиваем мок для requests.post
        mock_post.return_value.status_code = 200
        
        data = {
            "name": "Иван",
            "email": "ivan@example.com",
            "subject": "technical",
            "message": "Техническая проблема"
        }
        response = self.client.post(
            self.submit_feedback_url,
            data=json.dumps(data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что requests.post был вызван
        mock_post.assert_called_once()

    def test_feedback_model_str(self):
        """Тест строкового представления модели FeedbackMessage."""
        message = FeedbackMessage.objects.create(
            name="Иван",
            email="ivan@example.com",
            subject="suggestion",
            message="Предложение"
        )
        str_repr = str(message)
        self.assertIn("Иван", str_repr)
        self.assertIn("Предложение", str_repr)

    def test_feedback_model_ordering(self):
        """Тест сортировки сообщений по времени создания."""
        FeedbackMessage.objects.create(
            name="User1",
            email="user1@example.com",
            subject="booking",
            message="Сообщение 1"
        )
        FeedbackMessage.objects.create(
            name="User2",
            email="user2@example.com",
            subject="technical",
            message="Сообщение 2"
        )
        
        messages = list(FeedbackMessage.objects.all())
        # Проверяем, что они отсортированы по убыванию created_at
        self.assertGreaterEqual(messages[0].created_at, messages[1].created_at)

    def test_feedback_subject_choices(self):
        """Тест выбора тем обратной связи."""
        valid_subjects = ["booking", "technical", "suggestion", "other"]
        for subject in valid_subjects:
            message = FeedbackMessage(
                name="Test",
                email="test@example.com",
                subject=subject,
                message="Тест"
            )
            # Проверка, что subject в допустимых значениях
            choices = [choice[0] for choice in FeedbackMessage.SUBJECT_CHOICES]
            self.assertIn(subject, choices)
