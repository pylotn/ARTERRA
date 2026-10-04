from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("catalog/", views.catalog, name="catalog"),
    path("catalog/<slug:slug>/", views.category_artworks, name="category"),
    path("artwork/<slug:slug>/", views.artwork_detail, name="artwork_detail"),
    path("cart/", views.cart, name="cart"),
    path("cart/add/<int:artwork_id>/", views.cart_add, name="cart_add"),
    path("cart/change/<int:artwork_id>/<str:action>/", views.cart_change, name="cart_change", ),
    path("cart/remove/<int:artwork_id>/", views.cart_remove, name="cart_remove", ),
    path("checkout/", views.checkout, name="checkout"),
    path("account/orders/", views.my_orders, name="my_orders"),
    path("account/orders/<int:order_id>/", views.order_detail, name="order_detail"),
    path("order/success/<int:order_id>/", views.order_success, name="order_success", ),
    path("login/", views.user_login, name="login"),
    path("logout/", views.user_logout, name="logout"),
    path("register/", views.register, name="register"),

]
