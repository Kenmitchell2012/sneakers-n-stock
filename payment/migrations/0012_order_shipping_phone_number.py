# Generated by Django 4.2.21 on 2025-06-02 02:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payment', '0011_remove_order_date_ordered_remove_order_date_shipped_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='shipping_phone_number',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
    ]
