# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('taxbrain', '0054_outputurl_webapp_vers'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='taxsaveinputs',
            name='reform_style',
        ),
    ]
