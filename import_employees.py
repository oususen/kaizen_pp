import os
import sys
import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR / 'backend'))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kaizen_backend.settings')
django.setup()

from proposals.models import Department, Employee

DEPT_NAME = '未設定'
DEPT_LEVEL = 'section'

department, _ = Department.objects.get_or_create(name=DEPT_NAME, level=DEPT_LEVEL)

csv_path = BASE_DIR / '氏名.csv'
with open(csv_path, encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    header = next(reader, None)
    imported = 0
    for idx, row in enumerate(reader, start=1):
        if not row:
            continue
        name = row[0].strip()
        if not name:
            continue
        code = f"EMP{idx:04d}"
        Employee.objects.update_or_create(
            code=code,
            defaults={
                'name': name,
                'department': department,
                'email': '',
                'position': '',
                'division': '',
                'group': '',
                'team': '',
                'role': Employee.Role.STAFF,
                'is_active': True,
            },
        )
        imported += 1
print(f"Imported/updated {imported} employees. Total now: {Employee.objects.count()}")
