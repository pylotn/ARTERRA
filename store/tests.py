from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Artwork, Category, Order, OrderItem


class StoreFlowTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Абстракция", slug="abstract")
        self.artwork = Artwork.objects.create(
            title="Тестовая работа",
            slug="test-artwork",
            description="Описание работы",
            image="artworks/test.jpg",
            price=Decimal("1250.00"),
            category=self.category,
            featured=True,
        )
        self.user = User.objects.create_user(
            username="collector",
            password="Secure-test-password-471!",
        )

    def test_home_catalog_and_artwork_detail_render(self):
        for url in (
            reverse("home"),
            reverse("catalog"),
            reverse("category", args=[self.category.slug]),
            reverse("artwork_detail", args=[self.artwork.slug]),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_cart_changes_require_post_and_total_uses_quantity(self):
        add_url = reverse("cart_add", args=[self.artwork.id])
        self.assertEqual(self.client.get(add_url).status_code, 405)
        self.assertEqual(self.client.post(add_url).status_code, 302)
        self.client.post(add_url)

        response = self.client.get(reverse("cart"))

        self.assertContains(response, "2500,00 ₸")
        change_url = reverse("cart_change", args=[self.artwork.id, "minus"])
        self.assertEqual(self.client.get(change_url).status_code, 405)
        self.client.post(change_url)
        self.assertEqual(self.client.session["cart"][str(self.artwork.id)], 1)

    def test_checkout_creates_order_and_clears_cart(self):
        self.client.force_login(self.user)
        session = self.client.session
        session["cart"] = {str(self.artwork.id): 2}
        session.save()

        response = self.client.post(
            reverse("checkout"),
            {
                "customer_name": "Тестовый покупатель",
                "phone": "+77000000000",
                "email": "collector@example.com",
                "address": "Алматы, тестовый адрес",
            },
        )

        self.assertEqual(response.status_code, 302)
        order = Order.objects.get(user=self.user)
        item = OrderItem.objects.get(order=order)
        self.assertEqual(order.total_price, Decimal("2500.00"))
        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.line_total, Decimal("2500.00"))
        self.assertEqual(self.client.session["cart"], {})
        self.assertEqual(
            response.url,
            reverse("order_success", args=[order.id]),
        )

    def test_orders_are_private_to_their_owner(self):
        order = Order.objects.create(
            user=self.user,
            customer_name="Покупатель",
            phone="123",
            address="Адрес",
            total_price=Decimal("1250.00"),
        )
        self.client.force_login(User.objects.create_user("other", password="another-secure-pass-829!"))

        response = self.client.get(reverse("order_detail", args=[order.id]))

        self.assertEqual(response.status_code, 404)

    def test_deleting_account_preserves_order_record(self):
        order = Order.objects.create(
            user=self.user,
            customer_name="Покупатель",
            phone="123",
            address="Адрес",
            total_price=Decimal("1250.00"),
        )

        self.user.delete()

        order.refresh_from_db()
        self.assertIsNone(order.user)

    def test_registration_rejects_weak_password(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "new-collector",
                "email": "new@example.com",
                "password": "123",
                "password_confirm": "123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "минимум 8 символов")
        self.assertFalse(User.objects.filter(username="new-collector").exists())

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.assertEqual(self.client.post(reverse("logout")).status_code, 302)

    def test_login_and_registration_pages_render(self):
        self.assertEqual(self.client.get(reverse("login")).status_code, 200)
        self.assertEqual(self.client.get(reverse("register")).status_code, 200)

    def test_authenticated_order_pages_render(self):
        order = Order.objects.create(
            user=self.user,
            customer_name="Покупатель",
            phone="123",
            address="Адрес",
            total_price=Decimal("1250.00"),
        )
        self.client.force_login(self.user)

        self.assertEqual(self.client.get(reverse("my_orders")).status_code, 200)
        self.assertEqual(
            self.client.get(reverse("order_detail", args=[order.id])).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(reverse("order_success", args=[order.id])).status_code,
            200,
        )
