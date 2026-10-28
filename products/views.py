import stripe
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, HttpResponseBadRequest
from django.conf import settings
from django.shortcuts import render, redirect, reverse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import Order

stripe.api_key = settings.STRIPE_API_KEY


# PRICE_IDS = ['YOUR PRICE ID']
# @login_required
# def products(request):
#     price_objs = [stripe.Price.retrieve(pid) for pid in PRICE_IDS]

#     if request.method == 'POST':
#         price_id = request.POST.get('price_id')

#         order = Order.objects.create(
#             user = request.user,
#             stripe_session_id = '',
#             amount = 1,
#             paid = False
#         )

#         checkout_session = stripe.checkout.Session.create(
#             line_items = [
#                 {
#                     'price': price_id,
#                     'quantity': 1
#                 }
#             ],
#             mode = 'payment',
#             success_url=request.build_absolute_uri(reverse("products")) + "?success=1&session_id={CHECKOUT_SESSION_ID}",
#             cancel_url=request.build_absolute_uri(reverse("products")) + "?canceled=1",
#             metadata={'order_id': order.pk}
#         )

#         order.stripe_session_id = checkout_session.id
#         order.amount = checkout_session.amount_total
#         order.save()

#         return redirect(checkout_session.url, code=303)

#     return render(request, 'products.html', {'prices': price_objs})



@login_required
def products(request):
    PRICE = 500  # $5.00
    orders = Order.objects.filter(user=request.user)

    if request.method == 'POST':
        order = Order.objects.create(
            user=request.user,
            amount=PRICE,
        )

        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': 'Mouse',
                        },
                        'unit_amount': PRICE,
                    },
                    'quantity': 1,
                }
            ],
            mode='payment',
            success_url=request.build_absolute_uri(reverse("products")) + "?success=1&session_id={CHECKOUT_SESSION_ID}",
            cancel_url=request.build_absolute_uri(reverse("products")) + "?canceled=1",
            metadata={'order_id': order.pk}
        )

        order.stripe_session_id = checkout_session.id
        order.save()

        return redirect(checkout_session.url, code=303)
    return render(request, 'products.html', {'price': PRICE, 'orders': orders})


@csrf_exempt
def stripe_webhook(request):
    secret = settings.STRIPE_WEBHOOK_SECRET

    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponseBadRequest()

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        order_id = session['metadata'].get('order_id')

        Order.objects.filter(pk=order_id, status=Order.Status.PENDING).update(status=Order.Status.PAID, payment_intent_id=session.get('payment_intent'))
    elif event['type'] == 'charge.refunded':
        charge = event['data']['object']
        payment_intent_id = charge.get('payment_intent')

        Order.objects.filter(payment_intent_id=payment_intent_id, status=Order.Status.PAID).update(status=Order.Status.REFUNDED)

    return HttpResponse(status=200)


@staff_member_required
@login_required
@require_POST
def refund_order(request, order_id):
    try:
        order = Order.objects.get(pk=order_id, user=request.user)
    except Order.DoesNotExist:
        return HttpResponseBadRequest("Order not found.")

    if order.status != Order.Status.PAID:
        return HttpResponseBadRequest("Only paid orders can be refunded.")
    
    if not order.payment_intent_id:
        return HttpResponseBadRequest("No payment intent associated with this order.")

    try:
        stripe.Refund.create(
            payment_intent=order.payment_intent_id,
        )
    except stripe.error.StripeError as e:
        return HttpResponseBadRequest(f"Stripe error: {str(e)}")

    return redirect('products')
