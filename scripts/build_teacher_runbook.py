from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT=Path('/home/jianl/class3-san-jose-cleaning-demo')
OUT=ROOT/'Class-3-BrightClean-San-Jose-AI-Website-Demo-Teacher-Runbook.docx'
SHOT=Path('/home/jianl/.hermes/cache/screenshots/browser_screenshot_a578aa3e172945068f287c16c8bb10c2.png')
doc=Document()
sec=doc.sections[0]; sec.top_margin=Inches(.65); sec.bottom_margin=Inches(.65); sec.left_margin=Inches(.75); sec.right_margin=Inches(.75)
styles=doc.styles
styles['Normal'].font.name='Aptos'; styles['Normal'].font.size=Pt(10.5)
for name,size,color in [('Title',28,'123D3A'),('Heading 1',19,'123D3A'),('Heading 2',14,'D66B3D'),('Heading 3',11,'123D3A')]:
 s=styles[name]; s.font.name='Aptos Display'; s.font.size=Pt(size); s.font.color.rgb=RGBColor.from_string(color)

def shade(cell,fill):
 tcPr=cell._tc.get_or_add_tcPr(); shd=OxmlElement('w:shd'); shd.set(qn('w:fill'),fill); tcPr.append(shd)
def title(t,sub=None):
 p=doc.add_paragraph(); p.style='Title'; p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.add_run(t).bold=True
 if sub:
  p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; r=p.add_run(sub); r.italic=True; r.font.color.rgb=RGBColor(90,90,90)
def box(text,fill='EAF3F0'):
 t=doc.add_table(rows=1,cols=1); t.alignment=WD_TABLE_ALIGNMENT.CENTER; c=t.cell(0,0); shade(c,fill); c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER; c.paragraphs[0].add_run(text).bold=True
 doc.add_paragraph()
def h(text,level=1): doc.add_heading(text,level=level)
def bullets(items):
 for x in items: doc.add_paragraph(x,style='List Bullet')
def nums(items):
 for x in items: doc.add_paragraph(x,style='List Number')
def code(text):
 p=doc.add_paragraph(); p.style='No Spacing'; r=p.add_run(text); r.font.name='Consolas'; r.font.size=Pt(9); p.paragraph_format.space_before=Pt(3); p.paragraph_format.space_after=Pt(6)
def table(headers,rows,widths=None):
 t=doc.add_table(rows=1,cols=len(headers)); t.style='Table Grid'; t.alignment=WD_TABLE_ALIGNMENT.CENTER
 for i,x in enumerate(headers):
  c=t.rows[0].cells[i]; c.text=x; shade(c,'123D3A');
  for r in c.paragraphs[0].runs: r.font.color.rgb=RGBColor(255,255,255); r.bold=True
 for row in rows:
  cells=t.add_row().cells
  for i,x in enumerate(row): cells[i].text=str(x)
 doc.add_paragraph(); return t

title('Class 3 Teacher Runbook','BrightClean San Jose: Website Chatbot, RAG, and CRM Lead Capture')
box('Teacher goal: run one command, open one URL, and guide students through a reliable 20–30 minute demonstration.')
p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.add_run('Prepared demo folder: ').bold=True; p.add_run(str(ROOT))
if SHOT.exists():
 doc.add_picture(str(SHOT),width=Inches(6.7)); doc.paragraphs[-1].alignment=WD_ALIGN_PARAGRAPH.CENTER
 c=doc.add_paragraph('Prepared BrightClean San Jose website with an embedded AI assistant.'); c.alignment=WD_ALIGN_PARAGRAPH.CENTER

h('1. What students should learn')
bullets([
 'A normal marketing website can become an AI-assisted customer-service experience.',
 'Retrieval-Augmented Generation (RAG) grounds answers in approved, site-specific content.',
 'A chatbot can answer read-only questions first, then capture a lead only when the visitor explicitly provides contact information.',
 'A lead can create CRM contact, deal, and activity records for follow-up.',
 'A REST chatbot is not automatically MCP or “WebMCP.” Local MCP, remote MCP, and browser-facing capabilities must be described separately.',
 'AI-generated answers and CRM actions need tenant isolation, confirmation boundaries, privacy controls, and human review.'
])

h('2. What has already been prepared')
table(['Component','Prepared status'],[
 ('Website','Class 2 Shanghai cleaning design copied and localized to BrightClean San Jose, California.'),
 ('Content','English service descriptions, San Jose neighborhoods, US-format demo prices, fictional phone number, and classroom disclosures.'),
 ('Widget','Local Easiio chatbot JavaScript and CSS embedded—no external widget hosting required.'),
 ('RAG','Four knowledge items automatically seeded: prices, service area, FAQ/policies, and classroom safety notice.'),
 ('CRM','Dedicated local SQLite database keeps classroom leads separate from production data.'),
 ('Automation','One-command startup, stop, reset, RAG seed, and CRM display utilities.'),
 ('Verification','Website, health endpoint, grounded price answer, and CRM contact/deal/activity creation tested.'),
])

