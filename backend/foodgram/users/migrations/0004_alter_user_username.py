# Generated by Django 3.2 on 2023-12-13 13:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_auto_20231213_1340'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='username',
            field=models.CharField(max_length=128, unique=True, verbose_name='Имя пользователя'),
        ),
    ]