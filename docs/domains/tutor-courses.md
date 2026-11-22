# Tutor and courses

Covers: people and small organisations that are paid to teach: private tutors (school subjects, exam preparation, languages, music and other instruments, skills), tutoring agencies and learning centres, and course providers (adult classes, workshops, cookery, language and craft schools, online courses taught live or recorded).
Does not cover: kindergartens and daycare (use `kindergarten.md`); schools and universities as institutions; fitness coaching (use `fitness-trainer.md`); software documentation and help centres (use `product-docs.md`).
Written 2026-11-22. References checked 2026-11-22 (the brief named 2026-11-21; the fetches actually ran on 2026-11-22). Template: [README.md](README.md).

## 1. Objects

This domain sells **progress in a skill, delivered through scheduled time with a teacher**. Two shapes exist and most businesses lean to one:

- **Tutoring**: open-ended, one student (or a few), recurring lessons, matched to a tutor. The first step is a conversation.
- **Courses**: a fixed programme with a start date, a number of sessions, a capacity and a price. The first step is choosing a course and a date.

In both shapes the student is often a child, and then the person who talks, decides and pays is a parent.

### Provider (the business)

| Field | Required | Example (illustrative) |
|---|---|---|
| Name | required | "Bright Path Tutoring", or the tutor's own name |
| Shape | required | private tutor, tutoring agency, learning centre, course provider, online course |
| What is taught | required | maths and physics; English as a foreign language; piano; cookery |
| Levels or exams | required for school subjects | primary, secondary, a named national exam, university entrance |
| Who it is for | required | children of a stated age, teenagers, adults, professionals |
| Where teaching happens | required | at the tutor's address; at the student's home within an area; at a centre address; online; a mix |
| Phone or messaging number | required | |
| How to start | required | message, call, free first call, book a trial lesson, enrol on a course |
| Email | optional | |
| Languages of instruction | optional | |
| Year started, short story | optional | |
| Accreditation, membership of a body | optional, never invented | only what the customer can name and show |

### Location

Address and access note for a centre or the tutor's place; a service area for home visits; "online" with the platform named. A multi-site centre repeats address, hours and phone per location.

### Teacher or tutor (team member)

| Field | Required | Example |
|---|---|---|
| Display name | required | first name is enough |
| Subjects and levels | required | GCSE maths, A-level physics |
| Qualifications and experience | optional, never invented | "qualified teacher, 12 years in schools" only as the customer states it |
| Background check for work with children | optional, never invented | only if the customer confirms it was done |
| Hourly price | optional | some agencies show "from" per tutor (observed 2026-11-22) |
| Availability | optional on the page, required for online booking | |
| Photo | optional | only with consent |
| Short bio | optional | |
| Taking new students | optional | |

A one-person tutor has one teacher, and the Team section becomes About.

### Offer (tutoring)

| Field | Required | Example |
|---|---|---|
| Name | required | "One-to-one lesson", "Small group (up to 4)", "Exam crash course", "Free first call" |
| Subject and level | required | |
| Format | required | in person at the tutor's, at the student's home, at a centre, online live |
| Lesson length in minutes | required for anything bookable | 45, 60, 90 |
| Price | optional, see rule 4 | |
| Price type | required when a price is shown | per lesson, per hour, per pack, per month, "from", "on request" |
| Pack | optional | 10 lessons, valid 3 months |
| Assessment first | optional | a placement or diagnostic test |
| Progress reporting | optional, never invented | monthly written report, only if the customer does it |

### Course (courses)

| Field | Required | Example |
|---|---|---|
| Title | required | "Beginners' Spanish", "Knife skills evening" |
| Short description | required | what the student will be able to do afterwards |
| Subject or category | required | Languages, Cookery, Art |
| Level | required | beginner, intermediate, advanced, all levels |
| Prerequisites | optional | "you can read music", "completed Level 1" |
| Format | required | in person, online live, online recorded, blended |
| Language of instruction | required if not the site's language | |
| Number of sessions and length of each | required | 10 weekly sessions of 2 hours |
| What is included | optional | ingredients, materials, book, certificate |
| What to bring | optional | |
| Age range | required if children may attend | 8-17 |
| Certificate or qualification | optional, never invented | named awarding body only if real |
| Price | optional, see rule 4 | |
| Concessions | optional | reduced price for stated groups, only as the customer states |

