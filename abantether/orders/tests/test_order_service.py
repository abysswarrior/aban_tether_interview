from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from unittest.mock import patch, MagicMock
import json
from django.core.exceptions import ValidationError
from abantether.orders.models import Order, Wallet
from abantether.orders.services import OrderService, CoinPriceService
from abantether.orders.tests.mocks import MockRedis

User = get_user_model()

class OrderServiceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.wallet = Wallet.objects.create(user=self.user, balance=Decimal('100.00'))
        self.order_service = OrderService()
        self.mock_redis = MockRedis()
        self.order_service.redis_client = self.mock_redis

    @patch.object(CoinPriceService, 'get_coin_price')
    def test_create_order_success(self, mock_get_coin_price):
        mock_get_coin_price.return_value = Decimal('4.00')

        order = self.order_service.create_order(self.user, 'ABAN', Decimal('1'))

        self.assertEqual(order.status, Order.PENDING)
        self.assertEqual(order.amount, Decimal('1'))
        self.assertEqual(Wallet.objects.get(user=self.user).balance, Decimal('96.00'))

        # Check if order was added to Redis
        pending_orders = self.mock_redis.zrange('pending_orders:ABAN', 0, -1)
        self.assertEqual(len(pending_orders), 1)
        order_data = json.loads(pending_orders[0])
        self.assertEqual(order_data['id'], order.id)
        self.assertEqual(order_data['amount'], str(order.amount))

    @patch.object(CoinPriceService, 'get_coin_price')
    def test_create_order_insufficient_funds(self, mock_get_coin_price):
        mock_get_coin_price.return_value = Decimal('4.00')

        with self.assertRaises(ValidationError):
            self.order_service.create_order(self.user, 'ABAN', Decimal('30'))

    @patch.object(CoinPriceService, 'get_coin_price')
    @patch.object(OrderService, '_buy_from_exchange')
    def test_process_pending_orders_below_threshold(self, mock_buy_from_exchange, mock_get_coin_price):
        mock_get_coin_price.return_value = Decimal('4.00')

        # Create an order below the threshold
        self.order_service.create_order(self.user, 'ABAN', Decimal('1'))

        # Check that _buy_from_exchange was not called
        mock_buy_from_exchange.assert_not_called()

        # Check that the order is still in Redis
        pending_orders = self.mock_redis.zrange('pending_orders:ABAN', 0, -1)
        self.assertEqual(len(pending_orders), 1)

    @patch.object(CoinPriceService, 'get_coin_price')
    @patch.object(OrderService, '_buy_from_exchange')
    def test_process_pending_orders_above_threshold(self, mock_buy_from_exchange, mock_get_coin_price):
        mock_get_coin_price.return_value = Decimal('4.00')

        # Create orders above the threshold
        order1 = self.order_service.create_order(self.user, 'ABAN', Decimal('1'))
        order2 = self.order_service.create_order(self.user, 'ABAN', Decimal('1.5'))

        # Check that _buy_from_exchange was called
        mock_buy_from_exchange.assert_called_once_with('ABAN', Decimal('10'))

        # Check that orders were updated in the database
        order1.refresh_from_db()
        order2.refresh_from_db()
        self.assertEqual(order1.status, Order.COMPLETED)
        self.assertEqual(order2.status, Order.COMPLETED)

        # Check that Redis was cleared
        pending_orders = self.mock_redis.zrange('pending_orders:ABAN', 0, -1)
        self.assertEqual(len(pending_orders), 0)

    @patch.object(CoinPriceService, 'get_coin_price')
    @patch.object(OrderService, '_buy_from_exchange')
    def test_process_pending_orders_exchange_failure(self, mock_buy_from_exchange, mock_get_coin_price):
        mock_get_coin_price.return_value = Decimal('4.00')
        mock_buy_from_exchange.side_effect = Exception("Exchange error")

        # Create orders above the threshold
        with self.assertRaises(Exception):
            order1 = self.order_service.create_order(self.user, 'ABAN', Decimal('1'))
            order2 = self.order_service.create_order(self.user, 'ABAN', Decimal('1.5'))

            # Check that orders were updated in the database
            order1.refresh_from_db()
            order2.refresh_from_db()
            self.assertEqual(order1.status, Order.FAILED)
            self.assertEqual(order2.status, Order.FAILED)

            # Check that Redis was cleared
            pending_orders = self.mock_redis.zrange('pending_orders:ABAN', 0, -1)
            self.assertEqual(len(pending_orders), 0)
