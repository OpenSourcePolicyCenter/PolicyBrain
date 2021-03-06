from django.test import Client
import pytest
import mock
import os
# os.environ["NUM_BUDGET_YEARS"] = '2'

from ...taxbrain.models import TaxSaveInputs
from ...taxbrain.helpers import (expand_1D, expand_2D, expand_list, package_up_vars,
                                 format_csv, arrange_totals_by_row, default_taxcalc_data)
from ...taxbrain.compute import DropqCompute, MockCompute, ElasticMockCompute, MockFailedCompute
import taxcalc
from taxcalc import Policy

START_YEAR = '2016'


class DynamicViewsTests(object):
    ''' Test the views of this app. '''

    def setUp(self):
        # Every test needs a client.
        self.client = Client()

    def test_taxbrain_get(self):
        # Issue a GET request.
        response = self.client.get('/taxbrain/')

        # Check that the response is 200 OK.
        assert (response.status_code == 200)

    def behavioral_post_helper(self):
        #Monkey patch to mock out running of compute jobs
        import sys
        from webapp.apps.taxbrain import views
        webapp_views = sys.modules['webapp.apps.taxbrain.views']
        webapp_views.dropq_compute = MockCompute()
        from webapp.apps.dynamic import views
        dynamic_views = sys.modules['webapp.apps.dynamic.views']
        dynamic_views.dropq_compute = MockCompute(num_times_to_wait=2)

        # Do the microsim
        data = {'ID_BenefitSurtax_Switch_1': ['True'],
                'ID_BenefitSurtax_Switch_0': ['True'],
                'ID_BenefitSurtax_Switch_3': ['True'],
                'ID_BenefitSurtax_Switch_2': ['True'],
                'ID_BenefitSurtax_Switch_5': ['True'],
                'ID_BenefitSurtax_Switch_4': ['True'],
                'ID_BenefitSurtax_Switch_6': ['True'],
                'has_errors': ['False'], 'II_em': ['4333'],
                'start_year': '2016', 'csrfmiddlewaretoken': 'abc123'}

        response = self.client.post('/taxbrain/', data)
        # Check that redirect happens
        assert (response.status_code == 302)
        # Go to results page
        link_idx = response.url[:-1].rfind('/')
        assert response.url[:link_idx+1].endswith("taxbrain/")

        # Link to dynamic simulation
        model_num = response.url[link_idx+1:-1]
        dynamic_landing = '/dynamic/{0}/?start_year={1}'.format(model_num, START_YEAR)
        response = self.client.get(dynamic_landing)
        assert (response.status_code == 200)

        # Go to behavioral input page
        dynamic_behavior = '/dynamic/behavioral/{0}/?start_year={1}'.format(model_num, START_YEAR)
        response = self.client.get(dynamic_behavior)
        assert (response.status_code == 200)

        return dynamic_behavior

    def test_behavioral_post(self):
        dynamic_behavior = self.behavioral_post_helper()

        # Do the partial equilibrium job submission
        pe_data = {'BE_inc': ['-0.4']}
        response = self.client.post(dynamic_behavior, pe_data)
        assert (response.status_code == 302)
        print(response)

        #Check should get success this time
        response_success = self.client.get(response.url)
        assert (response_success.status_code == 200)
        link_idx = response.url[:-1].rfind('/')
        assert response.url[:link_idx+1].endswith("behavior_results/")

    def test_behavioral_post_invalid_param(self):
        """
        Check that we get a 400 error if we submit an invalid field
        """
        dynamic_behavior = self.behavioral_post_helper()

        pe_data = {'BE_inc': ['-0.4'], 'foo': ['0.0']}
        response = self.client.post(dynamic_behavior, pe_data)
        self.assertEqual(response.status_code, 400)

    # Test whether default elasticity is used if no param is given
    @pytest.mark.parametrize(
        'el_data',
        [{'elastic_gdp': ['0.55']}, {}]
    )
    def test_elastic_post(self, el_data):
        #Monkey patch to mock out running of compute jobs
        import sys
        from webapp.apps.taxbrain import views
        webapp_views = sys.modules['webapp.apps.taxbrain.views']
        webapp_views.dropq_compute = MockCompute()
        from webapp.apps.dynamic import views
        dynamic_views = sys.modules['webapp.apps.dynamic.views']
        dynamic_views.dropq_compute = ElasticMockCompute(num_times_to_wait=1)

        # Do the microsim
        data = {'ID_BenefitSurtax_Switch_1': ['True'],
                'ID_BenefitSurtax_Switch_0': ['True'],
                'ID_BenefitSurtax_Switch_3': ['True'],
                'ID_BenefitSurtax_Switch_2': ['True'],
                'ID_BenefitSurtax_Switch_5': ['True'],
                'ID_BenefitSurtax_Switch_4': ['True'],
                'ID_BenefitSurtax_Switch_6': ['True'],
                'has_errors': ['False'], 'II_em': ['4333'],
                'start_year': '2016', 'csrfmiddlewaretoken': 'abc123'}

        response = self.client.post('/taxbrain/', data)
        # Check that redirect happens
        assert (response.status_code == 302)
        # Go to results page
        link_idx = response.url[:-1].rfind('/')
        assert response.url[:link_idx+1].endswith("taxbrain/")

        # Link to dynamic simulation
        model_num = response.url[link_idx+1:-1]
        dynamic_landing = '/dynamic/{0}/?start_year={1}'.format(model_num, START_YEAR)
        response = self.client.get(dynamic_landing)
        assert (response.status_code == 200)

        # Go to macro input page
        dynamic_egdp = '/dynamic/macro/{0}/?start_year={1}'.format(model_num, START_YEAR)
        response = self.client.get(dynamic_egdp)
        assert (response.status_code == 200)

        # Do the elasticity job submission
        response = self.client.post(dynamic_egdp, el_data)
        assert (response.status_code == 302)
        print(response)

        #Check that we get success this time
        response_success = self.client.get(response.url)
        assert (response_success.status_code == 200)
        assert response.url[:-2].endswith("macro_results/")

    def test_elastic_failed_job(self):
        #Monkey patch to mock out running of compute jobs
        import sys
        from webapp.apps.taxbrain import views
        webapp_views = sys.modules['webapp.apps.taxbrain.views']
        webapp_views.dropq_compute = MockCompute()
        from webapp.apps.dynamic import views
        dynamic_views = sys.modules['webapp.apps.dynamic.views']
        #dynamic_views.dropq_compute = ElasticFailedMockCompute(num_times_to_wait=1)
        dynamic_views.dropq_compute = MockFailedCompute(num_times_to_wait=1)

        # Do the microsim
        data = {'ID_BenefitSurtax_Switch_1': ['True'],
                'ID_BenefitSurtax_Switch_0': ['True'],
                'ID_BenefitSurtax_Switch_3': ['True'],
                'ID_BenefitSurtax_Switch_2': ['True'],
                'ID_BenefitSurtax_Switch_5': ['True'],
                'ID_BenefitSurtax_Switch_4': ['True'],
                'ID_BenefitSurtax_Switch_6': ['True'],
                'has_errors': ['False'], 'II_em': ['4333'],
                'start_year': '2016', 'csrfmiddlewaretoken': 'abc123'}

        response = self.client.post('/taxbrain/', data)
        # Check that redirect happens
        assert (response.status_code == 302)
        # Go to results page
        link_idx = response.url[:-1].rfind('/')
        assert response.url[:link_idx+1].endswith("taxbrain/")

        # Link to dynamic simulation
        model_num = response.url[link_idx+1:-1]
        dynamic_landing = '/dynamic/{0}/?start_year={1}'.format(model_num, START_YEAR)
        response = self.client.get(dynamic_landing)
        assert (response.status_code == 200)

        # Go to macro input page
        dynamic_egdp = '/dynamic/macro/{0}/?start_year={1}'.format(model_num, START_YEAR)
        response = self.client.get(dynamic_egdp)
        assert (response.status_code == 200)

        # Do the elasticity job submission
        el_data = {'elastic_gdp': ['0.55']}
        response = self.client.post(dynamic_egdp, el_data)
        assert (response.status_code == 302)
        print(response)

        #Check that we get success this time
        response_success = self.client.get(response.url)
        assert (response_success.status_code == 200)
        assert response.url[:-2].endswith("macro_results/")
        response = self.client.get(response.url)
        # Make sure the failure message is in the response
        assert ("Your calculation failed" in response.content.decode('utf-8'))
