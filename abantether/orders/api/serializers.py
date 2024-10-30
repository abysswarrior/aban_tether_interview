from rest_framework import serializers
from ..models import Order

class OrderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['coin_name', 'amount']

class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['id', 'coin_name', 'amount', 'status', 'created_at']
