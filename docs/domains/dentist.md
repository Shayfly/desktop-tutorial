# Dentist

Covers: a dental practice: general dentistry, hygiene, children's dentistry, orthodontics, implants, cosmetic dentistry, emergency dental care. One chair or several locations.
Does not cover: medical clinics (use `clinic.md`); facial aesthetics as the main business (use `beauty-cosmetics.md`); dental laboratories; selling aligners or whitening kits online with no practice.
Written 2026-11-21. References checked 2026-11-21. Template: [README.md](README.md).

## 1. Objects

A dental practice sells **a treatment by a licensed clinician, in a chair, for a length of time**. It shares the clinic's duties (health data, licensed titles, restricted advertising) and adds three things of its own: a price list that people compare, treatment plans that run over several visits and large sums, and people who come in pain or in fear.

### Practice (the business)

| Field | Required | Example (illustrative) |
|---|---|---|
| Name | required | "Hill Street Dental" |
| Kind of practice | required | general, family, children's, orthodontic, implant, cosmetic |
| Who it treats | required | adults, children, everyone |
| Address | required | street, number, floor, city |
| Phone | required | reception line |
| Opening hours, per day | required | Sun-Thu 08:00-19:00, Fri 08:00-13:00 |
| How to book | required | call, message, online booking |
| Dental emergencies | required | what to do in pain today; what to do when closed |
| How payment works | required | private, named insurers or health funds, public scheme, payment plans |
| Licence or registration, body and number | required where the law requires it | |
| New patients accepted | optional | yes, waiting list, children only |
| Access | optional | step-free, lift, parking |
| Languages spoken | optional | |
| Care for anxious patients | optional | longer first visit, sedation, only if the practice offers it |

### Location (only when there is more than one)

Address, phone, hours, clinicians, treatments and closure dates repeated per location.

### Clinician

| Field | Required | Example |
|---|---|---|
| Name as licensed | required | |
| Profession | required | dentist, specialist orthodontist, hygienist, dental therapist, dental nurse |
| Speciality | required for specialists | only one the person is registered in |
| Registration number | required where it is required or customary to show | |
| Treatments this person provides | optional | |
| Days and hours | optional on the page, required for online booking | |
| Languages, photo, short professional bio | optional | photo with consent |

### Treatment category

| Field | Required | Example |
|---|---|---|
| Name | required | Check-ups and hygiene, Fillings and repairs, Root canal, Crowns and bridges, Implants, Orthodontics, Whitening and cosmetic, Children, Emergency |
| Order | required | routine care first |

### Treatment

| Field | Required | Example |
|---|---|---|
| Name in plain words | required | "Check-up", "Hygienist clean", "White filling", "Crown" |
| Category | required | |
| What it is, in two lines | optional | written or approved by the practice |
| Price | optional, see rule 5 | |
| Price type | required when a price is shown | fixed, "from", range, per tooth, per arch, "after examination" |
| What the price includes | optional | X-rays, laboratory fee, follow-up |
| Duration in minutes | optional on the page, required for online booking | 30 |
| Number of visits | optional | "usually two visits" |
| Who provides it | optional | |
| Bookable online directly | required, default no | only simple first steps are |
| Needs an examination first | optional | most treatments do |
| Age limits | optional | whitening not for minors |
| Currently offered | required, default yes | |

### Appointment (only when the product takes bookings)

| Field | Required | Example |
|---|---|---|
| Treatment or visit type | required | new-patient exam, check-up, hygiene, emergency, consultation |
| Clinician, or "first available" | required | |
| Location | required | |
| Date and start time | required | |
| Patient name and phone | required | |
| New or returning | optional | |
| In pain now | optional | routes to the emergency path |
| Notes | optional; not for medical history | |
| Status | required | requested, confirmed, cancelled by patient, cancelled by practice, completed, no-show |

### Other objects

| Object | Fields | Notes |
|---|---|---|
| Payment option | insurer, fund or scheme; membership plan; instalment plan with its provider | Credit is regulated; see Legal |
| Membership plan | name, monthly fee, what is included | A subscription; needs its own terms |
| Before-and-after case | images, treatment, clinician, consent, date | Regulated in many countries; off by default |
| Review | text, initials, date, source | See Legal |
| Closure | date or range | Overrides weekly hours |
| Notice | text, start date, end date | A notice without an end date goes stale; see failure modes |
| Policy | cancellation, missed appointment, deposit, children, complaints | Shown before booking |
| Patient form | medical history, consent | Health data; app only |
| Treatment plan, X-rays, records | | Outside this product; see section 8 |