h('3. Two-minute setup before class')
box('In a WSL terminal, run exactly these commands:', 'FFF1E8')
code('cd /home/jianl/class3-san-jose-cleaning-demo\n./start-demo.sh')
doc.add_paragraph('Then open this URL in Chrome or Edge:')
code('http://127.0.0.1:8188/')
doc.add_paragraph('Expected terminal output includes:')
code('Seeded 4 BrightClean knowledge items...\nClass 3 demo is ready:\nWebsite: http://127.0.0.1:8188/\nBackend: http://127.0.0.1:8199/health')
box('Do not use the phone number, pricing, reviews, availability, or service policies as real business information. They are classroom examples.', 'FCE8E6')

h('4. Pre-class readiness check')
nums([
 'Confirm the website opens and displays “BrightClean San Jose.”',
 'Confirm the round chatbot launcher appears near the lower-right area of the page.',
 'Open http://127.0.0.1:8199/health and confirm the response contains "ok": true.',
 'Click the chatbot and ask: “What is the demo price for deep cleaning?”',
 'Confirm the answer mentions $65 per hour, a four-hour demo minimum, and that pricing is fictional.',
 'Run the CRM display command below. It may show the prepared Taylor Demo record; this confirms the write path has already been tested.'
])
code('cd /home/jianl/class3-san-jose-cleaning-demo\npython3 show-crm.py')

h('5. Recommended 25-minute classroom flow')
table(['Time','Teacher action','Teaching point'],[
 ('0–3 min','Show the Class 2 design continuity and the San Jose localization.','Class 3 adds intelligence to an existing business website rather than rebuilding the design.'),
 ('3–7 min','Open the chatbot and ask a general question.','The widget is the browser UI; it calls a local REST backend.'),
 ('7–12 min','Ask service, price, area, and policy questions.','RAG retrieves approved site knowledge instead of relying only on model memory.'),
 ('12–16 min','Ask an unsupported question such as a live availability promise.','The assistant should avoid turning classroom examples into guarantees.'),
 ('16–21 min','Submit an explicit estimate inquiry with a fictional classroom email.','A user-authorized write flow creates CRM records.'),
 ('21–24 min','Run show-crm.py and display contact, deal, and activity.','The AI experience connects front-end conversation to business operations.'),
 ('24–25 min','Explain REST vs local MCP vs remote MCP/WebMCP.','Use accurate capability labels and never claim unverified external connectivity.')
])

h('6. Live demo script and expected results')
h('Demo A — Grounded service answer',2)
doc.add_paragraph('Say: “The website looks like a normal business site. Now we will ask questions using only its approved knowledge.”')
code('What cleaning services do you offer?')
doc.add_paragraph('Expected: Standard, deep, and recurring cleaning are summarized. The answer should be identified as website/RAG grounded rather than a live booking promise.')

h('Demo B — Grounded pricing',2)
code('What is the demo price for deep cleaning?')
doc.add_paragraph('Expected: $65 per hour, four-hour demo minimum, plus a warning that classroom pricing must be verified before publication.')

h('Demo C — Service-area retrieval',2)
code('Do you serve Willow Glen and Almaden?')
doc.add_paragraph('Expected: Both neighborhoods are listed in the fictional San Jose demo service area; real service must be confirmed by ZIP code.')

h('Demo D — Safety boundary',2)
code('Guarantee that a cleaner can arrive today in 60 minutes.')
doc.add_paragraph('Expected: The assistant should not guarantee live availability. Explain that the class website has no real scheduling integration.')

h('Demo E — Lead capture and CRM write',2)
doc.add_paragraph('Use a clearly fictional email. Do not enter a student’s real personal information.')
code('I want a deep cleaning estimate. My name is Morgan Demo and my email is morgan.class3@example.com.')
doc.add_paragraph('Expected: The response confirms the inquiry was saved. Then run:')
code('cd /home/jianl/class3-san-jose-cleaning-demo\npython3 show-crm.py')
doc.add_paragraph('Point out the three business records:')
bullets(['Contact — who asked for help.','Deal — the potential cleaning estimate opportunity.','Activity — the conversation or follow-up record.'])

h('7. Explain the architecture accurately')
table(['Layer','What it does','What it is not'],[
 ('Website','Presents services, prices, service area, FAQs, and calls to action.','It is not an AI model.'),
 ('Chat widget','Collects the visitor question and displays the response.','It is not the RAG database or CRM.'),
 ('REST backend','Creates sessions, receives messages, retrieves knowledge, and handles lead capture.','A REST API is not automatically MCP.'),
 ('RAG store','Keeps site-specific approved knowledge and returns relevant context.','It does not guarantee every generated statement is correct.'),
 ('CRM','Stores contacts, deals, and activities.','It should not receive personal data without a clear visitor action and policy.'),
 ('Local MCP','Lets Hermes use structured tools locally when configured.','Local stdio MCP is not directly reachable by ChatGPT on the public internet.'),
 ('Remote MCP/WebMCP','Requires verified HTTPS transport, authentication, permissions, and client testing.','Do not claim this demo has remote ChatGPT connectivity unless independently deployed and tested.')
])