### Course run (a dated instance of a course)

| Field | Required | Example |
|---|---|---|
| Course | required | |
| Start date, end date, weekday and time, time zone | required | starts Tue 13 Jan, 18:30-20:30, 10 weeks |
| Teacher | optional | |
| Location or online link | required | |
| Capacity | required | 12 |
| Places taken | derived | |
| Minimum to run | optional | 6; if not reached by a stated date the run is cancelled (rule 9) |
| Booking closes | required | a date or "at the first session" |
| Status | required | open, few places left, full, waitlist, cancelled, running, finished |

### Student, parent and enrolment

| Object | Fields | Notes |
|---|---|---|
| Student | name (required), age or school year (required if a minor), level, needs (optional) | Learning needs or a diagnosis is sensitive data; collected only if the customer decides to |
| Parent or guardian | name, phone, email (required when the student is a minor) | The contact and the payer for a minor |
| Enrolment or booking | student, course run or lesson series, status: enquiry, trial, enrolled, waitlisted, withdrawn, completed, payer, amount paid | |
| Lesson | date, time, teacher, student(s), status: scheduled, cancelled in time, late cancelled, missed, taught, notes | |
| Progress report | student, period, written by, text | Private to the student, parent and teacher |

### Other objects

| Object | Fields | Notes |
|---|---|---|
| Free resource | title, type (exam paper, guide, worksheet), author, file or link | Several references publish free resources and articles written by tutors (observed 2026-11-22). Copyright matters (see Legal) |
| Event or open day | title, date, time, place or online, sign-up | Course providers use webinars and open evenings (observed 2026-11-22) |
| Result claim | what (grades, admissions, pass rate), period, source, how measured | Only real figures with their basis (rule 14) |
| Review | text, first name or initials, relationship (parent, student), date, source, rating with count | Only real reviews |
| Policy | lesson cancellation notice, missed lessons, course refunds, transfers, minimum numbers, safeguarding, recording of online lessons | Each optional; if it exists it is shown before booking |
| Gift voucher | value or course, expiry | Involves payments |
| Accommodation, social programme | for residential language schools | Out of scope beyond a link; see `hotel-guesthouse.md` if it becomes central |

Relations: a course has many runs; a run has many enrolments; an enrolment belongs to one student and, for a minor, one parent. A tutor teaches some subjects and levels. A lesson belongs to one series between a tutor and a student (or a small group).

## 2. Rules

1. Every course belongs to exactly one category and has exactly one level.
2. A course run has a start date, a schedule and a capacity. Confirmed enrolments may never exceed the capacity; this is checked when the enrolment is saved.
3. A course run cannot be booked after booking closes. If late joining is allowed, the run says so.
4. A price is optional, but its absence is explicit: "price on request" or "ask about fees", never blank and never zero. A "free" first lesson or call is free with no hidden commitment.
5. Every price shows its currency and what it is per (lesson, hour, course, month). A course price says how many sessions it covers.
6. A concession price states who qualifies, as the customer defined it.
7. A lesson has a length in positive minutes; a recurring lesson has a weekday, time and time zone.
8. Times are shown in the provider's local time. Online lessons and courses also show the student's local time.
9. If a run has a minimum number and it is not reached by the stated date, every enrolled student is told, and offered a refund or a transfer, before the start date.
10. A cancelled lesson or run tells every affected student (or parent) and stays visible as "cancelled".
11. A lesson cancelled inside the notice window follows the stated policy; the policy is shown before the first booking, not after.
12. A minor is enrolled only with a parent's or guardian's contact and consent. Messages about a minor go to the parent.
13. A claim that tutors are background-checked, qualified teachers, or accredited appears only if the customer confirms it, and names the check or body.
14. A result claim (grade improvements, admissions, pass rates, percentages of satisfied parents) appears only with its period and basis, as supplied by the customer. Never invented and never rounded up.
15. Exam and syllabus names are written exactly as the customer gives them; the product does not guess which exam board or curriculum applies.
16. A certificate is offered only if the customer issues one; a recognised qualification names its awarding body only if real.
17. Progress reports, learning needs and assessment results are visible only to the student, the parent (for a minor) and the teacher.
18. Online lessons are recorded only if the customer says so, and then the student (or parent) is told before the lesson.
19. Free resources are the provider's own or used with permission; past exam papers belong to the exam body unless the customer wrote them.
20. The main action (enquire, book a trial, enrol) is reachable from every page without scrolling back to the top on a phone.
21. The phone number is a tappable link on a phone. A centre address opens a map.
22. Stock photographs of classrooms or students are not presented as the provider's own.