## 2. Rules

1. Every page says what to do about a dental emergency, in hours and out of hours, and when to go to a hospital emergency department instead (heavy bleeding, swelling that affects breathing or swallowing, injury to the face) in wording the practice approved.
2. A clinician's profession and speciality are exactly as registered. "Specialist" and "orthodontist" are protected words in many countries.
3. A clinician is booked only for treatments they provide, where and when they work. Two confirmed appointments for one clinician or one chair do not overlap.
4. Only visit types the practice marked "bookable online" can be booked directly. Everything else starts with an examination or consultation.
5. A price is optional but its absence is explicit: "after examination" or "ask us". Never blank, never zero.
6. A "from" price says "from" and says what moves it (number of teeth, material, laboratory). A fixed price is what the patient pays for the described treatment.
7. Every price shows its currency, and whether it is per tooth, per arch or per course.
8. "Free consultation" is written only if it is free with no condition; any condition is stated next to it.
9. An insurer, fund, public scheme or instalment provider is named only if the practice works with it.
10. No outcome is promised: no "painless", "guaranteed", "permanent", "perfect smile", "lasts a lifetime".
11. A before-and-after image is published only with the patient's written consent, of the practice's own work, unretouched, and only where local rules allow it.
12. Reviews are real, carry their source, and are shown only where rules on healthcare testimonials allow it.
13. Messages and reminders carry date, time and practice name only.
14. A public form does not require medical history. An upload of a photo of a visitor's teeth is health data and is treated as such.
15. A notice (holiday hours, a temporary change) has an end date and disappears after it.
16. A cancellation or missed-appointment fee, or a deposit, is shown before the visitor confirms.
17. Opening hours are per day, in local time, with closed days named.
18. The main action is reachable from every page on a phone; the phone is tappable; the address opens a map.
19. Stock photographs of smiles are not presented as the practice's work.

## 3. Mandatory facts

The product is not built until each has an answer. None may be guessed.

| # | Fact | The one question to ask | Why (the human reason) |
|---|---|---|---|
| 1 | Name | "What is the practice called?" | People recommend a dentist by name. |
| 2 | Kind of practice | "What kind of dentistry do you do, and for whom: adults, children, everyone?" | A parent needs to know if you see children; a person wanting implants needs to know if you place them. |
| 3 | Who treats | "Who treats patients? For each: full name as licensed, profession, speciality." | People choose the dentist, and a wrong title is a false claim. |
| 4 | Where | "What is the full address and floor, and how do people find the entrance?" | Without it people cannot arrive. |
| 5 | Phone | "What number do patients call, and when is it answered?" | A person in pain calls; they do not fill in forms. |
| 6 | Hours | "Which days and hours are you open?" | People come before or after work. |
| 7 | How to book | "How does a new patient get a first appointment?" | The whole site leads to this step. |
| 8 | Emergencies | "What should someone with a toothache or a broken tooth do today? And when you are closed?" | Pain does not wait, and a person with swelling may need a hospital. |
| 9 | Treatments | "What treatments do you offer? Say them as you say them to patients." | People search for a treatment, not for a practice. |
| 10 | Prices, or the decision not to show them | "What do a check-up, a clean and your common treatments cost? If you prefer not to show prices, say so." | Fear of the bill keeps people away. Hiding is allowed; inventing is not. |
| 11 | Payment | "Private only, or insurers, funds or a public scheme? Which, by name? Do you offer instalments, and through whom?" | People decide whether they can afford to come. |
| 12 | Licence | "Which body registers the practice and the clinicians, and what numbers should be shown?" | Patients and regulators look for it. |
| 13 | Who is the business legally | "What is the registered name and number, and who answers privacy requests?" | Health data must have a named holder. |

Needed only when the product takes bookings:

