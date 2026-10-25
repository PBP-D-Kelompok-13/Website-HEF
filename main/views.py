from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpResponse
from django.urls import reverse
from .forms import CustomUserCreationForm

''' =============================== 
    Functions for Main Landing Page
    =============================== '''

def show_landing_page(request):
    return render(request, "pages/landing_page.html")

''' =============================== 
    Functions for Authentication
    =============================== '''
def register_account(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()

            # HTMX response handling
            if request.headers.get('HX-Request') == 'true':
                response = HttpResponse(status=204)
                response['HX-Redirect'] = reverse("main:login_account")
                return response

            # POST fallback redirect
            return redirect("main:login_account")

        else:
            # Invalid HTMX post handling (returns HTTP status 422)
            if request.headers.get('HX-Request') == 'true':
                return render(request, 'modals/register.html', {'form': form}, status=422)
    else:
        # GET request - empty form initialization
        form = CustomUserCreationForm()

    return render(request, 'modals/register.html', {'form': form})

def login_account(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            
            # Successful HTMX post handling
            if request.headers.get('HX-Request') == 'true':
                response = HttpResponse(status=204)
                response['HX-Redirect'] = reverse('main:show_landing_page')
                return response
            
            # POST fallback redirect
            return redirect('main:show_landing_page')
        else:
            # Invalid HTMX post handling (returns HTTP status 422)
            if request.headers.get('HX-Request') == 'true':
                return render(request, 'modals/login.html', {'form': form}, status=422)
    else:
        # GET request - empty form initialization
        form = AuthenticationForm(request)

    return render(request, 'modals/login.html', {'form': form})