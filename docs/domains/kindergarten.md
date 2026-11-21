# Kindergarten

Covers: a place that looks after and teaches children below school age for payment or public funding: nursery, daycare, preschool, kindergarten, family daycare in a home. From babies to about six.
Does not cover: private lessons and after-school courses (use `tutor-courses.md`); a parents' group with no paid care (use `community.md`); primary schools.
Written 2026-11-21. References checked 2026-11-21. Template: [README.md](README.md).

## 1. Objects

A kindergarten sells **a place for one child in one group for a period**. The buyer (the parent) is not the user (the child), and the decision is made on trust: who is with my child, is it safe, what does the day look like. Almost nothing is bought on the spot; the path is enquiry, visit, registration, start date.

### Kindergarten (the business)

| Field | Required | Example (illustrative) |
|---|---|---|
| Name | required | "Little Orchard" |
| Kind of place | required | daycare, nursery, preschool, forest kindergarten, Montessori, family daycare at home |
| Ages accepted, youngest and oldest | required | 3 months to 3 years |
| Address, or "address given after first contact" for a home setting | required | street, number, city |
| Phone | required | a number a parent can call during the day |
| Days and hours of operation | required | Sun-Thu 07:30-16:30, Fri 07:30-12:30 |
| How to enquire or register | required | call, message, enquiry form, visit booking |
| Licence or registration with the authority, and its number | required where the law requires one (see Legal) | |
| Email | optional | |
| Approach or curriculum | optional | play-based, Montessori, outdoor |
| Languages spoken with the children | optional | |
| Outdoor space | optional | "own yard", "daily park visit" |
| Year opened, short story | optional | |

### Location (only when there is more than one)

Address, phone, hours, ages, manager and enquiry link repeated per location. Each location has its own licence, its own groups and its own free places.

### Group (class, room)

| Field | Required | Example |
|---|---|---|
| Name | required | "Babies", "Toddlers", "Pre-K" |
| Age range | required | 12 to 24 months |
| Maximum number of children | optional on the page, required to manage places | 12 |
| Staff in the group | optional | 3 |
| Places free now, or "waiting list" | optional | changes during the year |
| Short description of a day | optional | |

### Programme (schedule option)

| Field | Required | Example |
|---|---|---|
| Name | required | full day, half day, 3 days a week, extended day |
| Days and hours | required | 5 days, 07:30-16:30 |
| Price | optional, see rule 4 | per month |
| Price period | required when a price is shown | per month, per week, per day, per year |
| What the price includes | required when a price is shown | meals, nappies, trips, materials |
| Extra charges | optional | registration fee, late pick-up fee, deposit |
| Public funding or subsidy accepted | optional | which scheme, for which ages |

### Staff member

| Field | Required | Example |
|---|---|---|
| Display name | required | first name is enough |
| Role | required | owner, manager, lead teacher, assistant, cook |
| Group | optional | |
| Qualification | optional; only what the person really holds | early-years diploma, first-aid certificate |
| Photo | optional | only with the person's consent |
| Short bio | optional | |

### Enquiry (only when the product stores enquiries)

| Field | Required | Example |
|---|---|---|
| Parent name | required | |
| Parent phone | required | |
| Parent email | optional | |
| Child's age or month and year of birth | required | to match a group; full date of birth is not needed at this stage |
| Wanted start date | optional | |
| Wanted programme | optional | |
| Message | optional | |
| Status | required | new, answered, visit booked, registered, waiting list, closed |

### Other objects

| Object | Fields | Notes |
|---|---|---|
| Visit (tour, open day) | date, time, places, location | The main step before registration in every reference |
| Daily schedule | time, activity | Arrival, meals, sleep, outdoor time, pick-up |
| Menu | day, meals; kosher, halal, vegetarian, allergy policy | Parents ask about food early |
| Calendar | first and last day of the year, holidays, closure days | Parents plan work around it |
| Policy | sickness, medicine, late pick-up, who may collect a child, settling-in, notice period, photos | Each is optional; one that exists is shown before registration |
| Gallery item | image, caption, consent (required when a child is recognisable) | See rule 9 |
| Review | text, first name or initials, date, source | Only real ones, with source |
| Inspection result or rating | body, rating, date, link to the report | Only when a real one exists; always with its date |
| Registered child | name, date of birth, parents, allergies, medical notes, people allowed to collect | Sensitive. Only in an app with accounts; never on a public site |

