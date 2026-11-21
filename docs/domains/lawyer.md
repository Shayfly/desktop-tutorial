# Lawyer

Covers: a lawyer or law firm offering legal services to people or businesses: a solo practitioner, a small practice in one field (family, property, employment, immigration, criminal, injury), or a firm with several practice areas. Includes notaries and mediators working inside a law practice.
Does not cover: accountants and tax advisers (use `accountant.md`); legal-document products with no lawyer; courts and legal-aid bodies; a lawyer's personal blog with no practice (use `personal-site.md`).
Written 2026-11-21. References checked 2026-11-21. Template: [README.md](README.md).

## 1. Objects

A law practice sells **a licensed person's judgment on a specific problem**. Nothing can be bought off the page. The visitor arrives worried, often in the worst week of their year, and the site has to answer three things: do you handle my kind of problem, who would I be talking to, and what happens (and what does it cost) if I call. Everything the visitor tells the firm is confidential, and the firm may be unable to act at all if it already acts for the other side.

### Firm (the business)

| Field | Required | Example (illustrative) |
|---|---|---|
| Name | required | "Levi & Partners", or the lawyer's own name |
| Kind of practice | required | family law, property, employment, criminal defence, commercial, general practice |
| Who it acts for | required | private people, businesses, both; one side only (employees, tenants, claimants) if so |
| Where it is licensed to practise | required | country, state, bar |
| Address | required | office address; "meetings by appointment" |
| Phone | required | |
| Office hours | required | when the phone is answered |
| How to start | required | call, enquiry form, book a first conversation |
| What the first conversation is | required | length, in person or by phone, free or its price, what to bring |
| Regulatory details | required where the regulator requires them | regulator, firm number, licence numbers |
| Email | optional | |
| Languages | optional | |
| Urgent line | optional | arrests, injunctions; only if really staffed |
| Legal aid or public funding | optional | accepted or not; say which |
| Access | optional | step-free, home or hospital visits, video meetings |

### Office (only when there is more than one)

Address, phone, hours, and which lawyers and practice areas are there.

### Lawyer

| Field | Required | Example |
|---|---|---|
| Name as licensed | required | |
| Professional title | required | advocate, solicitor, barrister, attorney, notary, mediator, trainee, paralegal |
| Role in the firm | optional | partner, associate, founder |
| Licence number, year admitted, where | required where customary or required | |
| Practice areas | required | from the firm's list |
| Languages | optional | |
| Direct contact | optional | |
| Photo | optional | with consent |
| Professional bio | optional | training, fields; publications; no outcome claims |

Lawyers are professionals acting in public, so their names appear. Clients' names never do, unless the client agreed in writing.

### Practice area

| Field | Required | Example |
|---|---|---|
| Name in the visitor's words | required | "Divorce and separation", "Buying a home", "Dismissed from work" |
| Legal name | optional | family law, conveyancing, employment law |
| For whom | optional | people, businesses, employers, employees |
| What the firm does in it | required | a short list of situations and services |
| Who handles it | optional | |
| How it usually goes | optional | stages, as general information |
| Fees | optional, see rules 5 to 7 | |

### Fee arrangement

| Field | Required | Example |
|---|---|---|
| Type | required when fees are shown | hourly, fixed fee, staged fee, retainer, percentage of the result where allowed, legal aid |
| Amount or range | optional | |
| What is included and what is extra | required when an amount is shown | court fees, experts, registration fees, tax |
| Tax | required when an amount is shown | including or excluding VAT, stated |
| For which service | required | "uncontested divorce", "first consultation" |

### Enquiry (only when the product stores enquiries)

| Field | Required | Example |
|---|---|---|
| Name | required | |
| Phone or email | required | and whether it is safe to call or leave a message |
| Area of the problem | required | from the firm's list, plus "not sure" |
| The other party's name | optional | for a conflict check; only if the firm asks for it |
| Short description | optional, with a warning | see rule 9 |
| Any deadline or hearing date | optional | time limits matter |
| Status | required | new, conflict check, answered, meeting booked, engaged, declined, closed |

### Other objects

