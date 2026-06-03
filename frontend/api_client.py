"""
Frontend API Client — tất cả HTTP calls đến backend qua đây.
BASE_URL: http://localhost:8001/api/v1
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from typing import Optional, List

BASE_URL = "http://localhost:8001/api/v1"
_TIMEOUT = 15.0


def _get(path: str, params: dict = None) -> Optional[dict | list]:
    try:
        r = httpx.get(f"{BASE_URL}{path}", params=params, timeout=_TIMEOUT, follow_redirects=True)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[API GET] {path} -> ERROR: {e}")
        return None


def _post(path: str, json: dict = None, params: dict = None) -> Optional[dict | list]:
    try:
        r = httpx.post(f"{BASE_URL}{path}", json=json, params=params, timeout=_TIMEOUT, follow_redirects=True)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[API POST] {path} -> ERROR: {e}")
        return None


def _put(path: str, json: dict = None, params: dict = None) -> Optional[dict]:
    try:
        r = httpx.put(f"{BASE_URL}{path}", json=json, params=params, timeout=_TIMEOUT, follow_redirects=True)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[API PUT] {path} -> ERROR: {e}")
        return None


def _delete(path: str, params: dict = None) -> bool:
    try:
        r = httpx.delete(f"{BASE_URL}{path}", params=params, timeout=_TIMEOUT, follow_redirects=True)
        r.raise_for_status()
        return True
    except Exception as e:
        print(f"[API DELETE] {path} -> ERROR: {e}")
        return False


# ══════════════════════════════════════════════════════════════
# STAFF
# ══════════════════════════════════════════════════════════════

def get_staff(role: str = None, is_on_project: bool = None) -> list:
    params = {}
    if role:
        params["role"] = role
    if is_on_project is not None:
        params["is_on_project"] = is_on_project
    return _get("/staff", params=params) or []


def toggle_project(staff_id: int) -> Optional[dict]:
    return _put(f"/staff/{staff_id}/project-toggle")


def create_staff(full_name: str, role: str, is_on_project: bool = False,
                 display_order: int = 99) -> Optional[dict]:
    return _post("/staff", json={
        "full_name": full_name, "role": role,
        "is_on_project": is_on_project, "display_order": display_order,
    })


def update_staff(staff_id: int, full_name: str = None, role: str = None,
                 is_on_project: bool = None, display_order: int = None) -> Optional[dict]:
    body = {}
    if full_name is not None:
        body["full_name"] = full_name
    if role is not None:
        body["role"] = role
    if is_on_project is not None:
        body["is_on_project"] = is_on_project
    if display_order is not None:
        body["display_order"] = display_order
    return _put(f"/staff/{staff_id}", json=body)


def delete_staff(staff_id: int) -> bool:
    return _delete(f"/staff/{staff_id}")


# ══════════════════════════════════════════════════════════════
# ABSENCES
# ══════════════════════════════════════════════════════════════

def get_absences(month: int = None, year: int = None) -> list:
    params = {}
    if month:
        params["month"] = month
    if year:
        params["year"] = year
    return _get("/constraints/absences", params=params) or []


def create_absence(staff_id: int, absence_date: str) -> Optional[dict]:
    return _post("/constraints/absences", json={"staff_id": staff_id,
                                                 "absence_date": absence_date})


def create_absence_range(staff_id: int, from_date: str, to_date: str) -> Optional[dict]:
    return _post("/constraints/absences/range", json={
        "staff_id": staff_id, "from_date": from_date, "to_date": to_date,
    })


def delete_absence(absence_id: int) -> bool:
    return _delete(f"/constraints/absences/{absence_id}")


def delete_absence_range(staff_id: int, from_date: str, to_date: str) -> bool:
    return _delete("/constraints/absences/range", params={
        "staff_id": staff_id, "from_date": from_date, "to_date": to_date,
    })


# ══════════════════════════════════════════════════════════════
# DUTY REQUESTS
# ══════════════════════════════════════════════════════════════

def get_requests(year: int = None, staff_id: int = None) -> list:
    params = {}
    if year:
        params["year"] = year
    if staff_id:
        params["staff_id"] = staff_id
    return _get("/constraints/requests", params=params) or []


def validate_request(staff_id: int, date: str, year: int) -> Optional[dict]:
    return _get("/constraints/requests/validate",
                params={"staff_id": staff_id, "date": date, "year": year})


def create_request(staff_id: int, request_type: str, year: int,
                   specific_date: str = None,
                   day_of_week: int = None) -> Optional[dict]:
    body = {"staff_id": staff_id, "request_type": request_type, "year": year}
    if specific_date:
        body["specific_date"] = specific_date
    if day_of_week is not None:
        body["day_of_week"] = day_of_week
    return _post("/constraints/requests", json=body)


def delete_request(request_id: int) -> bool:
    return _delete(f"/constraints/requests/{request_id}")


# ══════════════════════════════════════════════════════════════
# SPECIAL DAYS
# ══════════════════════════════════════════════════════════════

def get_special_days(month: int = None, year: int = None,
                     day_type: str = None) -> list:
    params = {}
    if month:
        params["month"] = month
    if year:
        params["year"] = year
    if day_type:
        params["day_type"] = day_type
    return _get("/constraints/special-days", params=params) or []


def create_special_day(date: str, day_type: str, label: str = None) -> Optional[dict]:
    return _post("/constraints/special-days",
                 json={"date": date, "day_type": day_type, "label": label})


def compute_cutoff(month: int, year: int) -> list:
    return _post("/constraints/special-days/compute-cutoff",
                 json={"month": month, "year": year}) or []


def confirm_special_day(special_day_id: int) -> Optional[dict]:
    return _put(f"/constraints/special-days/{special_day_id}/confirm")


def delete_special_day(special_day_id: int) -> bool:
    return _delete(f"/constraints/special-days/{special_day_id}")


# ══════════════════════════════════════════════════════════════
# SHIFT CONFIG
# ══════════════════════════════════════════════════════════════

def get_shift_config(year: int) -> Optional[dict]:
    return _get(f"/constraints/shift-config/{year}")


def upsert_shift_config(year: int, nv_count: int) -> Optional[dict]:
    return _put(f"/constraints/shift-config/{year}", json={"nv_count": nv_count})


# ══════════════════════════════════════════════════════════════
# SCHEDULE
# ══════════════════════════════════════════════════════════════

def get_schedule(month: int, year: int, status: str = None) -> list:
    params = {"month": month, "year": year}
    if status:
        params["status"] = status
    return _get("/schedule", params=params) or []


def get_week_schedule(start_date: str) -> list:
    return _get("/schedule/week", params={"start_date": start_date}) or []


def get_shifts_for_date(date_str: str) -> list:
    return _get(f"/schedule/date/{date_str}") or []


def generate_schedule(month: int, year: int,
                      overwrite_draft: bool = False) -> Optional[dict]:
    return _post("/schedule/generate", json={
        "month": month, "year": year, "overwrite_draft": overwrite_draft
    })


def generate_week_schedule(week_start: str, overwrite_draft: bool = False,
                           overwrite_confirmed: bool = False) -> Optional[dict]:
    return _post("/schedule/generate-week", json={
        "week_start": week_start,
        "overwrite_draft": overwrite_draft,
        "overwrite_confirmed": overwrite_confirmed,
    })


def confirm_week_shifts(week_start: str) -> Optional[dict]:
    return _post("/schedule/confirm-week", params={"week_start": week_start})


def update_shift(shift_id: int, leader_id: int = None, sp_id: int = None,
                 nv_ids: list = None, sp_warning: str = None,
                 clear_sp: bool = False) -> Optional[dict]:
    body: dict = {}
    if leader_id is not None:
        body["leader_id"] = leader_id
    if clear_sp:
        body["clear_sp"] = True
    elif sp_id is not None:
        body["sp_id"] = sp_id
    if nv_ids is not None:
        body["nv_ids"] = nv_ids
    if sp_warning is not None:
        body["sp_warning"] = sp_warning
    return _put(f"/schedule/{shift_id}", json=body)


def confirm_shift(shift_id: int) -> Optional[dict]:
    return _put(f"/schedule/{shift_id}/confirm")


def confirm_all_shifts(month: int, year: int) -> Optional[dict]:
    return _post("/schedule/confirm-all", params={"month": month, "year": year})


def delete_shift(shift_id: int) -> bool:
    return _delete(f"/schedule/{shift_id}")


def get_rotation_state(year: int, role: str = None) -> list:
    params = {"year": year}
    if role:
        params["role"] = role
    return _get("/schedule/rotation-state", params=params) or []


def reset_rotation(year: int) -> Optional[dict]:
    return _post("/schedule/reset-rotation", params={"year": year})


# ══════════════════════════════════════════════════════════════
# STATS
# ══════════════════════════════════════════════════════════════

def get_shift_count(year: int) -> list:
    return _get("/stats/shift-count", params={"year": year}) or []


def get_monthly_summary(month: int, year: int) -> Optional[dict]:
    return _get("/stats/monthly-summary", params={"month": month, "year": year})


# ══════════════════════════════════════════════════════════════
# EXPORT
# ══════════════════════════════════════════════════════════════

def get_week_export_url(week_start: str) -> str:
    """Trả về URL download Excel cho tuần bắt đầu từ week_start (YYYY-MM-DD)."""
    return f"{BASE_URL}/export/schedule/week?week_start={week_start}"


def delete_week_schedule(week_start: str) -> bool:
    try:
        r = httpx.delete(
            f"{BASE_URL}/schedule/week",
            params={"week_start": week_start},
            timeout=_TIMEOUT, follow_redirects=True,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        print(f"[API DELETE] /schedule/week -> ERROR: {e}")
        return False
