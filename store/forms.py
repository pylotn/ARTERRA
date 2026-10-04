from django import forms


class CheckoutForm(forms.Form):
    customer_name = forms.CharField(
        label="Имя",
        max_length=150
    )

    phone = forms.CharField(
        label="Телефон",
        max_length=30
    )

    email = forms.EmailField(
        label="Email",
        required=False
    )

    address = forms.CharField(
        label="Адрес доставки",
        widget=forms.Textarea
    )