from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from .models import *


def index(request):
    '''returns the daily text form'''
    quot_obj = Quotes()
    auth_obj = Auth_names()
    mant_obj = Mantras()
    quot_count = Quotes.objects.all().count()
    auth_count = Auth_names.objects.all().count()
    mant_count = Mantras.objects.all().count()
    if request.method == 'POST':
        data = request.POST
        mant_obj.mantra = data["p_name"]
        try:
            mant_obj.save()
        except Exception as e:
            messages.info(request, 'Duplicate Mantra')
        auth_obj.name = data["a_name"]
        try:
            auth_obj.save()
        except Exception as e:
            messages.info(request, 'Duplicate Author')
        quot_obj.auth = Auth_names.objects.get(name = data["a_name"])
        quot_obj.quote = data["dec"]
        try:
            quot_obj.save()
        except Exception as e:
            messages.info(request, 'Duplicate Quote')

        return redirect('index')
    context = {'qc': quot_count, 'ac': auth_count, 'mc': mant_count}
    return render(request, 'todo/daily.html', context)
