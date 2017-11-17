import pytest
import json
import numpy as np
import taxcalc
from ..helpers import nested_form_parameters, rename_keys

CURRENT_LAW_POLICY = """
{
    "_ALD_IRAContributions_hc": {
        "long_name": "Deduction for IRA contributions haircut",
        "description": "If greater than zero, this decimal fraction reduces the portion of IRA contributions that can be deducted from AGI.",
        "section_1": "Above The Line Deductions",
        "section_2": "Misc. Adjustment Haircuts",
        "irs_ref": "",
        "notes": "The final adjustment amount would be (1-Haircut)*IRA_Contribution.",
        "row_var": "FLPDYR",
        "row_label": ["2013"],
        "start_year": 2013,
        "cpi_inflated": false,
        "col_var": "",
        "col_label": "",
        "boolean_value": false,
        "integer_value": false,
        "value": [0.0],
        "range": {"min": 0, "max": 1},
        "out_of_range_minmsg": "",
        "out_of_range_maxmsg": "",
        "out_of_range_action": "stop",
        "compatible_data": {"puf": true, "cps": true}
    },
    "_ALD_EarlyWithdraw_hc": {
            "long_name": "Adjustment for early withdrawal penalty haircut",
            "description": "Under current law, early withdraw penalty can be fully deducted from gross income. This haircut can be used to limit the adjustment allowed.",
            "section_1": "Above The Line Deductions",
            "section_2": "Misc. Adjustment Haircuts",
            "irs_ref": "Form 1040, line 30",
            "notes": "The final adjustment amount is (1-Haircut)*EarlyWithdrawPenalty.",
            "row_var": "FLPDYR",
            "row_label": ["2013"],
            "start_year": 2013,
            "cpi_inflated": false,
            "col_var": "",
            "col_label": "",
            "boolean_value": false,
            "integer_value": false,
            "value": [0.0],
            "range": {"min": 0, "max": 1},
            "out_of_range_minmsg": "",
            "out_of_range_maxmsg": "",
            "out_of_range_action": "stop",
            "compatible_data": {"puf": true, "cps": false}
    }
}
"""

@pytest.fixture
def mock_current_law_policy():
    return json.loads(CURRENT_LAW_POLICY)


def test_nested_form_parameters(monkeypatch, mock_current_law_policy):
    """
    Check that test_nested_form_parameters removes parameters that are not
    compatible with the specified data set
    """
    params = nested_form_parameters(2017, use_puf_not_cps=True,
                                    defaults=mock_current_law_policy)
    res = params[0]['Above The Line Deductions'][0]['Misc. Adjustment Haircuts']
    res = {k: v for r in res for k, v in r.iteritems()}
    assert (not res["ALD_EarlyWithdraw_hc"].gray_out and
            not res["ALD_IRAContributions_hc"].gray_out)

    params = nested_form_parameters(2017, use_puf_not_cps=False,
                                    defaults=mock_current_law_policy)
    res = params[0]['Above The Line Deductions'][0]['Misc. Adjustment Haircuts']
    res = {k: v for r in res for k, v in r.iteritems()}
    assert (res["ALD_EarlyWithdraw_hc"].gray_out and
            not res["ALD_IRAContributions_hc"].gray_out)


def test_rename_keys(monkeypatch):
    a = {
        'a': {
            'b': {
                'c': []
            }
        },
        'd': {
            'e': []
        },
        'f_1': [],
        'g': {
            'h': [],
            'i_0': [],
            'j': []
        }
    }
    exp = {
        'A': {
            'B': {
                'C': []
            }
        },
        'D': {
            'E': []
        },
        'F_1': [],
        'G': {
            'H': [],
            'I_0': [],
            'J': []
        }
    }

    map_dict = {
        'a': 'A',
        'b': 'B',
        'c': 'C',
        'd': 'D',
        'e': 'E',
        'f': 'F',
        'g': 'G',
        'h': 'H',
        'i': 'I',
        'j': 'J'
    }
    act = rename_keys(a, map_dict)
    np.testing.assert_equal(act, exp)