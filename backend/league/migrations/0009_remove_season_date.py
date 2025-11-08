from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('league', '0008_championseasonstats_remove_champion_kda_and_more'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='season',
            name='seasons_date_c884ea_idx',
        ),
        migrations.AlterModelOptions(
            name='season',
            options={'db_table': 'seasons', 'ordering': ['name']},
        ),
        migrations.RemoveField(
            model_name='season',
            name='date',
        ),
    ]