| Object | Fields | Notes |
|---|---|---|
| Article, guide, insight | title, text, author, date, jurisdiction, date reviewed | General information, never advice; old law is dangerous |
| FAQ | question, answer, date | From the firm's own answers |
| Case story or result | text, client's consent, date, what was particular about it | Restricted in many jurisdictions; off by default |
| Recognition | directory or award, year, source | Only real, with year |
| Review | text, initials, date, source | Client confidentiality applies |
| Document checklist | per practice area: what to bring | Useful, low risk |
| Complaints procedure | how to complain to the firm, then to the regulator | Required in some jurisdictions |
| Client file, documents, correspondence | | Privileged. Outside this product; see section 8 |

## 2. Rules

1. Every title is exactly what the person is licensed as. A trainee or paralegal is not called a lawyer. "Specialist" and "expert" are used only where the local rules allow and the person holds the status.
2. The site says where the firm is licensed to practise. It does not suggest it can act elsewhere.
3. No outcome is promised: no "we will win", "guaranteed", "100% success", no success rate without the basis the local rules require.
4. A past result or case story is shown only with the client's written consent, without identifying the other side, and with the line that past results do not predict future ones, and only where local rules allow it.
5. Fees are optional to show, unless the regulator requires them. Absence is explicit: "we explain fees in the first conversation".
6. A shown fee says its type, what is included, what is extra (court fees, experts), and whether tax is included.
7. "Free consultation" is written only with its real limits: who qualifies, how long, by phone or in person.
8. "No win, no fee" or a percentage fee is written only where it is lawful for that kind of case and with what the client may still have to pay.
9. Every form says, before the visitor types: sending this does not make you our client; do not send confidential details or documents yet; we may be unable to act.
10. A form does not require the story of the case. The required fields are contact details and the area of the problem.
11. The firm must be able to check for a conflict of interest before it reads sensitive details. If the firm asks for the other party's name, the form says why.
12. Everything published as information is general, dated, names its jurisdiction, and says it is not legal advice.
13. An article about law that has changed is updated or removed. Every article shows its date.
14. No client is identifiable anywhere public without written consent: no names, no logos of clients, no photos, no "we acted for".
15. A review is real, carries its source, and does not reveal a matter the client did not choose to reveal.
16. Recognitions and rankings carry the year and the body.
17. Replies, reminders and emails to a visitor do not state the subject of the matter in a subject line or preview ("Your appointment on Tuesday at 10:00", no more). Some visitors share a phone or an inbox with the other party.
18. If an urgent line is shown, it is answered when the site says it is.
19. The main action is reachable from every page on a phone; the phone number is tappable; the address opens a map.
20. Stock photographs of people are not presented as the firm's lawyers or clients.

## 3. Mandatory facts

The product is not built until each has an answer. None may be guessed.

| # | Fact | The one question to ask | Why (the human reason) |
|---|---|---|---|
| 1 | Name | "What is the firm called, exactly as registered?" | People are referred by name, and the regulator knows the firm by it. |
| 2 | What you handle | "Which kinds of problems do you take? Say them as clients say them to you." | A person must know in seconds whether you deal with their problem. |
| 3 | For whom | "Do you act for private people, businesses or both? Only one side, for example only employees?" | A tenant should not call a landlords' firm. |
| 4 | Where you are licensed | "In which country or state are you licensed to practise?" | Advice from a lawyer not licensed there can be worthless to the client. |
| 5 | Who the lawyers are | "Who works on cases? For each: full name as licensed, title, fields." | People hire a person, and a wrong title is a false claim. |
| 6 | Where | "Where is the office? Do you meet clients elsewhere or by video?" | People need to know if they can reach you. |
| 7 | Phone and hours | "What number do people call, and when is it answered?" | A person with a hearing tomorrow needs a human today. |
| 8 | The first step | "What happens when someone contacts you: who answers, how soon, is the first conversation free or paid, how long?" | Fear of the unknown bill stops people from calling at all. |
| 9 | Fees, or the decision not to show them | "How do you charge for your common matters: hourly, fixed, percentage? Do you want numbers on the site?" | Cost is the question behind every other question. Some regulators require it. |
| 10 | Regulatory details | "Which body regulates you, and which numbers or statements must appear on your site?" | Missing statements are a breach for you and a warning sign for careful clients. |
| 11 | Who is the business legally | "What is the registered entity and number, and who handles privacy requests?" | Enquiries hold confidential details; someone must be responsible for them. |

Needed only when the product stores enquiries or bookings:

