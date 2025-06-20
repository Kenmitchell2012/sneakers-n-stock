# Generated by Django 4.2.21 on 2025-06-02 02:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payment', '0010_alter_order_options_order_created_at_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='date_ordered',
        ),
        migrations.RemoveField(
            model_name='order',
            name='date_shipped',
        ),
        migrations.RemoveField(
            model_name='order',
            name='shipped',
        ),
        migrations.AddField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('shipped', 'Shipped'), ('delivered', 'Delivered'), ('canceled', 'Canceled')], default='pending', max_length=20),
        ),
        migrations.AlterField(
            model_name='order',
            name='amount_paid',
            field=models.FloatField(),
        ),
        migrations.AlterField(
            model_name='order',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='order',
            name='email',
            field=models.EmailField(max_length=254),
        ),
        migrations.AlterField(
            model_name='order',
            name='full_name',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='order',
            name='shipping_address',
            field=models.TextField(),
        ),
    ]
