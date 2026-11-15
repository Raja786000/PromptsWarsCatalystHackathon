"""
CareCircle Smart Care Intelligence Engine.
Transparent, rule-based healthcare calculations, adherence insights,
and weekly clinical care summary generation.
"""
from datetime import datetime, date, timedelta
from collections import defaultdict
from models import Medication, DoseLog, Appointment, CareTask, HealthJournalEntry, Patient, db

def get_adherence_metrics(patient_id, days=7):
    """
    Calculate comprehensive adherence metrics for a given patient over `days` days.
    Does not count doses scheduled in the future as missed.
    """
    start_date = date.today() - timedelta(days=days - 1)
    end_date = date.today()
    start_str = start_date.isoformat()
    end_str = end_date.isoformat() + "T23:59"

    # Fetch dose logs within window
    logs = DoseLog.query.filter(
        DoseLog.patient_id == patient_id,
        DoseLog.scheduled_for >= start_str,
        DoseLog.scheduled_for <= end_str
    ).all()

    status_counts = defaultdict(int)
    medication_counts = defaultdict(lambda: defaultdict(int))
    for log in logs:
        if log.status in ('Taken', 'Skipped', 'Missed'):
            status_counts[log.status] += 1
            medication_counts[log.medication_id][log.status] += 1

    taken = status_counts['Taken']
    skipped = status_counts['Skipped']
    missed = status_counts['Missed']

    total_past_due = taken + skipped + missed
    overall_rate = round((taken / total_past_due * 100), 1) if total_past_due > 0 else 100.0

    # Trend by day (dates in chronological order)
    daily_stats = []
    day_map = defaultdict(lambda: {'taken': 0, 'missed': 0, 'skipped': 0, 'total': 0})
    for log in logs:
        d_key = log.scheduled_for[:10]
        if log.status == 'Taken':
            day_map[d_key]['taken'] += 1
            day_map[d_key]['total'] += 1
        elif log.status == 'Missed':
            day_map[d_key]['missed'] += 1
            day_map[d_key]['total'] += 1
        elif log.status == 'Skipped':
            day_map[d_key]['skipped'] += 1
            day_map[d_key]['total'] += 1

    for i in range(days):
        current_day = start_date + timedelta(days=i)
        d_key = current_day.isoformat()
        info = day_map[d_key]
        rate = round((info['taken'] / info['total'] * 100), 1) if info['total'] > 0 else 100.0
        daily_stats.append({
            'date': d_key,
            'label': current_day.strftime('%a %b %d'),
            'day_name': current_day.strftime('%a'),
            'taken': info['taken'],
            'missed': info['missed'],
            'skipped': info['skipped'],
            'rate': rate
        })

    # Medication-wise adherence
    meds = Medication.query.filter_by(patient_id=patient_id, active=True).all()
    med_stats = []
    for med in meds:
        med_counts = medication_counts[med.id]
        m_taken = med_counts['Taken']
        m_missed = med_counts['Missed']
        m_skipped = med_counts['Skipped']
        m_total = m_taken + m_missed + m_skipped
        m_rate = round((m_taken / m_total * 100), 1) if m_total > 0 else 100.0
        med_stats.append({
            'id': med.id,
            'name': med.name,
            'dosage': med.dosage,
            'taken': m_taken,
            'missed': m_missed,
            'skipped': m_skipped,
            'total': m_total,
            'rate': m_rate
        })

    # Time-of-day adherence pattern
    tod_map = {
        'Morning (06:00-11:59)': {'taken': 0, 'total': 0},
        'Afternoon (12:00-16:59)': {'taken': 0, 'total': 0},
        'Evening (17:00-21:59)': {'taken': 0, 'total': 0},
        'Night (22:00-05:59)': {'taken': 0, 'total': 0}
    }
    for log in logs:
        if log.status in ('Taken', 'Missed', 'Skipped'):
            try:
                time_part = log.scheduled_for.split('T')[1]
                hour = int(time_part.split(':')[0])
            except Exception:
                hour = 8

            if 6 <= hour < 12:
                cat = 'Morning (06:00-11:59)'
            elif 12 <= hour < 17:
                cat = 'Afternoon (12:00-16:59)'
            elif 17 <= hour < 22:
                cat = 'Evening (17:00-21:59)'
            else:
                cat = 'Night (22:00-05:59)'

            tod_map[cat]['total'] += 1
            if log.status == 'Taken':
                tod_map[cat]['taken'] += 1

    tod_stats = []
    for cat, data in tod_map.items():
        rate = round((data['taken'] / data['total'] * 100), 1) if data['total'] > 0 else None
        tod_stats.append({
            'period': cat,
            'taken': data['taken'],
            'total': data['total'],
            'rate': rate
        })

    return {
        'days': days,
        'overall_rate': overall_rate,
        'taken': taken,
        'missed': missed,
        'skipped': skipped,
        'total_due': total_past_due,
        'daily_stats': daily_stats,
        'med_stats': med_stats,
        'tod_stats': tod_stats
    }

