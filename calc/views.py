from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .forms import CalcForm
from .models import BuildingClass
from .services import CalcError, calculate
from .models import BuildingClass, BuildingPurpose


@require_GET
def purpose_meta(request, purpose_id: int):
    p = BuildingPurpose.objects.filter(pk=purpose_id).values(
        "id", "category"
    ).first()
    if not p:
        return JsonResponse({"error": "not found"}, status=404)
    is_hotel = p["category"] == BuildingPurpose.CAT_HOTEL
    finish_enabled = p["category"] in (
        BuildingPurpose.CAT_RESIDENTIAL, BuildingPurpose.CAT_HOTEL
    )
    return JsonResponse({
        "category": p["category"],
        "finish_enabled": finish_enabled,
        "area_label": "Площадь номерного фонда" if is_hotel else "Общая площадь, м²",
    })

def index(request):
    result = None
    error = None
    if request.method == "POST":
        form = CalcForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            try:
                result = calculate(
                    city=cd["city"],
                    purpose=cd["purpose"],
                    building_class=cd["building_class"],
                    floors=cd["floors"],
                    total_area=cd["total_area"],
                    underground_parking=cd.get("underground_parking", False),
                    ground_parking_spaces=cd.get("ground_parking_spaces") or 0,
                    start_date=cd["start_date"],
                    finish_enabled=cd.get("finish_enabled", False),
                    finish_type=cd.get("finish_type") or "wb",
                    finish_custom_rate=cd.get("finish_custom_rate"),
                )
            except CalcError as e:
                error = str(e)
    else:
        form = CalcForm()

    return render(request, "calc/form.html", {
        "form": form,
        "result": result,
        "error": error,
        "active": "calc",
    })


def history(request):
    return render(request, "calc/history.html", {"active": "history"})


@require_GET
def classes_for_purpose(request, purpose_id: int):
    qs = (
        BuildingClass.objects
        .filter(purposes__id=purpose_id)
        .order_by("order", "name")
        .values("id", "name")
    )
    return JsonResponse({"classes": list(qs)})