| # | Fact | The one question to ask | Why |
|---|---|---|---|
| 12 | Where enquiries go | "Where should each enquiry arrive, and who reads it?" | An unanswered enquiry may be a missed time limit for that person. |
| 13 | Conflict check | "Do you want the other party's name on the form, so you can check for a conflict before reading details?" | You may be forbidden to act, and should not learn the other side's secrets. |
| 14 | Meeting length and times | "How long is a first meeting, and when do you hold them?" | For booking. |

## 4. Declared defaults

Each default is shown to the customer as "we filled this in - change it if it is wrong".

| Default | Value | Why it is safe | How it is marked |
|---|---|---|---|
| Form warning | "Sending this form does not make you our client. Please do not include confidential details or documents." | Protects the visitor and the firm | "Default notice - edit the wording, do not remove it without thought" |
| Information notice | "General information, not legal advice", on every article and FAQ | Standard caution | Default text |
| Main action | "Call us" | Works with zero setup | "default: phone" |
| Form fields | name, phone or email, area of the problem, "is it safe to call this number?" | The least needed to call back | Shown as a list the customer can cut |
| Description field | optional, short, with the warning above | Rule 10 | "Optional by default" |
| Missing fees | "We explain fees in the first conversation" | Says openly there is no number | Listed as "no fees given" |
| Case results, client names, reviews | hidden | Confidentiality and advertising rules | "Off until you confirm consent and that it is allowed" |
| Reply and reminder wording | date, time, firm name, phone | Rule 17 | Shown |
| Practice-area order | the order the customer said them | The customer's own priority | Editable |
| Page order | Skeleton A below | From the references | Named as default |
| Language, direction, currency | from the conversation and address | | Shown |
| Legal page structure | headings only | | "Draft - review before publishing" |

Never a default: titles, licence numbers, admission years, practice areas, fees, "free consultation", success rates, results, client names, awards and rankings, years of experience, number of cases, legal statements of any kind, time limits.

## 5. Failure modes

| What went wrong | What the visitor sees | What it costs | Prevention |
|---|---|---|---|
| No warning on the form | Writes the whole story, believing they now have a lawyer | A person who thinks they are represented and is not; a conflict problem for the firm | Rule 9 |
| Enquiry not seen for a week | Waits; a time limit passes | Harm to the person; a complaint | Mandatory fact 12; test the alert; state the answer time the firm gave |
| Reply reveals the subject | A spouse sees "Re: your divorce enquiry" on a shared phone | Real danger in family and abuse matters | Rule 17; ask "is it safe to call?" |
| "Free consultation" with unstated limits | Is told on the phone that it does not apply to them | Feels tricked | Rule 7 |
| Fee shown without extras | Court fees and tax double the bill | Dispute, complaint to the regulator | Rule 6 |
| Outcome language | Expects to win | Complaint; advertising breach | Rule 3 |
| Article states old law | Acts on a rule that changed | Harm to the reader; the firm looks careless | Rules 12, 13; review date on every article |
| Practice area listed that nobody handles any more | Calls, is turned away | Wasted calls | Practice areas tied to a named lawyer |
| Lawyer left, still listed | Asks for someone who is gone | Looks neglected | Profile can be hidden |
| Trainee shown as a lawyer | Believes a lawyer handles the case | A false claim | Rule 1 |
| Client named without consent | A client finds their matter on the site | Breach of confidentiality | Rule 14 |
| Jurisdiction not stated | A person abroad relies on the firm | Wasted time; unlicensed practice risk | Rule 2 |
| Urgent line not answered | Calls at night from a police station; voicemail | Harm; reputation | Rule 18 |
| Media hidden behind cookie consent with no fallback | An empty box and a line about cookies | Looks broken | Show a plain link when the media cannot load. Seen on a reference on 2026-11-21 |
| Home page is all news | A worried person cannot find "what do I do now" | Lost clients | Skeleton A puts the problem and the first step first |
| Jargon | Does not recognise their own problem | Lost clients | Practice areas named in the visitor's words |

## 6. Professional language

Hebrew and Arabic terms are the author's knowledge, not checked with a practising lawyer in either language. Legal terms differ between Arabic-speaking jurisdictions. "Not verified" means do not use a guess.

