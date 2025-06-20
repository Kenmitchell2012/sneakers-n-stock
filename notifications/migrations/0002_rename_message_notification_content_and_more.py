# Generated by Django 4.2.21 on 2025-06-16 01:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='notification',
            old_name='message',
            new_name='content',
        ),
        migrations.AddField(
            model_name='notification',
            name='notification_type',
            field=models.CharField(choices=[('order_shipped', 'Order Shipped'), ('order_canceled', 'Order Canceled'), ('tracking_update', 'Tracking Number Updated'), ('general', 'General Notification')], default='general', max_length=50),
        ),
    ]