## 3. Mandatory facts

The product is not built until each of these has an answer from the customer. None may be guessed.

| # | Fact | The one question to ask | Why (the human reason) |
|---|---|---|---|
| 1 | Name | "What should the site be called: your own name or a business name?" | Without a name people cannot find you or recommend you. |
| 2 | What you teach | "What do you teach, and at which levels or for which exams?" | A parent decides in seconds whether you cover their child's subject and level. |
| 3 | Who you teach | "Who are your students: children of what age, teenagers, adults?" | A visitor looks for "someone for people like me". Children also bring extra duties. |
| 4 | Where | "Where do lessons happen: your place, the student's home, a centre, or online?" | Without it people do not know if they can come, or if you come to them. A home address may not be meant for the public. |
| 5 | Contact | "What number or address should people use to reach you?" | Without it nobody can ask a question. |
| 6 | How to start | "What should a new student or parent do first: message you, book a first call, book a trial lesson, enrol on a course?" | The whole page leads to this one action. |
| 7 | When | "When do you teach? Or, for courses, when do the next ones start?" | Without it people ask for times you do not work, or miss the start date. |
| 8 | Prices, or the decision not to show them | "What do you charge, per lesson or per course? If you would rather discuss fees, say so." | Price is the first question parents ask. Hiding it is allowed; inventing it is not. |
| 9 | Who is the business legally | "What is the registered name and number, for the legal pages?" | The privacy and terms pages must name who is responsible. |

Needed only when the product takes bookings, enrolments or payments:

| # | Fact | The one question to ask | Why |
|---|---|---|---|
| 10 | Course dates, sessions and places | "For each course: start date, how many sessions, how long each, and how many places?" | Without it a course is overbooked or people enrol for the wrong dates. |
| 11 | Minimum numbers | "Do you cancel a course if too few people sign up? By when do you decide?" | People plan their weeks around a course; they must know early if it will not run. |
| 12 | Cancellation and refunds | "What happens if a student cancels a lesson late, misses one, or drops out of a course?" | The parent or student must know before paying, and you must be able to stand behind it. |
| 13 | Children | "Do you teach anyone under 18? Have you or your tutors had a background check for working with children?" | If yes, a parent must consent and be reachable, and any claim about checks must be true. |
| 14 | Where enquiries and bookings go | "Where should I send each new enquiry or enrolment: which phone or email?" | An enquiry nobody sees is a parent who signs up with someone else tomorrow. |

## 4. Declared defaults

Each default is shown to the customer as "we filled this in - change it if it is wrong". None of them is a fact about the business.

| Default | Value | Why it is safe | How it is marked |
|---|---|---|---|
| Subject groups and order | grouped by level, then subject (for tutoring); by category (for courses) | Seen in the references | Editable list, labelled "suggested order" |
| Missing price | "Fees on request" | Says openly that there is no number | Shown in the customer's review with "no price given" |
| Main action | "Message to ask about lessons", using the contact number | Works with zero setup | Labelled "default: message" |
| Page order | Skeleton A for tutoring, Skeleton B for courses | Extracted from the references | Named as the default skeleton |
| "How it works" steps | headings only: get in touch, first conversation, lessons start | General; content is the customer's | Marked "draft - confirm or change" |
| Course status labels | open, few places left (when 2 or fewer remain), full, cancelled | "Few places" threshold is an estimate | Setting, labelled "default" |
| Booking closes | at the start of the first session | Follows from rule 3 | Setting, labelled "default" |
| Reminder | one message 24 hours before a first lesson or first session | Estimate | Setting, labelled "default"; off until a channel exists |
| Language and direction | the language of the conversation | The customer chose it | Shown, changeable |
| Currency | the currency of the provider's country | Follows from the address | Shown next to every price |
| Time zone | the provider's location | Follows from the address | Shown on every date and time |
| Legal page structure | headings only: who we are, what we collect, children's data, why, how long, your rights, contact | Structure is general; content is not | Marked "draft - not legal advice - review before publishing" |
| Empty optional sections | hidden | Better than empty | Listed for the customer as "not shown yet: reviews, team, resources" |

