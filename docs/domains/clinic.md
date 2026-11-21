# Clinic

Covers: a medical practice people visit by appointment or walk-in: family doctor, private GP, specialist (skin, women's health, children, orthopaedics, fertility and so on), urgent care, and allied practices such as physiotherapy run as a clinic.
Does not cover: dentists (use `dentist.md`); cosmetic treatments without a medical practitioner (use `beauty-cosmetics.md`); hospitals; online-only pharmacies.
Written 2026-11-21. References checked 2026-11-21. Template: [README.md](README.md).

## 1. Objects

A clinic sells **a consultation with a licensed practitioner**. Two things set this domain apart from every other appointment business: what a visitor tells the clinic is health information, and a wrong or missing sentence on the site can delay someone who needs urgent help.

### Clinic (the business)

| Field | Required | Example (illustrative) |
|---|---|---|
| Name | required | "Riverside Family Clinic" |
| Kind of practice | required | family medicine, dermatology, children's clinic, urgent care, physiotherapy |
| Who it treats | required | adults, children, everyone; by referral only or direct |
| Address | required | street, number, floor, city |
| Phone | required | reception line |
| Opening hours, per day | required | Sun-Thu 08:00-19:00, Fri 08:00-13:00 |
| How to get an appointment | required | call, online booking, walk-in, referral needed |
| What to do in an emergency or when closed | required | "In an emergency call [the local emergency number]. We are not an emergency service." |
| How payment works | required | private fee, named insurers or health funds, public system |
| Operating licence or registration, with the body and number | required where the law requires it | |
| Email | optional | never for medical questions unless the clinic says so |
| Languages spoken | optional | |
| Access | optional | step-free entrance, lift, parking, accessible toilet |
| Remote consultations | optional | video or phone |

### Location (only when there is more than one)

Address, phone, hours, practitioners and services repeated per location. Not every service is offered at every location.

### Practitioner

| Field | Required | Example |
|---|---|---|
| Name as licensed | required | the name under which the person is registered |
| Title and profession | required | doctor, nurse, physiotherapist, psychologist |
| Speciality | required for specialists | only a speciality the person is registered in |
| Licence or registration number | required where it is customary or required to show it | |
| Services this person provides | optional | |
| Clinic days and hours | optional on the page, required for online booking | |
| Languages | optional | |
| Photo | optional | with consent |
| Short professional bio | optional | training and fields of interest; no outcome claims |
| Accepting new patients | optional | |

Practitioners are professionals acting in public, so their names appear. Patients' names never do.

### Service

| Field | Required | Example |
|---|---|---|
| Name | required | "First consultation", "Follow-up", "Skin check", "Blood test" |
| Category | required | Consultations, Tests, Procedures, Vaccinations, Certificates |
| Short description in plain words | optional | what happens, how long |
| Duration in minutes | optional on the page, required for online booking | 20 |
| Price | optional, see rule 6 | |
| Price type | required when a price is shown | fixed, "from", by insurer, "ask reception" |
| Who provides it | optional | |
| Needs a referral | optional | |
| Preparation | optional | fasting, bring previous results |
| In person, video, or both | optional | |
| Age limits | optional | adults only |
| Currently offered | required, default yes | |

### Payer (insurer, health fund, public scheme)

| Field | Required | Example |
|---|---|---|
| Name | required | an insurer or fund the clinic really works with |
| What is covered | optional | "consultations only", "with a referral form" |
| What the patient pays | optional | co-payment |

### Appointment (only when the product takes bookings)

| Field | Required | Example |
|---|---|---|
| Service | required | |
| Practitioner, or "first available" | required | |
| Location, or "video" | required | |
| Date and start time | required | |
| Patient name | required | |
| Patient phone | required | |
| Patient date of birth or ID number | optional; only if the clinic needs it to open a file | |
| First visit or returning | optional | |
| Reason for the visit | optional and sensitive; see rule 11 | |
| Status | required | requested, confirmed, cancelled by patient, cancelled by clinic, completed, no-show |

### Other objects

| Object | Fields | Notes |
|---|---|---|
| Closure | date or range | Overrides weekly hours |
| Patient information item | title, text, date reviewed, who reviewed it | General health information, never personal advice |
| Policy | cancellation, late arrival, deposit, chaperone, children's consent, repeat prescriptions, complaints | A complaints route is required in many places |
| Review | text, initials at most, date, source | Regulated in many countries; see Legal |
| Form | new-patient form, consent form | Health data; app only |
| Medical record | everything clinical | Outside this product; see section 8 |

## 2. Rules

1. Every page states what to do in an emergency and that the clinic is not an emergency service, unless it is one.
2. A practitioner's title and speciality are exactly what the person is registered as. The product never upgrades a title.
3. A practitioner can be booked only for services that practitioner provides, at a location where they work, inside their clinic hours.
4. Two confirmed appointments for the same practitioner do not overlap.
5. An appointment cannot be made in the past; closure dates override weekly hours.
6. A price is optional but its absence is explicit: "ask reception" or "depends on your insurer". Never blank, never zero.
7. A shown price has a currency and says what it covers (the consultation only, or tests too).
8. An insurer or health fund is named only if the customer said the clinic works with it.
9. No outcome is promised: no "cure", "guaranteed", "100%", "painless", "safe" as an absolute, no before-and-after claims without the conditions the local regulator sets.
10. Health information on the site is general, dated, and says it does not replace a consultation.
11. A public form does not ask for symptoms or history as a required field. If a "reason for visit" field exists it is optional, short, and protected like health data.
12. Messages, reminders and emails do not reveal the reason for a visit or the speciality where that itself is sensitive ("Your appointment tomorrow at 10:00" and no more).
13. No patient is identifiable anywhere public: no names, no photos, no case details, unless the patient gave written consent for that exact use.
14. A review is shown only if it is real, carries its source, and the local rules on medical testimonials allow it.
15. A cancellation fee or deposit is shown before the visitor confirms.
16. Opening hours are per day, in local time, with closed days named. Phone hours are stated separately if different.
17. The main action (book, call) is reachable from every page on a phone; the phone number is tappable; the address opens a map.
18. Results, prescriptions and anything from the medical record are never sent or shown through the public site.
19. Stock photographs are not presented as the clinic's staff or rooms.

## 3. Mandatory facts

The product is not built until each has an answer. None may be guessed.

| # | Fact | The one question to ask | Why (the human reason) |
|---|---|---|---|
| 1 | Name | "What is the clinic called?" | People are referred by name. |
| 2 | Kind of practice | "What kind of medicine do you practise, and for whom: adults, children, everyone?" | A visitor must know at once whether this is the right door. |
| 3 | Who treats | "Who sees patients here? For each: full name as licensed, profession, speciality." | People choose a doctor, not a building, and a wrong title is a false claim. |
| 4 | Where | "What is the full address, floor, and how do people find the entrance?" | A sick person should not search for the door. |
| 5 | Phone | "What number do patients call, and during which hours is it answered?" | Without it nobody can book or cancel. |
| 6 | Hours | "Which days and hours do you see patients?" | People take time off work to come. |
| 7 | How to get an appointment | "How does a new patient get an appointment today? Is a referral needed?" | The whole site leads to this step. |
| 8 | Emergencies | "What should the site tell someone who needs urgent help, or who calls when you are closed?" | A person in danger must not wait for a callback. |
| 9 | Payment | "Do patients pay privately, through insurers or health funds, or both? Which ones, by name?" | People do not come if they do not know what it will cost them. |
| 10 | Services | "What do you actually offer? List it as you would say it to a patient." | Without it people call for things you do not do. |
| 11 | Licence | "Which authority licenses the clinic and the practitioners, and what numbers should be shown?" | Patients and regulators look for it. |
| 12 | Who is the business legally | "What is the registered name and number, and who answers privacy requests?" | Health data must have a named, responsible holder. |

Needed only when the product takes bookings:

| # | Fact | The one question to ask | Why |
|---|---|---|---|
| 13 | Durations | "How long is a first visit and a follow-up for each service?" | Otherwise the waiting room fills and everyone runs late. |
| 14 | Who works when | "Who is in on which days and hours, at which location?" | Otherwise a patient is booked with a doctor who is not there. |
| 15 | Cancellation | "What happens when a patient cancels late or does not come?" | The patient must know before booking. |
| 16 | Where bookings go | "Where does each new booking arrive, and who sees it?" | A booking nobody saw is a patient at the desk with no slot. |
| 17 | Existing systems | "Do you already use a practice-management or booking system?" | Building a second diary next to it creates double bookings. |

## 4. Declared defaults

Each default is shown to the customer as "we filled this in - change it if it is wrong".

| Default | Value | Why it is safe | How it is marked |
|---|---|---|---|
| Emergency line | "This clinic is not an emergency service. In an emergency call your local emergency number." The number itself is filled from the country and shown to the customer to confirm | Safer than silence; the number is confirmed, not assumed | Shown in review as "default emergency notice - confirm the number" |
| Main action | "Call to book" | Works with zero setup | "default: phone" |
| Service categories | Consultations, Tests, Procedures | Descriptive | Editable |
| Missing price | "Ask reception" | Says openly there is no number | Listed as "no price given" |
| Reason-for-visit field | absent | Avoids collecting health data by default | "Off by default" |
| Reminder wording | date, time, clinic name, phone; nothing clinical | Rule 12 | Shown to the customer |
| Health-information pages | none | The product does not write medical content | "Not created - you can add your own, with a review date" |
| Reviews section | hidden | Rules differ by country | "Off until you confirm it is allowed where you practise" |
| Page order | Skeleton A below | From the references | Named as default |
| Language, direction, currency | from the conversation and the address | | Shown, changeable |
| Legal page structure | headings only | | "Draft - not legal advice" |

Never a default: titles, specialities, licence numbers, services, prices, insurers, hours, emergency arrangements of the clinic itself, waiting times, success rates, equipment, awards, "accepting new patients", any medical statement.

## 5. Failure modes

| What went wrong | What the visitor sees | What it costs | Prevention |
|---|---|---|---|
| No emergency notice | A person with chest pain fills in a contact form and waits | Harm to a person | Rule 1 on every page |
| Hours on the site are old | Arrives ill at a closed door | Harm, anger | Hours with a "last updated" date; closures |
| Insurer listed that the clinic no longer works with | Gets a bill they did not expect | Dispute, complaint | Rule 8; dated payer list |
| "From" price read as the full price | Tests are charged on top | Distrust | Rule 7 |
| Doctor left, still listed and bookable | Books a doctor who is gone | A wasted visit | Practitioner can be hidden; future slots closed |
| Wrong title or speciality | Believes they are seeing a specialist | A regulatory complaint against the practitioner | Rule 2; customer confirms each title by reading it back |
| Double booking | Two patients, one slot | Long waits | Rule 4 at save time |
| Booking saved, reception never told | Arrives; no record | The worst ordinary case | Mandatory fact 16; "requested" until confirmed |
| Reminder reveals the reason | A family member reads "your fertility appointment" on a locked screen | A breach of confidence | Rule 12 |
| Symptoms typed into a contact form and emailed | Health data sits in an inbox | A data-protection problem | Rule 11; the form says what not to write |
| Visitor sends an urgent question by form | No answer for two days | Harm | Form states the answer time and repeats the emergency notice |
| Referral requirement not stated | Turned away at the desk | A wasted visit | Service field "needs a referral" |
| Preparation not stated | Test cannot be done (not fasting) | A second visit | Service field "preparation" |
| Booking link to an external system breaks | Taps, nothing | Silent loss | Check the link at publish and on a schedule |
| No access information | A wheelchair user meets stairs | Exclusion; a legal issue in many places | Ask about access at intake |
| Outcome promised in the text | Expects a cure | A complaint to the regulator | Rule 9 |

## 6. Professional language

Hebrew and Arabic terms are the author's knowledge, not checked with a practitioner in either language. "Not verified" means do not use a guess.

| English | Meaning | Hebrew | Arabic |
|---|---|---|---|
| Clinic, practice | the place | מרפאה | عيادة |
| Family doctor, GP | first-contact doctor | רופא/ת משפחה | طبيب عائلة / طبيب عام |
| Specialist | doctor registered in a speciality | רופא/ה מומחה/ית | طبيب مختص / أخصائي |
| Paediatrician | children's doctor | רופא/ת ילדים | طبيب أطفال |
| Dermatologist | skin doctor | רופא/ת עור | طبيب جلدية |
| Gynaecologist | women's health doctor | רופא/ת נשים | طبيب نسائية |
| Nurse | | אח / אחות | ممرض / ممرضة |
| Physiotherapist | | פיזיותרפיסט/ית | معالج طبيعي |
| Receptionist, front desk | | מזכירות רפואית / קבלה | الاستقبال |
| Patient | the person treated | מטופל/ת | مريض / مراجع |
| Appointment | | תור | موعد |
| Walk-in | without an appointment | ללא תור | بدون موعد |
| Consultation | a visit to discuss a problem | ייעוץ / ביקור | استشارة |
| First visit / follow-up | | ביקור ראשון / ביקור חוזר | زيارة أولى / مراجعة |
| Referral | a doctor's letter sending you on | הפניה | تحويل / إحالة |
| Prescription | | מרשם | وصفة طبية |
| Test, lab test | | בדיקה / בדיקת מעבדה | فحص / تحليل |
| Results | | תוצאות | نتائج |
| Health fund (Israel) | public health organisation | קופת חולים | صندوق المرضى |
| Health insurance | | ביטוח בריאות | تأمين صحي |
| Payment commitment form (Israel) | fund's undertaking to pay | טופס 17 / התחייבות | not verified |
| Co-payment | the patient's share | השתתפות עצמית | not verified |
| Private care | paid by the patient | רפואה פרטית | طب خاص (not verified) |
| Emergency room | | מיון / חדר מיון | الطوارئ |
| Urgent care | same-day care for non-emergencies | רפואה דחופה / מוקד | not verified |
| Telehealth, video visit | remote consultation | ביקור מרחוק / וידאו | استشارة عن بعد (not verified) |
| Medical record | | תיק רפואי | ملف طبي |
| Informed consent | agreement after explanation | הסכמה מדעת | موافقة مستنيرة |
| Medical confidentiality | | סודיות רפואית | السرية الطبية |
| Sick note, medical certificate | | אישור מחלה | تقرير طبي (not verified) |

Notes on language:

- UK: "GP", "surgery", "A&E". US: "primary care physician", "office", "ER", "provider". Pick by country.
- Patients say "doctor" for everyone; the site must use the real profession of each person.
- Words to avoid: "cure", "guaranteed", "painless", "risk-free", "best doctor", "leading expert", "miracle", "no side effects". Also "specialist" for anyone not registered as one.
- The product does not write medical explanations. It can lay out text the clinic supplies.

## 7. Legal

A checklist of questions, not legal advice. The author is not a lawyer and read no statute for this file. In this domain errors can harm people; every item needs checking by someone qualified in the clinic's country.

### Applies almost everywhere

- **Health data is a special category.** An appointment at a named speciality, a reason for visit, a test request: all are health information and are more strictly protected than ordinary personal data.
- **Medical confidentiality** binds practitioners by professional rules as well as law, and extends to reminders and emails.
- **Practitioners must be licensed**, and using a protected title without being registered is an offence in many countries.
- **Advertising of medical services is restricted**: limits on testimonials, before-and-after images, superlatives, price promotions and outcome claims are common. The limits differ by country and profession.
- **A complaints route** to the clinic and to a regulator is often required to be published.
- **Privacy notice, terms for paid bookings, marketing consent**: as in every domain, but with health data in scope.

### Israel

- Patients' Rights Law (1996): confidentiality, informed consent, the patient's right to their record. Application to a website: not verified.
- Protection of Privacy Law and Amendment 13 (in force August 2025): health data is highly sensitive information; data-security regulations set duties by database level. What a small clinic must do: not verified.
- Advertising by physicians is limited by regulations under the Physicians Ordinance and by ethics rules (no misleading claims, limits on superlatives and testimonials). Current text: not verified.
- Clinics are licensed or registered with the Ministry of Health depending on type; whether a private single-doctor practice needs a facility licence: not verified.
- Accessibility: service-accessibility regulations cover health services, physically and online, with an accessibility statement and coordinator details. Exemptions: not verified.
- Advertising messages need prior consent (section 30A, Communications Law). Whether appointment reminders fall outside it: not verified.

### European Union and United Kingdom

- GDPR / UK GDPR, Article 9: health data needs a specific legal basis; a data-protection impact assessment and a data-protection officer may be required for larger providers. Thresholds: not verified.
- England: providers of regulated health activities register with the Care Quality Commission and display their rating. Doctors register with the General Medical Council. Scope and display rules: not verified.
- UK advertising rules (CAP code) restrict medical claims and prescription-only-medicine advertising to the public. Not verified.
- One UK reference states on its home page that it is not an emergency service and directs emergencies to 999 or the nearest emergency department; it also states a consultation price as "from" and an administrative charge for cancellation (observed 2026-11-21).
- Each EU state has its own professional chamber rules on doctors' advertising (strict in Germany and France): not verified.

### United States

- HIPAA applies to most providers that bill electronically: a Notice of Privacy Practices, safeguards for protected health information, and written agreements with any vendor handling it. A website builder that stores appointment reasons may itself fall under these rules. Not verified.
- Practitioners are licensed by state boards; telehealth across state lines is restricted. Not verified.
- FTC rules on endorsements and health claims; price-transparency rules (good-faith estimates for uninsured patients). Not verified.
- Section 1557 and the ADA on accessibility and language access. Not verified.

### What the product does with this

- Asks the country and the profession before generating any page.
- Does not store clinical information. A "reason for visit" field is off unless the customer turns it on after being told what it implies.
- Never writes a medical claim, and never states that the site "complies with" a named law.
- Marks every legal page as a draft for review.

## 8. Site vs app

### Content pages (no data, no accounts)

Home, services, practitioners, fees and insurers, what to expect on a first visit, how to find us, access, contact, policies, complaints, legal pages. With a phone link as the action, this is a complete and honest product for a small clinic, and it holds no health data.

| Part | Empty | Error | Notes |
|---|---|---|---|
| Emergency notice | cannot be empty | | On every page |
| Services | cannot be empty | | |
| Fees | "Ask reception" | | Dated |
| Insurers | "Ask us which insurers we work with" | | Never a guessed list |
| Practitioners | cannot be empty (at least one) | missing photo: initials, not a stock face | |
| Reviews | hidden | | Off by default |
| Health information | hidden | | Only the clinic's own, dated |
| Hours, map | hours cannot be empty | address text remains if the map fails | |

### Needs data

| Part | What it needs | Empty state | Loading | Error | Save | Permissions |
|---|---|---|---|---|---|---|
| Callback request | name, phone, preferred time | n/a | "sending", no double press | "Not sent - please call", with the number and the emergency notice | "Received. We call back within [the time the clinic gave]. Not for urgent problems." | visitor writes; reception reads |
| Booking request (clinic confirms) | service, practitioner, wanted time | "No times this week - call us" | placeholder, never an empty diary that reads as "full" | "Could not load times - call us" | "requested - not confirmed yet" | patient sees only own request |
| Live booking | services with durations, practitioners' hours, closures, existing appointments | as above | as above | slot taken meanwhile: nearest alternatives | confirmed only after the server saved it; confirmation contains no clinical detail | patient: own; practitioner: own diary; reception and owner: all |
| Cancel or change | a personal link from the confirmation | "No upcoming appointments" | | expired link: show the phone | slot freed at once; clinic alerted | only through the link |
| Reception diary | day and week list | "No appointments today" | | never show a stale diary without saying so | every change records who made it | staff only, behind a login |
| New-patient or consent form | health data | | | a failed save keeps what was typed | patient gets a copy | only the patient and the clinical staff; encrypted; not sent by email |
| Clinic edits content | edit screen | | | failed save says so | live after saving | owner or manager |

### Needs accounts

- Staff, as soon as anything is stored.
- Patients should not need an account to book. A phone number and a personal link are enough.
- A patient portal (results, records, messages with the doctor, prescriptions) is a medical-records system. It is outside what this product builds. Three US references offer one through their own app (observed 2026-11-21); the right move for a small clinic is to link to the system it already has.

### Needs payments

- Deposit, prepaid consultation, membership fee.
- Brings refunds, receipts, failed payments, and in some countries rules on charging before a medical service. Default: none.
- Two references sell membership (a yearly or monthly fee for access); this is a subscription product and needs its own terms.

### Using an existing system

Most clinics run a practice-management system that already holds the diary and records. Ask first (mandatory fact 17). If one exists, the product is a content site whose main action links to it, and the product holds no patient data. That is the default.

## 9. References

**How these were checked.** Each URL was fetched on 2026-11-21 with a page-extraction tool that returns text and image references. No browser, no screenshot. Section order and wording are observed; visual quality and image-to-text ratio are not, and every ratio is an estimate from counts in the extracted text.

**Curation.** Chosen by the author from known US and UK providers, not from a search-result list. No awwwards.com category was consulted. All in English, Latin script. Home pages only.

**Limit.** All seven are multi-site, venture-backed or group-owned providers. No single-doctor practice was verified, although that is the typical customer.

Verified: 7.

| # | Site | Checked | What was observed |
|---|---|---|---|
| 1 | https://www.onemedical.com | 2026-11-21 | US membership primary care. Order: enrolment notice strip - headline with in-office and remote appointments, and a line for existing members - three feature cards (mental health, annual physical, pharmacy) - "Get care today for" a list of conditions - insurance paragraph with an in-network check - benefit blocks (same or next-day appointments, longer appointments, on-site labs, range of care, providers) - what the app does - membership price stated as a yearly figure with what it includes - closing sign-up. Extraction: 4 image references, about 6,900 characters. |
| 2 | https://www.londondoctorsclinic.co.uk | 2026-11-21 | London private GP group. Order: headline naming the service - same-day appointments - five patient reviews, each with a short title - service descriptions (in-person, online) - about, stating the group owner and a "from" price - a section headed that it is not an emergency service, directing to 999 or A&E - a long FAQ (how to book, walk-in, specialists, blood tests, waiting lists, insurers, cancellation charge). Text-heavy, written for search. Extraction: 21 images, about 13,400 characters. |
| 3 | https://www.parsleyhealth.com | 2026-11-21 | US functional-medicine membership. Order: headline on the root cause of symptoms - positioning - insurance acceptance - "Two ways to get started" with two priced options side by side, prices stated per month and per year and by insurance status - a five-star quote - conditions grouped by area, each a list of symptoms - more below. Extraction: about 50 image references, about 18,100 characters. |
| 4 | https://www.sollishealth.com | 2026-11-21 | US members-only urgent and emergency care. Order: promotion - one-sentence promise - "Choose your membership": three tiers, each a paragraph and a bullet list of inclusions - locations grouped by region - "Who is it for": five audience blocks. No prices in the extracted text. Extraction: 11 images, about 3,600 characters. |
| 5 | https://www.zoomcare.com | 2026-11-21 | US Pacific Northwest clinics. Navigation by state and city, then by "everyday care" and "speciality care". Order: headline on scheduling - four care types named - a promoted service - six benefits (same-day visits, extended hours, labs and medicines on site, results online, providers, evidence-based) - care lists - "Schedule a visit" - "Pricing and insurance" stating no memberships and transparent self-pay prices - clinic locations - six patient reviews under first names - mission. Extraction: about 27 image references, about 7,500 characters. |
| 6 | https://www.carbonhealth.com | 2026-11-21 | US urgent and primary care. Navigation: services, locations by state, company, for business. Order: headline - "Book an appointment" - positioning line stating no membership fees - four feature blocks (same-day booking, chat with the care team, prescriptions delivered, records in one place) - app - "Insurance and pricing" telling the visitor to check coverage with their insurer - patient reviews - closing. Extraction: about 62 image references including icons, about 9,500 characters. |
| 7 | https://www.kindbody.com | 2026-11-21 | US fertility clinics, a specialist practice. Header has Schedule, Member Portal and Provider Portal. Order: headline - three entry blocks (services, making care accessible through benefits, financing and insurance, employers) - the patient experience - a free introductory class sign-up - "Meet our experts": a long run of doctors, each with qualifications and the locations they serve - patient stories - press - contact. Shows how a specialist site leads with the doctors. Extraction: about 12 image references, about 35,300 characters, most of it doctor biographies. |

Loaded and not used:

| Site | Checked | Why not |
|---|---|---|
| https://www.citymd.com | 2026-11-21 | Loads, but the extraction returned only five headings and about 780 characters. Not enough to describe the structure. |

## 10. Skeletons

Structure only. No colours, logos, photographs or wording were taken from any reference.

### Skeleton A: the practice (appointment-first)

For a general or family practice, or an urgent-care clinic. Default for this domain.
From references 1, 2, 5, 6: the benefit blocks of 1 and 5, the emergency section and FAQ of 2, the pricing-and-insurance block of 5 and 6. The reduction to one location is the author's.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; one action (book / call); emergency line in small type | action prominent; emergency line always present | yes |
| 1 | Opening | one sentence: kind of practice, for whom, where; the main action; a quiet line for existing patients | one heading, one line, one action | yes |
| 2 | What we help with | services or common reasons to come, in plain words, grouped | short lists, not paragraphs | yes |
| 3 | How it works here | three or four practical facts the clinic gave: how soon, how long a visit is, tests on site, remote visits | heading and one line each | optional |
| 4 | Who you will see | practitioners: name, profession, speciality, languages | equal cards; real titles | yes |
| 5 | Fees and insurance | prices or "ask reception"; named insurers; what the patient pays | plain table | yes, even if only "ask reception" |
| 6 | First visit | what to bring, referral, preparation, cancellation policy | short list | optional |
| 7 | Questions | FAQ from the clinic's own answers | question as heading | optional |
| 8 | Not an emergency service | what to do in an emergency or out of hours | its own heading, plain words | yes |
| 9 | Find us | address, entrance, access, phone and its hours, opening hours per day | complete without the map | yes |
| 10 | Footer | licence and registration details, complaints route, privacy, terms, accessibility statement | small | yes |

Image-to-text ratio: **estimate**, from extraction counts only (references 1 and 2 returned 4 and 21 images against about 7,000 and 13,000 characters). Text-led: roughly one image for every three or four text blocks. Text carries almost everything a patient needs. Not confirmed in a rendered view.

### Skeleton B: the specialist (doctor-first)

For a specialist practice where patients choose the doctor and the treatment path matters.
From references 3, 4, 7: the doctors section of 7, the "ways to start" of 3, the "who is it for" of 4.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; book a consultation; emergency line | | yes |
| 1 | Opening | the speciality and who it is for, one sentence; the main action | | yes |
| 2 | Conditions and treatments | grouped by area, each a short list; no outcome claims | groups as headings | yes |
| 3 | The doctors | name, speciality, training, locations; one doctor first for a solo practice | this is the proof | yes |
| 4 | The path | first consultation, tests, plan, follow-up, as steps | numbered | optional |
| 5 | Ways to start and what it costs | one or two entry options with price or "on consultation"; insurers; financing if offered | options side by side | yes |
| 6 | Patient stories | only where allowed, with consent | few | optional, off by default |
| 7 | Find us, emergency notice, footer | as Skeleton A, sections 8 to 10 | | yes |

Image-to-text ratio: **estimate**. Mixed: reference 7 is text-heavy because of biographies; reference 3 returned about 50 image references against 18,000 characters. Not confirmed in a rendered view.

## 11. Not verified

1. All Hebrew and Arabic terms in section 6: author's knowledge, not checked with a practitioner.
2. Every legal statement in section 7. None was checked against a statute, a regulator's code or an official source. Advertising rules for doctors, facility licensing, and HIPAA's reach over a website builder are the least certain and the most consequential.
3. Image-to-text ratios and visual quality of all references: text extraction only.
4. No awwwards.com category was consulted; design quality is the author's prior judgement.
5. No single-doctor or neighbourhood clinic reference was verified. No reference outside the US and UK.
6. Sub-pages (services, doctor profiles, booking flows, privacy notices) were not fetched.
7. The claim that most clinics already run a practice-management system is the author's belief, not sourced.
8. Whether showing patient reviews is lawful for a given profession and country: open in every jurisdiction listed.
9. The emergency number per country must be confirmed by the customer; the product's table of numbers has not been written or checked.
10. No references in Hebrew, Arabic or any non-Latin script.
