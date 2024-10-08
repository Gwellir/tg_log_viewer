# Generated by Django 3.0.7 on 2022-12-28 22:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mainapp', '0005_auto_20221227_1818'),
    ]

    operations = [
        migrations.AddField(
            model_name='mediafile',
            name='hash',
            field=models.SlugField(max_length=8, null=True, verbose_name='CRC32 hash'),
        ),
        migrations.AddField(
            model_name='mediafile',
            name='size',
            field=models.IntegerField(null=True, verbose_name='file size'),
        ),
        migrations.AlterField(
            model_name='mediafile',
            name='media_type',
            field=models.CharField(db_index=True, max_length=50, null=True, verbose_name='media_type as in TG log format'),
        ),
    ]
