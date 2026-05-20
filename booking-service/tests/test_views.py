import json
from datetime import date, time
from django.test import TestCase, Client
from django.urls import reverse

from app.models import Booking


class BookingViewsTestCase(TestCase):
    """Тесты для представлений booking-service."""

    def setUp(self):
        self.client = Client()
        self.slots_url = reverse('slots')
        self.create_booking_url = reverse('create_booking')
        self.my_bookings_url = reverse('my_bookings')
        self.user_payload = {
            "user_id": 1,
            "username": "testuser",
            "first_name": "Test"
        }

    def test_slots_without_date(self):
        """Тест получения слотов без указания даты."""
        response = self.client.get(self.slots_url)
        self.assertEqual(response.status_code, 400)
        json_response = response.json()
        self.assertIn("error", json_response)

    def test_slots_with_date(self):
        """Тест получения слотов с указанной датой."""
        response = self.client.get(f"{self.slots_url}?date=2025-06-01")
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertIn("date", json_response)
        self.assertIn("slots", json_response)
        self.assertEqual(json_response["date"], "2025-06-01")
        self.assertIsInstance(json_response["slots"], list)

    def test_create_booking_without_auth(self):
        """Тест создания бронирования без авторизации."""
        data = {"date": "2025-06-01", "time": "10:00"}
        response = self.client.post(
            self.create_booking_url,
            data=json.dumps(data),
            content_type="application/json"
        )
        # Должна быть ошибка авторизации (401 или редирект в зависимости от реализации)
        self.assertIn(response.status_code, [401, 403])

    def test_my_bookings_without_auth(self):
        """Тест получения своих бронирований без авторизации."""
        response = self.client.get(self.my_bookings_url)
        self.assertIn(response.status_code, [401, 403])

    def test_create_and_get_booking(self):
        """Тест создания и получения бронирования."""
        # Создаем бронь напрямую через модель для тестирования
        booking = Booking.objects.create(
            user_id=1,
            username="TestUser",
            date=date(2025, 6, 1),
            time=time(10, 0)
        )
        
        # Проверяем, что бронь сохранилась
        self.assertEqual(Booking.objects.count(), 1)
        saved_booking = Booking.objects.first()
        self.assertEqual(saved_booking.username, "TestUser")
        self.assertEqual(saved_booking.date, date(2025, 6, 1))
        self.assertEqual(saved_booking.time, time(10, 0))

    def test_booking_unique_together(self):
        """Тест уникальности бронирования на одно время."""
        Booking.objects.create(
            user_id=1,
            username="User1",
            date=date(2025, 6, 1),
            time=time(12, 0)
        )
        
        # Попытка создать дубликат должна вызвать ошибку
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Booking.objects.create(
                user_id=2,
                username="User2",
                date=date(2025, 6, 1),
                time=time(12, 0)
            )

    def test_booking_to_dict(self):
        """Тест метода to_dict модели Booking."""
        booking = Booking.objects.create(
            user_id=1,
            username="TestUser",
            date=date(2025, 6, 1),
            time=time(14, 30)
        )
        result = booking.to_dict()
        self.assertIn("id", result)
        self.assertEqual(result["user_id"], 1)
        self.assertEqual(result["username"], "TestUser")
        self.assertEqual(result["date"], "2025-06-01")
        self.assertEqual(result["time"], "14:30")