| # | Fact | The one question to ask | Why |
|---|---|---|---|
| 14 | What can be booked online | "Which visits may a patient book without talking to you first?" | A patient who books a crown without an examination loses a morning. |
| 15 | Durations | "How long is each of those visits?" | Otherwise the day runs late for everyone. |
| 16 | Who works when | "Who is in on which days, and in which room?" | Otherwise two patients share a chair. |
| 17 | Cancellation | "What happens if a patient cancels late or does not come?" | The patient must know before booking. |
| 18 | Where bookings go, and existing systems | "Where does a new booking arrive? Do you already use dental software with a diary?" | A booking nobody saw; or two diaries that disagree. |

## 4. Declared defaults

Each default is shown to the customer as "we filled this in - change it if it is wrong".

| Default | Value | Why it is safe | How it is marked |
|---|---|---|---|
| Emergency block | "In pain? Call us on [phone] during opening hours." plus a hospital line for bleeding, swelling or injury, with the wording sent to the customer for approval | Better than silence; nothing clinical is asserted without approval | "Default emergency notice - approve the wording" |
| Main action | "Call to book" | Works with zero setup | "default: phone" |
| Category names and order | as in the Treatment category table | Common structure across the references | "suggested order", editable |
| Missing price | "After examination" | Honest: most dental prices depend on the mouth | Listed as "no price given" |
| Online-bookable visits | none | Rule 4 | "Off until you choose which visits" |
| Before-and-after gallery | hidden | Consent and local rules | "Off until you confirm consent and that it is allowed" |
| Reviews | hidden | Rules differ by country | "Off by default" |
| Photo-upload ("smile assessment") | off | Health data by upload | "Off by default" |
| Reminder wording | date, time, practice name, phone | Rule 13 | Shown |
| Page order | Skeleton A below | From the references | Named as default |
| Language, direction, currency | from the conversation and address | | Shown |
| Legal page structure | headings only | | "Draft - not legal advice" |

Never a default: titles, specialities, registration numbers, treatments, prices, "free consultation", insurers and schemes, instalment terms, hours, emergency cover, equipment and technology claims, awards, years of experience, any clinical statement.

## 5. Failure modes

| What went wrong | What the visitor sees | What it costs | Prevention |
|---|---|---|---|
| No emergency guidance | A person with a swollen face fills in a form and waits | Harm | Rule 1 |
| "From" price read as the price | Quote in the chair is three times the site | Walks out; a complaint | Rule 6 |
| Old price list | Pays more than the site said | Dispute | Dated price list; yearly prompt |
| "Free consultation" with hidden conditions | Charged for X-rays at the "free" visit | Feels tricked | Rule 8 |
| Complex treatment booked directly | Arrives for an implant; today is only an examination | A wasted morning | Rule 4 |
| Insurer or scheme listed wrongly | Unexpected bill | Dispute | Rule 9; dated list |
| "Accepting new patients" out of date | Calls, is refused | Frustration | Dated; easy to switch |
| Old notice still on the home page | Reads a restriction from years ago and assumes the practice is half closed | Lost patients; looks abandoned | Rule 15. Seen on a reference on 2026-11-21 |
| Dentist left, still listed | Asks for someone who is gone | Looks neglected | Clinician can be hidden; future slots closed |
| Wrong title ("specialist") | Believes they see a specialist | A regulatory complaint | Rule 2 |
| Double booking of a chair | Long wait in the waiting room | Anxiety, bad review | Rule 3 at save time |
| Booking saved, reception never told | Arrives; no record | The worst ordinary case | Mandatory fact 18; "requested" until confirmed |
| Before-and-after without consent, or retouched | A patient recognises their own mouth; or results do not match | Complaint; regulator | Rule 11 |
| Reminder reveals the treatment | Someone else reads it | Breach of confidence | Rule 13 |
| Photo upload goes to an ordinary inbox | Health images in email | Data-protection problem | Rule 14 |
| Instalments advertised with no provider named | Asks for "0% finance" that does not exist | Consumer-credit problem | Rule 9 |
| Site requires scripts to show anything | A blank page or a "turn on JavaScript" line | Silent loss | Content readable without scripts. Seen on a reference on 2026-11-21 |
| Fear not addressed | An anxious person never calls | The patients who most need care stay away | Ask the practice what it does for anxious patients; say only that |

## 6. Professional language

Hebrew and Arabic terms are the author's knowledge, not checked with a dentist in either language. "Not verified" means do not use a guess.