## 2. Rules

1. Every group has an age range. Age ranges of groups in one location do not leave gaps the business claims to serve.
2. A child belongs to one group at a time.
3. The number of registered children in a group never exceeds its maximum. When it is full, the group shows "waiting list", not "register".
4. A price is optional, but its absence is explicit: "fees on request", never blank and never zero.
5. A shown price states its period, its currency, and what it includes. Charges on top (registration, deposit, meals) are listed next to it, not hidden.
6. A staff-to-child ratio is stated only if the customer gave it. If the law sets a ratio, the stated one may not be worse than the legal one (see Legal).
7. A licence, registration, inspection rating or accreditation is shown only if it is real and current, with its number or date and the body that gave it.
8. A qualification is shown only for the person who holds it.
9. No photo, name or detail of a child is published without written consent from a parent. Without consent, photos show spaces, materials and hands, not faces.
10. A child's full name is never public. Reviews carry the parent's first name or initials at most.
11. Opening hours are stated per day, with the closed days and the yearly closure periods named.
12. An enquiry is not a registration. The visitor is told so, and told what happens next and when.
13. Medical details, allergies and custody arrangements are never collected through a public enquiry form.
14. Who may collect a child is recorded only inside an app with accounts, and changed only by a parent or the manager.
15. The exact address of a home-based setting may be withheld from the public page if the customer asks; the neighbourhood is shown instead.
16. The main action (enquire, book a visit, call) is reachable from every page on a phone.
17. The phone number is a tappable link. The address opens a map.
18. Stock photographs of children are not presented as this kindergarten's children or spaces.
19. A claim about results ("children read by age four", "school-ready guaranteed") is not written unless the customer said it and stands behind it.

## 3. Mandatory facts

The product is not built until each has an answer from the customer. None may be guessed.

| # | Fact | The one question to ask | Why (the human reason) |
|---|---|---|---|
| 1 | Name | "What is your kindergarten called?" | Parents recommend a place by name. |
| 2 | Kind of place | "How would you describe it to a parent in one sentence: daycare, preschool, a home setting, a special approach?" | A parent decides in seconds whether this is what they are looking for. |
| 3 | Ages | "From what age to what age do you take children?" | Without it a parent of a baby calls a place that starts at three. |
| 4 | Where | "What is the address? If it is in your home, do you want the full address shown or only the neighbourhood?" | Parents choose by distance from home or work. A home address is the owner's private address. |
| 5 | Phone | "What number should parents call or message?" | Without it a parent cannot ask and cannot say they are late. |
| 6 | Days and hours | "Which days are you open, from when to when, and when are you closed during the year?" | Parents build their working day around these hours. |
| 7 | How to start | "What should an interested parent do first: call, fill in a form, come for a visit?" | The whole site leads to this one step. |
| 8 | Places | "Are you taking new children now, for which ages, and from when?" | A parent who is told "full" after a visit feels cheated. |
| 9 | Fees, or the decision not to show them | "What does a month cost and what does that include? If you prefer not to show fees, say so." | It is the first question parents ask. Hiding is allowed; inventing is not. |
| 10 | Licence | "Are you licensed or registered with an authority? What is the number?" | Parents look for it, and in many places it must exist before you may operate. |
| 11 | Who is the business legally | "What is the registered business name and number, for the legal pages?" | The privacy page must name who holds parents' details. |

Needed only when the product stores enquiries or registrations:

