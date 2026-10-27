from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from .forms import *
from .models import *

''' =============================== 
    Functions for Main Landing Page
    =============================== '''

def show_landing_page(request):
    return render(request, "pages/landing_page.html")

''' =============================== 
    Functions for Authentication
    =============================== '''
def register_account(request):
    if request.user.is_authenticated:
        return redirect('main:show_landing_page')

    form = CustomUserCreationForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('main:login_account')

    return render(request, 'pages/register.html', {'form': form})

def login_account(request):
    if request.user.is_authenticated:
        return redirect('main:show_landing_page')

    form = CustomAuthenticationForm(
        request,
        data=request.POST if request.method == 'POST' else None,
    )
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        return redirect('main:show_landing_page')

    return render(request, 'pages/login.html', {'form': form})

''' =============================== 
    Functions for Food Inventory
    =============================== '''
@login_required(login_url='main:login_account')
def show_inventory(request):
    ingredients = Ingredient.objects.filter(user=request.user)
    form = IngredientForm()
    context = {
        'ingredients': ingredients,
        'form': form,
    }
    return render(request, 'pages/inventory.html', context)

@login_required(login_url='main:login_account')
def add_ingredient(request):
    if request.method == 'POST':
        form = IngredientForm(request.POST)
        if form.is_valid():
            ingredient = form.save(commit=False)
            ingredient.user = request.user
            ingredient.save()
    return redirect('main:show_inventory')

@login_required(login_url='main:login_account')
def edit_ingredient(request, pk):
    ingredient = get_object_or_404(Ingredient, pk=pk, user=request.user)
    if request.method == 'POST':
        form = IngredientForm(request.POST, instance=ingredient)
        if form.is_valid():
            form.save()
    return redirect('main:show_inventory')

@login_required(login_url='main:login_account')
def delete_ingredient(request, pk):
    ingredient = get_object_or_404(Ingredient, pk=pk, user=request.user)
    ingredient.delete()
    return redirect('main:show_inventory')