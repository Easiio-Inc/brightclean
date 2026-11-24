from __future__ import annotations
import json
import os
from pathlib import Path
import secrets
import time

SITE_ID = "class3-brightclean-san-jose"
ITEMS = [
    {
        "title": "BrightClean San Jose demo services and prices",
        "url": "http://127.0.0.1:8188/#services",
        "content": "Classroom demonstration only. Standard Cleaning is shown at $45 per hour with a 3-hour demo minimum. Deep Cleaning is shown at $65 per hour with a 4-hour demo minimum. Recurring Cleaning is shown at $40 per hour. All prices are fictional examples and must be verified before real publication."
    },
    {
        "title": "BrightClean San Jose demo service area",
        "url": "http://127.0.0.1:8188/#service-area",
        "content": "The fictional classroom service area is San Jose, California, including Downtown, Willow Glen, Almaden, Cambrian, Berryessa, Evergreen, Rose Garden, and Japantown. A real business must confirm coverage by ZIP code before promising service."
    },
    {
        "title": "BrightClean supplies, scheduling, and concerns",
        "url": "http://127.0.0.1:8188/#faq",
        "content": "Basic supplies are included in the classroom scenario. Customers should discuss special surfaces, allergies, equipment, and product preferences before service. Availability is not live and same-day service is not guaranteed. Customers should review work and report concerns promptly; remedies depend on the final published policy."
    },
    {
        "title": "BrightClean service advantages",
        "url": "http://127.0.0.1:8188/#process",
        "content": "In this classroom demonstration, BrightClean's advantages are a clear three-step process, upfront demo pricing, cleaning priorities agreed before work begins, basic supplies included, notes for recurring visits, and a prompt review of concerns. These are fictional teaching examples rather than guarantees from a real cleaning company."
    },
    {
        "title": "BrightClean main website overview",
        "url": "http://127.0.0.1:8188/",
        "content": "The BrightClean San Jose homepage shows 2,400+ sample completed jobs, a 4.9-star sample rating, a 60-minute sample response time, and a 98% sample on-time rate. These numbers are fictional classroom demonstration data, not verified real-business history. The site presents Standard Cleaning at $45 per hour with a 3-hour demo minimum, Deep Cleaning at $65 per hour with a 4-hour demo minimum, and Recurring Cleaning at $40 per hour. Basic supplies are included in the classroom scenario. Demonstration service areas include Downtown San Jose, Willow Glen, Almaden, Cambrian, Berryessa, Evergreen, Rose Garden, and Japantown. The demo inquiry line is shown as open daily from 8:00 AM to 8:00 PM. Reviews, prices, availability, performance statistics, and policies must be verified before any real publication."
    },
    {
        "title": "Classroom safety notice",
        "url": "http://127.0.0.1:8188/",
        "content": "This is a teaching demo, not a real cleaning company. Phone number, prices, reviews, ratings, order counts, response times, availability, and policies are fictional. Do not treat them as real offers or guarantees."
    },
]
# Local reset/seed utility only; no unauthenticated administration endpoint.
path = Path(__file__).resolve().parents[1] / 'data/rag-content.json'
doc = json.loads(path.read_text()) if path.exists() else {'version': 1, 'sites': {}}
now = int(time.time())
doc['sites'][SITE_ID] = [{**item, 'content_id': 'rag_' + secrets.token_hex(8),
                         'created_at': now, 'updated_at': now} for item in ITEMS]
temporary = path.with_suffix('.json.tmp')
temporary.write_text(json.dumps(doc, indent=2) + '\n')
os.replace(temporary, path)
print(f'Seeded {len(ITEMS)} BrightClean knowledge items for {SITE_ID}.')
