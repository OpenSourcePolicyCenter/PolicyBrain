import json
import pytz
import datetime
from urllib.parse import urlparse, parse_qs
import os
#Mock some module for imports because we can't fit them on Heroku slugs
from mock import Mock
import sys
import traceback
MOCK_MODULES = []

sys.modules.update((mod_name, Mock()) for mod_name in MOCK_MODULES)
import taxcalc


from django.core.mail import send_mail
from django.core import serializers
from django.template.context_processors import csrf
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required, permission_required
from django.http import (HttpResponseRedirect, HttpResponse, Http404, HttpResponseServerError,
                         JsonResponse)
from django.shortcuts import render, render_to_response, get_object_or_404, redirect
from django.template import loader, Context
from django.template.context import RequestContext
from django.utils.translation import ugettext_lazy as _
from django.views.generic import DetailView, TemplateView
from django.contrib.auth.models import User
from django import forms

from .forms import (DynamicInputsModelForm, DynamicBehavioralInputsModelForm,
                    has_field_errors, DynamicElasticityInputsModelForm)
from .models import (DynamicSaveInputs, DynamicOutputUrl,
                     DynamicBehaviorSaveInputs, DynamicBehaviorOutputUrl,
                     DynamicElasticitySaveInputs, DynamicElasticityOutputUrl)
from ..taxbrain.models import (TaxSaveInputs, OutputUrl,
                               ErrorMessageTaxCalculator, JSONReformTaxCalculator)
from ..taxbrain.views import (make_bool, dropq_compute,
                              JOB_PROC_TIME_IN_SECONDS,
                              add_summary_column)
from ..taxbrain.param_formatters import (to_json_reform, get_reform_from_gui,
                                         parse_fields, append_errors_warnings)
from ..taxbrain.helpers import (taxcalc_results_to_tables,
                                convert_val)
from ..taxbrain.param_displayers import default_behavior
from ..taxbrain.compute import JobFailError, DROPQ_WORKERS
from .helpers import (default_parameters, job_submitted,
                      ogusa_results_to_tables, success_text,
                      failure_text, normalize, denormalize, strip_empty_lists,
                      cc_text_finished, cc_text_failure, dynamic_params_from_model,
                      send_cc_email, default_behavior_parameters,
                      elast_results_to_tables, default_elasticity_parameters)

from .compute import DynamicCompute, NUM_BUDGET_YEARS

dynamic_compute = DynamicCompute()

from ..constants import (DISTRIBUTION_TOOLTIP, DIFFERENCE_TOOLTIP,
                          PAYROLL_TOOLTIP, INCOME_TOOLTIP, BASE_TOOLTIP,
                          REFORM_TOOLTIP, INCOME_BINS_TOOLTIP,
                          INCOME_DECILES_TOOLTIP, START_YEAR, START_YEARS,
                          OUT_OF_RANGE_ERROR_MSG)

from ..formatters import format_dynamic_params, get_version


tcversion_info = taxcalc._version.get_versions()
TAXCALC_VERSION = tcversion_info['version']

# TODO: use import ogusa; ogusa.__version__
version_path = os.path.join(os.path.split(__file__)[0], "ogusa_version.json")
with open(version_path, "r") as f:
    ogversion_info = json.load(f)
OGUSA_VERSION = ogversion_info['version']

from django.conf import settings
WEBAPP_VERSION = settings.WEBAPP_VERSION

