# Generated by Django 5.0.6 on 2024-10-31 01:29

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('payment', '0002_rename_address_shippingaddress_shipping_address_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='shippingaddress',
            old_name='shipping_fullname',
            new_name='shipping_full_name',
        ),
    ]