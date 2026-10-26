import os
import urllib.request
import re
import json
import datetime
import zoneinfo
from dateutil import rrule

CALENDARS = [
    {
        'id': 'anna_mj',
        'name': 'Anna & MJ',
        'color': '#3f51b5',
        'textColor': '#ffffff',
        'url': 'https://calendar.google.com/calendar/ical/anna.mj926%40gmail.com/private-4dab14e393a4f15ce3cc88eabc507dea/basic.ics'
    },
    {
        'id': 'anna',
        'name': 'Anna',
        'color': '#ab47bc',
        'textColor': '#ffffff',
        'url': 'https://calendar.google.com/calendar/ical/f3bd86198ef8f79f6fb88c5047ffc5967947bbeefcdad72355720a8360128869%40group.calendar.google.com/private-e6457ebda58a4cd7b0970be0fabec622/basic.ics'
    },
    {
        'id': 'boys',
        'name': 'Boys',
        'color': '#f57c00',
        'textColor': '#ffffff',
        'url': 'https://calendar.google.com/calendar/ical/9962575fcf70c60fade29118376ede6b7c77be0f76573c913a4c6b762beeb35a%40group.calendar.google.com/private-a515d533ea776eed2d434820fdc731fa/basic.ics'
    },
    {
        'id': 'mj',
        'name': 'MJ',
        'color': '#00897b',
        'textColor': '#ffffff',
        'url': 'https://calendar.google.com/calendar/ical/75346f0671963a428ca63690f5ea0859ebcc294eb44d1475b7f8709ebf872b5b%40group.calendar.google.com/private-0fbf334d4911c6f151e11eaa0f16cada/basic.ics'
    }
]

def parse_dt(val, tz):
    val = val.strip()
    if 'T' in val:
        clean_val = val.split('T')[0] + 'T' + val.split('T')[1][:6]
        if val.endswith('Z'):
            dt = datetime.datetime.strptime(clean_val + 'Z', '%Y%m%dT%H%M%SZ').replace(tzinfo=datetime.timezone.utc)
            return dt.astimezone(tz), False
        else:
            dt = datetime.datetime.strptime(clean_val, '%Y%m%dT%H%M%S')
            return dt.replace(tzinfo=tz), False
    else:
        dt = datetime.datetime.strptime(val[:8], '%Y%m%d')
        return dt.replace(tzinfo=tz), True

def fetch_and_parse():
    local_tz = zoneinfo.ZoneInfo('America/Los_Angeles')
    now = datetime.datetime.now(local_tz)
    start_window = now - datetime.timedelta(days=1)
    end_window = now + datetime.timedelta(days=14)

    all_events = []

    for cal in CALENDARS:
        req = urllib.request.Request(cal['url'], headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                lines = resp.read().decode('utf-8', errors='ignore').splitlines()
        except Exception as e:
            print(f"Error fetching {cal['name']}: {e}")
            continue

        raw_events = []
        curr = None
        for line in lines:
            if line.startswith(' '):
                if curr and curr.get('_last_key'):
                    curr[curr['_last_key']] += line[1:]
                continue
            if line.startswith('BEGIN:VEVENT'):
                curr = {}
            elif line.startswith('END:VEVENT'):
                if curr: raw_events.append(curr)
                curr = None
            elif curr is not None and ':' in line:
                k, v = line.split(':', 1)
                base_k = k.split(';')[0]
                curr[base_k] = v
                curr['_last_key'] = base_k

        for ev in raw_events:
            summary = ev.get('SUMMARY', 'Untitled')
            dtstart_raw = ev.get('DTSTART')
            if not dtstart_raw: continue
            dtend_raw = ev.get('DTEND')

            start_dt, is_all_day = parse_dt(dtstart_raw, local_tz)
            end_dt = parse_dt(dtend_raw, local_tz)[0] if dtend_raw else (start_dt + datetime.timedelta(days=1) if is_all_day else start_dt + datetime.timedelta(hours=1))
            duration = end_dt - start_dt

            rrule_str = ev.get('RRULE')
            if rrule_str:
                try:
                    rule = rrule.rrulestr(rrule_str, dtstart=start_dt.astimezone(datetime.timezone.utc))
                    between = rule.between(start_window.astimezone(datetime.timezone.utc), end_window.astimezone(datetime.timezone.utc), inc=True)
                    for occ in between:
                        occ_local = occ.astimezone(local_tz)
                        all_events.append({
                            'title': summary,
                            'calendarId': cal['id'],
                            'calendarName': cal['name'],
                            'color': cal['color'],
                            'textColor': cal['textColor'],
                            'start': occ_local.isoformat(),
                            'end': (occ_local + duration).isoformat(),
                            'allDay': is_all_day,
                            'location': ev.get('LOCATION', '')
                        })
                except Exception:
                    pass
            else:
                if (start_dt <= end_window) and (end_dt >= start_window):
                    all_events.append({
                        'title': summary,
                        'calendarId': cal['id'],
                        'calendarName': cal['name'],
                        'color': cal['color'],
                        'textColor': cal['textColor'],
                        'start': start_dt.isoformat(),
                        'end': end_dt.isoformat(),
                        'allDay': is_all_day,
                        'location': ev.get('LOCATION', '')
                    })

    all_events.sort(key=lambda x: x['start'])
    with open('events.json', 'w') as f:
        json.dump(all_events, f, indent=2)
    print(f"Generated events.json with {len(all_events)} events.")

if __name__ == '__main__':
    fetch_and_parse()


