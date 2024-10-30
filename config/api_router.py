from django.conf import settings
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from abantether.orders.api.views import OrderViewSet
from abantether.users.api.views import UserViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("users", UserViewSet)
router.register(r'orders', OrderViewSet, basename='order')

app_name = "api"
urlpatterns = router.urls
