# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('taxbrain', '0045_taxsaveinputs_ald_invinc_ec_base_ryanbrady'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='taxsaveinputs',
            name='CTC_new_ps',
        ),
    ]