| # | Fact | The one question to ask | Why |
|---|---|---|---|
| 12 | Where enquiries go | "Where should I send each new enquiry: which phone or email?" | An enquiry nobody sees is a family that went elsewhere. |
| 13 | Group sizes | "How many children can each group take?" | Without it the product offers a place that does not exist. |
| 14 | Registration terms | "Is there a registration fee or deposit, and what happens if a family cancels before the start?" | The parent must know before paying. |

## 4. Declared defaults

Each default is shown to the customer as "we filled this in - change it if it is wrong".

| Default | Value | Why it is safe | How it is marked |
|---|---|---|---|
| Main action | "Call us", using the phone number | Works with zero setup | Labelled "default: phone" |
| Second action | "Book a visit" as a request the customer confirms by hand | Every reference leads to a visit or enquiry | Labelled "default" |
| Group names | by age: Babies, Toddlers, Preschool | Descriptive, not a claim | Editable list |
| Missing fees | "Fees on request" | Says openly there is no number | Shown in the customer's review as "no fee given" |
| Page order | Skeleton A below | Extracted from the references | Named as the default skeleton |
| Enquiry form fields | parent name, phone, child's age, wanted start month, message | The least data that lets the customer answer | Shown as a list the customer can cut |
| Child photos | off | Consent cannot be assumed | "No faces of children until you confirm you hold parents' consent" |
| Daily schedule section | hidden until the customer gives times | A made-up day is an invented fact | Listed as "not shown yet" |
| Language and direction | the language of the conversation | The customer chose it | Shown, changeable |
| Currency | the currency of the country of the address | Follows from the address | Shown next to every fee |
| Legal page structure | headings only | Structure is general; content is not | "Draft - not legal advice - review before publishing" |
| Empty optional sections | hidden | A missing gallery is better than an empty one | Listed for the customer |

Never a default: ages, hours, fees, ratios, group sizes, free places, licence or inspection status, staff names and qualifications, curriculum claims ("Montessori", "bilingual"), menu, kosher or allergy claims, security measures, reviews, awards, years of experience.

## 5. Failure modes

| What went wrong | What the visitor sees | What it costs | Prevention |
|---|---|---|---|
| Site says "places available", group is full | Visits, is told there is no place | A wasted visit, anger | Mandatory fact 8; date on the availability line; rule 3 |
| Fees shown without what they include | The first bill is higher (meals, registration) | Distrust at the start of a long relationship | Rule 5 |
| Old fees | Quoted a different number on the phone | Looks dishonest | Date on the fee table; yearly prompt before registration season |
| Enquiry saved but nobody told | Waits for a call that never comes | A lost family; the customer never knows | Mandatory fact 12; test the alert at setup; visitor sees "received - we answer within X" only if the customer gave X |
| Child's face published without consent | A parent finds their child online | A serious complaint; possibly a legal one | Rule 9; consent field on each image |
| Closure days not listed | A parent learns in August that the place closes for two weeks | Conflict with working parents | Calendar object; rule 11 |
| Ages unclear | Parents of the wrong age call | Wasted calls on both sides | Mandatory fact 3 in the opening line |
| "Licensed" written with no number | A careful parent cannot check it | Loss of trust; a false claim if untrue | Rule 7 |
| Staff member left, still pictured | A parent asks for a teacher who is gone | Looks neglected | Staff can be hidden without deleting |
| Home address published against the owner's wish | Strangers know where a home daycare is | Safety concern | Rule 15; ask at mandatory fact 4 |
| Health details typed into a public form | Sensitive data arrives by email | A privacy problem for the customer | Rule 13; form says "do not write medical details here" |
| Site in one language in a mixed community | A parent cannot read the hours | Lost families | Ask which languages the parents speak |
| Phone not tappable, map pin wrong | Cannot call, arrives at the wrong gate | Silent loss | Rule 17; ask "which gate do parents use?" |
| Stock photos | The place does not look like the pictures | Distrust on the first visit | Rule 18 |

## 6. Professional language

Hebrew and Arabic terms are the author's knowledge, not checked with a working educator in either language. Arabic usage varies by country. "Not verified" means do not use a guess.