| English | Meaning | Hebrew | Arabic |
|---|---|---|---|
| Dental practice, dental clinic | the place | מרפאת שיניים | عيادة أسنان |
| Dentist | | רופא/ת שיניים | طبيب أسنان |
| Dental hygienist | cleans and teaches care | שיננית | أخصائية صحة الفم (not verified) |
| Dental nurse, assistant | | סייעת שיניים | مساعدة طبيب أسنان |
| Orthodontist | straightens teeth | אורתודונט/ית | أخصائي تقويم أسنان |
| Oral surgeon | | מומחה/ית לכירורגיית פה ולסת | جراح فم وفكين (not verified) |
| Children's dentist | | רופא/ת שיניים לילדים | طبيب أسنان أطفال |
| Check-up, examination | | בדיקה תקופתית | فحص دوري |
| Scale and polish, cleaning | | ניקוי אבנית | تنظيف أسنان |
| X-ray | | צילום רנטגן | صورة أشعة |
| Filling | | סתימה | حشوة |
| Root canal treatment | | טיפול שורש | علاج عصب / علاج جذور |
| Extraction | | עקירה | خلع |
| Crown | cap over a tooth | כתר | تاج / تلبيسة |
| Bridge | fixed replacement between teeth | גשר | جسر |
| Implant | artificial root | שתל | زراعة أسنان |
| Denture | removable teeth | תותבת | طقم أسنان |
| Veneer | thin front covering | ציפוי חרסינה | قشور / فينير |
| Bonding | tooth-coloured reshaping | הדבקה (not verified) | not verified |
| Whitening | | הלבנת שיניים | تبييض أسنان |
| Braces | fixed orthodontic appliance | גשר יישור / קוביות | تقويم أسنان |
| Clear aligners | removable transparent trays | קשתיות שקופות | تقويم شفاف |
| Retainer | holds teeth after straightening | ריטיינר / קיבוע (not verified) | مثبت (not verified) |
| Gum disease | | מחלת חניכיים | أمراض اللثة |
| Local anaesthetic | numbing injection | הרדמה מקומית | تخدير موضعي |
| Sedation | calming medication during treatment | סדציה / טשטוש | تخدير واعٍ (not verified) |
| Laughing gas | inhaled sedation | גז צחוק | غاز الضحك |
| Treatment plan | written list of treatments and costs | תוכנית טיפול | خطة علاج |
| Quote, estimate | | הצעת מחיר | عرض سعر |
| Dental emergency | pain, swelling, broken tooth | עזרה ראשונה בשיניים | طوارئ أسنان |
| Dental anxiety | fear of the dentist | חרדה מטיפולי שיניים | not verified |

Notes on language:

- UK: "practice", "surgery", "scale and polish", "NHS". US: "office", "cleaning", "insurance", "DDS". Pick by country.
- Patients say "cleaning", "tooth pulled", "braces". Use the patient's word as the heading and the clinical word second.
- Words to avoid: "painless", "pain-free", "guaranteed", "permanent", "perfect", "best dentist", "leading", "Hollywood smile" as a promise, "specialist" for a non-registered clinician. Superlatives are common on real dental sites (seen in the references) and are exactly what advertising rules restrict.

## 7. Legal

A checklist of questions, not legal advice. The author is not a lawyer and read no statute for this file. Everything needs checking by someone qualified in the practice's country. Section 7 of `clinic.md` applies in full; only what dentistry adds or changes is listed here.

### Applies almost everywhere

- Dental records, X-rays and photographs of teeth are health data.
- Dentists and other dental professionals are licensed; titles and specialities are protected.
- Advertising of dental services is restricted: before-and-after images, testimonials, superlatives, discounts and time-limited offers are limited or banned in several countries.
- Offering instalments can make the practice a credit intermediary that needs authorisation. One UK reference carries a footer statement naming its credit partner and that partner's regulator (observed 2026-11-21).
- Tooth whitening above a set concentration is restricted to dental professionals in many places, with age limits.
- A written treatment plan and estimate before treatment starts is required or expected in many places.

### Israel

- Dentists Ordinance: dentistry is practised only by licensed dentists; specialities are registered. Advertising rules for dentists (misleading claims, comparisons, testimonials): current text not verified.
- Children's dental care is included in the public health basket through the health funds up to a set age, and some care for older adults. Current ages and scope: not verified.
- Dental X-ray equipment needs a permit. Not verified.
- Hygienists work under rules on what they may do alone. Not verified.
- Patients' Rights Law, privacy law (Amendment 13, 2025), accessibility statement, consent for advertising messages: as in `clinic.md`, all not verified for a small practice.
- Prices shown to consumers include VAT; how that applies to "from" prices: not verified.

