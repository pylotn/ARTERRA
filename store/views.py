from decimal import Decimal
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django import forms
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from .forms import CheckoutForm
from .models import Artwork, Category, Order, OrderItem


def home(request):
    categories = Category.objects.all()
    active_artworks_count = Artwork.objects.filter(is_active=True).count()
    featured_artworks = Artwork.objects.filter(
        is_active=True,
        featured=True,
    )[:8]

    return render(
        request,
        "store/home.html",
        {
            "categories": categories,
            "active_artworks_count": active_artworks_count,
            "featured_artworks": featured_artworks,
        },
    )


def catalog(request):
    artworks = Artwork.objects.filter(is_active=True)
    return render(request, "store/catalog.html", {"artworks": artworks})


def category_artworks(request, slug):
    category = get_object_or_404(Category, slug=slug)
    artworks = Artwork.objects.filter(category=category, is_active=True)
    return render(
        request,
        "store/catalog.html",
        {"artworks": artworks, "category": category},
    )


def artwork_detail(request, slug):
    artwork = get_object_or_404(Artwork, slug=slug, is_active=True)
    return render(request, "store/artwork_detail.html", {"artwork": artwork})


def _get_cart(request):
    # вспомогательная функция. Она сама не связана с URL. Её запускают другие функции.
    # Получить корзину из сессии →
    # проверить и очистить её от неправильных данных →
    # сохранить исправленную версию → вернуть её.
    stored_cart = request.session.get("cart", {})
    if not isinstance(stored_cart, dict):
        stored_cart = {}

    cart = {}
    for artwork_id, quantity in stored_cart.items():
        try:
            artwork_id = str(int(artwork_id))
            quantity = int(quantity)
        except (TypeError, ValueError):
            continue

        if int(artwork_id) > 0 and quantity > 0:
            cart[artwork_id] = quantity

    if cart != stored_cart:
        request.session["cart"] = cart
    return cart


def _get_cart_items(request):
    # какие реальные товары лежат в корзине + сколько их + сколько всё стоит.
    cart = _get_cart(request)
    artworks = list(
        Artwork.objects.filter(id__in=cart.keys(), is_active=True)
    )

    valid_cart = {str(artwork.id): cart[str(artwork.id)] for artwork in artworks}
    if valid_cart != cart:
        request.session["cart"] = valid_cart
        cart = valid_cart

    total = Decimal("0.00")
    for artwork in artworks:
        artwork.cart_quantity = cart[str(artwork.id)]
        artwork.line_total = artwork.price * artwork.cart_quantity
        total += artwork.price * artwork.cart_quantity

    return cart, artworks, total


def cart_add(request, artwork_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    get_object_or_404(Artwork, id=artwork_id, is_active=True)
    cart = _get_cart(request)
    key = str(artwork_id)
    cart[key] = cart.get(key, 0) + 1
    request.session["cart"] = cart
    return redirect("cart")


def cart(request):
    cart, artworks, total = _get_cart_items(request)
    return render(
        request,
        "store/cart.html",
        {"artworks": artworks, "cart": cart, "total": total},
    )


def cart_change(request, artwork_id, action):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    cart = _get_cart(request)
    key = str(artwork_id)

    if key not in cart:
        return redirect("cart")

    if action == "plus":
        cart[key] += 1
    elif action == "minus":
        if cart[key] > 1:
            cart[key] -= 1
        else:
            cart.pop(key)

    request.session["cart"] = cart
    return redirect("cart")


def cart_remove(request, artwork_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    cart = _get_cart(request)
    cart.pop(str(artwork_id), None)
    request.session["cart"] = cart
    return redirect("cart")


@login_required
def checkout(request):
    cart, artworks, total = _get_cart_items(request)
    if not artworks:
        return redirect("cart")

    form = CheckoutForm(
        request.POST if request.method == "POST" else None
    )
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            order = Order.objects.create(
                customer_name=form.cleaned_data["customer_name"],
                phone=form.cleaned_data["phone"],
                email=form.cleaned_data["email"],
                address=form.cleaned_data["address"],
                total_price=total,
            )

            OrderItem.objects.bulk_create(
                [
                    OrderItem(
                        order=order,
                        artwork=artwork,
                        price=artwork.price,
                        quantity=artwork.cart_quantity,
                    )
                    for artwork in artworks
                ]
            )

        request.session["cart"] = {}
        return redirect("order_success", order_id=order.id)

    return render(
        request,
        "store/checkout.html",
        {"form": form, "artworks": artworks, "total": total},
    )


@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "store/my_orders.html", {"orders": orders})


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related("items__artwork"),
        id=order_id,
        user=request.user,
    )
    return render(request, "store/order_detail.html", {"order": order})


@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "store/order_success.html", {"order": order})


def user_login(request):
    error = None
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username", ""),
            password=request.POST.get("password", ""),
        )
        if user is not None:
            login(request, user)
            next_url = request.POST.get("next") or request.GET.get("next")
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}
            ):
                return redirect(next_url)
            return redirect("home")
        error = "Неверное имя пользователя или пароль."

    return render(request, "store/login.html", {"error": error})


def user_logout(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    logout(request)
    return redirect("home")


def register(request):
    if request.method != "POST":
        return render(request, "store/register.html")

    username = request.POST.get("username", "").strip()
    email = request.POST.get("email", "").strip()
    password = request.POST.get("password", "")
    password_confirm = request.POST.get("password_confirm", "")
    errors = []

    if not username:
        errors.append("Укажи имя пользователя.")
    if not password:
        errors.append("Укажи пароль.")
    elif password != password_confirm:
        errors.append("Пароли не совпадают.")
    if username and User.objects.filter(username=username).exists():
        errors.append("Такое имя пользователя уже существует.")
    if username:
        try:
            User._meta.get_field("username").clean(username, None)
        except ValidationError as exc:
            errors.extend(exc.messages)
    try:
        email = forms.EmailField().clean(email)
    except ValidationError as exc:
        errors.extend(exc.messages)
    if password:
        try:
            validate_password(password)
        except ValidationError as exc:
            errors.extend(exc.messages)

    if not errors:
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )
        login(request, user)
        return redirect("home")

    return render(
        request,
        "store/register.html",
        {
            "errors": errors,
            "username_value": username,
            "email_value": email,
        },
    )
