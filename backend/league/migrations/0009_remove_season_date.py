from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('league', '0008_championseasonstats_remove_champion_kda_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql="DROP INDEX IF EXISTS seasons_date_c884ea_idx;",
            reverse_sql="CREATE INDEX IF NOT EXISTS seasons_date_c884ea_idx ON seasons(date);",
        ),
        migrations.AlterModelOptions(
            name='season',
            options={'db_table': 'seasons', 'ordering': ['name']},
        ),
        migrations.RunSQL(
            sql="ALTER TABLE seasons DROP COLUMN IF EXISTS date;",
            reverse_sql=(
                "ALTER TABLE seasons ADD COLUMN IF NOT EXISTS date date; "
                "UPDATE seasons SET date = CURRENT_DATE WHERE date IS NULL; "
                "ALTER TABLE seasons ALTER COLUMN date SET NOT NULL;"
            ),
        ),
    ]