def dynamic_input(request, pk):
    """
    This view handles the dynamic input page and calls the function that
    handles the calculation on the inputs.
    """

    if request.method=='POST':
        # Client is attempting to send inputs, validate as form data
        fields = dict(request.POST)
        fields['first_year'] = fields['start_year']
        start_year = fields['start_year']
        strip_empty_lists(fields)
        dyn_mod_form = DynamicInputsModelForm(start_year, fields)

        if dyn_mod_form.is_valid():
            model = dyn_mod_form.save()

            #Can't proceed if there is no email address
            if not (request.user.is_authenticated() or model.user_email):
               msg = 'Dynamic simulation must have an email address to send notification to!'
               return HttpResponse(msg, status=403)

            curr_dict = dict(model.__dict__)
            for key, value in list(curr_dict.items()):
                print("got this ", key, value)

            # get macrosim data from form
            worker_data = {k:v for k, v in list(curr_dict.items()) if v not in ('', None, [])}

            #get microsim data
            outputsurl = OutputUrl.objects.get(pk=pk)
            model.micro_sim = outputsurl
            taxbrain_model = outputsurl.unique_inputs
            submitted_ids = None

            if not taxbrain_model.json_text:
                taxbrain_dict = dict(taxbrain_model.__dict__)
                for key, value in list(taxbrain_dict.items()):
                    if type(value) == type(str()):
                        try:
                            taxbrain_dict[key] = [float(x) for x in value.split(',') if x]
                        except ValueError:
                            taxbrain_dict[key] = [make_bool(x) for x in value.split(',') if x]
                    else:
                        print("missing this: ", key)


                microsim_data = {k:v for k, v in list(taxbrain_dict.items()) if not (v == [] or v == None)}

                #Don't need to pass around the microsim results
                if 'tax_result' in microsim_data:
                    del microsim_data['tax_result']

                # start calc job
                submitted_ids, guids = dynamic_compute.submit_ogusa_calculation(worker_data, int(start_year), microsim_data)
            else:
                microsim_data = {"reform": taxbrain_model.json_text.reform_text, "assumptions": taxbrain_model.json_text.assumption_text}
                # start calc job
                submitted_ids, guids = dynamic_compute.submit_json_ogusa_calculation(worker_data,
                                                                         int(start_year),
                                                                         microsim_data,
                                                                         pack_up_user_mods=False)
            # TODO: use OutputUrl class
            if submitted_ids:
                model.job_ids = denormalize(submitted_ids)
                model.guids = denormalize(guids)
                model.first_year = int(start_year)
                if request.user.is_authenticated():
                    current_user = User.objects.get(pk=request.user.id)
                    model.user_email = current_user.email

                model.save()
                job_submitted(model.user_email, model)
                return redirect('show_job_submitted', model.pk)

            else:
                raise HttpResponseServerError

        else:
            # received POST but invalid results, return to form with errors
            form_personal_exemp = dyn_mod_form

    else:

        # Probably a GET request, load a default form
        start_year = request.GET.get('start_year')
        form_personal_exemp = DynamicInputsModelForm(first_year=start_year)

    ogusa_default_params = default_parameters(int(start_year))
    disabled_flag = os.environ.get('OGUSA_DISABLED', '')

    init_context = {
        'form': form_personal_exemp,
        'params': ogusa_default_params,
        'taxcalc_version': TAXCALC_VERSION,
        'ogusa_version': OGUSA_VERSION,
        'webapp_version': WEBAPP_VERSION,
        'start_year': start_year,
        'pk': pk,
        'is_disabled': disabled_flag,
        'not_logged_in': not request.user.is_authenticated()
    }

    if has_field_errors(form_personal_exemp):
        form_personal_exemp.add_error(None, "Some fields have errors.")

    return render(request, 'dynamic/dynamic_input_form.html', init_context)