| English | Meaning | Hebrew | Arabic |
|---|---|---|---|
| Lawyer, attorney, advocate | | עורך/ת דין | محامٍ / محامية |
| Law firm, law office | | משרד עורכי דין | مكتب محاماة |
| Partner / associate | owner / employed lawyer | שותף/ה / עורך דין שכיר | شريك / not verified |
| Trainee, intern | not yet licensed | מתמחה | محامٍ متدرب |
| Notary | certifies documents | נוטריון | كاتب عدل |
| Mediator | helps parties agree | מגשר/ת | وسيط |
| Client | | לקוח/ה | موكّل |
| First consultation | | פגישת ייעוץ ראשונית | استشارة أولية |
| Legal advice | | ייעוץ משפטי | استشارة قانونية |
| Representation | acting for a client | ייצוג | تمثيل قانوني |
| Fee, legal fee | | שכר טרחה | أتعاب المحاماة |
| Fee agreement, engagement letter | | הסכם שכר טרחה | اتفاقية أتعاب |
| Retainer | fixed periodic fee | ריטיינר | not verified |
| Court fee | paid to the court | אגרת בית משפט | رسوم المحكمة |
| Power of attorney | | ייפוי כוח | توكيل / وكالة |
| Lawyer-client privilege | | חיסיון עורך דין-לקוח | not verified |
| Confidentiality | | סודיות | السرية |
| Conflict of interest | | ניגוד עניינים | تضارب مصالح |
| Claim, lawsuit | | תביעה | دعوى |
| Claimant / defendant | | תובע / נתבע | مدّعٍ / مدّعى عليه |
| Court | | בית משפט | محكمة |
| Hearing | | דיון | جلسة |
| Appeal | | ערעור | استئناف |
| Limitation period | time limit to sue | התיישנות | تقادم |
| Contract, agreement | | חוזה / הסכם | عقد / اتفاقية |
| Will / inheritance | | צוואה / ירושה | وصية / ميراث |
| Divorce | | גירושין | طلاق |
| Custody | | משמורת | حضانة |
| Mediation / arbitration | | גישור / בוררות | وساطة / تحكيم |
| Family law | | דיני משפחה | قانون الأحوال الشخصية |
| Employment law | | דיני עבודה | قانون العمل |
| Property law, real estate | | מקרקעין / נדל"ן | قانون العقارات |
| Personal injury, torts | | נזיקין | not verified |
| Criminal law | | פלילי | القانون الجنائي |
| Legal aid | publicly funded help | סיוע משפטי | مساعدة قانونية |

Notes on language:

- England and Wales: "solicitor", "barrister", "conveyancing", "claimant". United States: "attorney", "closing", "plaintiff". Israel: one profession, "advocate". Pick by jurisdiction; do not mix.
- Visitors say "divorce", "fired", "sued", "buying a flat". Use their word as the heading.
- Words to avoid unless the rules allow and the fact is true: "specialist", "expert", "best", "leading", "top-rated", "aggressive", "we win", "guaranteed", "no risk".
- The product does not write legal explanations. It lays out what the firm supplies, with a date.

## 7. Legal

A checklist of questions, not legal advice. The author is not a lawyer and read no statute or professional rule for this file. The customer here is a lawyer and is better placed than the product to check each item; the product's job is to ask.

### Applies almost everywhere

- **Lawyer advertising is regulated by the bar or regulator**, beyond ordinary consumer law: limits on outcome claims, comparisons, testimonials, naming clients, the word "specialist", and soliciting people in distress.
- **Confidentiality and privilege** cover what a prospective client tells the firm, including through a web form.
- **Conflict of interest**: a firm may be barred from acting, and information received from the other side can itself create a problem.
- **Anti-money-laundering duties** require identifying clients before certain work (property, companies, handling money). This happens at engagement, not on the website.
- **Client money** is held in separate accounts under strict rules. A website that takes payments on account of fees touches these rules.
- **Privacy notice**: enquiries can include data on crimes, health and family, which is specially protected in many places.
- **Unauthorised practice**: only licensed people may give legal advice in most countries; a site, a chatbot or a form must not appear to give it.

### Israel