### European Union and United Kingdom

- GDPR / UK GDPR for health data.
- UK: dental professionals register with the General Dental Council, whose guidance covers advertising (register number and qualification displayed, no misleading claims, a complaints procedure). Practices in England register with the Care Quality Commission. Details: not verified.
- UK: NHS dental charges are set in bands; a practice must be clear about which treatment is NHS and which is private. Not verified.
- UK: credit broking for patient finance is regulated by the Financial Conduct Authority, with exemptions for some interest-free instalment arrangements. Not verified.
- EU: whitening products above 0.1% and up to 6% hydrogen peroxide are for use by or under a dentist, not for under-18s. Not verified.
- Advertising rules for dentists differ by member state: not verified.

### United States

- State dental boards license dentists and hygienists; some states restrict advertising a speciality. Not verified.
- HIPAA as in `clinic.md`. Not verified.
- Patient-financing and membership plans are regulated by state; some states treat in-house membership plans as insurance. Not verified.

### What the product does with this

- Asks the country before generating any page; marks every legal page as a draft.
- Before-and-after, reviews, photo upload and "free" offers are off until the customer confirms they are allowed and true.
- Never writes a clinical claim and never states that the site "complies with" a named law.

## 8. Site vs app

### Content pages (no data, no accounts)

Home, treatments, price list, team, new patients (first visit, what to bring), emergencies, anxious patients, payment and plans, how to find us, policies, complaints, legal pages. With a phone link as the action, this is a complete product for a small practice and holds no health data.

| Part | Empty | Error | Notes |
|---|---|---|---|
| Emergency block | cannot be empty | | On every page |
| Treatments | cannot be empty | | |
| Price list | "Prices after examination - call us" | | Dated; "from" explained |
| Team | cannot be empty (at least one clinician) | missing photo: initials, no stock face | |
| Payment options | "Ask us about payment" | | Never a guessed insurer |
| Before-and-after, reviews | hidden | | Off by default |
| Notices | hidden | | Removed after the end date |
| Hours, map | hours cannot be empty | text address remains | |

### Needs data

| Part | What it needs | Empty state | Loading | Error | Save | Permissions |
|---|---|---|---|---|---|---|
| Callback or enquiry form | name, phone, what it is about from a short list | n/a | "sending", no double press | "Not sent - please call", with the number | "Received", the answer time the practice gave, and "in pain now? call" | visitor writes; reception reads |
| Booking request | visit type, wanted time | "No times this week - call us" | placeholder, never an empty diary that reads as "full" | "Could not load times - call us" | "requested - not confirmed" | patient sees own request only |
| Live booking of allowed visit types | durations, clinicians' hours, rooms, closures | as above | as above | slot taken meanwhile: nearest alternatives | confirmed only after the server saved it | patient: own; clinician: own diary; reception, owner: all |
| Cancel or change | personal link | "No upcoming appointments" | | expired link: show the phone | slot freed at once; practice alerted; late-cancellation rule shown before confirming | only through the link |
| Photo upload for an online consultation | image storage for health data | | upload progress shown | failed upload says so and keeps the form | visitor told who will look and when | only clinical staff; not email |
| Membership plan sign-up | payments, recurring | | | failed payment states | receipt and terms sent | patient: own plan; owner: all |
| Practice edits content | edit screen | | | failed save says so | live after saving | owner or manager |

### Needs accounts

- Staff, once anything is stored.
- Patients do not need an account to book.
- A patient login (treatment plans, records, bills) belongs to the dental software, not to this product. One reference shows "Login" beside "Book now" in its header (observed 2026-11-21).

### Needs payments

- Deposit for long appointments, membership plan, prepaid whitening or hygiene.
- Instalments are provided by a credit company, not by the product. The product links to it and names it.
- Default: no payments.

### Using an existing system

Dental practices almost always run dental software that holds the diary, charting and X-rays. If it offers online booking, the product is a content site whose "Book" button links to it. Ask before building a second diary.

## 9. References

