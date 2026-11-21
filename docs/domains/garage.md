# Car garage and repair shop

Covers: a business that maintains and repairs cars, vans and motorcycles for the public. Includes general garages, single-make specialists, tyre and exhaust shops, body shops and mobile mechanics who come to the driver.
Does not cover: selling cars as the main business (use `catalogue-collection.md`); selling parts online as the main business (use `clothing-shop.md` for the shop mechanics, until a general shop file exists); roadside-rescue membership schemes.
Written 2026-11-21. References checked 2026-11-21. Template: [README.md](README.md).

## 1. Objects

A garage sells **a diagnosis and a repair on one specific vehicle**. Unlike a haircut, the price is often unknown until someone has looked at the car. So the central object is not a price list but a **job**: a vehicle, a described problem, an estimate the driver approved, and the work actually done.

### Garage (the business)

| Field | Required | Example (illustrative) |
|---|---|---|
| Name | required | "North Road Garage" |
| What kind of garage | required | general repair, Japanese-car specialist, tyres and brakes, body and paint, mobile mechanic |
| Address, or the area covered for a mobile mechanic | required | street, number, city; "we come to you within the city" |
| Phone | required | a number that is answered in working hours |
| Opening hours, per day of the week | required | Mon-Fri 07:30-17:30, closed Sat-Sun |
| How to get the car in | required | call, message, online request, drive in |
| Vehicles worked on | required | all makes; or named makes; cars only, or also vans, motorcycles, hybrids, electric |
| Licence or registration number of the garage | required where the law asks for it (see Legal) | |
| Email | optional | |
| Drop-off and collection arrangements | optional | key drop box, early drop-off, shuttle, courtesy car |
| Warranty on work | optional | "12 months on parts and labour" - only if the garage states it |
| Payment methods, finance | optional | |
| Towing or recovery | optional | own truck, or a named partner |
| Languages spoken | optional | |
| Year opened, short story | optional | |

### Location (only when there is more than one)

Address, phone, hours and booking route, repeated per location. A location can do different work from its sister: one reference has three repair shops and a separate collision shop with shorter hours.

### Service category

| Field | Required | Example |
|---|---|---|
| Name | required | Servicing, Brakes, Tyres, Diagnostics, Air conditioning, Bodywork, Inspection and test |
| Order on the page | required | most asked first |
| Short note | optional | "All servicing includes a written health check" |

### Service

| Field | Required | Example |
|---|---|---|
| Name | required | "Brake pads, front axle" |
| Category | required | Brakes |
| Plain description of the symptom it answers | optional but valuable | "grinding or squealing when you brake" |
| Price | optional, see rule 3 | 240 |
| Price type | required when a price is shown | fixed, "from", per hour, "after inspection" |
| What the price includes | required when a price is shown | parts, labour, tax, disposal fees |
| What the price depends on | optional | engine size, make, part quality |
| Typical time the car is needed | optional | "about two hours", "leave it for the day" |
| Vehicles it applies to | optional | not every service is offered for every make or for electric cars |
| Currently offered | required, default yes | |

### Vehicle (only when the product stores jobs)

| Field | Required | Example |
|---|---|---|
| Make, model, year | required | |
| Registration (plate) number | required for a job, optional for a first enquiry | |
| Fuel or drive type | optional | petrol, diesel, hybrid, electric |
| Mileage | optional | read at drop-off |
| VIN (chassis number) | optional | needed to order the right part |
| Owner | required | a vehicle belongs to one customer record; a customer can have several vehicles |

### Enquiry and job (only when the product takes requests)

| Field | Required | Example |
|---|---|---|
| Visitor name | required | |
| Visitor phone | required | to phone the estimate through |
| Vehicle | required | at least make, model, year |
| What is wrong, in the visitor's words | required | "rattle from the front left over bumps" |
| Preferred drop-off day | optional | a request, not a confirmed slot |
| Photos | optional | a warning light, a dent |
| Status | required | requested, booked in, car received, diagnosing, waiting for approval, approved, waiting for parts, in work, ready, collected, declined, cancelled |
| Estimate | required before work starts | lines of parts and labour, total, date, valid until |
| Approval | required before work starts | who approved, when, how (phone, message, signature) |
| Extra work found | optional | each item needs its own approval |
| Final invoice | required at the end | must be explainable against the estimate |
| Promised-by time | optional | a promise, shown as an estimate until the car is ready |

