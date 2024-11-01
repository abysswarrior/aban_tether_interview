from decimal import Decimal
from typing import List
import json
import redis
from django.conf import settings
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Order, Wallet


class CoinPriceService:
    # In a real application, this would fetch from a price feed
    COIN_PRICES = {
        'ABAN': Decimal('4.00'),
    }

    @classmethod
    def get_coin_price(cls, coin_name: str) -> Decimal:
        return cls.COIN_PRICES.get(coin_name)


class OrderService:
    MIN_EXCHANGE_ORDER_VALUE = Decimal('10.00')

    def __init__(self):
        self.coin_price_service = CoinPriceService()
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True
        )

    @transaction.atomic
    def create_order(self, user, coin_name: str, amount: Decimal) -> Order:
        price = self.coin_price_service.get_coin_price(coin_name)
        if not price:
            raise ValidationError(f"Invalid coin: {coin_name}")

        total_value = price * amount

        # Check and update user's wallet
        wallet = Wallet.objects.select_for_update().get(user=user)
        if wallet.balance < total_value:
            raise ValidationError("Insufficient funds")

        wallet.balance -= total_value
        wallet.save()

        # Create order
        order = Order.objects.create(
            user=user,
            coin_name=coin_name,
            amount=amount,
            status=Order.PENDING
        )

        # Add order to Redis
        self._add_pending_order_to_redis(order)
        self._process_pending_orders(coin_name)

        return order

    def _add_pending_order_to_redis(self, order: Order) -> None:
        """Add a pending order to Redis"""
        pending_orders_key = f"pending_orders:{order.coin_name}"
        order_data = {
            'id': order.id,
            'amount': str(order.amount)  # Convert Decimal to string for JSON serialization
        }

        # Use Redis transaction to ensure atomicity
        with self.redis_client.pipeline() as pipe:
            pipe.multi()
            # Add order to sorted set with timestamp as score for order preservation
            pipe.zadd(pending_orders_key, {json.dumps(order_data): order.created_at.timestamp()})
            pipe.execute()

    def _process_pending_orders(self, coin_name: str) -> None:
        """Process pending orders from Redis"""
        pending_orders_key = f"pending_orders:{coin_name}"

        # Get all pending orders for this coin
        pending_orders_data = self.redis_client.zrange(pending_orders_key, 0, -1)

        if not pending_orders_data:
            return

        total_amount = Decimal('0')
        order_ids = []

        # Calculate total amount and collect order IDs
        for order_json in pending_orders_data:
            order_data = json.loads(order_json)
            total_amount += Decimal(order_data['amount'])
            order_ids.append(order_data['id'])

        total_value = total_amount * self.coin_price_service.get_coin_price(coin_name)

        if total_value >= self.MIN_EXCHANGE_ORDER_VALUE:
            try:
                # Execute the exchange order
                self._buy_from_exchange(coin_name, total_value)

                # Update orders in database
                Order.objects.filter(id__in=order_ids).update(status=Order.COMPLETED)

                # Remove processed orders from Redis
                self.redis_client.delete(pending_orders_key)

            except Exception as e:
                # Mark orders as failed in database
                Order.objects.filter(id__in=order_ids).update(status=Order.FAILED)
                # Remove failed orders from Redis
                self.redis_client.delete(pending_orders_key)
                raise e

    def _buy_from_exchange(self, coin_name: str, total_value: Decimal) -> None:
        # Implementation for external exchange interaction
        pass