Never a default, whatever the customer left out: prices, course dates, capacities, minimum numbers, cancellation and refund rules, qualifications, background checks, accreditation, certificates, exam boards and syllabuses, result figures, pass rates, "qualified teachers", "experienced", "guaranteed improvement", reviews, ratings.

## 5. Failure modes

| What went wrong | What the visitor sees | What it costs | Prevention |
|---|---|---|---|
| Course dates old | Enrols for a course that already started or ended | Refund, annoyance | Runs carry dates; finished runs move off the page automatically |
| Stale promotion | Sees an offer whose end date has passed next to a current one | Confusion; misleading price | Promotions carry an end date that hides them. One reference showed an expired discount text alongside a current one (observed 2026-11-22) |
| Course overbooked | More students than seats or cookers | Someone sent home | Rule 2, at save time |
| Course cancelled late for low numbers | Turned away the week it starts | Lost evening plans; refund | Rule 9; mandatory fact 11 |
| Time zone wrong on an online lesson | Joins an hour late or early | Lost lesson, still charged | Rule 8 |
| Messages about a child go to the child | Parent never hears about a change | Missed lessons; safeguarding concern | Rule 12 |
| Invented result claim | Expects a grade jump that does not come | Distrust; misleading advertising | Rule 14 |
| "Qualified" or "checked" claim not true | Trusts a stranger with their child on a false basis | Serious harm risk; legal risk | Rule 13; mandatory fact 13 |
| Wrong exam or syllabus named | Child prepared for the wrong paper | Real harm to the student | Rule 15 |
| Enquiry form fails silently | Thinks they asked; never hears back | Lost student | A failed send says so and shows the phone number |
| Price per hour read as per course, or the reverse | Surprise at the first invoice | Dispute | Rule 5 |
| Progress report or learning need exposed | Sees another child's report | Privacy breach | Rule 17; permissions in section 8 |
| Site only works with JavaScript | Sees a "JavaScript is disabled" notice and little else | Lost visitors on old devices and in some search previews | Serve the course list as plain content; one reference's extracted text begins with such a notice (observed 2026-11-22) |
| Booking link to an external system broken | Taps "Enrol", nothing happens | Silent loss | Check the link at publish and on a schedule |

## 6. Professional language

Hebrew and Arabic terms are the author's knowledge and were not checked with a working teacher in either language. Regional Arabic usage varies. Exam names are national and must come from the customer. Where the cell says "not verified", do not use a guess.

| English | Meaning | Hebrew | Arabic |
|---|---|---|---|
| Tutor, private tutor | teaches one student or a few | מורה פרטי / מורה פרטית | مدرس خصوصي |
| Private lesson | | שיעור פרטי | درس خصوصي |
| Tutoring agency | matches tutors to families | not verified | not verified |
| Learning centre | premises for after-school tuition | מרכז למידה | مركز تعليمي (not verified) |
| Course | fixed programme | קורס | دورة |
| Workshop | short practical session | סדנה | ورشة عمل |
| Lesson | one teaching session | שיעור | درس |
| Group lesson | | שיעור קבוצתי | درس جماعي (not verified) |
| Trial lesson | first lesson to try | שיעור ניסיון | درس تجريبي (not verified) |
| Enrolment, registration | | הרשמה | تسجيل |
| Level | | רמה | مستوى |
| Beginner, intermediate, advanced | | מתחילים, מתקדמים (intermediate: not verified) | مبتدئ, متوسط, متقدم |
| Placement test, assessment | test to find the level | מבחן מיון / אבחון | امتحان تحديد المستوى (not verified) |
| Exam preparation | | הכנה לבחינות | التحضير للامتحانات |
| Matriculation exams (Israel) | national school-leaving exams | בגרות | not verified |
| Homework | | שיעורי בית | واجبات منزلية / وظائف (regional) |
| Syllabus, curriculum | | תוכנית לימודים / סילבוס | منهاج |
| Certificate | | תעודה | شهادة |
| Online lesson | | שיעור אונליין / שיעור מקוון | درس عبر الإنترنت (not verified) |
| Learning difficulties, special needs | | לקויות למידה | صعوبات تعلم |
| Progress report | | דוח התקדמות (not verified) | تقرير تقدم (not verified) |
| Cohort, intake | a group starting together | מחזור | دفعة (not verified) |
| Open day | | יום פתוח | يوم مفتوح |

