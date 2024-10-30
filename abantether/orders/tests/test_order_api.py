from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from abantether.orders.models import Order, Wallet

User = get_user_model()

class OrderAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.wallet = Wallet.objects.create(user=self.user, balance=Decimal('100.00'))
        self.client.force_authenticate(user=self.user)

    def test_create_order_api(self):
        response = self.client.post('/api/orders/', {
            'coin_name': 'ABAN',
            'amount': '1.0'
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Order.objects.count(), 1)
