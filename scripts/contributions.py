"""Fetch GitHub's calendar, without third-party services or Python dependencies."""
import datetime as dt
from html.parser import HTMLParser
import json
import os
import re
import urllib.request

LEVELS = ['NONE', 'FIRST_QUARTILE', 'SECOND_QUARTILE', 'THIRD_QUARTILE', 'FOURTH_QUARTILE']

class CalendarParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.days = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'td' and 'ContributionCalendar-day' in a.get('class', '').split() and a.get('data-date'):
            self.days.append({'date': a['data-date'], 'level': int(a['data-level'])})


def validate(days):
    days = sorted(days, key=lambda d: d['date'])
    if not 350 <= len(days) <= 371:
        raise ValueError(f'Expected a full year of contributions, received {len(days)} days')
    start = dt.date.fromisoformat(days[0]['date'])
    sunday = start - dt.timedelta(days=(start.weekday() + 1) % 7)
    for i, d in enumerate(days):
        date = dt.date.fromisoformat(d['date'])
        if date != start + dt.timedelta(days=i) or not 0 <= d['level'] <= 4:
            raise ValueError('Calendar contains gaps, duplicates, or invalid levels')
        d.update(x=(date-sunday).days // 7, y=(date.weekday()+1) % 7)
    return days


def fetch(username):
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9-]{0,38}', username):
        raise ValueError('Invalid GitHub username')
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    headers = {'User-Agent': 'contribution-piggy', 'Accept': 'application/vnd.github+json'}
    if token:
        query = '''query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{weeks{contributionDays{date contributionCount contributionLevel}}}}}}'''
        req = urllib.request.Request('https://api.github.com/graphql',
            data=json.dumps({'query': query, 'variables': {'login': username}}).encode(),
            headers={**headers, 'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=40) as response:
            result = json.load(response)
        if result.get('errors'):
            raise ValueError('GitHub GraphQL returned errors; check token permissions')
        user = result['data']['user']
        if not user:
            raise ValueError('GitHub user not found')
        days = [dict(date=d['date'], level=LEVELS.index(d['contributionLevel']), count=d['contributionCount'])
                for w in user['contributionsCollection']['contributionCalendar']['weeks'] for d in w['contributionDays']]
        source = 'github-graphql'
    else:
        # The same first-party public calendar used on the profile; levels are
        # authoritative. Do not fabricate contribution counts from quartiles.
        req = urllib.request.Request(f'https://github.com/users/{username}/contributions', headers=headers)
        with urllib.request.urlopen(req, timeout=40) as response:
            parser = CalendarParser()
            parser.feed(response.read().decode())
        days, source = parser.days, 'github-public-calendar'
    return {'username': username, 'source': source,
            'fetched_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'days': validate(days)}
