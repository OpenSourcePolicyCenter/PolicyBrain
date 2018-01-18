from django.test import TestCase

from ..models import TaxSaveInputs, WorkerNodesCounter
from ..models import convert_to_floats
from ..helpers import (expand_1D, expand_2D, expand_list, package_up_vars,
                     format_csv, arrange_totals_by_row, default_taxcalc_data,
                     default_policy)
from ...taxbrain import compute as compute
from ..views import convert_val
import taxcalc
from taxcalc import Policy
import pytest

FBY = 2015

@pytest.mark.django_db
def test_compute():
    assert compute
    compute.DROPQ_WORKERS = [1,2,3,4,5,6,7,8,9,10]
    compute.NUM_BUDGET_YEARS = 5
    wnc, created = WorkerNodesCounter.objects.get_or_create(singleton_enforce=1)
    dropq_worker_offset = wnc.current_offset
    hostnames = compute.DROPQ_WORKERS[dropq_worker_offset:
        dropq_worker_offset + compute.NUM_BUDGET_YEARS]
    assert hostnames == [1,2,3,4,5]
    wnc.current_offset = (dropq_worker_offset + compute.NUM_BUDGET_YEARS) % len(compute.DROPQ_WORKERS)
    wnc.save()

    assert wnc.current_offset == 5
    dropq_worker_offset = wnc.current_offset
    hostnames = compute.DROPQ_WORKERS[dropq_worker_offset:
        dropq_worker_offset + compute.NUM_BUDGET_YEARS]
    assert hostnames == [6,7,8,9,10]
    wnc.current_offset = (dropq_worker_offset + compute.NUM_BUDGET_YEARS) % len(compute.DROPQ_WORKERS)
    wnc.save()

    assert wnc.current_offset == 0
    dropq_worker_offset = wnc.current_offset
    hostnames = compute.DROPQ_WORKERS[dropq_worker_offset:
        dropq_worker_offset+ compute.NUM_BUDGET_YEARS]
    assert hostnames == [1,2,3,4,5]
    #Reset to original values
    compute.DROPQ_WORKERS = ['localhost:5050']
    wnc.current_offset = 0
    wnc.save()
    compute.NUM_BUDGET_YEARS = 2


def test_convert_val():
    field = u'*,*,130000'
    out = [convert_val(x) for x in field.split(',')]
    exp = ['*', '*', 130000.0]
    assert out == exp
    field = u'False'
    out = [convert_val(x) for x in field.split(',')]
    exp = [False]
    assert out == exp
    field = u'0.12,0.13,0.14'
    out = [convert_val(x) for x in field.split(',')]
    exp = [0.12, 0.13, 0.14]
    assert out == exp


def cycler(max):
    count = 0
    while True:
        yield count
        count = (count + 1) % max