def dynamic_behavioral(request, pk):
    """
    This view handles the dynamic behavioral input page and calls the function that
    handles the calculation on the inputs.
    """
    start_year = START_YEAR
    has_errors = False
    if request.method == 'POST':
        print('method=POST get', request.GET)
        print('method=POST post', request.POST)
        fields = dict(request.GET)
        fields.update(dict(request.POST))
        fields = {k: v[0] if isinstance(v, list) else v for k, v in list(fields.items())}
        start_year = fields['start_year']
        # TODO: migrate first_year to start_year to get rid of weird stuff like
        # this
        fields['first_year'] = fields['start_year']
        # use_puf_not_cps set to True by default--doesn't matter for dynamic
        # input page. It is there for API consistency
        dyn_mod_form = DynamicBehavioralInputsModelForm(start_year, True,
                                                        fields)

        if dyn_mod_form.is_valid():
            model = dyn_mod_form.save(commit=False)
            model.set_fields()

            #get microsim data
            outputsurl = OutputUrl.objects.get(pk=pk)
            model.micro_sim = outputsurl
            taxbrain_model = outputsurl.unique_inputs
            model.data_source = taxbrain_model.data_source
            model.save()
            # get taxbrain data
            # inputs are re-built because the loaded JSON serialization loses
            # some info around the start year
            taxbrain_model.set_fields()
            (reform_dict, _, reform_text, _,
                errors_warnings) = taxbrain_model.get_model_specs()
            json_reform = JSONReformTaxCalculator(
                reform_text=json.dumps(reform_dict),
                raw_reform_text=reform_text,
                errors_warnings_text=json.dumps(errors_warnings)
            )
            json_reform.save()
            taxbrain_model.json_text = json_reform

            (_, assumptions_dict, _, _,
                errors_warnings) = model.get_model_specs()

            taxbrain_model.json_text.assumption_text = json.dumps(assumptions_dict)
            taxbrain_model.json_text.raw_assumption_text = ''
            # update the behavior key in the errors warnings dictionary created
            # in the static run
            policy_ew = taxbrain_model.json_text.get_errors_warnings()
            policy_ew['behavior'] = errors_warnings['behavior']
            taxbrain_model.json_text.errors_warnings_text = json.dumps(policy_ew)
            taxbrain_model.save()
            # no problems--let's submit the jobs
            if len(errors_warnings['behavior']['errors']) == 0:

                # start calc job
                user_mods = dict({'policy': reform_dict}, **assumptions_dict)
                data = {'user_mods': user_mods,
                        'first_budget_year': int(start_year),
                        'use_puf_not_cps': model.use_puf_not_cps}
                data_list = [dict(year=i, **data) for i in range(NUM_BUDGET_YEARS)]
                submitted_ids, max_q_length = dropq_compute.submit_dropq_calculation(
                    data_list
                )

                model.job_ids = denormalize(submitted_ids)
                model.first_year = int(start_year)
                model.save()

                unique_url = DynamicBehaviorOutputUrl()
                if request.user.is_authenticated():
                    current_user = User.objects.get(pk=request.user.id)
                    unique_url.user = current_user
                if unique_url.taxcalc_vers != None:
                    pass
                else:
                    unique_url.taxcalc_vers = TAXCALC_VERSION

                if unique_url.webapp_vers != None:
                    pass
                else:
                    unique_url.webapp_vers = WEBAPP_VERSION

                unique_url.unique_inputs = model
                unique_url.model_pk = model.pk
                cur_dt = datetime.datetime.utcnow()
                future_offset = datetime.timedelta(seconds=((2 + max_q_length) * JOB_PROC_TIME_IN_SECONDS))
                expected_completion = cur_dt + future_offset
                unique_url.exp_comp_datetime = expected_completion
                unique_url.save()

                return redirect('behavior_results', unique_url.pk)
            else: # parameters caused some errors; store errors on object
                # ensure that parameters causing the warnings are shown on page
                # with warnings/errors
                dyn_mod_form = DynamicBehavioralInputsModelForm(
                    start_year,
                    True,
                    initial=json.loads(dyn_mod_form.data['raw_input_fields'])
                )
                dyn_mod_form.add_error(None, OUT_OF_RANGE_ERROR_MSG)
                append_errors_warnings(
                    errors_warnings['behavior'],
                    lambda param, msg: dyn_mod_form.add_error(param, msg)
                )
        has_errors = True
        # received POST but invalid results, return to form with errors
        form_personal_exemp = dyn_mod_form

    else:
        # Probably a GET request, load a default form
        print('method=GET get', request.GET)
        print('method=GET post', request.POST)
        params = parse_qs(urlparse(request.build_absolute_uri()).query)
        if 'start_year' in params and params['start_year'][0] in START_YEARS:
            start_year = params['start_year'][0]
        # Probably a GET request, load a default form
        form_personal_exemp = DynamicBehavioralInputsModelForm(
            first_year=start_year,
            use_puf_not_cps=True
        )


    behavior_default_params = default_behavior(int(start_year))

    init_context = {
        'form': form_personal_exemp,
        'params': behavior_default_params,
        'taxcalc_version': TAXCALC_VERSION,
        'webapp_version': WEBAPP_VERSION,
        'start_year': start_year,
        'pk': pk,
        'has_errors': has_errors
    }

    return render(request, 'dynamic/behavior.html', init_context)


