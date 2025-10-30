from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CrearUserForms
from .models import *


def blogin(request):
    '''returns the login templets'''
    if request.user.is_authenticated:
        return redirect('faq')
    else:
        if request.method == 'POST':
            email = request.POST.get('email')
            password = request.POST.get('password')
            user = authenticate(request, username=email, password=password)
            #print(user)
            if user is not None:
                print("done")
                login(request, user)
                return redirect('faq')
            else:
                messages.info(request, 'Username OR Password is Incorrect')
        # return HttpResponse("Hello, world. You're at the polls index.")
        return render(request, 'todo/login.html')

def signout(request):
    logout(request)
    return redirect('faq')

def signup(request):
    if request.user.is_authenticated:
        return redirect('batch')
    else:
        form = CrearUserForms()
        if request.method == 'POST':
            form = CrearUserForms(request.POST)
            if form.is_valid():
                form.save()
                user = form.cleaned_data.get('first_name')
                messages.success(request, 'Account has been Created Successfully for ' + user)
                return redirect('login')
        context = {'form': form}
        return render(request, 'todo/signup.html', context)

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

@login_required(login_url='login')
def faqdb(request):
    faq_form = FaqDb()
    if request.method == 'POST':
        data = request.POST
        faq_form.question = data["question"]
        faq_form.short_description = data["sdec"]
        faq_form.created_by = request.user
        faq_form.save()
        return redirect('faq')
    faqs = FaqDb.objects.filter(created_by=request.user).order_by('-created_at')
    return render(request, 'todo/faq.html', {'faqs': faqs})