| English | Meaning | Hebrew | Arabic |
|---|---|---|---|
| Kindergarten, preschool | setting for ages about 3 to 6 | גן ילדים | روضة أطفال |
| Daycare, nursery (UK) | setting for babies and toddlers | מעון יום / פעוטון | حضانة |
| Family daycare, childminder (UK) | care for a few children in a home | משפחתון | not verified |
| Private kindergarten | not run by the municipality | גן פרטי | روضة خاصة (not verified) |
| Teacher (kindergarten) | leads the group | גננת / גנן | معلمة روضة / مربية |
| Assistant | supports the teacher | סייעת | مساعدة (not verified) |
| Caregiver (babies) | cares for under-threes | מטפלת | حاضنة (not verified) |
| Group, class, room | children of one age band | קבוצה / כיתה | صف / مجموعة (not verified) |
| Babies / toddlers / preschoolers | age bands | תינוקייה / פעוטות / בוגרים | not verified |
| Registration, enrolment | securing a place | רישום / הרשמה | تسجيل |
| Waiting list | queue for a place | רשימת המתנה | قائمة الانتظار |
| Tuition, fees | the price | שכר לימוד | رسوم / أقساط |
| Registration fee | one-time charge | דמי רישום | رسوم تسجيل |
| Visit, tour | seeing the place before registering | ביקור / סיור היכרות | زيارة |
| Open day | a set day for visits | יום פתוח | يوم مفتوح |
| Settling-in, adaptation | first days with a parent present | ימי הסתגלות | فترة التأقلم (not verified) |
| Daily schedule | order of the day | סדר יום | البرنامج اليومي |
| Long day, extended day | care after the main programme | צהרון | not verified |
| Nap, rest time | sleep during the day | שנת צהריים / מנוחה | قيلولة |
| Staff-to-child ratio | children per adult | יחס צוות-ילדים (not verified as the common phrase) | not verified |
| Licence | permission to operate | רישיון הפעלה / סמל מעון (not verified) | ترخيص |
| Pick-up, collection | taking the child home | איסוף | not verified |
| Curriculum, approach | how the children learn | תוכנית חינוכית / גישה | منهج |
| Play-based learning | learning through play | למידה דרך משחק | التعلم باللعب (not verified) |

Notes on language:

- "Kindergarten" means ages 3 to 6 in most of Europe and Israel, and the first school year (age 5) in the United States. "Nursery" is the UK word for daycare. Pick by the customer's country.
- Parents say "the price" and "a place"; the trade says "tuition" and "enrolment".
- Words to avoid unless the customer said them and can show them: "licensed", "accredited", "Montessori", "certified", "outstanding", "best", "safe" as an absolute, "organic food", "school-ready".
- Do not describe children by diagnosis or ability on a public page.

## 7. Legal

A checklist of questions, not legal advice. The author is not a lawyer and read no statute for this file. Everything needs checking by someone qualified in the kindergarten's country.

### Applies almost everywhere

- **Operating permission.** Caring for young children for payment is licensed, registered or supervised in most countries, usually above a small number of children. The site must not suggest a status the business does not hold.
- **Children's data is the most protected kind.** A child's name with a photo, health or allergy information, and custody arrangements need a parent's consent and careful storage. Default: the public product collects none of it.
- **Photos of children** need a parent's written consent before publication, separately from consent to take them.
- **Privacy notice** as soon as an enquiry form stores a parent's name and phone.
- **Terms** when registration or money is taken online: fees, deposit, notice period, refunds.
- **Marketing messages** to parents generally need prior agreement.
- **Staff vetting** (criminal-record checks for people working with children) exists in many countries. A site may say staff are vetted only if the customer confirms it.

### Israel

