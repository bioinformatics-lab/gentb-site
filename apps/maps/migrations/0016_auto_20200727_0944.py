# Generated by Django 2.2.13 on 2020-07-27 13:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('maps', '0015_auto_20200724_1338'),
    ]

    operations = [
        migrations.AlterField(
            model_name='countrydetail',
            name='world_bank_gdp',
            field=models.CharField(blank=True, help_text='GDP (current US$)', max_length=36, null=True),
        ),
    ]
