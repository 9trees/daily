import calendar
from datetime import date, datetime, timedelta
from typing import Optional

from django.shortcuts import render
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
    }
    return render(request, 'meal_planner/calander_view.html', context)