### Other objects

| Object | Fields | Notes |
|---|---|---|
| Make serviced | name, specialist or not | A specialist garage lives on this list |
| Certification or membership | name, issuer, number, valid until | Only real ones, as stated by the customer |
| Offer | text, price or discount, conditions, end date | Expires on its end date without anyone remembering |
| Review | text, first name or initials, date, source | Only real, with source and count |
| Closure | date or range | Overrides weekly hours |
| Courtesy car | availability, conditions | Involves insurance; a fact from the customer, never a default |
| Reminder | vehicle, what is due (service, annual test), date | Needs consent to send |
| Inspection report | vehicle, date, items with status, photos | Sent to the driver; several references describe this as a "digital vehicle inspection" |

## 2. Rules

1. Every service belongs to exactly one category.
2. The garage states which vehicles it works on. A visitor with a vehicle outside that list is told before sending a request, not after.
3. A price is optional, but its absence is explicit: "price after inspection" or "call for a quote", never a blank and never zero.
4. A shown price says what it includes (parts, labour, tax) and what it depends on. A "from" price says "from".
5. Every price shows its currency.
6. No work starts without an estimate the customer approved. The approval is recorded with a time and a channel.
7. Work that goes beyond the approved estimate needs a new approval before it is done. The product never moves a job to "in work" on extra items without it.
8. An online request for a day is a request. It becomes a booking only when the garage confirms it, unless the garage has given real capacity per day.
9. A drop-off can only be requested on a day the garage is open and not on a closure date.
10. A closure date overrides the weekly hours.
11. Opening hours are stated per day of the week, in local time, with closed days named.
12. A job's final invoice lists parts and labour separately.
13. A "ready" status is set only by the garage. The driver is told once, on the channel they chose.
14. A warranty on work is shown only in the garage's own words, with its length and its conditions.
15. A certification, an "authorised by" claim or a manufacturer logo is shown only if the customer confirmed it is current. Servicing a make is not the same as being authorised by its manufacturer.
16. A review is shown only if it is real, with its source. No star rating without a count and a source.
17. An offer has an end date, or says "until further notice". Past its end date it is not shown.
18. The phone number is a tappable link. The address opens a map. Both are reachable from every page without scrolling back to the top on a phone.
19. Photos of customers' cars show no readable number plate unless the owner agreed.
20. Stock photographs of workshops are not presented as the garage's own premises.
21. The product never gives a diagnosis. It may list symptoms the garage deals with; it does not tell a driver the car is safe to drive.

## 3. Mandatory facts

The product is not built until each of these has an answer from the customer. None may be guessed.

| # | Fact | The one question to ask | Why (the human reason) |
|---|---|---|---|
| 1 | Business name | "What is the garage called?" | Without a name people cannot find it or recommend it. |
| 2 | Kind of garage | "What do you mainly do: general repairs, a speciality, tyres, bodywork? Do you have a workshop or do you travel to the car?" | A driver with a dented door and a driver with a warning light need different places. |
| 3 | Vehicles | "Which vehicles do you work on, and which do you turn away?" | Without it people tow a car to a garage that cannot touch it. |
| 4 | Where | "Where do people bring the car? Full address. Or which area do you travel to?" | Without it the car cannot arrive. |
| 5 | Phone | "What number should drivers call?" | A broken-down driver calls; they do not fill in forms. |
| 6 | Opening hours | "Which days are you open, from when to when? When can cars be dropped and collected?" | Without hours people arrive at a locked gate with a car they cannot drive home. |
| 7 | How to get the car in | "How does a driver get a slot today: call, message, just turn up?" | The whole site leads to this one action. |
| 8 | Services | "What work do you do? Say it the way you say it to a driver." | Without the list a visitor does not know whether to call. |
| 9 | Prices, or the decision not to show them | "Are there jobs with a fixed price you want to show? What is your hourly rate, if you want it public? Or no prices at all?" | Price is the first fear in this domain. Hiding it is allowed; inventing it is not. |
| 10 | Who is the business legally | "What is the registered business name and number, and the garage licence number if your country has one?" | The legal pages must name who is responsible, and some countries require the licence number on display. |