- Daycare for babies and toddlers: the Supervision of Daycare Centres for Toddlers Law (2018) requires a licence for settings above a minimum number of toddlers, with rules on ratios, first-aid training and security cameras. Thresholds, the responsible ministry today, and current ratio numbers: not verified.
- Ages 3 to 6: compulsory free education applies from age 3 in public kindergartens; private ones need a licence from the Ministry of Education. Details: not verified.
- Staff: the law preventing the employment of sex offenders in institutions serving minors requires a police clearance for male employees. Scope: not verified.
- Accessibility statement and website accessibility duties, privacy law (including Amendment 13 of 2025), and the consent rule for advertising messages apply as in `hair-salon.md`. Exemptions and details: not verified.
- Fees must be shown including VAT where VAT applies; whether a given kindergarten's fees carry VAT: not verified.

### European Union and United Kingdom

- GDPR and UK GDPR. Children's data and health data need particular care; consent for non-essential cookies. One reference (Bright Horizons UK) lists separate privacy, cookie and GDPR notices in its footer (observed 2026-11-21).
- England: providers caring for children under eight for more than two hours a day must register with Ofsted or a childminder agency and follow the Early Years Foundation Stage framework, which sets staff ratios. Exact ratios and exemptions: not verified. Two UK references display an Ofsted rating; one states the date the rating was correct (observed 2026-11-21).
- England: government-funded childcare hours exist for working parents and for three- and four-year-olds. Current eligibility and hours: not verified.
- Other EU states each have their own licensing and ratios: not verified.

### United States

- Childcare is licensed by each state, with state ratios, group sizes and background checks. Not verified per state.
- COPPA concerns online services collecting data from children under 13; a site used by parents, not children, is usually outside it. Not verified.
- The ADA applies to childcare centres as public accommodations, and is applied by courts to websites in many cases. Not verified.

### What the product does with this

- Asks the country before generating any legal page, and marks every legal page as a draft.
- Never writes "licensed", "registered" or a rating without the number, body and date from the customer.
- Never states that the site "complies with" a named law.

## 8. Site vs app

### Content pages (no data, no accounts)

Home, approach, groups and ages, a day with us, team, fees, calendar, gallery, how to find us, contact, policies, legal pages. With a phone link as the only action this is a complete product for a small kindergarten.

| Part | Empty | Error | Notes |
|---|---|---|---|
| Fees | "Fees on request - call us" | n/a | Shows the school year it applies to |
| Availability | "Ask us about places" | n/a | Never "places available" without a date |
| Daily schedule | section hidden | | |
| Team | section hidden; for one person, About instead | | |
| Gallery | section hidden | broken image hidden | No children's faces without consent |
| Reviews, ratings | section hidden | | Never placeholders |
| Hours and calendar | hours cannot be empty | | |
| Map | address or neighbourhood as text always shown | text and a link remain if the map fails | |

### Needs data

| Part | What it needs | Empty state | Loading | Error | Save | Permissions |
|---|---|---|---|---|---|---|
| Enquiry form | stores the enquiry; alerts the customer | n/a | button shows "sending", cannot be pressed twice | "Not sent - please call", with the number | "Received. This is not a registration." and what happens next | parent writes; only the customer reads |
| Visit booking | visit dates with places | "No visit dates right now - call us" | placeholder, never an empty list that reads as "closed" | "Could not load dates - call us" | "requested" until the customer confirms, unless places are counted live | parent sees own request; customer sees all |
| Waiting list | group, child's age, wanted start | n/a | | | parent is told their request is on the list, with no promised position unless the customer wants one | customer only; a parent sees only their own entry |
| Online registration | child and parent details, programme, terms accepted | group full: waiting list offered | | a failed save keeps what was typed | registered only after the server saved it; parent gets a copy | parent: own child; manager: all; staff: own group |
| Customer edits content (fees, hours, calendar, places) | an edit screen | | | a failed save says so | visible on the site right after saving | owner or manager only |
| Parent area (messages, photos, daily report, who may collect) | accounts for parents and staff | "No updates today" | | never show yesterday's report as today's | every entry carries who wrote it and when | a parent sees only their own child; photos of a group only to that group's parents; staff see their group; owner sees all |

### Needs accounts

- The customer, as soon as anything is editable or stored.
- Staff, only for a parent area or attendance.
- Parents should not need an account to enquire or book a visit. A parent account is justified only for the parent area. One reference (The Learning Experience) advertises daily reports and photos through a parent app (observed 2026-11-21).

