# Generated by Django 5.0.6 on 2024-06-24 01:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('items', '0002_alter_category_options_items'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='items',
            options={'ordering': ('name',), 'verbose_name_plural': 'Items'},
        ),
        migrations.AlterField(
            model_name='items',
            name='description',
            field=models.CharField(blank=True, max_length=455, null=True),
        ),
        migrations.AlterField(
            model_name='items',
            name='image',
            field=models.ImageField(default='default_image.jpg', upload_to='item_images'),
            preserve_default=False,
        ),
    ]
