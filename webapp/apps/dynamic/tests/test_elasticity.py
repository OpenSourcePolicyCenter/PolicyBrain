from __future__ import print_function
from django.test import TestCase
from django.test import Client
import mock
import os
import json
os.environ["NUM_BUDGET_YEARS"] = '2'

from ...taxbrain.models import TaxSaveInputs
from ...taxbrain.models import convert_to_floats
from ...taxbrain.helpers import (expand_1D, expand_2D, expand_list, package_up_vars,
                                 format_csv, arrange_totals_by_row, default_taxcalc_data)
from ...taxbrain.compute import DropqCompute, MockCompute, ElasticMockCompute
import taxcalc
from taxcalc import Policy
from .utils import *


class DynamicElasticityViewsTests(TestCase):
    ''' Test the elasticity of GDP dynamic views of this app. '''

    def setUp(self):
        # Every test needs a client.
        self.client = Client()

    def test_elasticity_edit(self):
        import sys
        from webapp.apps.taxbrain import views
        webapp_views = sys.modules['webapp.apps.taxbrain.views']
        webapp_views.dropq_compute = MockCompute()

        # Do the microsim
        reform = {u'ID_BenefitSurtax_Switch_1': [u'True'],
                u'ID_BenefitSurtax_Switch_0': [u'True'],
                u'ID_BenefitSurtax_Switch_3': [u'True'],
                u'ID_BenefitSurtax_Switch_2': [u'True'],
                u'ID_BenefitSurtax_Switch_5': [u'True'],
                u'ID_BenefitSurtax_Switch_4': [u'True'],
                u'ID_BenefitSurtax_Switch_6': [u'True'],
                u'has_errors': [u'False'], u'II_em': [u'4333'],
                u'start_year': u'2016', 'csrfmiddlewaretoken': 'abc123'}

        micro1 = do_micro_sim(self.client, reform)

        # Do another microsim
        reform[u'II_em'] += [u'4334']
        micro2 = do_micro_sim(self.client, reform)

        # Do a third microsim
        reform[u'II_em'] += [u'4335']
        micro3 = do_micro_sim(self.client, reform)

        from webapp.apps.dynamic import views
        dynamic_views = sys.modules['webapp.apps.dynamic.views']
        dynamic_views.dropq_compute = ElasticMockCompute(num_times_to_wait=1)

        # Do the elasticity of GDP simulation based on the third microsim
        egdp_reform = {u'elastic_gdp': [u'0.4']}
        egdp_response = do_elasticity_sim(self.client, micro3, egdp_reform)
        orig_micro_model_num = micro3.url[-2:-1]

        # Now edit this elasticity of gdp sim
        # Go to macro input page
        egdp_num = egdp_response.url[egdp_response.url[:-1].rfind('/')+1:-1]
        dynamic_macro_edit = '/dynamic/macro/edit/{0}?start_year={1}'.format(egdp_num, START_YEAR)
        #Redirect first
        response = self.client.get(dynamic_macro_edit)
        self.assertEqual(response.status_code, 301)
        #Now load the page
        rep2 = self.client.get(response.url)
        page = rep2.content
        # Read the page to find the linked microsim. It should be the third
        # microsim above
        idx = page.find('dynamic/macro')
        idx_ms_num_start = idx + 14
        idx_ms_num_end = idx_ms_num_start + page[idx_ms_num_start:].find('/') 
        microsim_model_num = page[idx_ms_num_start:idx_ms_num_end]
        assert microsim_model_num == orig_micro_model_num

    def test_elasticity_reform_from_file(self):
        import sys
        from webapp.apps.taxbrain import views
        webapp_views = sys.modules['webapp.apps.taxbrain.views']
        webapp_views.dropq_compute = MockCompute()
        # Do the microsim from file
        fname = "../../taxbrain/tests/test_reform.json"
        micro1 = do_micro_sim_from_file(self.client, fname)

        from webapp.apps.dynamic import views
        dynamic_views = sys.modules['webapp.apps.dynamic.views']
        dynamic_views.dropq_compute = ElasticMockCompute(num_times_to_wait=1)

        # Do the partial equilibrium simulation based on the microsim
        el_reform = {u'elastic_gdp': [u'0.4']}
        el_response = do_elasticity_sim(self.client, micro1, el_reform)
        orig_micro_model_num = micro1.url[-2:-1]
        from webapp.apps.dynamic import views
        post = views.dropq_compute.last_posted
        # Verify that partial equilibrium job submitted with proper
        # SS_Earnings_c with wildcards filled in properly
        beh_params = json.loads(json.loads(post['elasticity_params']))
        assert beh_params["elastic_gdp"][0]  == 0.4