def dynamic_elasticities(request, pk):
    """
    This view handles the dynamic macro elasticities input page and
    calls the function that handles the calculation on the inputs.
    """
    start_year = START_YEAR
    if request.method=='POST':
        # Client is attempting to send inputs, validate as form data
        fields = dict(request.GET)
        fields.update(dict(request.POST))
        fields = {k: v[0] if isinstance(v, list) else v for k, v in list(fields.items())}
        start_year = fields.get('start_year', START_YEAR)
        print(fields)
        # TODO: migrate first_year to start_year to get rid of weird stuff like
        # this
        fields['first_year'] = fields['start_year']
        # use_puf_not_cps set to True by default--doesn't matter for dynamic
        # input page. It is there for API consistency
        dyn_mod_form = DynamicElasticityInputsModelForm(start_year, True,
                                                        fields)

        if dyn_mod_form.is_valid():
            model = dyn_mod_form.save()

            gdp_elasticity = float(model.elastic_gdp)

            #get microsim data
            outputsurl = OutputUrl.objects.get(pk=pk)
            model.micro_sim = outputsurl
            taxbrain_model = outputsurl.unique_inputs
            model.data_source = taxbrain_model.data_source
            # get taxbrain data
            # inputs are re-built because the loaded JSON serialization loses
            # some info around the start year
            taxbrain_model.set_fields()
            (reform_dict, _, reform_text, _,
                errors_warnings) = taxbrain_model.get_model_specs()
            json_reform = JSONReformTaxCalculator(
                reform_text=json.dumps(reform_dict),
                raw_reform_text=reform_text,
                errors_warnings_text=json.dumps(errors_warnings)
            )
            json_reform.save()
            taxbrain_model.json_text = json_reform
            # empty assumptions dictionary
            assumptions_dict = {"behavior": {},
                                "growdiff_response": {},
                                "consumption": {},
                                "growdiff_baseline": {},
                                "growmodel": {}}

            user_mods = dict({'policy': reform_dict}, **assumptions_dict)
            data = {'user_mods': user_mods,
                    'gdp_elasticity': gdp_elasticity,
                    'first_budget_year': int(start_year),
                    'use_puf_not_cps': model.use_puf_not_cps}

            # start calc job
            data_list = [dict(year_n=i, **data) for i in range(NUM_BUDGET_YEARS)]
            submitted_ids, max_q_length = dropq_compute.submit_elastic_calculation(
                data_list
            )

            if not submitted_ids:
                no_inputs = True
                form_personal_exemp = personal_inputs
            else:
                model.job_ids = denormalize(submitted_ids)
                model.first_year = int(start_year)
                model.save()

                unique_url = DynamicElasticityOutputUrl()
                if request.user.is_authenticated():
                    current_user = User.objects.get(pk=request.user.id)
                    unique_url.user = current_user

                if unique_url.taxcalc_vers != None:
                    pass
                else:
                    unique_url.taxcalc_vers = TAXCALC_VERSION

                if unique_url.webapp_vers != None:
                    pass
                else:
                    unique_url.webapp_vers = WEBAPP_VERSION

                unique_url.unique_inputs = model
                unique_url.model_pk = model.pk

                cur_dt = datetime.datetime.utcnow()
                future_offset = datetime.timedelta(seconds=((2 + max_q_length) * JOB_PROC_TIME_IN_SECONDS))
                expected_completion = cur_dt + future_offset
                unique_url.exp_comp_datetime = expected_completion
                unique_url.save()
                return redirect('elastic_results', unique_url.pk)

        else:
            # received POST but invalid results, return to form with errors
            form_personal_exemp = dyn_mod_form

    else:
        # Probably a GET request, load a default form
        params = parse_qs(urlparse(request.build_absolute_uri()).query)
        if 'start_year' in params and params['start_year'][0] in START_YEARS:
            start_year = params['start_year'][0]

        form_personal_exemp = DynamicElasticityInputsModelForm(
            first_year=start_year,
            use_puf_not_cps=True
        )

    elasticity_default_params = default_elasticity_parameters(int(start_year))

    init_context = {
        'form': form_personal_exemp,
        'params': elasticity_default_params,
        'taxcalc_version': TAXCALC_VERSION,
        'webapp_version': WEBAPP_VERSION,
        'start_year': start_year,
        'pk': pk
    }

    if has_field_errors(form_personal_exemp):
        form_personal_exemp.add_error(None, "Some fields have errors.")

    return render(request, 'dynamic/elasticity.html', init_context)


