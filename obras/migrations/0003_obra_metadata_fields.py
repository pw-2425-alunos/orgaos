from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("obras", "0002_nota"),
    ]

    operations = [
        migrations.AddField(
            model_name="obra",
            name="ano",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="obra",
            name="descricao_fisica",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="obra",
            name="efectivo_orgao",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name="obra",
            name="efectivo_vocal",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="obra",
            name="genero",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="obra",
            name="onomastica",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="obra",
            name="referencias",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="obra",
            name="tonalidade",
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