- Bar Association Law (1961) and the Bar Association Rules (Professional Ethics) and (Advertising, 2001): advertising is permitted within limits (truthful, dignified, no misleading or comparative claims; limits on naming clients and on stating outcomes). Current text: not verified.
- Fees: percentage-of-result fees are believed forbidden in criminal matters and limited by law in some areas (for example road-accident and national-insurance claims). Not verified.
- A written fee agreement is strongly expected; whether it is mandatory: not verified.
- Privilege under the Evidence Ordinance and the Bar Association Law. Application to web enquiries: not verified.
- Privacy law (Amendment 13, in force August 2025), website accessibility statement, consent for advertising messages: as in other domain files; application to a small law office: not verified.
- Fees quoted to private clients include VAT under consumer law: not verified for legal services.

### European Union and United Kingdom

- England and Wales: firms regulated by the Solicitors Regulation Authority must publish, for certain services (believed to include residential conveyancing, probate, immigration, employment tribunal claims, some motoring offences, debt recovery), price information, who does the work and typical timescales, and must publish their complaints procedure and display the regulator's digital badge. Exact list and wording: not verified.
- Two references carry a footer statement that the firm is authorised and regulated by the Solicitors Regulation Authority, one with its number and VAT number (observed 2026-11-21). One reference states on its home page that it does not offer legal aid and that it offers both a fixed-fee and an hourly package (observed 2026-11-21).
- "No win, no fee" arrangements are regulated (conditional fee and damages-based agreements). Not verified.
- GDPR / UK GDPR: criminal-offence data and special-category data in enquiries. Not verified.
- EU member states: each bar has its own advertising code; the CCBE code applies to cross-border practice. Not verified.

### United States

- Each state has rules of professional conduct based on the ABA Model Rules: 7.1 (no false or misleading communication), 7.2 and 7.3 (advertising and solicitation), 1.18 (duties to prospective clients), 5.5 (unauthorised and multi-jurisdictional practice). Some states require the words "Attorney Advertising", a responsible lawyer's name and office address, or a disclaimer next to past results. Not verified per state.
- Contingency fees are allowed in many civil matters with a written agreement, and prohibited in criminal and most family matters. Not verified.
- ADA applied to websites; state privacy laws. Not verified.

### What the product does with this

- Asks the jurisdiction and the regulator before generating any page, and asks the customer which statements their regulator requires on a website.
- Keeps results, client names and reviews off until the customer confirms consent and permission.
- Never writes a statement of law, a time limit or a prediction.
- Never states that the site "complies with" a named rule.

## 8. Site vs app

### Content pages (no data, no accounts)

Home, practice areas, lawyers, how we work and the first conversation, fees, articles and FAQ, contact, complaints procedure, regulatory details, legal pages. With a phone link as the action, this is a complete product and holds no confidential information.

| Part | Empty | Error | Notes |
|---|---|---|---|
| Practice areas | cannot be empty | | In the visitor's words |
| Lawyers | cannot be empty (at least one) | missing photo: initials, no stock face | Real titles |
| Fees | "We explain fees in the first conversation" | | Unless the regulator requires numbers |
| Articles | section hidden | | Each with date and jurisdiction |
| Results, clients, reviews, recognitions | hidden | | Off by default |
| Regulatory details | cannot be empty where required | | Footer of every page |
| Embedded media | plain link | plain link when blocked by cookie choice | |
| Hours, map | office hours cannot be empty | text address remains | |

### Needs data

| Part | What it needs | Empty state | Loading | Error | Save | Permissions |
|---|---|---|---|---|---|---|
| Enquiry or callback form | contact details, area; alerts the firm | n/a | "sending", no double press | "Not sent - please call", with the number; what was typed is kept | "Received. You are not yet our client. We call back within [the time the firm gave]." | visitor writes; only the firm reads; stored encrypted, not only forwarded by email |
| Book a first conversation | meeting times, length | "No times this week - call us" | placeholder, never an empty calendar that reads as "full" | "Could not load times - call us" | "requested" until the firm confirms (it may need a conflict check first) | visitor sees own request |
| Document upload before a meeting | secure storage | | upload progress | failed upload says so | visitor told who will read it | only the firm; off by default; never before the conflict check |
| Newsletter | email, consent | | | | confirmation of subscription | firm; unsubscribe in every message |
| Firm edits content | edit screen | | | failed save says so | live after saving; articles get a new "reviewed" date only when someone reviewed them | lawyers or the office manager |
| Paid first consultation | payment | | | failed payment states | receipt; what happens if the firm cannot act | visitor: own; firm: all |

### Needs accounts

- The firm, once anything is stored or editable.
- Visitors need no account to enquire.
- A client portal (documents, messages, case status, bills) is a practice-management product holding privileged material. It is outside what this product builds; link to the firm's own system if one exists.

