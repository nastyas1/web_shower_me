import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse


class AuthViewsTestCase(TestCase):
    """Тесты для представлений auth-service."""

    def setUp(self):
        self.client = Client()
        self.register_url = reverse('register')
        self.login_url = reverse('login_view')
        self.token_refresh_url = reverse('token_refresh')
        self.me_url = reverse('me')

    def test_register_success(self):
        """Тест успешной регистрации пользователя."""
        data = {
            "name": "Иван",
            "email": "ivan@example.com",
            "password": "password123"
        }
        response = self.client.post(
            self.register_url,
            data=json.dumps(data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)
        json_response = response.json()
        self.assertIn("access", json_response)
        self.assertIn("refresh", json_response)
        self.assertIn("user", json_response)
        self.assertEqual(json_response["user"]["email"], "ivan@example.com")
        self.assertEqual(json_response["user"]["name"], "Иван")

    def test_register_invalid_name(self):
        """Тест регистрации с некорректным именем."""
        data = {
            "name": "и",
            "email": "test@example.com",
            "password": "password123"
        }
        response = self.client.post(
            self.register_url,
            data=json.dumps(data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 422)
        json_response = response.json()
        self.assertIn("errors", json_response)
        self.assertIn("name", json_response["errors"])

    def test_register_duplicate_email(self):
        """Тест регистрации с уже существующим email."""
        User.objects.create_user(username="existing", email="dup@example.com", password="pass")
        data = {
            "name": "Петр",
            "email": "dup@example.com",
            "password": "password123"
        }
        response = self.client.post(
            self.register_url,
            data=json.dumps(data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 422)
        json_response = response.json()
        self.assertIn("errors", json_response)
        self.assertIn("email", json_response["errors"])

    def test_register_short_password(self):
        """Тест регистрации с коротким паролем."""
        data = {
            "name": "Анна",
            "email": "anna@example.com",
            "password": "123"
        }
        response = self.client.post(
            self.register_url,
            data=json.dumps(data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 422)
        json_response = response.json()
        self.assertIn("errors", json_response)
        self.assertIn("password", json_response["errors"])

    def test_login_success(self):
        """Тест успешного входа."""
        User.objects.create_user(username="loginuser", email="login@example.com", password="pass123")
        data = {
            "email": "login@example.com",
            "password": "pass123"
        }
        response = self.client.post(
            self.login_url,
            data=json.dumps(data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertIn("access", json_response)
        self.assertIn("refresh", json_response)

    def test_login_wrong_password(self):
        """Тест входа с неправильным паролем."""
        User.objects.create_user(username="wrongpass", email="wrong@example.com", password="correctpass")
        data = {
            "email": "wrong@example.com",
            "password": "wrongpass"
        }
        response = self.client.post(
            self.login_url,
            data=json.dumps(data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)

    def test_login_nonexistent_user(self):
        """Тест входа с несуществующим пользователем."""
        data = {
            "email": "nobody@example.com",
            "password": "anypass"
        }
        response = self.client.post(
            self.login_url,
            data=json.dumps(data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)

    def test_token_refresh(self):
        """Тест обновления токена."""
        # Сначала регистрируем пользователя
        reg_data = {
            "name": "Refresh",
            "email": "refresh@example.com",
            "password": "password123"
        }
        reg_response = self.client.post(
            self.register_url,
            data=json.dumps(reg_data),
            content_type="application/json"
        )
        refresh_token = reg_response.json()["refresh"]

        # Обновляем токен
        data = {"refresh": refresh_token}
        response = self.client.post(
            self.token_refresh_url,
            data=json.dumps(data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertIn("access", json_response)
        self.assertIn("refresh", json_response)

    def test_me_with_valid_token(self):
        """Тест получения информации о пользователе с валидным токеном."""
        # Регистрируемся и получаем токен
        reg_data = {
            "name": "MeUser",
            "email": "me@example.com",
            "password": "password123"
        }
        reg_response = self.client.post(
            self.register_url,
            data=json.dumps(reg_data),
            content_type="application/json"
        )
        access_token = reg_response.json()["access"]

        # Запрашиваем информацию о себе
        response = self.client.get(
            self.me_url,
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(json_response["first_name"], "MeUser")
        self.assertEqual(json_response["email"], "me@example.com")

    def test_me_without_token(self):
        """Тест получения информации о пользователе без токена."""
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, 401)

    def test_me_with_invalid_token(self):
        """Тест получения информации о пользователе с невалидным токеном."""
        response = self.client.get(
            self.me_url,
            HTTP_AUTHORIZATION="Bearer invalidtoken"
        )
        self.assertEqual(response.status_code, 401)
