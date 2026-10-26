import datetime as dt
import sys
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from contributions import validate, CalendarParser
from piggy import plan, render


def calendar(active):
    start=dt.date(2025,10,26)
    return validate([{'date':(start+dt.timedelta(days=i)).isoformat(),'level':active(i)} for i in range(366)])

class PiggyTest(unittest.TestCase):
    def test_routes_and_svg(self):
        for fn in [lambda i:0, lambda i:4, lambda i:3 if i%29==0 else 0]:
            days=calendar(fn)
            frames,eaten,duration=plan(days)
            self.assertEqual(set(eaten),{(d['x'],d['y']) for d in days if d['level']})
            self.assertEqual(frames[0][1:],frames[-1][1:])
            self.assertTrue(all(a[0]<b[0] for a,b in zip(frames,frames[1:])))
            for a,b in zip(frames,frames[1:]):
                self.assertLessEqual(abs(a[1]-b[1])+abs(a[2]-b[2]),.5)
            for theme in ('light','dark'):
                xml=render({'days':days},theme,frames,eaten,duration)
                root=ET.fromstring(xml)
                self.assertNotIn('<script',xml)
                self.assertNotIn('<foreignObject',xml)
                self.assertNotIn('href=',xml)
                for node in root.iter():
                    if node.tag.rsplit('}',1)[-1] in ('animate','animateTransform'):
                        times=list(map(float,node.attrib['keyTimes'].split(';')))
                        self.assertEqual(times[0],0); self.assertEqual(times[-1],1)
                        self.assertEqual(len(times),len(node.attrib['values'].split(';')))
                        self.assertTrue(all(a<b for a,b in zip(times,times[1:])))
                        self.assertEqual(node.attrib['repeatCount'],'indefinite')

    def test_parser_and_validation(self):
        p=CalendarParser(); p.feed('<td class="ContributionCalendar-day" data-date="2026-10-26" data-level="2"></td>')
        self.assertEqual(p.days,[{'date':'2026-10-26','level':2}])
        with self.assertRaises(ValueError): validate(p.days)
        days=calendar(lambda i:0); days[5]['date']=days[4]['date']
        with self.assertRaises(ValueError): validate(days)

if __name__=='__main__': unittest.main()