def edit_dynamic_behavioral(request, pk):
    """
    This view handles the editing of previously entered inputs
    """
    try:
        url = DynamicBehaviorOutputUrl.objects.get(pk=pk)
    except:
        raise Http404

    model = url.unique_inputs
    start_year = model.first_year
    model.set_fields()
    #Get the user-input from the model in a way we can render
    ser_model = serializers.serialize('json', [model])
    user_inputs = json.loads(ser_model)
    inputs = user_inputs[0]['fields']

    form_personal_exemp = DynamicBehavioralInputsModelForm(
        first_year=start_year,
        use_puf_not_cps=model.use_puf_not_cps,
        instance=model
    )
    behavior_default_params = default_behavior_parameters(int(start_year))

    taxcalc_vers_disp = get_version(url, 'taxcalc_vers', TAXCALC_VERSION)
    webapp_vers_disp = get_version(url, 'webapp_vers', WEBAPP_VERSION)

    init_context = {
        'form': form_personal_exemp,
        'params': behavior_default_params,
        'taxcalc_version': taxcalc_vers_disp,
        'webapp_version': webapp_vers_disp,
        'start_year': str(start_year),
        'pk': model.micro_sim.pk
    }

    return render(request, 'dynamic/behavior.html', init_context)


def edit_dynamic_elastic(request, pk):
    """
    This view handles the editing of previously compute elasticity of GDP
    dynamic simulation
    """
    try:
        url = DynamicElasticityOutputUrl.objects.get(pk=pk)
    except:
        raise Http404

    model = url.unique_inputs
    start_year = model.first_year
    #Get the user-input from the model in a way we can render
    ser_model = serializers.serialize('json', [model])
    user_inputs = json.loads(ser_model)
    inputs = user_inputs[0]['fields']

    form_personal_exemp = DynamicElasticityInputsModelForm(
        first_year=start_year,
        use_puf_not_cps=model.use_puf_not_cps,
        instance=model
    )
    elasticity_default_params = default_elasticity_parameters(int(start_year))

    taxcalc_vers_disp = get_version(url, 'taxcalc_vers', TAXCALC_VERSION)
    webapp_vers_disp = get_version(url, 'webapp_vers', WEBAPP_VERSION)

    init_context = {
        'form': form_personal_exemp,
        'params': elasticity_default_params,
        'taxcalc_version': taxcalc_vers_disp,
        'webapp_version': webapp_vers_disp,
        'start_year': str(start_year),
        'pk': model.micro_sim.pk
    }

    return render(request, 'dynamic/elasticity.html', init_context)


def dynamic_landing(request, pk):
    """
    This view gives a landing page to choose a type of dynamic simulation that
    is linked to the microsim
    """
    outputsurl = OutputUrl.objects.get(pk=pk)
    taxbrain_model = outputsurl.unique_inputs
    include_ogusa = True
    init_context = {
            'pk': pk,
            'is_authenticated': request.user.is_authenticated(),
            'include_ogusa': include_ogusa,
            'start_year': request.GET['start_year'],
            'taxcalc_version': TAXCALC_VERSION,
            'webapp_version': WEBAPP_VERSION
            }

    return render_to_response('dynamic/landing.html', init_context)



def dynamic_finished(request):
    """
    This view sends an email to the job submitter that the dynamic job
    is done. It also sends CC emails to the CC list.
    """

    job_id = request.GET['job_id']
    status = request.GET['status']
    qs = DynamicSaveInputs.objects.filter(job_ids__contains=job_id)
    dsi = qs[0]
    email_addr = dsi.user_email

    # We know the results are ready so go get them from the server
    job_ids = dsi.job_ids
    submitted_ids = normalize(job_ids)
    result = dynamic_compute.ogusa_get_results(submitted_ids, status=status)
    dsi.tax_result = result
    dsi.creation_date = datetime.datetime.now()
    dsi.save()

    params = dynamic_params_from_model(dsi)
    microsim_url = "/taxbrain/" + str(dsi.micro_sim.pk)
    #Create a new output model instance
    if status == "SUCCESS":
        unique_url = DynamicOutputUrl()
        if request.user.is_authenticated():
            current_user = User.objects.get(pk=request.user.id)
            unique_url.user = current_user
        unique_url.unique_inputs = dsi
        unique_url.model_pk = dsi.pk
        unique_url.save()
        result_url = "/dynamic/results/{pk}".format(pk=unique_url.pk)
        text = success_text()
        text = text.format(url=result_url, microsim_url=microsim_url,
                           job_id=job_id, params=params)
        cc_txt, subj_txt = cc_text_finished(url=result_url)

    elif status == "FAILURE":
        text = failure_text()
        text = text.format(traceback=result['job_fail'], microsim_url=microsim_url,
                           job_id=job_id, params=params)

        cc_txt, subj_txt = cc_text_failure(traceback=result['job_fail'])
    else:
        raise ValueError("status must be either 'SUCCESS' or 'FAILURE'")

    send_mail(subject="Your TaxBrain simulation has completed!",
        message = text,
        from_email = "Open Source Policy Center <mailing@ospc.org>",
        recipient_list = [email_addr])

    send_cc_email(cc_txt, subj_txt, dsi)
    response = HttpResponse('')

    return response