### Needs payments

- Registration fee, deposit, monthly fees.
- Each brings receipts, failed payments, refunds on cancellation and the consumer law of the country.
- Default: no payments. Monthly fees are usually collected by standing order or an existing system; ask before building one.

### Using an existing system

Larger settings use childcare-management software for registration, parent messaging and billing. If the customer has one, the product is a content site that links to it, and owns no children's data. That is the safer default.

## 9. References

**How these were checked.** Each URL was fetched on 2026-11-21 with a page-extraction tool that returns text and image references. No browser, no screenshot. Section order and wording are observed; visual quality, layout and image-to-text ratio are not, and every ratio is an estimate from counts in the extracted text.

**Curation.** Chosen by the author from known UK and US childcare providers, not from a search-result list. No awwwards.com category was consulted; none is claimed as an award winner for design. All in English, Latin script. Home pages only.

**Limit.** All six are multi-site groups. No single-site or home-based kindergarten was verified, although that is the typical customer.

Verified: 6.

| # | Site | Checked | What was observed |
|---|---|---|---|
| 1 | https://www.littleforestfolk.com | 2026-11-21 | London outdoor nurseries for ages two to five. Order: name and one-line promise - welcome sentence stating the approach and ages - image run - "Our locations": one block per site with a paragraph and a link - "Enquire about a place" with one enquiry link per location, mentioning the waiting list - one endorsement quote - newsletter - four trust items (inspection rating, awards). The extracted page also shows an unconfigured newsletter block with the site builder's own error text, a live example of a visible setup failure. Extraction: about 29 image references, about 7,500 characters. |
| 2 | https://www.guidepostmontessori.com | 2026-11-21 | International Montessori school network, ages 0 to 6. Order: promotion strip - welcome heading with "find a school near you" - "Who we are" in three short blocks - mission - "Our programs" as three age-band cards, each one sentence and a link - parent reviews with a score and a count - blog - closing call to start. Extraction: about 26 image references, about 17,100 characters, much of it review text. |
| 3 | https://www.brighthorizons.co.uk | 2026-11-21 | UK nursery group. Order: open-day notice strip - "Find your perfect nursery" search as the first action - a directory rating shown with its source and the date it was correct - welcome paragraph with brochure download - childcare funding explained with a guide to download - news - footer with separate privacy, cookie and GDPR notices, a fake-review policy, company number and registered office. Extraction: 5 image references, about 5,200 characters. |
| 4 | https://www.vivvi.com | 2026-11-21 | New York childcare and early-learning campuses. Order: new-campus notice - one-sentence promise (teachers, full-day schedules, rolling admissions) with "Get started" - three difference blocks (quality, flexibility, health and safety) - split "For families" / "For employers" - parent quotes signed with first name and initial - "Where we are": each campus with full address, phone, email and weekday hours in plain text - events - closing call - newsletter. Extraction: 6 image references, about 9,100 characters. |
| 5 | https://www.thelearningexperience.com | 2026-11-21 | US preschool and daycare franchise, 6 weeks to 6 years. Order: headline and sub-headline naming preschool and daycare - trust line with a rating - enrolment link - parent stories signed with first name and initial - programmes as six age-band cards, each with an exact age range and focus areas - four reasons (curriculum, safety and security, qualified teachers, family communication through a parent app) - four steps: find a centre, schedule a tour, meet the team, start. Extraction: about 149 image references including icons, about 22,700 characters. |
| 6 | https://www.fennies.com | 2026-11-21 | UK nursery group. The extraction returned a short page: welcome heading - one-sentence promise for under-fives - four counted facts (nurseries, graduates, years) - "Book a visit" with a phone number and a form promising contact within 24 hours. Thin extraction (about 670 characters, 8 images); used only for the opening and the visit form. |

Loaded and not used:

| Site | Checked | Why not |
|---|---|---|
| https://www.kidoschools.com | 2026-11-21 | Loads, but the extraction returned one sentence and navigation labels. Not enough to describe a structure. |

