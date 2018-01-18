import pytest
import taxcalc
import json
import numpy as np

from ..taxbrain.views import (to_json_reform, read_json_reform,
                              parse_errors_warnings, parse_fields)
def test_tcja_construction():
    tcja_fields = {
        # '_state': "<django.db.models.base.ModelState object at 0x10c764950>",
        # 'creation_date': "datetime.datetime(2015, 1, 1, 0, 0)",
        # 'id': 64,
        # 'quick_calc': False,
        'first_year': 2018,

        "II_rt1": ["0.1,*,*,*,*,*,*,*,0.1"],
        "II_rt2": ["0.12,*,*,*,*,*,*,*,0.15"],
        "II_rt3": ["0.22,*,*,*,*,*,*,*,0.25"],
        "II_rt4": ["0.24,*,*,*,*,*,*,*,0.28"],
        "II_rt5": ["0.32,*,*,*,*,*,*,*,0.33"],
        "II_rt6": ["0.35,*,*,*,*,*,*,*,0.35"],
        "II_rt7": ["0.37,*,*,*,*,*,*,*,0.396"],

        "II_brk1_0": ["9525,*,*,*,*,*,*,*,11242"],
        "II_brk1_1": ["19050,*,*,*,*,*,*,*,22484"],
        "II_brk1_2": ["9525,*,*,*,*,*,*,*,11242"],
        "II_brk1_3": ["13600,*,*,*,*,*,*,*,16094"],

        "II_brk2_0": ["38700,*,*,*,*,*,*,*,45751"],
        "II_brk2_1": ["77400,*,*,*,*,*,*,*,91502"],
        "II_brk2_2": ["38700,*,*,*,*,*,*,*,45751"],
        "II_brk2_3": ["51800,*,*,*,*,*,*,*,61242"],

        "II_brk3_0": ["82500,*,*,*,*,*,*,*,110791"],
        "II_brk3_1": ["165000,*,*,*,*,*,*,*,184571"],
        "II_brk3_2": ["82500,*,*,*,*,*,*,*,92286"],
        "II_brk3_3": ["82500,*,*,*,*,*,*,*,158169"],

        "II_brk4_0": ["157500,*,*,*,*,*,*,*,231045"],
        "II_brk4_1": ["315000,*,*,*,*,*,*,*,281317"],
        "II_brk4_2": ["157500,*,*,*,*,*,*,*,140659"],
        "II_brk4_3": ["157500,*,*,*,*,*,*,*,256181"],

        "II_brk5_0": ["200000,*,*,*,*,*,*,*,502356"],
        "II_brk5_1": ["400000,*,*,*,*,*,*,*,502356"],
        "II_brk5_2": ["200000,*,*,*,*,*,*,*,251178"],
        "II_brk5_3": ["200000,*,*,*,*,*,*,*,502356"],

        "II_brk6_0": ["500000,*,*,*,*,*,*,*,504406"],
        "II_brk6_1": ["600000,*,*,*,*,*,*,*,567457"],
        "II_brk6_2": ["300000,*,*,*,*,*,*,*,283728"],
        "II_brk6_3": ["500000,*,*,*,*,*,*,*,535931"],

        "PT_rt1": ["0.1,*,*,*,*,*,*,*,0.1"],
        "PT_rt2": ["0.12,*,*,*,*,*,*,*,0.15"],
        "PT_rt3": ["0.22,*,*,*,*,*,*,*,0.25"],
        "PT_rt4": ["0.24,*,*,*,*,*,*,*,0.28"],
        "PT_rt5": ["0.32,*,*,*,*,*,*,*,0.33"],
        "PT_rt6": ["0.35,*,*,*,*,*,*,*,0.35"],
        "PT_rt7": ["0.37,*,*,*,*,*,*,*,0.396"],

        "PT_brk1_0": ["9525,*,*,*,*,*,*,*,11242"],
        "PT_brk1_1": ["19050,*,*,*,*,*,*,*,22484"],
        "PT_brk1_2": ["9525,*,*,*,*,*,*,*,11242"],
        "PT_brk1_3": ["13600,*,*,*,*,*,*,*,16094"],

        "PT_brk2_0": ["38700,*,*,*,*,*,*,*,45751"],
        "PT_brk2_1": ["77400,*,*,*,*,*,*,*,91502"],
        "PT_brk2_2": ["38700,*,*,*,*,*,*,*,45751"],
        "PT_brk2_3": ["51800,*,*,*,*,*,*,*,61242"],

        "PT_brk3_0": ["82500,*,*,*,*,*,*,*,110791"],
        "PT_brk3_1": ["165000,*,*,*,*,*,*,*,184571"],
        "PT_brk3_2": ["82500,*,*,*,*,*,*,*,92286"],
        "PT_brk3_3": ["82500,*,*,*,*,*,*,*,158169"],

        "PT_brk4_0": ["157500,*,*,*,*,*,*,*,231045"],
        "PT_brk4_1": ["315000,*,*,*,*,*,*,*,281317"],
        "PT_brk4_2": ["157500,*,*,*,*,*,*,*,140659"],
        "PT_brk4_3": ["157500,*,*,*,*,*,*,*,256181"],

        "PT_brk5_0": ["200000,*,*,*,*,*,*,*,502356"],
        "PT_brk5_1": ["400000,*,*,*,*,*,*,*,502356"],
        "PT_brk5_2": ["200000,*,*,*,*,*,*,*,251178"],
        "PT_brk5_3": ["200000,*,*,*,*,*,*,*,502356"],

        "PT_brk6_0": ["500000,*,*,*,*,*,*,*,504406"],
        "PT_brk6_1": ["600000,*,*,*,*,*,*,*,567457"],
        "PT_brk6_2": ["300000,*,*,*,*,*,*,*,283728"],
        "PT_brk6_3": ["500000,*,*,*,*,*,*,*,535931"],

        "PT_exclusion_rt": ["0.2,*,*,*,*,*,*,*,0.0"],
        "PT_exclusion_wage_limit": ["0.5,*,*,*,*,*,*,*,9e99"],

        "STD_0": ["12000,*,*,*,*,*,*,*,7655"],
        "STD_1": ["24000,*,*,*,*,*,*,*,15311"],
        "STD_2": ["12000,*,*,*,*,*,*,*,7655"],
        "STD_3": ["18000,*,*,*,*,*,*,*,11272"],

        "II_em": ["0,*,*,*,*,*,*,*,4883"],

        "CTC_ps_0": ["200000,*,*,*,*,*,*,*,75000"],
        "CTC_ps_1": ["400000,*,*,*,*,*,*,*,110000"],
        "CTC_ps_2": ["200000,*,*,*,*,*,*,*,55000"],
        "CTC_ps_3": ["200000,*,*,*,*,*,*,*,75000"],

        "CTC_c": ["1400,*,*,*,1500,*,*,1600,1000"],

        "DependentCredit_Child_c": ["600,*,*,*,500,*,*,400,0"],
        "DependentCredit_Nonchild_c": ["500,*,*,*,*,*,*,*,0"],
        "DependentCredit_before_CTC": ["True"],

        "ACTC_Income_thd": ["2500,*,*,*,*,*,*,*,3000"],

        "AMT_em_0": ["70300,*,*,*,*,*,*,*,65462"],
        "AMT_em_1": ["109400,*,*,*,*,*,*,*,101870"],
        "AMT_em_2": ["54700,*,*,*,*,*,*,*,50935"],
        "AMT_em_3": ["70300,*,*,*,*,*,*,*,65461"],

        "AMT_em_ps_0": ["500000,*,*,*,*,*,*,*,145511"],
        "AMT_em_ps_1": ["1000000,*,*,*,*,*,*,*,193974"],
        "AMT_em_ps_2": ["500000,*,*,*,*,*,*,*,96987"],
        "AMT_em_ps_3": ["500000,*,*,*,*,*,*,*,145511"],

        "ALD_DomesticProduction_hc": ["1,*,*,*,*,*,*,*,0"],
        "ALD_Alimony_hc": ["*,1,*,*,*,*,*,*,0"],

        "ID_prt": ["0,*,*,*,*,*,*,*,0.03"],
        "ID_crt": ["1,*,*,*,*,*,*,*,0.8"],
        "ID_Charity_crt_all": ["0.6,*,*,*,*,*,*,*,0.5"],
        "ID_Casualty_hc": ["1,*,*,*,*,*,*,*,0"],

        "ID_AllTaxes_c_0": ["10000,*,*,*,*,*,*,*,9e99"],
        "ID_AllTaxes_c_1": ["10000,*,*,*,*,*,*,*,9e99"],
        "ID_AllTaxes_c_2": ["5000,*,*,*,*,*,*,*,9e99"],
        "ID_AllTaxes_c_3": ["10000,*,*,*,*,*,*,*,9e99"],

        "ID_Miscellaneous_hc": ["1,*,*,*,*,*,*,*,0"],
        "ID_Medical_frt": ["<,0.075,*,0.1"],
        "cpi_offset": ["<,-0.0025"]
    }

    tcja_json = """
    // Title: Tax Cuts and Jobs Act, Reconciliation version
    // Reform_File_Author: Cody Kallen
    // Reform_Reference: http://docs.house.gov/billsthisweek/20171218/CRPT-115HRPT-466.pdf
    // Reform_Baseline: 2017_law.json
    // Reform_Description:
    // -  New personal income tax schedule (regular/non-AMT/non-pass-through) (1)
    // -  New pass-through income tax schedule (2)
    // -  New standard deductions (3)
    // -  Repeal personal exemption (4)
    // -  Modification to child tax credit, nonrefundable dependent credits (5)
    // -  Modification of Alternative Minimum Tax exemption (6)
    // -  Repeal of certain above the line deductions (7)
    // -  Changes to itemized deductions (8)
    // -  Switch to chained CPI from CPI-U for tax parameter adjustment (9)
    // Reform_Parameter_Map:
    // - 1: _II_*
    // - 2: _PT_*
    // - 3: _STD (can safely ignore WARNINGs about 2026+ values)
    // - 4: _II_em
    // - 5: _DependentCredit_*, _CTC_c, _CTC_ps, _ACTC_Income_thd
    // - 6: _AMT_rt*
    // - 7: _ALD_*
    // - 8: _ID_* (can safely ignore WARNINGs about values for several parameters)
    // - 9: _cpi_offset
    // Note: _II_rt*, _PT_rt*, _STD and _II_em are rounded to the nearest integer value.
    {
        "policy": {
            "_II_rt1":
                {"2018": [0.1],
                 "2026": [0.1]},
            "_II_rt2":
                {"2018": [0.12],
                 "2026": [0.15]},
            "_II_rt3":
                {"2018": [0.22],
                 "2026": [0.25]},
            "_II_rt4":
                {"2018": [0.24],
                 "2026": [0.28]},
            "_II_rt5":
                {"2018": [0.32],
                 "2026": [0.33]},
            "_II_rt6":
                {"2018": [0.35],
                 "2026": [0.35]},
            "_II_rt7":
                {"2018": [0.37],
                 "2026": [0.396]},
            "_II_brk1":
                {"2018": [[9525, 19050, 9525, 13600, 19050]],
                 "2026": [[11242, 22484, 11242, 16094, 22484]]},
            "_II_brk2":
                {"2018": [[38700, 77400, 38700, 51800, 77400]],
                 "2026": [[45751, 91502, 45751, 61242, 91502]]},
            "_II_brk3":
                {"2018": [[82500, 165000, 82500, 82500, 165000]],
                 "2026": [[110791, 184571,  92286, 158169, 184571]]},
            "_II_brk4":
                {"2018": [[157500, 315000, 157500, 157500, 315000]],
                 "2026": [[231045, 281317, 140659, 256181, 281317]]},
            "_II_brk5":
                {"2018": [[200000, 400000, 200000, 200000, 400000]],
                 "2026": [[502356, 502356, 251178, 502356, 502356]]},
            "_II_brk6":
                {"2018": [[500000, 600000, 300000, 500000, 500000]],
                 "2026": [[504406 ,567457, 283728, 535931, 567457]]},
            "_PT_rt1":
                {"2018": [0.1],
                 "2026": [0.1]},
            "_PT_rt2":
                {"2018": [0.12],
                 "2026": [0.15]},
            "_PT_rt3":
                {"2018": [0.22],
                 "2026": [0.25]},
            "_PT_rt4":
                {"2018": [0.24],
                 "2026": [0.28]},
            "_PT_rt5":
                {"2018": [0.32],
                 "2026": [0.33]},
            "_PT_rt6":
                {"2018": [0.35],
                 "2026": [0.35]},
            "_PT_rt7":
                {"2018": [0.37],
                 "2026": [0.396]},
            "_PT_brk1":
                {"2018": [[9525, 19050, 9525, 13600, 19050]],
                 "2026": [[11242, 22484, 11242, 16094, 22484]]},
            "_PT_brk2":
                {"2018": [[38700, 77400, 38700, 51800, 77400]],
                 "2026": [[45751, 91502, 45751, 61242, 91502]]},
            "_PT_brk3":
                {"2018": [[82500, 165000, 82500, 82500, 165000]],
                 "2026": [[110791, 184571, 92286, 158169, 184571]]},
            "_PT_brk4":
                {"2018": [[157500, 315000, 157500, 157500, 315000]],
                 "2026": [[231045, 281317, 140659, 256181, 281317]]},
            "_PT_brk5":
                {"2018": [[200000, 400000, 200000, 200000, 400000]],
                 "2026": [[502356, 502356, 251178, 502356, 502356]]},
            "_PT_brk6":
                {"2018": [[500000, 600000, 300000, 500000, 500000]],
                 "2026": [[504406, 567457, 283728, 535931, 567457]]},
            "_PT_exclusion_rt":
                {"2018": [0.2],
                 "2026": [0.0]},
            "_PT_exclusion_wage_limit":
                {"2018": [0.5],
                 "2026": [9e+99]},
            "_STD":
                {"2018": [[12000, 24000, 12000, 18000, 24000]],
                 "2026": [[7655, 15311, 7655, 11272, 15311]]},
            "_II_em":
                {"2018": [0],
                 "2026": [4883]},
            "_CTC_ps":
                {"2018": [[200000, 400000, 200000, 200000, 400000]],
                 "2026": [[75000, 110000, 55000, 75000, 75000]]},
            "_CTC_c":
                {"2018": [1400],
                 "2022": [1500],
                 "2025": [1600],
                 "2026": [1000]},
            "_DependentCredit_Child_c":
                {"2018": [600],
                 "2022": [500],
                 "2025": [400],
                 "2026": [0]},
            "_DependentCredit_Nonchild_c":
                {"2018": [500],
                 "2026": [0]},
            "_DependentCredit_before_CTC":
                {"2018": [true]},
            "_ACTC_Income_thd":
                {"2018": [2500],
                 "2026": [3000]},
            "_AMT_em":
                {"2018": [[70300, 109400, 54700, 70300, 109400]],
                 "2026": [[65462, 101870, 50935, 65461, 101870]]},
            "_AMT_em_ps":
                {"2018": [[500000, 1000000, 500000, 500000, 1000000]],
                 "2026": [[145511, 193974, 96987, 145511, 193974]]},
            "_ALD_DomesticProduction_hc":
                {"2018": [1],
                 "2026": [0]},
            "_ALD_Alimony_hc":
                {"2019": [1],
                 "2026": [0]},
            "_ID_prt":
                {"2018": [0],
                 "2026": [0.03]},
            "_ID_crt":
                {"2018": [1],
                 "2026": [0.8]},
            "_ID_Charity_crt_all":
                {"2018": [0.6],
                 "2026": [0.5]},
            "_ID_Casualty_hc":
                {"2018": [1],
                 "2026": [0]},
            "_ID_AllTaxes_c":
                {"2018": [[10000, 10000, 5000, 10000, 10000]],
                 "2026": [[9e99, 9e99, 9e99, 9e99, 9e99]]},
            "_ID_Miscellaneous_hc":
                {"2018": [1],
                 "2026": [0]},
            "_ID_Medical_frt":
                {"2017": [0.075],
                 "2019": [0.1]},
            "_cpi_offset":
                {"2017": [-0.0025]}
        }
    }
    """

    (json_dict, _,
        errors_warnings) = read_json_reform(tcja_json, None)

    for field in tcja_fields:
        if isinstance(tcja_fields[field], list):
            tcja_fields[field] = tcja_fields[field][0]
    parsed_fields = parse_fields(tcja_fields)
    fields_json, map_back_to_tb = to_json_reform(parsed_fields, 2018)
    fields_json = {"policy": fields_json}
    fields_json = json.dumps(fields_json)
    assumptions_dict_json = {"behavior": {},
                             "growdiff_response": {},
                             "consumption": {},
                             "growdiff_baseline": {}}
    assumptions_dict_json = json.dumps(assumptions_dict_json)

    (fields_dict, _,
        errors_warnings) = read_json_reform(fields_json,
                                            assumptions_dict_json,
                                            map_back_to_tb)

    meta_pol = taxcalc.Policy.default_data(start_year=2018, metadata=True)
    fam_cols = [u'single', u'joint', u'separate', u'headhousehold', u'widow']
    for year in fields_dict:
        fields_dict_params = set(fields_dict[year].keys())
        json_dict_params = set(json_dict[year].keys())
        diff1 = fields_dict_params - json_dict_params
        assert len(diff1) == 0
        diff2 = json_dict_params - fields_dict_params
        assert len(diff2) == 0

    for year in fields_dict:
        for param in fields_dict[year]:
            # ignore widow param value
            if (isinstance(fields_dict[year][param], list) and
                isinstance(fields_dict[year][param][0], list) and
                len(fields_dict[year][param][0]) == 5 and
                meta_pol[param]["col_label"] == fam_cols):
                print(param)
                field_cmp = fields_dict[year][param][0][:4]
                json_cmp = json_dict[year][param][0][:4]
            else:
                field_cmp = fields_dict[year][param]
                json_cmp = json_dict[year][param]

            np.testing.assert_equal(
                field_cmp,
                json_cmp
            )