**How these were checked.** Each URL was fetched on 2026-11-21 with a page-extraction tool that returns text and image references. No browser, no screenshot. Section order and wording are observed; visual quality and image-to-text ratio are not, and every ratio is an estimate from counts in the extracted text. Names of individual clinicians that appear on the sites are left out.

**Curation.** Chosen by the author from known London and New York practices, not from a search-result list. No awwwards.com category was consulted. All in English, Latin script. Home pages only.

**Limit.** All six are private, city-centre practices or groups in London and New York. No public-scheme practice and no small-town family dentist was verified. References 3, 5 and 6 are useful for content and structure, and also show what not to copy: long search-driven text and superlatives.

Verified: 6.

| # | Site | Checked | What was observed |
|---|---|---|---|
| 1 | https://www.hellotend.com | 2026-11-21 | US dental studio group. Header: Book now, Login, a phone number. Order: headline about looking forward to the dentist, with a line for people who have not been in years - "full range of services" - "the difference" - a long run of patient reviews - "Dental studios across the US": one entry per studio, each showing the dates that studio is closed for the coming holiday - "Questions?" with call, email, social - services list. Extraction: about 49 image references, about 19,900 characters. |
| 2 | https://www.dntlbar.com | 2026-11-21 | New York practice. Order: short headline - a second heading naming the neighbourhood - six one-line trust points (judgement-free care, short-notice and emergency availability, insurance friendly, third-party financing, patient count, technology) - "Our promise" - services, each one line - insurance - reviews - press - quality care in two blocks - "Book today" - contact - business hours in one line - a service disclaimer saying listed services may vary - mailing list. Extraction: about 32 image references, about 12,900 characters. |
| 3 | https://www.bowlanedental.com | 2026-11-21 | City of London private practice. Very large navigation: every treatment as its own link, grouped (general, orthodontics, whitening, cosmetic), plus guides. Order: a notice that the clinic is open with a link to a COVID policy, and a notice that one service is temporarily stopped - headline with an award claim - free 3D scan offer - a review - smile gallery - membership club - long descriptive text - "Book a consultation" with the phone number - team, stating languages spoken - treatments. Footer: finance statement naming a credit partner and its regulator; terms, offer terms, privacy, cookies, cancellation policy; six downloadable guides (anxiety, orthodontics, whitening and so on). Extraction: about 143 image references, about 49,900 characters. |
| 4 | https://www.banningdental.co.uk | 2026-11-21 | London multi-clinic group. Navigation split in two: Dental and Skin. Order: headline that this is "more than just a dentist" - philosophy paragraphs - one-stop positioning between public and expensive private care - skin clinic - price-match promise - news - virtual consultation - "we beat any quote" - clinics as a list of names followed by full addresses - featured in - newsletter - reviews - policies - memberships. A callback form protected by a captcha. Extraction: about 38 image references, about 17,200 characters. |
| 5 | https://www.wimpolestreetdental.com | 2026-11-21 | London private practice in the Harley Street area. The extraction opens with a "JavaScript is turned off" notice. Order: headline and several headings using "best" - emergency appointments mentioned early - awards - cosmetic treatments - "Where you can find us" with the address - treatments list - six quoted patient reviews - featured in - a podcast - blog - footer with treatments, contact, and opening hours listed per day. Extraction: about 30 image references, about 8,700 characters. |
| 6 | https://www.thewelbeckclinic.co.uk | 2026-11-21 | London cosmetic dental practice. Two offers appear before the main content: a free "smile simulation" and a free e-consultation, both asking the visitor to fill in a form and upload a photo. Order: headline "cosmetic dentist in London" - long paragraphs including payment-plan mention and the lead dentist - technology as a numbered list - cosmetic techniques as a numbered list (aligners, bonding, whitening, veneers) - two persuasion sections - "Schedule your consultation" - contact. Extraction: about 66 image references, about 10,200 characters. |

Loaded and not used:

| Site | Checked | Why not |
|---|---|---|
| https://www.elleven.co.uk | 2026-11-21 | Loads, but the domain now shows a domain-for-sale page, not a dental practice. |
| https://www.smilepod.co.uk | 2026-11-21 | Loads, but the extraction returned seven short sentences and no structure. |

## 10. Skeletons

Structure only. No colours, logos, photographs or wording were taken from any reference.

### Skeleton A: the family practice (booking-first)