Needed only when the product takes requests or stores jobs:

| # | Fact | The one question to ask | Why |
|---|---|---|---|
| 11 | Where requests go | "Where should I send each new request: which phone or email, and who reads it?" | A request nobody sees is a driver who arrives and is not expected. |
| 12 | How estimates are approved | "How do you get the driver's OK on a price today: phone, message, signature?" | The approval is the garage's protection in any later argument. |
| 13 | How many cars per day | "How many cars can you take in a day?" - only for instant booking | Without it the site promises slots the workshop does not have. |
| 14 | Warranty wording | "Do you give a warranty on your work? Say exactly what and for how long." | A warranty written by someone else is a promise the garage did not make. |

## 4. Declared defaults

Each default is shown to the customer as "we filled this in - change it if it is wrong". None of them is a fact about the business.

| Default | Value | Why it is safe | How it is marked |
|---|---|---|---|
| Category names and order | Servicing, Brakes, Tyres, Diagnostics, Air conditioning, Battery and electrics, Suspension and steering | Seen across the references' service menus | Editable list, labelled "suggested order" |
| Which category a service falls in | by the service's name | Wrong placement is visible and easy to fix | Customer confirms the grouped list |
| Missing price | "Price after inspection - call us" | Says openly that there is no number | Listed in the customer's review as "no price given" |
| Main action | "Call us", using the phone number | Works with zero setup; matches how drivers behave | Labelled "default: phone" |
| Second action | "Request a visit" form, sent to the garage, status "requested" | Does not promise a slot | Labelled "default: request, not a booking" |
| Request form fields | name, phone, make, model, year, what is wrong | The minimum a garage needs to call back | Shown as the default form |
| Page order | Skeleton A below | Extracted from the references | Named as the default skeleton |
| Symptom wording | plain words next to trade names ("clutch - the pedal feels soft or the car slips") | Drivers search by symptom | Shown to the customer for approval; the customer can delete any line |
| Language and direction | the language of the conversation | The customer chose it by speaking it | Shown, changeable |
| Currency | the currency of the garage's country | Follows from the address | Shown next to every price |
| Legal page structure | headings only | Structure is general; content is not | Marked "draft - not legal advice - review before publishing" |
| Empty optional sections | hidden | A missing reviews block is better than an empty one | Listed for the customer as "not shown yet" |

Never a default, whatever the customer left out: opening hours, prices, hourly rate, makes serviced, warranty terms, certifications, "authorised", "dealer-level", "same-day", courtesy car, towing, years of experience, number of technicians, reviews, ratings, and any statement about safety.

## 5. Failure modes

| What went wrong | What the visitor sees | What it costs | Prevention |
|---|---|---|---|
| Hours on the site are old | A locked gate, with a car that barely drives | A lost job and an angry driver | Ask for hours explicitly; show "hours last updated" |
| Holiday not marked | Tows the car to a closed garage | A towing bill the driver blames on the garage | Closure object (rule 10) |
| Makes list missing or wrong | Brings a car the garage does not touch | Wasted trip, bad review | Mandatory fact 3; shown above the request form |
| Request saved, garage never told | Arrives; nobody expects the car | The worst case in this domain | Mandatory fact 11; test the alert at setup; status "requested" until confirmed |
| Request read as a confirmed slot | Takes a day off work, is turned away | Distrust | Rule 8; the confirmation text says "we will call you to confirm" |
| "From" price read as the price | Bill is far above the expectation | Dispute at the counter | Rule 4; say what the price depends on |
| Work done beyond the estimate | A bill the driver never agreed to | Refusal to pay; a legal problem in some places | Rules 6 and 7 |
| Car not ready when promised | Arrives to collect; car is on the lift | A second wasted trip | Status set only by the garage (rule 13); "promised by" shown as an estimate |
| No status at all | Phones three times a day | Staff time; driver anxiety | Status visible to the driver, or one message when ready |
| Expired offer still shown | Asks for a discount that ended | Argument, or a loss | Rule 17 |
| "Authorised" claim not true | Believes the manufacturer stands behind the work | A misleading-advertising problem | Rule 15 |
| Warranty text invented or generic | Claims under a warranty the garage never gave | A dispute the garage cannot win | Mandatory fact 14 |
| Phone not tappable, or goes to a dead line | Cannot call from the roadside | Silent loss | Rule 18; customer reads the number back |
| Map pin on the wrong entrance | Circles an industrial estate | Late drop-off | Ask "how do people find the gate?" |
| Site says the car is "safe" or diagnoses by form | Keeps driving a dangerous car | Harm, and liability | Rule 21 |
| Number plates readable in gallery photos | Sees their own car online | A privacy complaint | Rule 19 |
| Reminder sent for a car already sold | An irrelevant message | Looks careless | A vehicle can be marked "no longer owned" |

