import calendar
from datetime import date, datetime, timedelta
from typing import Optional

from django.shortcuts import render
from django.shortcuts import redirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone

# Create your views here.
def calendar_view(request):
    """Render a month/week/day calendar with planned meals.

    Query params:
    - view: month|week|day (default: month)
    - year, month: for month view
    - date: YYYY-MM-DD for week/day view
    """

    today = timezone.localdate()
    mode = (request.GET.get('view') or 'month').lower()
    if mode not in {'month', 'week', 'day'}:
        mode = 'month'

    def parse_date(value: Optional[str], default: date) -> date:
        if not value:
            return default
        try:
            return datetime.strptime(value, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return default

    # Local import to avoid circular imports if you later restructure the app.
    from .models import Meal

    weekday_names = list(calendar.day_abbr)
    return_to = request.get_full_path()

    if mode == 'day':
        current_date = parse_date(request.GET.get('date'), today)
        meals = (
            Meal.objects.filter(date=current_date, is_plan=True)
            .select_related('main_dish')
            .prefetch_related('side_dishes', 'tags')
            .order_by('type')
        )

        context = {
            'mode': 'day',
            'weekday_names': weekday_names,
            'today': today,
            'focus_date': current_date,
            'current_date': current_date,
            'prev_date': current_date - timedelta(days=1),
            'next_date': current_date + timedelta(days=1),
            'meals': meals,
            'return_to': return_to,
        }
        return render(request, 'meal_planner/calander_view.html', context)

    if mode == 'week':
        current_date = parse_date(request.GET.get('date'), today)
        week_start = current_date - timedelta(days=current_date.weekday())
        week_end = week_start + timedelta(days=6)

        meals = (
            Meal.objects.filter(date__range=(week_start, week_end), is_plan=True)
            .select_related('main_dish')
            .prefetch_related('side_dishes', 'tags')
            .order_by('date', 'type')
        )
        meals_by_date = {}
        for meal in meals:
            meals_by_date.setdefault(meal.date, []).append(meal)

        days = []
        for offset in range(7):
            day = week_start + timedelta(days=offset)
            days.append(
                {
                    'date': day,
                    'is_today': day == today,
                    'meals': meals_by_date.get(day, []),
                }
            )

        context = {
            'mode': 'week',
            'weekday_names': weekday_names,
            'today': today,
            'focus_date': current_date,
            'current_date': current_date,
            'week_start': week_start,
            'week_end': week_end,
            'prev_date': current_date - timedelta(days=7),
            'next_date': current_date + timedelta(days=7),
            'days': days,
            'return_to': return_to,
        }
        return render(request, 'meal_planner/calander_view.html', context)

    # month mode
    try:
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
        if month < 1 or month > 12:
            raise ValueError('month out of range')
    except (TypeError, ValueError):
        year = today.year
        month = today.month

    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])

    meals = (
        Meal.objects.filter(date__range=(first_day, last_day), is_plan=True)
        .select_related('main_dish')
        .prefetch_related('side_dishes', 'tags')
        .order_by('date', 'type')
    )

    meals_by_date = {}
    for meal in meals:
        meals_by_date.setdefault(meal.date, []).append(meal)

    cal = calendar.Calendar(firstweekday=0)  # Monday
    weeks = []
    for week in cal.monthdatescalendar(year, month):
        week_days = []
        for day in week:
            week_days.append(
                {
                    'date': day,
                    'in_month': day.month == month,
                    'is_today': day == today,
                    'meals': meals_by_date.get(day, []),
                }
            )
        weeks.append(week_days)

    prev_month_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    next_month_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)

    context = {
        'mode': 'month',
        'weekday_names': weekday_names,
        'today': today,
        'focus_date': first_day,
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'weeks': weeks,
        'prev_year': prev_month_year,
        'prev_month': prev_month,
        'next_year': next_month_year,
        'next_month': next_month,
        'return_to': return_to,
    }
    return render(request, 'meal_planner/calander_view.html', context)


def _next_url(request):
    return request.POST.get("next") or request.GET.get("next") or reverse("calendar")


def meal_add(request):
    from .forms import MealForm

    today = timezone.localdate()

    # Reuse calendar_view's parse behavior (simple + safe)
    date_str = request.GET.get("date")
    initial_date = today
    if date_str:
        try:
            initial_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            initial_date = today

    if request.method == "POST":
        form = MealForm(request.POST)
        if form.is_valid():
            meal = form.save(commit=False)
            meal.is_plan = True
            meal.save()
            form.save_m2m()
            return redirect(_next_url(request))
    else:
        form = MealForm(initial={"date": initial_date})

    return render(
        request,
        "meal_planner/meal_form.html",
        {
            "mode": "add",
            "form": form,
            "next": _next_url(request),
        },
    )


def meal_edit(request, pk: int):
    from .forms import MealForm
    from .models import Meal

    meal = get_object_or_404(Meal, pk=pk)

    if request.method == "POST":
        form = MealForm(request.POST, instance=meal)
        if form.is_valid():
            meal = form.save(commit=False)
            meal.is_plan = True
            meal.save()
            form.save_m2m()
            return redirect(_next_url(request))
    else:
        form = MealForm(instance=meal)

    return render(
        request,
        "meal_planner/meal_form.html",
        {
            "mode": "edit",
            "form": form,
            "meal": meal,
            "next": _next_url(request),
        },
    )


def meal_delete(request, pk: int):
    from .models import Meal

    meal = get_object_or_404(Meal, pk=pk)

    if request.method == "POST":
        meal.delete()
        return redirect(_next_url(request))

    return render(
        request,
        "meal_planner/meal_confirm_delete.html",
        {
            "meal": meal,
            "next": _next_url(request),
        },
    )


def tags_view(request):
    from .forms import TagForm
    from .models import Tag

    if request.method == "POST":
        form = TagForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("tags")
    else:
        form = TagForm()

    tags = Tag.objects.order_by("name")
    return render(
        request,
        "meal_planner/tags.html",
        {
            "tags": tags,
            "form": form,
        },
    )


def main_dishes_view(request):
    from .forms import MainDishForm
    from .models import MainDish

    if request.method == "POST":
        form = MainDishForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("main_dishes")
    else:
        form = MainDishForm()

    dishes = MainDish.objects.prefetch_related("tags").order_by("name")
    return render(
        request,
        "meal_planner/main_dishes.html",
        {
            "dishes": dishes,
            "form": form,
        },
    )


def side_dishes_view(request):
    from .forms import SideDishForm
    from .models import SideDish

    if request.method == "POST":
        form = SideDishForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("side_dishes")
    else:
        form = SideDishForm()

    dishes = SideDish.objects.prefetch_related("tags").order_by("name")
    return render(
        request,
        "meal_planner/side_dishes.html",
        {
            "dishes": dishes,
            "form": form,
        },
    )