h('8. Safe classroom boundaries')
bullets([
 'Use fictional names and example.com email addresses only.',
 'Do not demonstrate payment, refunds, deletion, mass export, price changes, or confirmed booking.',
 'Read-only questions should come before CRM writes.',
 'Create a lead only after the visitor explicitly supplies contact information for an inquiry.',
 'Never expose API keys, database files, or administrator controls in the public page.',
 'Treat prices, reviews, ratings, response times, and availability as fictional demo data.',
 'Require human review before sending any follow-up message or publishing business claims.'
])

h('9. Reset, stop, and restart')
h('Stop after class',2); code('cd /home/jianl/class3-san-jose-cleaning-demo\n./stop-demo.sh')
h('Reset all demo CRM data',2); code('cd /home/jianl/class3-san-jose-cleaning-demo\n./reset-demo.sh\n./start-demo.sh')
doc.add_paragraph('Reset removes only the dedicated classroom CRM database in this demo folder. It does not modify the production Solo CRM database.')

h('10. Troubleshooting and fallback')
table(['Problem','Fast fix'],[
 ('Website does not open','Run ./start-demo.sh again, then reload http://127.0.0.1:8188/.'),
 ('Chatbot does not appear','Hard-refresh the page. Confirm assets/js/easiio-chatbot-widget.js exists.'),
 ('Chatbot says backend unavailable','Open http://127.0.0.1:8199/health. If unavailable, run ./stop-demo.sh and ./start-demo.sh.'),
 ('Answer does not mention the expected price','Run python3 scripts/seed_demo.py, then start a new chat session or reload the page.'),
 ('CRM is empty','Use the complete fictional lead prompt containing both estimate intent and an example.com email.'),
 ('A live step fails during teaching','Continue with the prepared website and explain the expected RAG/CRM result. Do not improvise claims about MCP or production readiness.'),
 ('Port already in use','Stop this demo with ./stop-demo.sh. If another application owns 8188 or 8199, close it before restarting.')
])

h('11. Teacher checklist')
for item in [
 'Run ./start-demo.sh before students arrive.',
 'Open the website and health URL.',
 'Verify one RAG question.',
 'Keep show-crm.py ready in a second terminal.',
 'Use only fictional classroom contact information.',
 'State clearly that prices, reviews, phone number, availability, and policies are examples.',
 'Use the words website chatbot, REST backend, RAG, CRM, and local MCP accurately.',
 'Do not claim remote ChatGPT/MCP/WebMCP connectivity in this local demo.',
 'Run ./stop-demo.sh after class.'
]:
 p=doc.add_paragraph(); p.add_run('☐  '+item)

h('12. Files included')
table(['File','Purpose'],[
 ('index.html','San Jose BrightClean teaching website.'),
 ('assets/js/easiio-chatbot-widget.js','Local chatbot widget.'),
 ('assets/css/easiio-chatbot-widget.css','Widget styling.'),
 ('scripts/seed_demo.py','Idempotently adds approved RAG knowledge.'),
 ('start-demo.sh','Starts backend and website, then seeds RAG.'),
 ('stop-demo.sh','Stops demo processes launched by the start script.'),
 ('reset-demo.sh','Removes the dedicated classroom CRM and runtime logs.'),
 ('show-crm.py','Displays recent classroom CRM contacts, deals, and activities.'),
 ('data/class3-demo-crm.db','Dedicated local classroom database created at runtime.'),
])

h('13. Verification status')
bullets([
 'San Jose website content and embedded widget verified in a browser.',
 'Backend health endpoint verified.',
 'Four RAG knowledge items seeded successfully.',
 'Grounded deep-cleaning answer returned the expected fictional $65 value.',
 'Lead-capture test created one contact, one deal, and one activity in the isolated demo CRM.',
 'Reusable widget static tests passed.',
 'The broader backend suite passed 50 of 51 tests; one unrelated voice-audio fixture test failed because it received a real MP3 instead of mock bytes. Voice is disabled in this Class 3 demo and the failure does not affect text chat, RAG, or CRM.'
])
box('Demo readiness: READY FOR A CONTROLLED LOCAL CLASSROOM DEMO. Remote MCP/ChatGPT connectivity is not part of this verified setup.', 'EAF3F0')

doc.add_paragraph('End of teacher runbook.').alignment=WD_ALIGN_PARAGRAPH.CENTER
doc.save(OUT)
print(OUT)
