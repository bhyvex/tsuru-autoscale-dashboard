from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from django.contrib import messages

from wizard import forms
from wizard import client

import requests
import os
import urllib
import json


def tsuru_host():
    return os.environ.get("TSURU_HOST", "")


def app_info(name, token):
    url = "{}/apps/{}".format(tsuru_host(), name)
    headers = {"Authorization": token}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    return None


def get_or_create_tsuru_instance(instance_name, token):
    token = urllib.unquote(token)
    token = "bearer {}".format(token)
    url = "{}/services/instances/{}".format(tsuru_host(), instance_name)
    headers = {"Authorization": token}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return

    app = app_info(instance_name, token)
    url = "{}/services/instances".format(tsuru_host(), instance_name)
    headers = {"Authorization": token}
    data = {"service_name": "autoscale", "name": instance_name, "owner": app["teamowner"]}
    response = requests.post(url, headers=headers, data=json.dumps(data))

    url = "{}/services/instances/{}/{}".format(tsuru_host(), instance_name, instance_name)
    headers = {"Authorization": token}
    response = requests.put(url, headers=headers)


def new(request, instance=None):
    token = request.GET.get("TSURU_TOKEN")

    scale_up_form = forms.ScaleForm(request.POST or None, prefix="scale_up")
    scale_down_form = forms.ScaleForm(request.POST or None, prefix="scale_down")
    config_form = forms.ConfigForm(request.POST or None)

    if scale_up_form.is_valid() and scale_down_form.is_valid() and config_form.is_valid():
        get_or_create_tsuru_instance(instance, token)
        config_data = {
            "name": instance,
            "minUnits": config_form.cleaned_data["min"],
            "scaleUp": scale_up_form.cleaned_data,
            "scaleDown": scale_down_form.cleaned_data,
        }
        client.new(config_data, token)
        messages.success(request, u"Auto scale saved.")
        url = "{}?TSURU_TOKEN={}".format(reverse("app-info", args=[instance]), urllib.quote(token))
        return redirect(url)

    token = urllib.quote(token)
    context = {
        "scale_up_form": scale_up_form,
        "scale_down_form": scale_down_form,
        "config_form": config_form,
        "token": token,
    }

    return render(request, "wizard/index.html", context)