class TaxInputTests(TestCase):

    def test_expand1d(self):
        x = [1, 2, 3]
        assert expand_1D(x, 5) == [1, 2, 3, None, None]

    def test_expand2d(self):
        x = [[1, 2, 3], [4, 5, 6]]
        exp = [[1, 2, 3], [4, 5, 6], [None, None, None]]
        assert expand_2D(x, 3) == exp

    def test_expand_list_1(self):
        x = [1, 2, 3]
        assert expand_list(x, 5) == [1, 2, 3, None, None]

    def test_expand2d(self):
        x = [[1, 2, 3], [4, 5, 6]]
        exp = [[1, 2, 3], [4, 5, 6], [None, None, None]]
        assert expand_list(x, 3) == exp

    def test_format_csv(self):
        c = cycler(40)
        tab_types = ["dist2_xdec", "dist1_xdec", "diff_itax_xdec", "diff_ptax_xdec",
                     "diff_comb_xdec", "dist2_xbin", "dist1_xbin", "diff_itax_xbin",
                     "diff_itax_xbin", "diff_ptax_xbin", "diff_comb_xbin", "aggr_d",
                     "aggr_1", "aggr_2"]

        bin_keys = [
            '$10-20K_0',
            '$10-20K_1',
            '$10-20K_2',
            '$100-200K_0',
            '$100-200K_1',
            '$100-200K_2',
            '$20-30K_0',
            '$20-30K_1',
            '$20-30K_2',
            '$200-500K_0',
            '$200-500K_1',
            '$200-500K_2',
            '$30-40K_0',
            '$30-40K_1',
            '$30-40K_2',
            '$40-50K_0',
            '$40-50K_1',
            '$40-50K_2',
            '$50-75K_0',
            '$50-75K_1',
            '$50-75K_2',
            '$500-1000K_0',
            '$500-1000K_1',
            '$500-1000K_2',
            '$75-100K_0',
            '$75-100K_1',
            '$75-100K_2',
            '<$10K_0',
            '<$10K_1',
            '<$10K_2',
            '>$1000K_0',
            '>$1000K_1',
            '>$1000K_2',
            'all_0',
            'all_1',
            'all_2'
        ]

        dec_keys = [
            '0-10_0',
            '0-10_1',
            '0-10_2',
            '10-20_0',
            '10-20_1',
            '10-20_2',
            '20-30_0',
            '20-30_1',
            '20-30_2',
            '30-40_0',
            '30-40_1',
            '30-40_2',
            '40-50_0',
            '40-50_1',
            '40-50_2',
            '50-60_0',
            '50-60_1',
            '50-60_2',
            '60-70_0',
            '60-70_1',
            '60-70_2',
            '70-80_0',
            '70-80_1',
            '70-80_2',
            '80-90_0',
            '80-90_1',
            '80-90_2',
            '90-100_0',
            '90-100_1',
            '90-100_2',
            'all_0',
            'all_1',
            'all_2'
        ]

        tot_keys = [u'combined_tax', u'ind_tax', u'payroll_tax']

        tax_results = {}
        tax_results[u'aggr_d'] = {k:[1,2,3] for k in tot_keys}
        tax_results[u'dist2_xbin'] = { k:[next(c)] for k in bin_keys}
        tax_results[u'dist1_xbin'] = { k:[next(c)] for k in bin_keys}
        tax_results[u'diff_itax_bin'] = { k:[next(c)] for k in bin_keys}
        tax_results[u'dist2_xdec'] = { k:[next(c)] for k in dec_keys}
        tax_results[u'dist1_xdec'] = { k:[next(c)] for k in dec_keys}
        tax_results[u'diff_itax_xdec'] = { k:[next(c)] for k in dec_keys}

        ans = format_csv(tax_results, u'42', first_budget_year=FBY)
        assert ans[0] == ['#URL: http://www.ospc.org/taxbrain/42/']


    def test_arrange_totals_by_row(self):
        total_row_names = ["ind_tax", "payroll_tax", "combined_tax"]
        tots = {'ind_tax_0': "1", 'ind_tax_1': "2", 'ind_tax_2': "3",
                'payroll_tax_0': "4", 'payroll_tax_1': "5", 'payroll_tax_2': "6",
                'combined_tax_0': "7", 'combined_tax_1': "8", 'combined_tax_2': "9"}
        ans = arrange_totals_by_row(tots, total_row_names)
        exp = {'ind_tax': ["1", "2", "3"], 'payroll_tax': ["4", "5", "6"], 'combined_tax': ["7", "8", "9"]}
        assert ans == exp

    def test_default_taxcalc_data(self):
        import math
        dd = default_taxcalc_data(taxcalc.policy.Policy, start_year=2017)
        dd_raw = taxcalc.policy.Policy.default_data(start_year=2017)
        dd_meta = default_taxcalc_data(taxcalc.policy.Policy, start_year=2017, metadata=True)
        floored_std_aged = list(map(math.floor, dd['_STD_Aged'][0]))
        assert dd['_STD_Aged'] == [floored_std_aged]
        assert dd_meta['_STD_Aged']['value'] == [floored_std_aged]

        floored_ii_em_ps = list(map(math.floor, dd['_II_em_ps'][0]))
        assert dd['_II_em_ps'] == [floored_ii_em_ps]
        assert dd_meta['_II_em_ps']['value'] == [floored_ii_em_ps]

        floored_ii_em = [math.floor(dd['_II_em'][0])]
        assert dd['_II_em'] == floored_ii_em
        assert dd_meta['_II_em']['value'] == floored_ii_em

        assert dd_raw['_II_rt6'] == dd['_II_rt6']

    def test_default_taxcalc_data_cpi_flags_on_II_credit(self):
        taxcalc_default_params = default_policy(int(FBY))
        assert taxcalc_default_params['II_credit'].inflatable
        assert taxcalc_default_params['II_credit_ps'].inflatable
