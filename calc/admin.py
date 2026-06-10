from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.html import format_html

from . import views_admin
from .models import (
    BuildingClass,
    BuildingPurpose,
    City,
    ConstructionDuration,
    CostItem,
    CostRate,
    Inflation,
    ParkingRate,
    Settings,
    SocialNorms,
)


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(BuildingPurpose)
class BuildingPurposeAdmin(admin.ModelAdmin):
    list_display = ("name", "apartments_area_ratio", "allowed_classes_count")
    search_fields = ("name",)
    filter_horizontal = ("allowed_classes",)

    @admin.display(description="Классов")
    def allowed_classes_count(self, obj):
        return obj.allowed_classes.count()


@admin.register(BuildingClass)
class BuildingClassAdmin(admin.ModelAdmin):
    list_display = ("name", "order")
    list_editable = ("order",)


class CostRateAdmin(admin.ModelAdmin):
    list_display = ("city", "building_class", "price_per_sqm")
    list_filter = ("city", "building_class")
    search_fields = ("city__name", "building_class__name")
    list_editable = ("price_per_sqm",)
    change_list_template = "calc/admin_costrate_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("pivot/", self.admin_site.admin_view(views_admin.cost_pivot),
                 name="calc_costrate_pivot"),
            path("pivot/save/", self.admin_site.admin_view(views_admin.cost_pivot_save),
                 name="calc_costrate_pivot_save"),
            path("pivot/add-city/", self.admin_site.admin_view(views_admin.cost_pivot_add_city),
                 name="calc_costrate_pivot_add_city"),
            path("pivot/import/preview/",
                 self.admin_site.admin_view(views_admin.cost_pivot_import_preview),
                 name="calc_costrate_pivot_import_preview"),
            path("pivot/import/apply/",
                 self.admin_site.admin_view(views_admin.cost_pivot_import_apply),
                 name="calc_costrate_pivot_import_apply"),
        ]
        return custom + urls


admin.site.register(CostRate, CostRateAdmin)


# Алиасы под namespace, который ждёт views_admin (reverse 'calc_admin:...').
# Используем имена URL-ов admin-сайта напрямую — переопределим reverse через шорткат.
# Чтобы не плодить namespace, переписываем views_admin reverse на admin-имена:
# (см. правки ниже в шаблоне — используем {% url 'admin:calc_costrate_pivot_save' %})


@admin.register(ConstructionDuration)
class ConstructionDurationAdmin(admin.ModelAdmin):
    list_display = ("area", "months")
    list_editable = ("months",)
    list_display_links = ("area",)
    ordering = ("area",)
    list_per_page = 100
    search_fields = ("area",)


@admin.register(Inflation)
class InflationAdmin(admin.ModelAdmin):
    list_display = ("rate", "is_active", "note")
    list_editable = ("is_active",)


@admin.register(SocialNorms)
class SocialNormsAdmin(admin.ModelAdmin):
    list_display = (
        "sqm_per_doo_seat",
        "cost_per_doo_seat",
        "sqm_per_school_seat",
        "cost_per_school_seat",
        "is_active",
    )


@admin.register(ParkingRate)
class ParkingRateAdmin(admin.ModelAdmin):
    list_display = ("city", "cost_per_space")
    list_editable = ("cost_per_space",)


@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    list_display = ("inflation_clean_coef", "is_active")


class CostItemChildInline(admin.TabularInline):
    model = CostItem
    fk_name = "parent"
    extra = 0
    fields = ("code", "name", "percent", "order", "item_type", "is_active")
    verbose_name = "Подстатья"
    verbose_name_plural = "Подстатьи"


@admin.register(CostItem)
class CostItemAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "percent", "order", "item_type", "parent", "is_active")
    list_editable = ("percent", "order", "is_active")
    list_display_links = ("code",)
    list_filter = ("item_type", "is_active")
    search_fields = ("code", "name")
    ordering = ("order", "code")
    inlines = [CostItemChildInline]


admin.site.site_header = "Экспресс-стройэкспертиза — админка"
admin.site.site_title = "Экспресс-стройэкспертиза"
admin.site.index_title = "Управление справочниками"