Notes on language:

- Parents say "lessons" and "how much an hour"; providers say "tuition" and "programmes". Use the parent's words.
- UK and US English differ: tutor/tutoring, maths/math, enrol/enroll, Year 6/sixth grade. Pick one by the provider's country.
- Words to avoid unless the customer said them and can back them: "guaranteed grades", "top tutors", "best", "number one", "100% pass rate", "certified" without naming by whom, "Oxbridge success" or any named-university claim.
- Do not describe a student's diagnosis or needs in public text.

## 7. Legal

A checklist of questions, not legal advice. The author is not a lawyer and did not read the statutes for this file. Every item needs checking by someone qualified in the provider's country before it is relied on.

### Applies almost everywhere

- **Privacy notice.** Needed as soon as the site collects a name and contact.
- **Children's data.** Data about minors is more protected in many places, and online services aimed at children may need a parent's consent below a set age. Default: the product collects a minor's details only through the parent.
- **Learning needs and diagnoses** may be health data. Default: not collected unless the customer decides to, and then private.
- **Safeguarding.** Working one-to-one with children brings duties and expectations (background checks, lesson in a visible place, no private messaging with a child). Which are legal duties and which are good practice differs by country.
- **Terms.** Lesson cancellation, missed lessons, course refunds and transfers, minimum numbers, shown before the parent or student pays.
- **Distance purchases.** Online enrolment may carry a cooling-off right; recorded online courses may have a different rule once access starts.
- **Copyright.** Exam papers, textbooks and worksheets belong to their owners. Recording lessons needs the participants' agreement.
- **Advertising claims.** Results and qualifications must be true and evidenced.
- **Marketing messages** generally need prior agreement.

### Israel

- Accessibility: websites of businesses serving the public must be accessible with an accessibility statement and a contact, under the Equal Rights for Persons with Disabilities Law and its regulations, with Israeli Standard 5568 as the technical reference. Small-business exemptions exist. Not verified in detail.
- Privacy: the Protection of Privacy Law applies; Amendment 13 came into force in August 2025. Not verified for a one-person tutor.
- Work with minors: a law on preventing the employment of sex offenders in certain institutions requires an employer to obtain a police certificate before employing someone to work with minors. Whether it covers a self-employed private tutor, or an agency placing tutors: not verified.
- Private tutoring is not a licensed occupation as far as the author knows; some course types (for example driving lessons) are regulated. Not verified.
- Consumer protection: cancellation of distance transactions with capped fees, and specific rules for cancelling courses and ongoing services. Not verified in detail.
- Displayed consumer prices must include VAT: believed true; not verified. Spam law (section 30A of the Communications Law): not verified in detail.

### European Union and United Kingdom

- GDPR and UK GDPR: children's data needs care; for online services offered directly to children, parental consent is needed below an age set by each country (13 to 16; 13 in the UK). Believed true; details not verified.
- UK: criminal-record checks (DBS) are available for work with children; whether a self-employed private tutor is required to have one: believed not required by law, but expected. Not verified. One reference states its tutors are DBS-checked (observed 2026-11-22).
- UK: English language schools may be accredited by the British Council; one reference states that a low-cost evening offer is not accredited and is taught by trainee teachers (observed 2026-11-22). The accreditation scheme's rules: not verified.
- Cookies: consent for non-essential cookies (ePrivacy, PECR). One reference shows an "if you continue we will assume you are happy" notice (observed 2026-11-22); whether that wording is valid consent under UK rules is believed not, but not verified.
- Distance contracts: 14-day cancellation right for many online purchases; exceptions for leisure services on a specific date and for digital content once access starts with consent. How they apply to a course run or a lesson pack: not verified.
- Accessibility: the European Accessibility Act from June 2025, microenterprise exemption; scope not verified.

