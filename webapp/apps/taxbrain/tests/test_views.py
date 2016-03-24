from django.test import TestCase
from django.test import Client
import mock

from ..models import TaxSaveInputs
from ..models import convert_to_floats
from ..helpers import (expand_1D, expand_2D, expand_list, package_up_vars,
                     format_csv, arrange_totals_by_row, default_taxcalc_data)
from ..compute import (DropqCompute, MockCompute, MockFailedCompute,
                       NodeDownCompute)
import taxcalc
from taxcalc import Policy
from .utils import *

START_YEAR = 2016

class TaxBrainViewsTests(TestCase):
    ''' Test the views of this app. '''

    def setUp(self):
        # Every test needs a client.
        self.client = Client()

    def test_taxbrain_get(self):
        # Issue a GET request.
        response = self.client.get('/taxbrain/')

        # Check that the response is 200 OK.
        self.assertEqual(response.status_code, 200)

    def test_taxbrain_post(self):
        #Monkey patch to mock out running of compute jobs
        import sys
        webapp_views = sys.modules['webapp.apps.taxbrain.views']
        webapp_views.dropq_compute = MockCompute()

        data = {u'ID_BenefitSurtax_Switch_1': [u'True'],
                u'ID_BenefitSurtax_Switch_0': [u'True'],
                u'ID_BenefitSurtax_Switch_3': [u'True'],
                u'ID_BenefitSurtax_Switch_2': [u'True'],
                u'ID_BenefitSurtax_Switch_5': [u'True'],
                u'ID_BenefitSurtax_Switch_4': [u'True'],
                u'ID_BenefitSurtax_Switch_6': [u'True'],
                u'has_errors': [u'False'], u'II_em': [u'4333'],
                u'start_year': unicode(START_YEAR), 'csrfmiddlewaretoken':'abc123'}

        response = self.client.post('/taxbrain/', data)
        # Check that redirect happens
        self.assertEqual(response.status_code, 302)
        # Go to results page
        link_idx = response.url[:-1].rfind('/')
        self.failUnless(response.url[:link_idx+1].endswith("taxbrain/"))


    def test_taxbrain_post_no_behavior_entries(self):
        #Monkey patch to mock out running of compute jobs
        import sys
        webapp_views = sys.modules['webapp.apps.taxbrain.views']
        webapp_views.dropq_compute = MockCompute()

        # Provide behavioral input
        data = {u'ID_BenefitSurtax_Switch_1': [u'True'],
                u'ID_BenefitSurtax_Switch_0': [u'True'],
                u'ID_BenefitSurtax_Switch_3': [u'True'],
                u'ID_BenefitSurtax_Switch_2': [u'True'],
                u'ID_BenefitSurtax_Switch_5': [u'True'],
                u'ID_BenefitSurtax_Switch_4': [u'True'],
                u'ID_BenefitSurtax_Switch_6': [u'True'],
                u'has_errors': [u'False'], u'BE_inc': [u'0.1'],
                u'start_year': unicode(START_YEAR)}

        response = self.client.post('/taxbrain/', data)
        # Check that we get a 400
        self.assertEqual(response.status_code, 400)

    def test_taxbrain_nodes_down(self):
        #Monkey patch to mock out running of compute jobs
        import sys
        from webapp.apps.taxbrain import views as webapp_views
        webapp_views.dropq_compute = NodeDownCompute()

        data = {u'ID_BenefitSurtax_Switch_1': [u'True'],
                u'ID_BenefitSurtax_Switch_0': [u'True'],
                u'ID_BenefitSurtax_Switch_3': [u'True'],
                u'ID_BenefitSurtax_Switch_2': [u'True'],
                u'ID_BenefitSurtax_Switch_5': [u'True'],
                u'ID_BenefitSurtax_Switch_4': [u'True'],
                u'ID_BenefitSurtax_Switch_6': [u'True'],
                u'has_errors': [u'False'], u'II_em': [u'4333'],
                u'start_year': unicode(START_YEAR), 'csrfmiddlewaretoken':'abc123'}

        response = self.client.post('/taxbrain/', data)
        # Check that redirect happens
        self.assertEqual(response.status_code, 302)
        link_idx = response.url[:-1].rfind('/')
        self.failUnless(response.url[:link_idx+1].endswith("taxbrain/"))
        # One more redirect
        response = self.client.get(response.url)
        # Check that we successfully load the page
        response = self.client.get(response.url)
        self.assertEqual(response.status_code, 200)

    def test_taxbrain_failed_job(self):
        #Monkey patch to mock out running of compute jobs
        import sys
        from webapp.apps.taxbrain import views as webapp_views
        webapp_views.dropq_compute = MockFailedCompute()

        data = {u'ID_BenefitSurtax_Switch_1': [u'True'],
                u'ID_BenefitSurtax_Switch_0': [u'True'],
                u'ID_BenefitSurtax_Switch_3': [u'True'],
                u'ID_BenefitSurtax_Switch_2': [u'True'],
                u'ID_BenefitSurtax_Switch_5': [u'True'],
                u'ID_BenefitSurtax_Switch_4': [u'True'],
                u'ID_BenefitSurtax_Switch_6': [u'True'],
                u'has_errors': [u'False'], u'II_em': [u'4333'],
                u'start_year': unicode(START_YEAR), 'csrfmiddlewaretoken':'abc123'}

        response = self.client.post('/taxbrain/', data)
        # Check that redirect happens
        self.assertEqual(response.status_code, 302)
        link_idx = response.url[:-1].rfind('/')
        self.failUnless(response.url[:link_idx+1].endswith("taxbrain/"))
        response = self.client.get(response.url)
        # Make sure the failure message is in the response
        self.failUnless("Your calculation failed" in str(response))

    def test_taxbrain_has_growth_params(self):
        #Monkey patch to mock out running of compute jobs
        import sys
        webapp_views = sys.modules['webapp.apps.taxbrain.views']
        webapp_views.dropq_compute = MockCompute()

        reform = {'factor_adjustment': [u'0.03'],
                  'FICA_ss_trt': [u'0.11'],
                  'start_year': unicode(START_YEAR),
                  'has_errors': [u'False'],
                  'growth_choice': u'factor_adjustment'
                  }
        micro = do_micro_sim(self.client, reform)