def generate_care_insights(patient_id):
    """
    Produce transparent, actionable, rule-based clinical observations
    based strictly on recorded database data.
    """
    recent_7d = get_adherence_metrics(patient_id, days=7)
    prior_14d = get_adherence_metrics(patient_id, days=14)

    insights = []

    # 1. Overall Trend
    rate_7d = recent_7d['overall_rate']
    rate_14d = prior_14d['overall_rate']
    diff = round(rate_7d - rate_14d, 1)

    if diff > 2.0:
        insights.append({
            'type': 'positive',
            'icon': 'trending-up',
            'title': 'Adherence Improvement',
            'text': f"Overall medication adherence reached {rate_7d}% this week, up {diff}% compared to the 14-day baseline."
        })
    elif diff < -3.0:
        insights.append({
            'type': 'warning',
            'icon': 'alert-triangle',
            'title': 'Recent Adherence Dip',
            'text': f"Recorded adherence dropped to {rate_7d}% in the last 7 days. Review recent evening routines."
        })
    else:
        insights.append({
            'type': 'info',
            'icon': 'check-circle',
            'title': 'Steady Routine Consistency',
            'text': f"Medication adherence remains stable at {rate_7d}% across the current week."
        })

    # 2. Time-of-day comparison
    morn = next((t for t in recent_7d['tod_stats'] if 'Morning' in t['period']), None)
    eve = next((t for t in recent_7d['tod_stats'] if 'Evening' in t['period']), None)
    if morn and eve and morn['rate'] is not None and eve['rate'] is not None:
        if morn['rate'] >= 90 and eve['rate'] < 85:
            insights.append({
                'type': 'info',
                'icon': 'clock',
                'title': 'Time of Day Variation',
                'text': f"Morning doses show excellent consistency ({morn['rate']}%), while evening doses are lower ({eve['rate']}%). Consider pairing evening medications with dinner or early relaxation."
            })

    # 3. Specific medication recognition
    for m in recent_7d['med_stats']:
        if m['total'] >= 4 and m['rate'] == 100.0:
            insights.append({
                'type': 'positive',
                'icon': 'award',
                'title': f"100% Adherence: {m['name']}",
                'text': f"All scheduled doses of {m['name']} ({m['dosage'] or ''}) were logged on time over the past 7 days."
            })
            break

    # 4. Missed dose audit check
    recent_missed = DoseLog.query.filter_by(patient_id=patient_id, status='Missed').order_by(DoseLog.scheduled_for.desc()).limit(3).all()
    if recent_missed:
        first_m = recent_missed[0]
        insights.append({
            'type': 'warning',
            'icon': 'calendar',
            'title': 'Attention Needed',
            'text': f"Dose for {first_m.medication.name if first_m.medication else 'Medication'} on {first_m.scheduled_for.replace('T', ' at ')} was marked missed. Note: '{first_m.note or 'No notes recorded.'}'."
        })

    return insights

def generate_weekly_care_summary(patient_id):
    """
    Generate an executive structured summary of the patient's week,
    suitable for clinical consultations, caregiver handoffs, and family updates.
    """
    patient = db.session.get(Patient, patient_id)
    if not patient:
        return None

    metrics = get_adherence_metrics(patient_id, days=7)
    now = datetime.now()

    # Next 14 days appointments
    upcoming_appts = Appointment.query.filter(
        Appointment.patient_id == patient_id,
        Appointment.status == 'Scheduled',
        Appointment.appt_at >= now.strftime('%Y-%m-%dT%H:%M'),
        Appointment.appt_at <= (now + timedelta(days=14)).strftime('%Y-%m-%dT23:59')
    ).order_by(Appointment.appt_at).all()

    # Active care tasks
    open_tasks = CareTask.query.filter(
        CareTask.patient_id == patient_id,
        CareTask.status.in_(['Pending', 'In Progress'])
    ).order_by(CareTask.due_date).all()

    # Recent journal vitals
    recent_vitals = HealthJournalEntry.query.filter_by(patient_id=patient_id).order_by(HealthJournalEntry.created_at.desc()).limit(5).all()

    avg_sys = None
    avg_dia = None
    bps = [v for v in recent_vitals if v.systolic_bp and v.diastolic_bp]
    if bps:
        avg_sys = round(sum(v.systolic_bp for v in bps) / len(bps))
        avg_dia = round(sum(v.diastolic_bp for v in bps) / len(bps))

    return {
        'patient_name': patient.name,
        'dob': patient.dob,
        'allergies': patient.allergies,
        'primary_physician': patient.primary_physician,
        'report_date': now.strftime('%B %d, %Y'),
        'period_start': (date.today() - timedelta(days=6)).strftime('%b %d'),
        'period_end': date.today().strftime('%b %d, %Y'),
        'adherence_rate': metrics['overall_rate'],
        'doses_taken': metrics['taken'],
        'doses_missed': metrics['missed'],
        'doses_skipped': metrics['skipped'],
        'total_due': metrics['total_due'],
        'medications': metrics['med_stats'],
        'avg_blood_pressure': f"{avg_sys}/{avg_dia} mmHg" if avg_sys else "Not recorded this week",
        'recent_vitals_count': len(recent_vitals),
        'upcoming_appointments': upcoming_appts,
        'open_tasks': open_tasks
    }