## 6. Professional language

Hebrew and Arabic terms are the author's knowledge and were not checked with a working mechanic in either language. Workshop Arabic is full of regional loanwords; the terms given are standard or common Levantine usage. Where a cell says "not verified", do not use a guess.

| English | Meaning | Hebrew | Arabic |
|---|---|---|---|
| Garage, repair shop (US: auto repair shop) | the business | מוסך | كراج / ورشة تصليح سيارات |
| Mechanic, technician | the person doing the work | מכונאי | ميكانيكي |
| Service (scheduled maintenance) | the periodic check and fluid change | טיפול (טיפול תקופתי) | صيانة دورية |
| Repair | fixing a fault | תיקון | تصليح |
| Diagnosis, diagnostics | finding the cause, often with a scan tool | אבחון תקלות / דיאגנוסטיקה | فحص (not verified for the trade term) |
| Estimate, quote | the price given before work | הצעת מחיר | عرض سعر |
| Labour (US: labor) | the charge for time | עבודה (שעת עבודה) | أجرة اليد (not verified) |
| Parts | what is fitted | חלפים | قطع غيار |
| Original parts (OEM) | made by or for the car's manufacturer | חלפים מקוריים | قطع غيار أصلية |
| Aftermarket parts | made by another manufacturer | חלפים תחליפיים | not verified |
| Annual roadworthiness test (UK: MOT; Israel: "test") | the legally required inspection | טסט (מבחן רישוי שנתי) | not verified |
| Brakes, brake pads, discs (US: rotors) | | בלמים, רפידות, דיסקים | فرامل (pads and discs: not verified) |
| Tyres (US: tires) | | צמיגים | إطارات |
| Wheel alignment | setting the wheel angles | כיוון פרונט | not verified |
| Oil change | | החלפת שמן | تغيير زيت |
| Battery | | מצבר | بطارية |
| Clutch | | מצמד (colloquial: קלאץ') | not verified |
| Gearbox (US: transmission) | | תיבת הילוכים (colloquial: גיר) | not verified |
| Timing belt | | רצועת טיימינג | not verified |
| Exhaust | | מערכת פליטה (colloquial: אגזוז) | عادم (not verified for workshop use) |
| Suspension | | מתלים | not verified |
| Air conditioning | | מיזוג אוויר | تكييف |
| Bodywork, panel beating | repairing dents and panels | פחחות | سمكرة |
| Paint | | צבע | دهان |
| Warning light, check-engine light | | נורת אזהרה, נורת מנוע | not verified |
| Mileage, odometer reading | | קילומטראז' | not verified |
| Registration number, plate | | מספר רישוי | رقم اللوحة |
| Courtesy car (US: loaner) | a car lent during the repair | רכב חלופי | سيارة بديلة |
| Towing, recovery | | גרירה | not verified |
| Warranty | | אחריות | ضمان |
| Authorised garage | approved by the manufacturer or importer | מוסך מורשה | not verified |
| Pre-purchase inspection | checking a used car before buying | בדיקה לפני קנייה | not verified |
| Hybrid, electric vehicle | | רכב היברידי, רכב חשמלי | سيارة هجينة، سيارة كهربائية |

Notes on language:

- Drivers describe symptoms ("it pulls to the left"); mechanics name systems ("alignment"). The site needs both next to each other.
- UK and US English differ widely here: tyre/tire, bonnet/hood, boot/trunk, gearbox/transmission, MOT/state inspection, garage/shop. Pick one by country.
- Words to avoid unless the customer said them and can back them: "authorised", "certified", "dealer-level", "cheapest", "guaranteed", "same day", "free inspection", "best rated".
- Never write "safe to drive" or "roadworthy" as a promise of the site.

## 7. Legal

A checklist of questions, not legal advice. The author is not a lawyer and did not read the statutes for this file. Every item needs checking by someone qualified in the garage's country before it is relied on.

### Applies almost everywhere

- **Privacy notice.** Needed as soon as the site collects a name, a phone and a plate number. A plate number and a VIN are linked to a person and should be treated as personal data.
- **Estimate and approval.** Many places have a rule, or at least strong consumer-law pressure, that work is agreed before it is done. Keep the approval record.
- **Terms.** Storage charges for uncollected cars, a lien on a car until the bill is paid, liability for items left in the car, replaced parts returned on request: each is a legal question in its own country. The product writes none of these without the customer's own text.
- **Environmental duties** (used oil, tyres, batteries) exist almost everywhere. They do not belong on the site unless the customer wants to state them.
- **Marketing messages** need prior agreement. A reminder that the annual test is due is closer to marketing than an appointment reminder is; treat it as needing consent.
- **Reviews** must be real.

### Israel

- Garages are licensed by the Ministry of Transport. The Vehicle Services and Professions Licensing Law of 2016 is believed to be the governing law. Whether the licence number must appear on a website: not verified.
- A duty to give a written estimate, to get the customer's approval for work beyond it, and to offer the replaced parts back: believed to exist in the garage regulations. Not verified.
- The annual test is done at licensed test stations, not at ordinary garages. A garage that "prepares the car for the test" should say that, not "we do the test". Not verified in detail.
- Displayed consumer prices must include VAT. Not verified for hourly rates.
- Website accessibility: a duty on businesses serving the public, with an accessibility statement and Israeli Standard 5568 as reference, and exemptions by turnover. Thresholds: not verified.
- Privacy: the Protection of Privacy Law, Amendment 13 in force since August 2025. What it asks of a small garage: not verified.
- Marketing by SMS or email needs prior consent (section 30A of the Communications Law). Details: not verified.

### European Union and United Kingdom

- GDPR and UK GDPR apply to customer and vehicle records. Consent is needed for non-essential cookies.
- EU: competition rules for the motor sector are understood to let a driver service a car at an independent garage without losing the manufacturer's warranty, if the work follows the manufacturer's schedule. A garage that wants to say this must have it checked. Not verified.
- UK: mechanics are not a licensed profession. MOT testing is done only by stations authorised by the Driver and Vehicle Standards Agency. A garage claims MOT testing only if it is an authorised station. Not verified in detail.
- UK: the Consumer Rights Act 2015 requires a service to be done with reasonable care and skill. Codes of practice for garages exist and are voluntary. Not verified.
- Work on air-conditioning refrigerant requires certified personnel in the EU and UK. Not verified.
- Displayed consumer prices include VAT: believed true in both. Not verified.

### United States

- Rules are by state. Several states require repair shops to register, to give a written estimate and to get authorisation before exceeding it; California's Bureau of Automotive Repair is the best-known example. Not verified per state.
- ASE certification of technicians is voluntary. It may be shown only if current.
- Federal warranty law is understood to stop a manufacturer from voiding a warranty only because an independent shop did the maintenance. Not verified.
- Emissions and safety inspections are state programmes with licensed stations. Not verified.
- The Americans with Disabilities Act is applied by courts to business websites in many cases. Not verified.

### What the product does with this

- It may generate the **structure** of a privacy page, a terms page and an accessibility statement, each marked as a draft.
- It never states that the garage "complies with" a named law, is "authorised" or is "licensed" unless the customer supplied the licence number.
- It asks which country the garage is in before generating any legal page.

## 8. Site vs app

### Content pages (no data, no accounts)

Home, services, vehicles we work on, prices or price policy, about and team, certifications, offers, how to find us, contact, legal pages. With a phone link as the only action this is a complete and honest product. Most of the references work this way plus one request form.

| Part | Empty | Error | Notes |
|---|---|---|---|
| Services | cannot be empty (mandatory fact) | n/a | Grouped by category |
| Price list | "Prices after inspection - call us" | n/a | Shows the date last updated |
| Makes serviced | cannot be empty | | "All makes" is a valid answer if the customer said it |
| Offers | section hidden | an expired offer is hidden, not shown struck through | |
| Reviews | section hidden | | Never placeholders |
| Certifications | section hidden | | |
| Hours | cannot be empty | | "Open now" needs the garage's time zone |
| Map | text address always shown | if the map fails, the text and a link remain | |

### Needs data

| Part | What it needs | Empty state | Loading | Error | Save | Permissions |
|---|---|---|---|---|---|---|
| Visit request form | stores the request; alerts the garage | n/a | button shows "sending", cannot be pressed twice | "Not sent - please call" with the number | "Received. We will call you to confirm a time." | visitor writes; only the garage reads |
| Photo upload with a request | file storage, size limit | n/a | progress per photo | a failed photo does not lose the typed text | request is saved even if a photo fails | as above |
| Instant booking of a drop-off day | capacity per day, closures, existing bookings | "No space this week - call us" | days show a placeholder, never look "all full" while loading | "Could not load days - call us" | confirmed only after the server saved it | visitor: own booking; garage: all |
| Estimate sent to the driver | job, estimate lines, a personal link | "No estimate yet - we are still looking at the car" | | link expired: show the phone | approval is saved with time and channel and cannot be edited afterwards | only through the personal link; garage sees all |
| Job status for the driver | job with status | "We have not received the car yet" | | never show a stale status without its time | status changes only from the garage side | personal link |
| Garage's job board | all open jobs | "No cars in today" | | a stale board says it is stale | every change saved with who made it | staff only, behind a login |
| Customer and vehicle history | customers, vehicles, past jobs | "First visit" | | | | staff only; a driver sees only their own vehicles |
| Reminders (service or test due) | vehicle dates, a sending channel, consent | | | a failed send is shown to the garage | | sent only with consent; stops when the vehicle is marked sold |
| Owner edits content (hours, services, offers) | an edit screen | | | a failed save says so and keeps what was typed | visible on the public site right after saving | owner only |

### Needs accounts

- The owner needs one as soon as anything is editable or any request is stored.
- Staff need them only if several people update jobs.
- Drivers should not need one. A phone number and a personal link are enough.

### Needs payments

- Paying the invoice online, a deposit for special-order parts, gift cards (one reference sells them).
- Each brings refunds, receipts and failed-payment states.
- Default: no payments. The bill is paid at the counter.

### Using an existing workshop system

Many garages already run workshop-management software that produces estimates, inspections and invoices. In that case the product is a content site with a request form or a link to the existing scheduler, and it owns no job data. Ask before building a second job board.

## 9. References

**How these were checked.** Each URL was fetched on 2026-11-21 with a page-extraction tool that returns the page's text and image references. No browser was used and no screenshot was taken. Section order and wording are observed; visual quality, layout and the image-to-text ratio are **not** observed, and every ratio below is an estimate from counts in the extracted text. Image counts include logos, icons and badges. Character counts are after removing link targets.

**Curation.** Chosen by the author from independent repair shops he believed to be real businesses with their own sites, then kept only if the page loaded and read as the business's own. No awwwards.com category was consulted; garages are rarely featured there, and none of these is claimed as a design-award site.

**Limit.** All eight are in the United States or Canada. No UK, EU or Israeli garage site was verified: the UK and German candidates tried did not load. Design quality is ordinary trade-site quality, not high design. The skeletons are a picture of what working garages actually publish, not a design ceiling.

Verified: 8.

| # | Site | Checked | What was observed |
|---|---|---|---|
| 1 | https://www.lucasautocare.com | 2026-11-21 | European-car specialist, Texas. Top strip: phone, directions, weekday hours, "Schedule Appointment". Order: headline naming the speciality - list of eight makes serviced - a second line of further makes - a rating claim - six short reasons (status updates by text and photo, loaner car, equipment, dealer alternative, a stated 3-year warranty, family-owned) - three longer paragraphs. No prices. Extraction: 29 images, about 4,200 characters. |
| 2 | https://www.hollenshades.com | 2026-11-21 | General repair shop, Maryland. Navigation lists about twenty services by system (alignment, battery, brakes ... tyres). "Call or Text" number in the header. Order: one-line history - headline - five key services - a local award line - services as cards, each a heading, one sentence and "Learn more" - values - blog - reputation - closing block with phone or "Get appointment". No prices. Extraction: 25 images, about 4,500 characters. |
| 3 | https://www.convoyautorepair.com | 2026-11-21 | General repair shop, California. Order: headline - customer reviews - welcome text - why choose us - diagnostics and digital inspections - range of services and makes - visit us with address and hours in the text - a stated nationwide warranty - financing - makes serviced - affiliation badges - online appointment request form - "Having trouble finding us?" map block. Text-heavy. Extraction: 31 images, about 6,200 characters. |
| 4 | https://www.fitzgeraldsautomotive.com | 2026-11-21 | Two-location family shop, North Carolina. Opening hours listed per day, Monday to Sunday, with closed days named, in the header. Order: headline with town names - both addresses and phones side by side - "Can we fix it the same day?" - "How much will it cost?" (answers with the estimate-before-work policy, not a number) - services - articles - one testimonial with a first name and initial - fixed "Tap to call now" bar. Extraction: 14 images, about 7,500 characters. |
| 5 | https://www.goodworksautorepair.com | 2026-11-21 | General repair shop, Arizona. Very large navigation: about twenty company links and more than thirty services. Separate "Call" and "Text" numbers, address and hours repeated at top and bottom. Order: one priced offer (a basic oil change with a stated price) - a stated warranty - a first-visit discount by text code - services - vehicles serviced - location with a landmark description. The only reference with a price on the home page. Extraction: 63 images, about 6,900 characters. |
| 6 | https://www.artsautomotive.com | 2026-11-21 | Japanese-car and hybrid specialist, California. Almost a letter: a welcome that says what the page will cover - "Cars we service" - a long reasoned section on why specialisation matters (experience, faster diagnosis, special tools) - how the shop operates - a job advert with an hourly pay range - community news. States that repair is billed by the hour. Extraction: 23 images, about 9,500 characters. |
| 7 | https://www.cleggauto.com | 2026-11-21 | Four locations, Utah: three repair shops and one collision shop. A review count in the header. Order: a block per location (name, type of work, address, phone, weekday hours) - two separate actions, "Schedule Auto Repair" and "Schedule Collision Repair" - welcome - location cards each with a review-source rating and "Schedule Service" - about text - locations again in the footer. Extraction: 109 images, about 9,100 characters, much of it repeated location blocks. |
| 8 | https://www.wrenchpatrol.com | 2026-11-21 | Mobile mechanic, British Columbia. Order: headline saying the mechanic comes to the driver's home - short description - call or appointment line - why choose us - three offers shown as percentages - credentials - hours as a table, Monday to Saturday, plus separate phone-support hours - service areas - contact. No address-led block, because there is no workshop to visit. Extraction: 13 images, about 2,300 characters. |

Loaded and not used: none. Every candidate that loaded was kept.

Tried and did not load (not counted, not references): pawlikautomotive.com, christianbrothersauto.com, luscious-garage.com, germanautospecialists.com, dubtechnik.co.uk, autotechniqueservices.com, oceanside-motorsports.com, hondabolonearme.com. Some of these may not exist at those addresses; they were guesses.

## 10. Skeletons

Structure only. No colours, logos, photographs or wording were taken from any reference.

### Skeleton A: the local garage (call-first)

For a garage with a workshop that wants calls and visit requests. Default for this domain.
From references 1, 2, 4, 5 and 7; the practical strip is from 1 and 5, the per-day hours from 4, the service cards from 2, the request form from 3.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Practical strip and header | phone (tappable), directions link, today's hours, one action button | this strip is the most useful thing on a phone; it stays reachable | yes |
| 1 | Opening | one sentence: what kind of garage, for which vehicles, where; the main action and a quieter "request a visit" | one heading, one line, two actions | yes |
| 2 | Vehicles we work on | makes or types as a short list | names only, no manufacturer logos unless the customer has the right to use them | yes |
| 3 | Services | categories; each service a name, a symptom line, and a price or "after inspection" | card or row per service; full detail on its own page | yes |
| 4 | How it works | drop-off, estimate before any work, approval, collection; courtesy car or shuttle if the garage offers one | three or four short steps | yes; the content is the customer's |
| 5 | Why trust us | warranty in the garage's words, certifications, years - only stated facts | short list | optional, hidden when empty |
| 6 | What drivers say | real reviews with source and count | at most three | optional, hidden when empty |
| 7 | Request a visit | the short form; says plainly it is a request | form after the reasons, never before the phone | optional |
| 8 | Find us | address as text, map link, hours per day with closed days named, entrance note; repeated per location | complete without the map | yes |
| 9 | Footer | name, phone, address; licence number where required; privacy, terms, accessibility statement | small | yes |

Image-to-text ratio: **estimate**, from extraction counts only (references 1 to 4 returned 14 to 31 images against roughly 4,000 to 7,500 characters, and many of those images are badges and icons). Text-led: roughly one real photograph for every three or four text blocks. One honest photograph of the actual workshop or team does more than a gallery. Not confirmed in a rendered view.

### Skeleton B: the specialist

For a garage whose reason to exist is one group of vehicles (one make, hybrids, classics, campers). The argument for specialisation carries the page.
From references 1 and 6.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Practical strip and header | as Skeleton A | | yes |
| 1 | Opening | the speciality in the headline, the place, the action | the speciality is the largest text on the page | yes |
| 2 | Exactly which vehicles | makes, models, years, and what is not taken | a precise list beats a broad claim | yes |
| 3 | Why a specialist | experience with the same cars, the right tools, faster diagnosis - in the customer's own words and only what is true | a few short reasoned paragraphs | yes for this skeleton |
| 4 | Services for these vehicles | typical jobs for the speciality | list | yes |
| 5 | How we work and how we charge | estimate, approval, hourly billing if that is the practice | plain statements | yes |
| 6 | Trust | warranty, reviews with source | | optional |
| 7 | Find us | as Skeleton A | | yes |
| 8 | Footer | as Skeleton A | | yes |

Image-to-text ratio: **estimate**. Text-heavy: reference 6 returned about 9,500 characters against 23 images. The visitor here is deciding whether to trust expertise, and reads. Not confirmed in a rendered view.

For a mobile mechanic (reference 8), use Skeleton A with section 8 replaced by "Where we come to": the service area as named places, the hours, and what the driver must provide (a safe place to work, access to the car).

## 11. Not verified

1. All Hebrew and Arabic terms in section 6: author's knowledge, not checked with a working mechanic. Cells marked "not verified" must not be filled by guessing.
2. Every legal statement in section 7. None was checked against a statute or an official source. This includes the name and content of the Israeli 2016 law, the EU and US warranty statements and the UK MOT statements.
3. Image-to-text ratios and visual quality of all references: text extraction only, no rendered view.
4. No awwwards.com category was consulted. The references are ordinary trade sites, not high-design sites.
5. All eight references are North American. No UK, EU or Israeli garage and no body shop as a main business was verified.
6. Sub-pages (service pages, scheduling forms, price pages) were not fetched. Whether the "schedule" buttons lead to an own form or to a third-party scheduler was not followed.
7. The claim that many garages use workshop-management software is the author's belief, supported only by the "digital vehicle inspection" wording on references 1 and 3.
8. Whether the eight "tried and did not load" addresses are real sites of real businesses is unknown.
9. Warranty terms, review counts and prices mentioned in the reference notes are what the pages stated on the day; they were not checked against any other source.
10. No references in Hebrew, Arabic or any non-Latin script. These come in a later phase.
