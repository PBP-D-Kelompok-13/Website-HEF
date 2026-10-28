from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Bookmark, CustomUser, Product

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    fieldsets = UserAdmin.fieldsets + (
        ('Extra Info', {'fields': ('date_of_birth',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Extra Info', {'fields': ('email', 'date_of_birth')}),
    )

admin.site.register(CustomUser, CustomUserAdmin)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "brand", "barcode", "category", "eco_grade", "nutri_grade")
    list_filter = ("category", "eco_grade", "nutri_grade")
    search_fields = ("name", "brand", "barcode")


admin.site.register(Bookmark)
