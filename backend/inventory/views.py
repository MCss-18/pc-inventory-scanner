import json
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
from django.http import HttpResponse
from .memory_store import DEVICES

@csrf_exempt
def receive_audit(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body)

        data["received_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        DEVICES.append(data)

        return JsonResponse({"status": "ok"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


def dashboard(request):
    return render(request, "inventory/dashboard.html", {
        "devices": DEVICES
    })

def devices_json(request):
    return JsonResponse(DEVICES, safe=False)

def download_inventory_json(request):
    filename = f"inventario_ti_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    response = HttpResponse(
        json.dumps(DEVICES, indent=2, ensure_ascii=False),
        content_type="application/json"
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response

def download_device_json(request, device_hash):
    device = next(
        (d for d in DEVICES if d["audit"]["device_hash"] == device_hash),
        None
    )

    if not device:
        return HttpResponse(status=404)

    filename = f"{device['hostname']}_{device_hash[:8]}.json"

    response = HttpResponse(
        json.dumps(device, indent=2, ensure_ascii=False),
        content_type="application/json"
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response