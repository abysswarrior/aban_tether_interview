from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from unittest.mock import patch
from abantether.orders.models import Order, Wallet
from abantether.orders.services import OrderService, CoinPriceService
from abantether.orders.tests.mocks import MockRedis

User = get_user_model()


class MultipleOrdersTestCase(TestCase):
    def setUp(self):
        self.order_service = OrderService()
        self.mock_redis = MockRedis()
        self.order_service.redis_client = self.mock_redis

        # Create three users with wallets
        self.users = []
        for i in range(3):
            user = User.objects.create_user(username=f'testuser{i}', password='12345')
            Wallet.objects.create(user=user, balance=Decimal('100.00'))
            self.users.append(user)

    @patch.object(CoinPriceService, 'get_coin_price')
    @patch.object(OrderService, '_buy_from_exchange')
    def test_multiple_users_order_processing(self, mock_buy_from_exchange, mock_get_coin_price):
        mock_get_coin_price.return_value = Decimal('4.00')

        # Create orders for three users
        orders = []
        for user in self.users:
            order = self.order_service.create_order(user, 'ABAN', Decimal('1'))
            orders.append(order)

            # Check wallet balance after each order
            wallet = Wallet.objects.get(user=user)
            self.assertEqual(wallet.balance, Decimal('96.00'))


        # After the last order, _buy_from_exchange should be called once
        mock_buy_from_exchange.assert_called_once_with('ABAN', Decimal('12'))

        # Check final status of orders
        for order in orders:
            order.refresh_from_db()
            self.assertEqual(order.status, Order.COMPLETED)

        # Check that Redis was cleared
        pending_orders = self.mock_redis.zrange('pending_orders:ABAN', 0, -1)
        self.assertEqual(len(pending_orders), 0)

        # Double-check final wallet balances
        for user in self.users:
            wallet = Wallet.objects.get(user=user)
            self.assertEqual(wallet.balance, Decimal('96.00'))
