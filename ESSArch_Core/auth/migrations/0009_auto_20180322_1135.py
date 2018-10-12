from django.apps import apps as global_apps
from django.db import connection, migrations

def db_table_exists(table_name):
    return table_name in connection.introspection.table_names()

def forwards(apps, schema_editor):
    if not db_table_exists('ess.auth_userprofile'):
        return

    with connection.schema_editor() as editor:
        editor.execute(editor.sql_delete_table % {
            "table": editor.quote_name("essauth_userprofile"),
        }) 

        editor.execute(editor.sql_delete_table % {
            "table": editor.quote_name("essauth_notification"),
        }) 

        editor.execute(editor.sql_rename_table % {
            "old_table": editor.quote_name('ess.auth_userprofile'),
            "new_table": editor.quote_name("essauth_userprofile"),
        })

        editor.execute(editor.sql_rename_table % {
            "old_table": editor.quote_name("ess.auth_notification"),
            "new_table": editor.quote_name("essauth_notification"),
        })

class Migration(migrations.Migration):
    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop, atomic=False),
    ]
    dependencies = [
        ('essauth', '0008_auto_20180209_1453'),
    ]