def show_job_submitted(request, pk):
    """
    This view gives the necessary info to show that a dynamic job was
    submitted.
    """
    model = DynamicSaveInputs.objects.get(pk=pk)
    job_id = model.job_ids
    submitted_ids_and_ips = normalize(job_id)
    submitted_id, submitted_ip = submitted_ids_and_ips[0]
    return render_to_response('dynamic/submitted.html', {'job_id': submitted_id})


def elastic_results(request, pk):
    """
    This view handles the results page.
    """
    try:
        url = DynamicElasticityOutputUrl.objects.get(pk=pk)
    except:
        raise Http404

    taxcalc_vers_disp = get_version(url, 'taxcalc_vers', TAXCALC_VERSION)
    webapp_vers_disp = get_version(url, 'webapp_vers', WEBAPP_VERSION)

    context_vers_disp = {'taxcalc_version': taxcalc_vers_disp,
                         'webapp_version': webapp_vers_disp}

    model = url.unique_inputs
    if model.tax_result:
        output = model.tax_result
        first_year = model.first_year
        created_on = model.creation_date
        tables = elast_results_to_tables(output, first_year)
        microsim_url = "/taxbrain/" + str(url.unique_inputs.micro_sim.pk)

        context = {
            'locals':locals(),
            'unique_url':url,
            'taxcalc_version':taxcalc_vers_disp,
            'webapp_version':webapp_vers_disp,
            'tables':tables,
            'created_on':created_on,
            'first_year':first_year,
            'microsim_url':microsim_url
        }

        return render(request, 'dynamic/elasticity_results.html', context)

    else:
        if not model.check_hostnames(DROPQ_WORKERS):
            print('bad hostname', model.jobs_not_ready, DROPQ_WORKERS)
            raise render_to_response('taxbrain/failed.html')
        job_ids = model.job_ids
        jobs_to_check = model.jobs_not_ready
        if not jobs_to_check:
            jobs_to_check = normalize(job_ids)
        else:
            jobs_to_check = normalize(jobs_to_check)

        try:
            jobs_ready = dropq_compute.dropq_results_ready(jobs_to_check)
        except JobFailError as jfe:
            print(jfe)
            return render_to_response('taxbrain/failed.html')

        if any([j == 'FAIL' for j in jobs_ready]):
            failed_jobs = [sub_id for (sub_id, job_ready) in
                           zip(jobs_to_check, jobs_ready) if job_ready == 'FAIL']

            #Just need the error message from one failed job
            error_msgs = dropq_compute.dropq_get_results([failed_jobs[0]], job_failure=True)
            error_msg = error_msgs[0]
            val_err_idx = error_msg.rfind("Error")
            error = ErrorMessageTaxCalculator()
            error_contents = error_msg[val_err_idx:].replace(" ","&nbsp;")
            error.text = error_contents
            error.save()
            model.error_text = error
            model.save()
            return render(request, 'taxbrain/failed.html', {"error_msg": error_contents})


        if all([job == 'YES' for job in jobs_ready]):
            model.tax_result = dropq_compute.elastic_get_results(normalize(job_ids))
            model.creation_date = datetime.datetime.now()
            model.save()
            return redirect(url)

        else:
            jobs_not_ready = [sub_id for (sub_id, job_ready) in
                                zip(jobs_to_check, jobs_ready) if not job_ready == 'YES']
            jobs_not_ready = denormalize(jobs_not_ready)
            model.jobs_not_ready = jobs_not_ready
            model.save()
            if request.method == 'POST':
                # if not ready yet, insert number of minutes remaining
                exp_comp_dt = url.exp_comp_datetime
                utc_now = datetime.datetime.utcnow()
                utc_now = utc_now.replace(tzinfo=pytz.utc)
                dt = exp_comp_dt - utc_now
                exp_num_minutes = dt.total_seconds() / 60.
                exp_num_minutes = round(exp_num_minutes, 2)
                exp_num_minutes = exp_num_minutes if exp_num_minutes > 0 else 0
                if exp_num_minutes > 0:
                    return JsonResponse({'eta': exp_num_minutes}, status=202)
                else:
                    return JsonResponse({'eta': exp_num_minutes}, status=200)

            else:
                print("rendering not ready yet")
                context = {'eta': '100'}
                context.update(context_vers_disp)
                return render_to_response('dynamic/not_ready.html', context, context_instance=RequestContext(request))