### Needs payments

- Paid first consultation; fixed-fee services bought online; payment of bills.
- Money paid before work is done may be client money under the regulator's account rules. Default: no payments.

### Using an existing system

Firms use practice-management and intake software. If the customer has one with an intake form, the product is a content site whose form is that system's form. Ask first.

## 9. References

**How these were checked.** Each URL was fetched on 2026-11-21 with a page-extraction tool that returns text and image references. No browser, no screenshot. Section order and wording are observed; visual quality and image-to-text ratio are not, and every ratio is an estimate from counts in the extracted text. Names of individual lawyers and clients that appear on the sites are left out.

**Curation.** Chosen by the author from known London law firms, not from a search-result list. No awwwards.com category was consulted. All in English, Latin script. Home pages only.

**Limit.** All seven are English firms with dozens to hundreds of lawyers. No solo practitioner or two-lawyer office was verified, although that is the typical customer. No reference outside England.

Verified: 7.

| # | Site | Checked | What was observed |
|---|---|---|---|
| 1 | https://www.stowefamilylaw.co.uk | 2026-11-21 | National family-law firm for private clients. Order: headline naming the speciality - three short points and two actions (book a free callback, find your local office) - a review score with its count - the callback explained as steps - "our services" as nine cards (divorce, children, unmarried couples, domestic abuse, finances, international, out of court, fertility and more), each one sentence - "Not sure which service you need?" - "What is family law?" in plain words - awards - costs, naming a fixed-fee package and an hourly package, and stating that legal aid is not offered - blog - FAQ - newsletter. A podcast and a video block show a "please enable marketing cookies" line instead of content. Extraction: about 90 image references, about 52,800 characters. |
| 2 | https://www.vardags.com | 2026-11-21 | Family-law firm for wealthy clients. Order: a long headline stating exactly who the firm acts for - "Are we right for you?" - "Free initial consultation", stated as for suitable clients with an asset and income threshold given in figures - awards - leadership team - why this firm - services as cards - FAQ (including what to bring to the first meeting) - media - offices - contact. Footer: registered office, regulator statement with firm number, VAT number. Extraction: about 54 image references, about 15,200 characters. |
| 3 | https://www.leighday.co.uk | 2026-11-21 | Claimant firm (injury, human rights, group claims). Top bar: skip to content, accessibility tools, phone number. Order: two news items - headline "lawyers against injustice" with a paragraph on whom the firm acts for - what clients say - "How can we help?" - "Why work with us" as three figures with a line each - "Have a question?" - news and cases - "How we have helped others": client stories told with the client's agreement. Extraction: 8 image references, about 8,300 characters. |
| 4 | https://www.bindmans.com | 2026-11-21 | Multidisciplinary firm known for civil-liberties work. Navigation lists practice areas directly. Order: news hero - a tribute to the founder - a three-part tagline - latest news, three items - "Our expertise": a paragraph and the practice areas as two long link lists - "Our people". Extraction: about 50 image references, about 21,300 characters. |
| 5 | https://www.kingsleynapley.co.uk | 2026-11-21 | Independent London firm for people and businesses. Order: a rotating hero of six messages (a budget commentary, crisis response, growth, services to law firms and more) - positioning paragraph - "Practice areas" as three link lists: by legal field, by kind of client (directors, founders), and by situation in the visitor's words ("arrested or charged with an offence") - people - careers - explore (articles, talks, events) - contact under the heading "Let us take it from here". Extraction: about 14 image references, about 13,400 characters. |
| 6 | https://www.mishcon.com | 2026-11-21 | Large London firm. Header states a switchboard open 24 hours. The home page is editorial: a lead article - two positioning statements - a topical legal change - latest - "Meet our people" with head-counts - two compliance topics - offices abroad - a private-client arm - a radio programme. Footer states the firm's regulatory status. Little about how to become a client. Extraction: about 64 image references, about 6,400 characters. |
| 7 | https://www.harbottle.com | 2026-11-21 | London firm with media and entertainment sectors. Short page: firm name - a two-sentence description - featured news and insights (three items) - services and sectors as menus - people - careers split three ways - contact - footer with the regulator statement and a note on notarial services. Extraction: 8 image references, about 2,800 characters. |

