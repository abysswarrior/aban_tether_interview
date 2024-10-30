from decimal import Decimal
from typing import List
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

        self._process_pending_orders(coin_name)
        return order

    def _process_pending_orders(self, coin_name: str) -> None:
        pending_orders = Order.objects.filter(
            status=Order.PENDING,
            coin_name=coin_name
        ).select_for_update()

        total_amount = sum(
            order.amount for order in pending_orders
        )
        total_value = total_amount * self.coin_price_service.get_coin_price(coin_name)

        if total_value >= self.MIN_EXCHANGE_ORDER_VALUE:
            self._execute_exchange_orders(pending_orders, coin_name, total_amount)

    def _execute_exchange_orders(self, orders: List[Order], coin_name: str, total_amount: Decimal) -> None:
        try:
            self._buy_from_exchange(coin_name, total_amount)
            orders.update(status=Order.COMPLETED)
        except Exception as e:
            orders.update(status=Order.FAILED)
            raise e

    def _buy_from_exchange(self, coin_name: str, amount: Decimal) -> None:
        # This would be implemented to interact with external exchange
        pass
