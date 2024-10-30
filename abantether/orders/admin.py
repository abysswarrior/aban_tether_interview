from django.contrib import admin

from abantether.orders.models import Order, Wallet

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    pass

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    pass