For a general practice whose site has one job: get a new or returning patient to book or call. Default for this domain.
From references 1, 2, 5: the opening and per-location closure dates of 1, the trust points, hours and disclaimer of 2, the per-day hours in the footer of 5. The reduction to one location is the author's.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; one action (book / call); the phone number visible | phone always visible, for people in pain | yes |
| 1 | Opening | one sentence: kind of practice, for whom, where; the main action; a quieter "in pain today?" link | one heading, one line, two actions of different weight | yes |
| 2 | Practical points | four to six one-line facts the practice gave: new patients, children, emergencies, insurers or plans, languages, access | icons or a plain list; one line each | optional |
| 3 | Treatments | categories in order, each with its treatments on one line: name, short note, price or "from" or "after examination" | category heading over rows | yes |
| 4 | Your first visit | what happens, how long, what to bring; a line for anxious patients if the practice has something real to say | short steps | optional |
| 5 | The team | name, profession, speciality, languages | real titles; faces with consent | yes |
| 6 | Payment | insurers, schemes, membership plan, instalments with the provider named | plain list | yes, even if only "ask us" |
| 7 | What patients say | real reviews with source | at most three | optional, off by default |
| 8 | Emergencies | in hours, out of hours, when to go to hospital | its own heading | yes |
| 9 | Find us | address, entrance, access, phone, hours per day, coming closure dates | complete without the map | yes |
| 10 | Footer | registration details, complaints, cancellation policy, privacy, terms, accessibility statement | small | yes |

Image-to-text ratio: **estimate**, from extraction counts only (references 2 and 5 returned about 30 image references against 9,000 to 13,000 characters). Roughly one image per two short text blocks; images are of the rooms and the team, text carries treatments and prices. Not confirmed in a rendered view.

### Skeleton B: the cosmetic or specialist practice (consultation-first)

For a practice whose main work is elective: orthodontics, implants, veneers, whitening. The visitor compares, hesitates and wants proof.
From references 3, 4, 6: the consultation offers of 6, the treatment navigation and finance statement of 3, the two-part navigation of 4.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; "book a consultation"; phone | | yes |
| 1 | Opening | the speciality in one sentence; the consultation action, with its real conditions and price | one action | yes |
| 2 | Treatments | each elective treatment as a card leading to its own page: what it is, how many visits, price "from" with what moves it | cards of equal weight | yes |
| 3 | Proof | the practice's own before-and-after cases with consent, where allowed; otherwise photographs of the rooms and team | images lead here | optional, off by default |
| 4 | The clinicians | names, professions, specialities, training | | yes |
| 5 | The path | consultation, plan and written estimate, treatment, follow-up | numbered steps | optional |
| 6 | Paying | price list link, instalments with the provider named and its conditions, membership | plain | yes |
| 7 | Questions | FAQ from the practice's answers | | optional |
| 8 | Consultation form or phone | few fields; no required medical history; no photo upload by default | | yes |
| 9 | Emergencies, find us, footer | as Skeleton A, sections 8 to 10 | | yes |

Image-to-text ratio: **estimate**. More image-led: references 3 and 6 returned about 143 and 66 image references against about 50,000 and 10,000 characters. Not confirmed in a rendered view.

Risk seen in references 3, 5 and 6: long paragraphs written for search engines, superlatives, and offers stacked before the content. The skeleton keeps their sections and drops that habit.

## 11. Not verified

1. All Hebrew and Arabic terms in section 6: author's knowledge, not checked with a dentist.
2. Every legal statement in section 7. None was checked against a statute, a regulator's guidance or an official source. Advertising rules, patient finance and whitening limits are the least certain.
3. Image-to-text ratios and visual quality of all references: text extraction only.
4. No awwwards.com category was consulted; design quality is the author's prior judgement, and three of the six are not design references.
5. No public-scheme, small-town or children's practice was verified. No reference outside London and New York.
6. Sub-pages (price lists, treatment pages, booking flows) were not fetched. Whether any reference publishes a full price list is not known.
7. The claim that practices almost always run dental software with a diary is the author's belief, not sourced.
8. Whether reference 5 shows content to a visitor without scripts was not tested; only the notice in the extracted text was seen.
9. The hospital-referral wording in rule 1 is a placeholder for the practice's own approved wording, not clinical guidance.
10. No references in Hebrew, Arabic or any non-Latin script.
