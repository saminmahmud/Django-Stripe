from django.urls import path
from .views import products, stripe_webhook, refund_order

urlpatterns = [
    path('products/', products, name='products'),
    path('payment/stripe_webhook', stripe_webhook, name='stripe-webhook'),
    path('refund/<int:order_id>/', refund_order, name='refund_order'),
]