Tried and failed to load (not counted, not a reference): farrer.co.uk.

## 10. Skeletons

Structure only. No colours, logos, photographs or wording were taken from any reference.

### Skeleton A: the practice for private people (problem-first)

For a solo lawyer or small firm serving individuals. The site has one job: a worried person understands that you handle their problem and takes the first step. Default for this domain.
From references 1, 2, 3, 5: the callback steps, service cards and costs block of 1; the "are we right for you" and first-consultation terms of 2; the "how can we help" and accessibility bar of 3; practice areas by situation from 5. The reduction to a solo practice is the author's.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; one action (call / request a callback); phone visible | phone always visible | yes |
| 1 | Opening | one sentence: what kinds of problems, for whom, where licensed; the main action | one heading, one line, one action | yes |
| 2 | What we help with | practice areas as cards in the visitor's words, one sentence each; a "not sure?" link to contact | cards of equal weight | yes |
| 3 | What happens when you call | three steps: who answers, the first conversation (length, free or priced), what comes after | numbered | yes |
| 4 | Who you will speak to | the lawyer or lawyers: name, title, fields, languages | real titles; one person first for a solo practice | yes |
| 5 | Fees | how the firm charges; numbers if the firm gave them, with inclusions, extras and tax; legal aid yes or no | plain; a table for fixed fees | yes, even if only "explained in the first conversation" |
| 6 | Questions | FAQ from the firm's answers, including what to bring | question as heading | optional |
| 7 | Guides | dated articles with jurisdiction | list | optional, hidden when empty |
| 8 | Contact | short form with the not-yet-a-client warning; phone; office hours; address | form and phone side by side | yes |
| 9 | Footer | regulator statement and numbers, complaints procedure, privacy, terms, accessibility statement | small | yes |

Image-to-text ratio: **estimate**, from extraction counts only (reference 3 returned 8 image references against about 8,000 characters; reference 1 about 90, many of them icons and badges, against about 53,000). Text-led: one photograph of the lawyer or the office near the top, portraits in the team section, and little else. Not confirmed in a rendered view.

### Skeleton B: the firm with several practice areas (expertise-first)

For a firm serving businesses, or both businesses and people, where visitors arrive looking for a named lawyer or a field.
From references 4, 5, 6, 7: the short description of 7, the three-way practice lists of 5, the people and insights blocks of 4 and 6.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; navigation: expertise, people, insights, contact; phone | | yes |
| 1 | Opening | two sentences: what the firm is and for whom | text over at most one image | yes |
| 2 | Expertise | practice areas as link lists, grouped for businesses and for individuals; optionally by situation | lists, not cards, when there are many | yes |
| 3 | People | search or list; partners first; each links to a profile | | yes |
| 4 | Insights | three recent dated articles | card per article | optional, hidden when empty |
| 5 | Recognition | directories and awards with year | small | optional |
| 6 | Contact | phone, enquiry form with the warning, offices | | yes |
| 7 | Footer | regulator statement, complaints, legal pages | | yes |

Image-to-text ratio: **estimate**. Text-led on references 5 and 7 (14 and 8 image references); more image-led on 4 and 6 (50 and 64, mostly article thumbnails and portraits). Not confirmed in a rendered view.

Risk seen in references 4, 6 and 7: when news leads the home page, the route for a new client is hard to find. For a customer who lives from individuals' enquiries, use Skeleton A.

## 11. Not verified

1. All Hebrew and Arabic terms in section 6: author's knowledge, not checked with a practising lawyer. Arabic terms vary by jurisdiction.
2. Every legal and professional-conduct statement in section 7. None was checked against a statute, a bar rule or a regulator's page. The customer is a lawyer and should confirm each one for their own jurisdiction.
3. Image-to-text ratios and visual quality of all references: text extraction only.
4. No awwwards.com category was consulted; design quality is the author's prior judgement.
5. No solo or small-office reference was verified, and none outside England. Skeleton A is a reduction made by the author.
6. Sub-pages (lawyer profiles, practice-area pages, price pages, complaints pages, enquiry forms) were not fetched. Whether the references' forms carry a not-yet-a-client warning is not known.
7. The consent basis for the client stories on reference 3 is assumed from their publication, not confirmed.
8. The claim that firms use practice-management and intake software is the author's belief, not sourced.
9. No references in Hebrew, Arabic or any non-Latin script.
