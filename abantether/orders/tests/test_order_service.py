from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from abantether.orders.models import Order, Wallet
from abantether.orders.services import OrderService

User = get_user_model()


class OrderServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.wallet = Wallet.objects.create(user=self.user, balance=Decimal('100.00'))
        self.service = OrderService()

    def test_create_order_success(self):
        order = self.service.create_order(self.user, 'ABAN', Decimal('1.0'))
        self.assertEqual(order.status, Order.PENDING)
        self.assertEqual(order.amount, Decimal('1.0'))

        # Check wallet balance was decreased
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('96.00'))

    def test_create_order_insufficient_funds(self):
        with self.assertRaises(ValidationError):
            self.service.create_order(self.user, 'ABAN', Decimal('100.0'))