### United States

- COPPA (federal) regulates online collection of personal information from children under 13. Believed true; details not verified.
- FERPA covers schools that receive federal funding, not private tutors. Not verified.
- Background checks for tutors are generally a matter of state law and contract. Not verified per state.
- Some states regulate private vocational schools and require approval before offering certain courses. Not verified per state.
- The Americans with Disabilities Act is applied by courts to business websites in many cases; one reference links an accessibility page from its footer (observed 2026-11-22). Not verified.

### What the product does with this

- The product may generate the **structure** of a privacy page (with a children's data heading), terms with cancellation and refunds, a safeguarding statement and an accessibility statement, each marked as a draft that needs review.
- The product never states that the site "complies with" a named law, or that tutors are "checked" or "qualified", unless the customer confirms it (mandatory fact 13).
- The product asks which country the provider is in before generating any legal page.

## 8. Site vs app

### Content pages (no data, no accounts)

Home, subjects and levels, how it works, fees, about the tutor or team, courses as a list with dates, free resources, reviews, where lessons happen, policies, legal pages. With a message link as the only action, this is a complete and honest product for a private tutor.

States still needed on content pages:

| Part | Empty | Error | Notes |
|---|---|---|---|
| Fees | "Fees on request - message us", never an empty table | n/a | Date last updated |
| Course list (static) | "No courses scheduled yet - join the list to hear first" | n/a | Finished runs removed; becomes stale quietly, so prefer data once runs change often |
| Team | hidden; for one person, About instead | | Subjects and levels per person |
| Resources | hidden | broken file link hidden and reported to the owner | Owner's own material only |
| Reviews | hidden | | Never placeholders |
| Where | cannot be empty (mandatory fact) | text address or area remains if a map fails | |

### Needs data

| Part | What it needs | Empty state | Loading | Error | Save | Permissions |
|---|---|---|---|---|---|---|
| Enquiry form | name, contact, student's age or year, subject, message; alerts the provider | n/a | button shows "sending" and cannot be pressed twice | "Not sent - please message us" with the number | "received", and what happens next and when | visitor writes; only the provider reads |
| First-call or trial booking | tutor availability, closures | "No free times this week - message us" | placeholder slots | "Could not load times - message us" | confirmed only after the server saved it | parent sees own; tutor sees own |
| Course catalogue | courses, runs, places, statuses | "No courses in this category right now" | placeholder cards | "Could not load courses - message us" | n/a | public read; owner edits |
| Enrolment | run, student, parent (for minors), payment if any | run full: "Full - join the waitlist" | | place taken meanwhile: "That course just filled up - join the waitlist or pick another date" | confirmed only after saving and payment; confirmation with dates the student can keep | parent or student: own; teacher: own class list; owner: everything |
| Lesson schedule | recurring lessons, cancellations | "No lessons booked" | | | changes saved with who changed them; the other side told | student or parent and tutor; owner |
| Lesson packs | purchases, lessons used, expiry | "No active pack" | | failed payment stated plainly | balance updates after each lesson | parent sees own; owner sees all |
| Progress reports | written by teacher | "No reports yet" | | | dated, not editable after sending except by a new version | student or parent and teacher only |
| Online course delivery | lessons, videos, materials, progress | "Your course starts on <date>" | | video fails: text and materials remain | progress saved per lesson | enrolled students only |
| Owner edits content | edit screen for fees, courses, runs | | | failed save keeps what was typed | public right after saving | owner only; teachers may edit their own runs if the customer wants |
| Reminders | channel and consent | | | failed send shown to the owner | | sent to the parent for minors |

### Needs accounts

- The owner always needs one, as soon as anything is editable or any enrolment is stored.
- Teachers need one only if they manage their own lessons or write reports.
- Parents or adult students need one for packs, recurring lessons, reports and online course access. A single course enrolment can work with an email confirmation.

### Needs payments

- Lesson packs, course fees, deposits, monthly fees, online course purchases, vouchers.
- Each brings refunds, receipts, failed-payment states and consumer law (see Legal), and for minors the payer is the parent.
- Default: no payments. Payments are added only when the customer asks and has answered mandatory facts 11 and 12.

### Using an existing system

Some providers already use a booking calendar, a student-management system or a course platform. One reference offers a consultation booked through an external calendar; another has a "My account" area for enrolled students (observed 2026-11-22). In that case the product links to it and owns no student data. Ask before building a second system.

## 9. References

**How these were checked.** Each URL was fetched on 2026-11-22 with a page-extraction tool that returned the page's text only, with no image references. No browser was used and no screenshot was taken. Section order and wording are observed; visual quality, layout and the image-to-text ratio are **not** observed, and every ratio below is an estimate.

**Curation.** Chosen by the author from known UK and US tutoring and course businesses, not from a search-result list. No awwwards.com category was consulted for this file; none is claimed as an award winner. All seven are in English, in Latin script.

**Limit.** Six of the seven are in the UK and all are established organisations. No single private tutor's own site, no music teacher and no one-person online course was verified. The skeletons are a ceiling for structure, not a picture of the typical customer.

Verified: 7.

| # | Site | Checked | What was observed |
|---|---|---|---|
| 1 | https://www.keystonetutors.com | 2026-11-22 | London tutoring agency. Order: headline and one paragraph covering every stage from primary entrance exams to university admissions - why their tutors are different (employed full-time, matched on subject and personality) - services by exam stage (school entrance, national secondary exams, university entrance, homeschooling) - education consultancy - feedback - a five-step process (consultation, optional assessment, tutor selection, progress monitoring, monthly reports) - articles written by tutors, each with a first name - upcoming webinars. No prices on the home page. |
| 2 | https://www.owltutors.co.uk | 2026-11-22 | UK tutoring agency, enquiry-first. Order: headline (tuition by qualified teachers) - three steps (we recommend a background-checked tutor, a free 20-minute call before any fee, lessons with monthly progress reports) - free resources (past papers written in-house, a school guide, an advice blog) - featured tutors with first name, "from" hourly price, subjects and a short bio - more tutors - parent reviews stated as "published as received", with an on-site score and count and a separate Google score and count - blog - subjects - newsletter with a terms line - cookie notice. |
| 3 | https://www.tutorsinternational.com | 2026-11-22 | Full-time private tutors placed worldwide. Order: about (a search for each placement) - services (full-time, part-time, travelling tutors, specific learning needs) - case studies by country, without client names - testimonials - media mentions - news - contact form and phone. States plainly that its cost may be beyond many families, instead of showing a price. |
| 4 | https://www.mathnasium.com | 2026-11-22 | US maths learning-centre franchise. Navigation: getting started, why us, programmes (catch up, keep up, get ahead; by school stage), FAQ, own a franchise; a phone number; a country selector including an Arabic-language country. Order: "find a center near you" - test-prep banner - "schedule a free assessment" (repeated) - three benefits - parent testimonials with first name, initial and centre - how we are different - how it works in three steps - in-centre and online - results as percentages of parents reporting improvement - a long FAQ, including a cost answer that gives no number - footer with accessibility, privacy, cookie settings, terms. |
| 5 | https://www.citylit.ac.uk | 2026-11-22 | London adult-education college, catalogue-first. The extracted text begins with a "JavaScript seems to be disabled" notice. Order: introduction - discount promotions with their own terms (one of them dated two years earlier than the other) - collections (last places, taster courses, beginners' languages, seasonal) - nine course categories - events and blog - partners - newsletter - "My City Lit" account - map. |
| 6 | https://www.leiths.com | 2026-11-22 | London cookery school. Order: webinar banner with date and time - welcome paragraph naming every offer (schools programme, diploma, professional development, online, careers service) - a chef's quote - food photographs - open evening with date and time - offer tiles - history - "why choose" (career, reputation, teaching, experience) - schools programme - news and dated events - newsletter with a terms-and-privacy consent line - FAQ - footer with full address, phone, email, company registration number and accreditation logos. |
| 7 | https://www.ihlondon.com | 2026-11-22 | London language school. Order: "courses starting every week" with a course link - professional courses - teacher portal - social programme - young-learner summer schools with an age range - teacher training - other languages - exam centre - content hub - low-cost lessons with a starting price and a plain statement that they are not accredited and are taught by trainees - accommodation (homestays and residences, with a note that a third-party agency is sometimes used) - social programme - consultation by phone, in person or video through an external calendar - review-platform badge. |

Loaded and not used: none. All seven sites loaded were usable.

## 10. Skeletons

Structure only. No colours, logos, photographs or wording were taken from any reference.

### Skeleton A: the tutor (enquiry-first)

For a private tutor, a small tutoring team or a learning centre, where the first step is a conversation. Default for tutoring.
From references 1, 2 and 4: the three-step "how it works" of 2 and 4, the tutor cards with subjects and "from" price of 2, the stage-by-stage services of 1, the plain FAQ of 4.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; one action (message / book a first call); reachable on a phone | action most prominent after the name | yes |
| 1 | Opening | one sentence: what is taught, to whom, where; the main action | one heading, one line, one action | yes |
| 2 | Subjects and levels | grouped by level or exam; each a line | list | yes |
| 3 | How it works | three steps: get in touch, first conversation or assessment, regular lessons with feedback | numbered | yes |
| 4 | Fees | per lesson or hour, packs, "from" or "on request"; what is included | short table | yes |
| 5 | About the tutor, or the tutors | first names, subjects, qualifications and checks only as confirmed | cards or one About block | yes |
| 6 | What parents and students say | real reviews with source, count and relationship | at most three | optional, hidden when empty |
| 7 | Free resources | the provider's own guides or papers | list | optional, hidden when empty |
| 8 | Questions | cancellation, missed lessons, online or in person, children and safeguarding | short FAQ | yes if any policy exists |
| 9 | Where | address, area or "online"; availability | | yes |
| 10 | Final action | the main action again | one button | yes |
| 11 | Footer | name, contact; privacy, terms, accessibility statement | small | yes |

Image-to-text ratio: **estimate**. No image references were returned for any reference, so no count exists. Judged from structure: text-led, with one photograph of the tutor or a lesson for every three or four text blocks. Parents read; the page must answer questions. Not confirmed in a rendered view.

### Skeleton B: the course provider (catalogue-first)

For a school or provider that runs dated courses. Use when the customer has courses with start dates.
From references 5, 6 and 7: the collections and categories of 5, the dated events and open day of 6, the "starting every week" and plain accreditation statement of 7, the full footer identity of 6.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; "Find a course" always visible; account link if one exists | | yes |
| 1 | Opening | one line on what the school teaches and to whom; two actions: browse courses, ask a question | two actions | yes |
| 2 | Next starting | the soonest runs with date, length, price and places status | cards with date first | yes |
| 3 | Categories | each category leading to its course list | grid of labels | yes |
| 4 | Collections | beginners, last places, short courses, children's courses | a few labelled groups | optional |
| 5 | Why learn here | teachers, method, accreditation only if real | three or four short points | optional |
| 6 | Open day or webinar | date, time, place or link, sign-up | one block | optional, hidden when none |
| 7 | What students say | real reviews with source | at most three | optional, hidden when empty |
| 8 | Practical | location, access, what to bring, refunds and transfers, minimum numbers | short list | yes |
| 9 | Footer | full name, address, phone, email, registration number; privacy, terms, accessibility statement | small, complete | yes |

Image-to-text ratio: **estimate**, from structure only (no image references returned). One image per course card or category, otherwise text: dates, prices and levels must be readable at a glance. Not confirmed in a rendered view.

## 11. Not verified

1. All Hebrew and Arabic terms in section 6: author's knowledge, not checked with a working teacher in either language. Cells marked "not verified" must not be filled by guessing.
2. Every legal statement in section 7. None was checked against a statute or an official source for this file. In particular: whether Israeli police-certificate rules cover self-employed tutors, UK DBS expectations, the validity of implied cookie consent, US state rules for vocational courses.
3. Image-to-text ratios and visual quality: text extraction only, no image references returned, no rendered view.
4. No awwwards.com category was consulted; design quality is the author's prior judgement.
5. No single private tutor, music teacher, home-visit tutor or one-person online course reference was verified.
6. The "few places left" threshold (2 or fewer) and the 24-hour reminder in section 4 are estimates.
7. External calendar and account links in the references were not followed.
8. Sub-pages (course pages, fees pages, policies) were not fetched; observations are of home pages only.
9. No references in Hebrew, Arabic or any non-Latin script. These come in a later phase.
