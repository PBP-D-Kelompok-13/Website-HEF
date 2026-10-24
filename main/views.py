from django.shortcuts import render

''' =============================== 
    Functions for Main Landing Page
    =============================== '''

def show_landing_page(request):
    return render(request, "pages/landing_page.html")