Tried and failed to load (not counted, not a reference): n-family-club.co.uk.

## 10. Skeletons

Structure only. No colours, logos, photographs or wording were taken from any reference.

### Skeleton A: the single kindergarten (visit-first)

For one setting whose site has one job: get a parent to call or book a visit. Default for this domain.
Adapted from references 1, 4, 5, 6: the age-band cards of 5, the plain-text contact block of 4, the visit form of 6, the trust items of 1. None of the references is a single setting, so the reduction to one location is the author's.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; one action (call / book a visit), reachable on a phone | action most prominent after the name | yes |
| 1 | Opening | one sentence: what kind of place, which ages, where; the main action | one heading, one line, one or two actions | yes |
| 2 | Groups and ages | one card per group: name, exact age range, one sentence; "places" or "waiting list" if the customer gave it | cards of equal weight, in age order | yes |
| 3 | A day with us | daily schedule, food, outdoor time | short timeline or list | optional, hidden when empty |
| 4 | Approach | two or three short blocks: how children learn, safety, contact with parents | heading and two lines each | optional |
| 5 | The people | owner or manager and staff, first names and roles | faces only with consent | optional |
| 6 | Trust | licence number, inspection rating with date and body, real reviews with source | small, factual | required if a licence exists |
| 7 | Hours, calendar, fees | hours per day, closure periods, fees or "on request", what is included | table; fees with period and inclusions | hours yes; fees optional |
| 8 | Visit or enquire | short form or phone, and what happens next | one form, few fields | yes |
| 9 | Find us | address or neighbourhood as text, map link, phone, entrance note | complete without the map | yes |
| 10 | Footer | name, phone; privacy, terms, accessibility statement | small | yes |

Image-to-text ratio: **estimate**, from extraction counts only (references 1, 4 and 6 returned 6 to 29 image references against 700 to 9,000 characters). Roughly one image per section; the opening and the groups carry most of them. Images are of spaces and activity; text carries ages, hours and fees. Not confirmed in a rendered view.

### Skeleton B: several locations (find-your-nearest)

For a group with more than one setting.
From references 1, 2, 3, 4: the location search of 2 and 3, the per-location blocks of 1 and 4.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; "find a location"; enquire | | yes |
| 1 | Opening | one-line promise; location finder or list as the first action | finder is the main action | yes |
| 2 | Who we are | three short blocks | | optional |
| 3 | Programmes by age | age-band cards linking to detail | in age order | yes |
| 4 | Locations | one block per location: name, short paragraph, address, phone, hours, enquire link | each location complete on its own | yes |
| 5 | Proof | rating with source and date; parent quotes with first name and initial | | optional |
| 6 | Funding or fees guide | how payment and public funding work | one paragraph and a link | optional |
| 7 | Closing action | enquire, per location | | yes |
| 8 | Footer | legal notices, company details | | yes |

Image-to-text ratio: **estimate**. Text-led on references 2 to 4 (5 to 26 image references against 5,000 to 17,000 characters); image-led on 5. Not confirmed in a rendered view.

## 11. Not verified

1. All Hebrew and Arabic terms in section 6: author's knowledge, not checked with an educator. Cells marked "not verified" must not be filled by guessing.
2. Every legal statement in section 7. None was checked against a statute or official source. Licensing thresholds, ratios, funding schemes and vetting duties are the least certain.
3. Image-to-text ratios and visual quality of all references: text extraction only.
4. No awwwards.com category was consulted; design quality is the author's prior judgement.
5. No single-site or home-based kindergarten reference was verified. Skeleton A is a reduction made by the author.
6. Only 6 references verified; reference 6 is a thin extraction.
7. Sub-pages (fees, location pages, enquiry flows) were not fetched. Whether any reference shows fees publicly is not known; none did on its home page.
8. The statement that larger settings use childcare-management software is the author's belief, supported only by one reference mentioning a parent app.
9. No references in Hebrew, Arabic or any non-Latin script.