def ogusa_results(request, pk):
    """
    This view handles the results page.
    """
    try:
        url = DynamicOutputUrl.objects.get(pk=pk)
    except:
        raise Http404

    output = url.unique_inputs.tax_result
    first_year = url.unique_inputs.first_year
    created_on = url.unique_inputs.creation_date
    tables = ogusa_results_to_tables(output, first_year)
    microsim_url = "/taxbrain/" + str(url.unique_inputs.micro_sim.pk)

    ogusa_vers_disp = get_version(url, 'ogusa_vers', OGUSA_VERSION)
    taxcalc_vers_disp = get_version(url, 'taxcalc_vers', TAXCALC_VERSION)
    webapp_vers_disp = get_version(url, 'webapp_vers', WEBAPP_VERSION)

    context = {
        'locals':locals(),
        'unique_url':url,
        'ogusa_version':ougsa_vers_display,
        'webapp_version': webapp_vers_disp,
        'taxcalc_vers': taxcalc_vers_disp,
        'tables':tables,
        'created_on':created_on,
        'first_year':first_year,
        'microsim_url':microsim_url
    }

    return render(request, 'dynamic/results.html', context)



def behavior_results(request, pk):
    """
    This view handles the partial equilibrium results page.
    """
    try:
        url = DynamicBehaviorOutputUrl.objects.get(pk=pk)
    except:
        raise Http404

    taxcalc_vers_disp = get_version(url, 'taxcalc_vers', TAXCALC_VERSION)
    webapp_vers_disp = get_version(url, 'webapp_vers', WEBAPP_VERSION)

    context_vers_disp = {'taxcalc_version': taxcalc_vers_disp,
                         'webapp_version': webapp_vers_disp}

    model = url.unique_inputs

    first_year = model.first_year or int(START_YEAR)
    micro = model.micro_sim.unique_inputs
    if (micro.json_text is not None and (micro.json_text.raw_reform_text or
                                         micro.json_text.raw_assumption_text)):
        reform_file_contents = micro.json_text.raw_reform_text
        reform_file_contents = reform_file_contents.replace(" ", "&nbsp;")
        assump_file_contents = micro.json_text.raw_assumption_text
        assump_file_contents = assump_file_contents.replace(" ", "&nbsp;")
    elif micro.input_fields is not None:
        reform = to_json_reform(first_year, micro.input_fields)
        reform_file_contents = json.dumps(reform, indent=4)
        assump_file_contents = '{}'
    else:
        reform_file_contents = ''
        assump_file_contents = ''

    dynamic_parameters = to_json_reform(first_year, model.input_fields)
    dynamic_file_contents = json.dumps(dynamic_parameters, indent=4)

    if model.tax_result:
        # try to render table; if failure render not available page
        try:
            output = model.get_tax_result()
            first_year = model.first_year
            created_on = model.creation_date
            if 'fiscal_tots' in output:
                # Use new key/value pairs for old data
                output['aggr_d'] = output['fiscal_tots']
                output['aggr_1'] = output['fiscal_tots']
                output['aggr_2'] = output['fiscal_tots']
                del output['fiscal_tots']

            tables = taxcalc_results_to_tables(output, first_year)
            tables["tooltips"] = {
                'distribution': DISTRIBUTION_TOOLTIP,
                'difference': DIFFERENCE_TOOLTIP,
                'payroll': PAYROLL_TOOLTIP,
                'income': INCOME_TOOLTIP,
                'base': BASE_TOOLTIP,
                'reform': REFORM_TOOLTIP,
                'bins': INCOME_BINS_TOOLTIP,
                'deciles': INCOME_DECILES_TOOLTIP
            }
            is_registered = True if request.user.is_authenticated() else False
            microsim_url = "/taxbrain/" + str(model.micro_sim.pk)

            # TODO: Fix the java script mapping problem.  There exists somewhere in
            # the taxbrain javascript code a mapping to the old table names.  As
            # soon as this is changed to accept the new table names, this code NEEDS
            # to be removed.
            tables['fiscal_change'] = add_summary_column(tables.pop('aggr_d'))
            tables['fiscal_currentlaw'] = add_summary_column(tables.pop('aggr_1'))
            tables['fiscal_reform'] = add_summary_column(tables.pop('aggr_2'))
            tables['mY_dec'] = tables.pop('dist2_xdec')
            tables['mX_dec'] = tables.pop('dist1_xdec')
            tables['df_dec'] = tables.pop('diff_itax_xdec')
            tables['pdf_dec'] = tables.pop('diff_ptax_xdec')
            tables['cdf_dec'] = tables.pop('diff_comb_xdec')
            tables['mY_bin'] = tables.pop('dist2_xbin')
            tables['mX_bin'] = tables.pop('dist1_xbin')
            tables['df_bin'] = tables.pop('diff_itax_xbin')
            tables['pdf_bin'] = tables.pop('diff_ptax_xbin')
            tables['cdf_bin'] = tables.pop('diff_comb_xbin')
            json_table = json.dumps(tables)

        except Exception as e:
            print('Exception rendering pk', pk, e)
            traceback.print_exc()
            edit_href = '/dynamic/behavioral/edit/{}/?start_year={}'.format(
                pk,
                model.first_year or START_YEAR # sometimes first_year is None
            )
            not_avail_context = dict(edit_href=edit_href,
                                     **context_vers_disp)
            return render(request, 'taxbrain/not_avail.html', not_avail_context)

        context = {
            'locals':locals(),
            'unique_url':url,
            'tables': json_table,
            'created_on': created_on,
            'first_year': first_year,
            'is_registered': is_registered,
            'is_behavior': True,
            'microsim_url': microsim_url,
            'reform_file_contents': reform_file_contents,
            'assump_file_contents': assump_file_contents,
            'dynamic_file_contents': dynamic_file_contents,
            'results_type': "behavioral"
        }
        context.update(context_vers_disp)
        return render(request, 'taxbrain/results.html', context)

    else:
        if not model.check_hostnames(DROPQ_WORKERS):
            print('bad hostname', model.jobs_not_ready, DROPQ_WORKERS)
            raise render_to_response('taxbrain/failed.html')
        job_ids = model.job_ids
        jobs_to_check = model.jobs_not_ready
        if not jobs_to_check:
            jobs_to_check = normalize(job_ids)
        else:
            jobs_to_check = normalize(jobs_to_check)

        try:
            jobs_ready = dropq_compute.dropq_results_ready(jobs_to_check)
        except JobFailError as jfe:
            print(jfe)
            return render_to_response('taxbrain/failed.html')

        if all([job == 'YES' for job in jobs_ready]):
            results = dropq_compute.dropq_get_results(normalize(job_ids))
            model.tax_result = results
            model.creation_date = datetime.datetime.now()
            model.save()
            return redirect('behavior_results', url.pk)
        else:
            jobs_not_ready = [sub_id for (sub_id, job_ready) in
                                zip(jobs_to_check, jobs_ready) if not job_ready == 'YES']
            jobs_not_ready = denormalize(jobs_not_ready)
            model.jobs_not_ready = jobs_not_ready
            model.save()
            if request.method == 'POST':
                # if not ready yet, insert number of minutes remaining
                exp_comp_dt = url.exp_comp_datetime
                utc_now = datetime.datetime.utcnow()
                utc_now = utc_now.replace(tzinfo=pytz.utc)
                dt = exp_comp_dt - utc_now
                exp_num_minutes = dt.total_seconds() / 60.
                exp_num_minutes = round(exp_num_minutes, 2)
                exp_num_minutes = exp_num_minutes if exp_num_minutes > 0 else 0
                if exp_num_minutes > 0:
                    return JsonResponse({'eta': exp_num_minutes}, status=202)
                else:
                    return JsonResponse({'eta': exp_num_minutes}, status=200)

            else:
                print("rendering not ready yet")
                context = {'eta': '100'}
                context.update(context_vers_disp)
                return render_to_response('dynamic/not_ready.html', context, context_instance=RequestContext(request))
