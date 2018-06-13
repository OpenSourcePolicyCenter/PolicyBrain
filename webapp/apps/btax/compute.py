from functools import partial
import os
from ..taxbrain.models import WorkerNodesCounter
import json
import requests
from requests.exceptions import Timeout, RequestException
from .helpers import arrange_totals_by_row
from ..taxbrain.compute import (DropqCompute,
                                MockCompute,
                                MockFailedCompute,
                                NodeDownCompute,
                                JobFailError,
                                ENFORCE_REMOTE_VERSION_CHECK,
                                TIMEOUT_IN_SECONDS,
                                dropq_version)
import requests_mock
requests_mock.Mocker.TEST_PREFIX = 'dropq'
btax_workers = os.environ.get('BTAX_WORKERS', '')
BTAX_WORKERS = btax_workers.split(",")


def package_up_vars(self, user_mods, first_budget_year):
    # TODO - is first_budget_year important here?
    user_mods = {k: v for k, v in user_mods.items()
                 if k.startswith(('btax_', 'start_year'))}
    user_mods = {k: (v[0] if hasattr(v, '__getitem__') else v)
                 for k, v in user_mods.items()}
    return user_mods


def mock_submit_calculation(self, *args, **kwargs):
    return (list(args), 1)


def mock_dropq_results_ready(arg, self, *args, **kwargs):
    return [arg,]


def mock_dropq_get_results(is_error, self, *args, **kwargs):
    if is_error:
        ret = {0: 'Error expected in test'}
        return ret
    ret = {0: {'mY_dec': None,
                'mX_dec': None,
                'df_dec': None,
                'pdf_dec': None,
                'cdf_dec': None,
                'mY_bin': None,
                'mX_bin': None,
                'df_bin': None,
                'pdf_bin': None,
                'cdf_bin': None,
                'fiscal_tot_diffs': None,
                'fiscal_tot_base': None,
                'fiscal_tot_ref': None,}}
    return ret


class DropqComputeBtax(DropqCompute):
    num_budget_years = 1
    package_up_vars = package_up_vars

    def submit_btax_calculation(self, user_mods, first_budget_year):
        url_template = "http://{hn}/btax_start_job"
        data = {}
        user_mods = self.package_up_vars(user_mods, first_budget_year)
        if not bool(user_mods):
            return False
        user_mods = {first_budget_year: user_mods}
        data['user_mods'] = json.dumps(user_mods)
        data['first_budget_year'] = str(first_budget_year)
        data['start_budget_year'] = '0'
        data['num_budget_years'] = 1
        print('submitting btax data:', data)
        return self.submit_calculation(data, url_template,
                                       workers=BTAX_WORKERS,
                                       increment_counter=False,
                                       use_wnc_offset=False)

    def btax_get_results(self, job_ids, job_failure=False):
        return self._get_results_base(job_ids, job_failure=job_failure)


class MockComputeBtax(MockCompute, DropqComputeBtax):
    num_budget_years = 1
    package_up_vars = package_up_vars
    dropq_get_results = partial(mock_dropq_get_results, 'YES')
    submit_calculation = mock_submit_calculation
    dropq_results_ready = partial(mock_dropq_results_ready, "YES")



class MockFailedComputeBtax(MockFailedCompute, DropqComputeBtax):
    num_budget_years = 1
    package_up_vars = package_up_vars
    dropq_get_results = partial(mock_dropq_get_results, 'Failure message')
    submit_calculation = mock_submit_calculation
    dropq_results_ready = partial(mock_dropq_results_ready, "FAIL")




class NodeDownComputeBtax(NodeDownCompute, DropqComputeBtax):
    num_budget_years = 1
    package_up_vars = package_up_vars
    dropq_get_results = partial(mock_dropq_get_results, 'Failure message')
    submit_calculation = mock_submit_calculation
    dropq_results_ready = partial(mock_dropq_results_ready, "FAIL")
