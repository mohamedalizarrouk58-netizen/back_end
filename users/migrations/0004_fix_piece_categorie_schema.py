from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_categoriemateriel_materiel_categorie'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE users_piece
                ADD COLUMN IF NOT EXISTS categorie_id bigint NULL;

                CREATE INDEX IF NOT EXISTS users_piece_categorie_id_idx
                ON users_piece (categorie_id);

                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'users_piece_categorie_id_fk'
                    ) THEN
                        ALTER TABLE users_piece
                        ADD CONSTRAINT users_piece_categorie_id_fk
                        FOREIGN KEY (categorie_id)
                        REFERENCES users_categoriemateriel(id)
                        ON DELETE SET NULL
                        DEFERRABLE INITIALLY DEFERRED;
                    END IF;
                END
                $$;

                ALTER TABLE users_materiel
                DROP COLUMN IF EXISTS categorie_id CASCADE;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
