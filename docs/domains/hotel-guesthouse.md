# Hotel and guesthouse

Covers: a place where people pay to sleep for one night or more: small hotels, guesthouses, bed and breakfasts, inns, rural cabins and holiday units run by their owner.
Does not cover: the hotel's restaurant as a business open to non-guests (use `restaurant.md` for that page); guided trips and day tours (use `tour-guide.md`); weddings and events as the main business (use `wedding.md` or `event.md`); selling or letting property long-term (use `real-estate-agent.md`).
Written 2026-11-21. References checked 2026-11-21. Template: [README.md](README.md).

## 1. Objects

A hotel sells **one room for one night**. A room that was empty last night can never be sold again, and a room sold twice for the same night is a guest with a suitcase and no bed. Everything else follows from that: a price belongs to a date, a booking is a range of nights, and availability must be true everywhere the room is sold.

### Property (the business)

| Field | Required | Example (illustrative) |
|---|---|---|
| Name | required | "Mill House" |
| What kind of place | required | hotel, guesthouse, bed and breakfast, inn, cabins, holiday apartment |
| Address | required | street, number, village, region, country |
| How to get there | optional but nearly always needed | nearest town, last turning, "sat-nav takes you to the wrong gate" |
| Phone | required | and when it is answered |
| Email | required | bookings are confirmed in writing |
| Number of rooms or units | required | 9 |
| How to book | required | on the site, by phone or email, through an outside booking system |
| Check-in from, check-out by | required | from 15:00, by 11:00 |
| Reception hours, or how late arrival works | required | "staffed until 20:00; later by key box" |
| What every stay includes | required | breakfast; breakfast and dinner; nothing |
| Open all year or seasonal | required | closed January |
| Children | optional | all ages; over 12 only; cots on request |
| Pets | optional | "one dog-friendly room; not in the main house" |
| Access | optional | ground-floor room, step-free entrance, lift, adapted bathroom |
| Parking, electric-car charging | optional | |
| Facilities | optional | pool (with its season), sauna, garden, bar |
| Wifi, phone signal | optional | in rural places the lack of signal is information |
| Kosher kitchen, Sabbath arrangements | optional, see rule 20 | only with the certificate or the customer's own description |
| Official classification | optional, see rule 19 | stars or keys from a named body |
| Short story | optional | the building, the owners |

### Room type (or unit)

| Field | Required | Example |
|---|---|---|
| Name | required | "Garden double", "The Hayloft" |
| How many of this type | required | 3; or 1 when every room is unique |
| Sleeps | required | 2 adults; 2 adults and 1 child |
| Beds | required | one double; two singles; double plus sofa bed |
| Bathroom | required | private in the room; private across the hall; shared |
| Size | optional | 22 square metres |
| Floor and access | optional | first floor, no lift |
| View, outside space | optional | |
| What is in the room | optional | bath or shower, kettle, desk, air conditioning, heating |
| Pets allowed in this room | optional | |
| Photographs | required for a room that can be booked online | of this room, not of another |
| Base price | optional, see rule 3 | "from 180 per night" |
| Currently bookable | required, default yes | a room can be closed for repair without being deleted |

### Rate (the price of a room type on a date)

| Field | Required | Example |
|---|---|---|
| Room type | required | |
| Date or season | required | weekends in July-August; 24-31 December |
| Price | required | 220 |
| Per what | required | per room per night; per person per night |
| For how many guests | required | for 2; extra adult +40 |
| What is included | required | breakfast; breakfast and dinner |
| Taxes and fees included or added | required | "includes VAT; tourist tax 2 per person per night paid on arrival" |
| Minimum nights | optional | 2 at weekends |
| Arrival-day restriction | optional | "Sunday arrival only" for a package |
| Cancellation terms for this rate | required | free until 7 days before; non-refundable |

### Booking (only when the product takes bookings)

| Field | Required | Example |
|---|---|---|
| Room type, and the specific room once assigned | required | |
| Arrival date and departure date | required | nights are derived |
| Adults, children with ages | required | ages matter for beds and price |
| Lead guest name, phone, email | required | |
| Arrival time | optional | needed when reception is not staffed all day |
| Requests | optional | cot, ground floor, dog, dietary needs for an included dinner |
| Total price, with what it includes and excludes | required | shown before confirming and stored as shown |
| Deposit paid, balance due and when | required | |
| Cancellation terms that applied at booking | required | stored with the booking, not looked up later |
| Source | required | own site, phone, an outside channel |
| Status | required | requested, confirmed, cancelled by guest, cancelled by property, checked in, checked out, no-show |

### Other objects

| Object | Fields | Notes |
|---|---|---|
| Availability | per room type per night: how many are free | The one thing that must be true. One source only |
| Closure or block | room or whole property, date range, reason | Repairs, owner's use, private hire, off season |
| Package or offer | name, nights, arrival-day rule, what is included, price for how many, dates it runs, exclusions, deposit rule | Reference 3 states all of these for each offer |
| Extra | name, price, per stay or per night or per person | Dinner, cot, dog fee, late check-out, parking |
| Whole-property hire | capacity, minimum nights, enquiry contact | An enquiry, not a booking |
| Restaurant, bar, treatments, activities | own hours, own booking, open to non-guests or not | Each is a small business inside the property; see `restaurant.md` |
| Event at the property | date, name, price | References 3, 4 and 7 list dated events |
| Nearby | walks, beaches, towns, with distance | Content. Distances as the customer states them |
| Frequently asked question | question, answer | Reference 2 answers "what is included", "how do I book" and practical details this way |
| Gift voucher | value or a named stay, expiry | Involves payments |
| Review, award, press | text, source, year | Only real ones, with source |

## 2. Rules

1. A booking has an arrival date and a departure date, and departure is after arrival.
2. A room cannot be confirmed for a night on which it is already confirmed or blocked. This is checked when the booking is saved, across every place the room is sold.
3. A room type may show a "from" price. A "from" price is a real price for a real date, and the page says what it is for (per room, per night, for two).
4. Before the guest confirms, the total price is shown: all nights, all guests, and every charge that cannot be avoided. A charge that is only payable on arrival (a local tourist tax) is named with its amount.
5. Every price shows its currency and says per room or per person, per night or per stay.
6. What the price includes is stated: breakfast, dinner, parking, use of facilities. "Breakfast included" is never assumed.
7. The number of guests in a booking cannot exceed what the room sleeps. Children's ages are asked when beds or prices depend on them.
8. A minimum-nights rule and an arrival-day rule are applied when dates are chosen. A stay that breaks one is refused with the reason and the nearest stay that fits.
9. The cancellation terms are shown before confirming, in dates and amounts ("free until 14 June; after that the first night is charged"), and are stored with the booking.
10. If a deposit is taken, the guest sees how much, when the balance is due, and whether the deposit is refunded on cancellation.
11. Check-in and check-out times are stated. If nobody is at reception after a certain hour, the page says how a late guest gets in.
12. A booking cannot start in the past. Same-day booking is allowed only up to a stated hour.
13. Seasonal closure is stated. No night is offered inside it.
14. Facilities with their own season or hours state them (a pool open May to October).
15. A room's photographs are of that room or that room type. A photograph of the best suite does not illustrate the cheapest room.
16. Access is described in facts (steps, lift, door width, bathroom) and only as the customer stated them. The word "accessible" is not used on its own.
17. A rule about children or pets is stated before booking, with any fee.
18. A package states its nights, its arrival day, what is included, for how many people, the dates it runs, and what it excludes.
19. Stars, keys or any classification are shown only when awarded by a named body, with the body named. The product never assigns stars.
20. Kosher kitchen and Sabbath arrangements are shown only with the certificate or in the customer's own words.
21. A review, a rating or an award carries its source and year. A rating shows its count.
22. A whole-property enquiry and an events enquiry are not bookings until the property confirms.
23. A cancelled booking frees its nights at once. The record stays.
24. The confirmation sent to the guest repeats: dates, room, guests, total, what is included, what is still to pay and when, cancellation terms, check-in time, address and how to arrive.
25. The main action is "check availability" or "book", or "call" or "email" where bookings are taken by hand. It is reachable from every page on a phone.
26. The phone number is a tappable link. The address opens a map.

## 3. Mandatory facts

The product is not built until each of these has an answer from the customer. None may be guessed.

| # | Fact | The one question to ask | Why (the human reason) |
|---|---|---|---|
| 1 | Name | "What is the place called?" | Without a name people cannot find it or recommend it. |
| 2 | What kind of place | "Is it a hotel, a guesthouse, a bed and breakfast, cabins? How many rooms?" | Someone wanting a quiet house of five rooms and someone wanting a hotel with a night desk are looking for different things. |
| 3 | Where, and how to arrive | "What is the full address? Is there anything people get wrong on the way?" | A guest arrives tired, often in the dark, often without signal. Without clear directions the stay starts badly. |
| 4 | Phone and email | "What number and email do guests use, and when is the phone answered?" | A guest who is lost or late at night needs a number that someone answers. |
| 5 | The rooms | "Describe each room or room type: how many people it sleeps, which beds, private or shared bathroom, which floor." | People choose a room by who is travelling. A family of four sent to a room for two has nowhere to sleep. |
| 6 | Prices, or the decision not to show them | "What does each room cost per night? Does it change by season or weekend? If you prefer 'price on request', say so." | Price is the first filter. Hiding it is allowed; inventing it is not. |
| 7 | What the price includes | "Is breakfast included? Dinner? Are there any charges on top, such as a tourist tax or a cleaning fee?" | A bill higher than the page said is the most common complaint in this domain. |
| 8 | How to book | "How do guests book today: on a booking system, by phone or email, through outside sites?" | The whole site leads to this one action. If you also sell on outside sites, two calendars can sell the same night twice. |
| 9 | Check-in and check-out | "From what time can guests arrive, by when must they leave, and what happens if someone arrives late at night?" | A guest at a locked door at 22:00 is the picture of a ruined holiday. |
| 10 | Cancellation | "If a guest cancels, what do they pay, depending on how early they cancel?" | The guest must know before booking, and you must be able to stand behind it. |
| 11 | When you are open | "Are you open all year? Any weeks you close?" | Without it people plan a trip around a closed house. |
| 12 | Children and pets | "Do you take children of any age? Dogs? Any limits or fees?" | A family or a dog owner needs this before anything else. Being turned away on arrival is unforgivable. |
| 13 | Who is the business legally | "What is the registered business name and number, for the legal pages?" | The privacy and terms pages must name who is responsible. |

Needed only when the product takes bookings itself:

| # | Fact | The one question to ask | Why |
|---|---|---|---|
| 14 | One calendar | "Where is the one true calendar of which room is free on which night? Who updates it when a booking comes by phone or from another site?" | Two calendars are how one room gets two guests. |
| 15 | Deposit and payment | "Do guests pay everything at booking, a deposit, or on arrival? By what means?" | Money taken without a clear rule becomes a dispute. |
| 16 | Minimum stay | "Is there a minimum number of nights, at weekends or in season?" | A one-night Saturday booking can block a whole weekend. |
| 17 | Where booking alerts go | "Where should I send each new booking and each cancellation: which phone or email, and who reads it?" | A booking nobody saw is a guest arriving to an unmade room, or no room. |

Needed only in some cases:

| # | Fact | The one question to ask | Why |
|---|---|---|---|
| 18 | Access | "Is there a room someone using a wheelchair can reach and use? Tell me the facts: steps, door, bathroom." | A wrong "accessible" strands a guest. Facts let them judge for themselves. |
| 19 | Classification and certificates | "You mentioned stars (or kosher). Who awarded it and when?" | These are promises made by someone else. Without the source the product does not show them. |

## 4. Declared defaults

Each default is shown to the customer as "we filled this in - change it if it is wrong". None of them is a fact about the business.

| Default | Value | Why it is safe | How it is marked |
|---|---|---|---|
| Main action | "Email or call to book", using the given contact | Works with zero setup and cannot double-book | Labelled "default: we confirm each booking by hand" |
| Booking mode when online booking is wanted | request; the property confirms | Cannot sell a night twice | Labelled "default" |
| Price display | per room, per night, for two guests | The common form in the references that show prices | Shown next to every price; changeable |
| Missing price | "Price on request" | Says openly that there is no number | Listed as "no price given" |
| Night count | departure date minus arrival date | Definition, not a guess | Not changeable |
| Longest stay bookable online | 14 nights | Estimate | Setting, labelled "default" |
| How far ahead | 12 months | Estimate | Setting |
| Same-day booking | off | A room may not be ready | Setting |
| Page order | Skeleton A below | Extracted from the references | Named as the default skeleton |
| Practical questions block | headings only: what is included, how to book, arrival and departure, children, pets, access, parking | Structure seen in reference 2; the answers are facts | Each empty answer is listed for the customer |
| Language and direction | the language of the conversation; guests' languages are asked | The customer chose it by speaking it | Shown, changeable |
| Currency | the currency of the property's country | Follows from the address | Shown next to every price |
| Legal page structure | headings only | Structure is general; content is not | Marked "draft - not legal advice - review before publishing" |
| Empty optional sections | hidden | A missing gallery is better than an empty one | Listed as "not shown yet: offers, events, nearby, press" |

Never a default, whatever the customer left out: prices, taxes, what is included, check-in and check-out times, cancellation terms, deposit, minimum stay, number of rooms, beds, room size, views, "sea view", "quiet", "accessible", "family friendly", "pet friendly", "free parking", "free wifi", "air-conditioned", distances to places, stars, awards, reviews, photographs.

## 5. Failure modes

| What went wrong | What the visitor sees | What it costs | Prevention |
|---|---|---|---|
| The same night sold twice (two calendars, or a phone booking not entered) | Arrives with luggage; the room is taken | The worst case in this domain: a relocation at the property's cost, and a public review | Rule 2; mandatory fact 14; default is request mode |
| Booking saved but the property never told | Arrives; nobody expects them | The same | Mandatory fact 17; status "requested" until confirmed; test the alert at setup |
| Total at the desk higher than the total online | Feels cheated on the first evening | Dispute, chargeback, review | Rule 4; mandatory fact 7 |
| "From" price that no real date has | Clicks through and finds every date dearer | Distrust | Rule 3 |
| Room photographs are of a better room | Opens the door to a smaller, darker room | Complaint, refund | Rule 15 |
| Bed set-up wrong (one double for two colleagues; no bed for the child) | Nowhere suitable to sleep | A move or a refund | Mandatory fact 5; rule 7 |
| Shared bathroom not stated | Finds out in the corridor | A bad review | Room type field "bathroom" is required |
| Late arrival, nobody at reception, no instructions | Stands at a locked door at night | A ruined stay; sometimes a hotel bill elsewhere | Rule 11; mandatory fact 9; arrival time asked at booking |
| Cancellation terms unclear or changed after booking | Is charged and did not expect it | Dispute, chargeback | Rule 9; terms stored with the booking |
| Minimum stay not applied | A one-night booking blocks a weekend | Lost revenue; or a cancelled guest | Rule 8; mandatory fact 16 |
| Seasonal closure or a private hire not blocked | Books nights when the house is shut or full | A cancelled trip | Rule 13; closure object |
| "Accessible" written loosely | A wheelchair user cannot enter the bathroom | A stranded guest | Rule 16; mandatory fact 18 |
| Dog or child rule not stated | Turned away or charged on arrival | Anger, refund | Rule 17; mandatory fact 12 |
| Included dinner is a set menu and dietary needs were not asked | Nothing the guest can eat | A spoiled evening | Ask at booking when a meal is included (reference 2 asks in advance) |
| Pool, sauna or restaurant closed that season or day | The reason they came is shut | Disappointment, refund request | Rule 14 |
| Directions follow the map pin to the wrong gate | Lost in the dark with no signal | A bad start; calls at midnight | Mandatory fact 3; directions in the confirmation |
| Confirmation email missing or vague | Is not sure the booking exists | Calls, double bookings elsewhere | Rule 24 |
| Stars shown without a body | Expects a standard the place does not claim | Misleading-advertising exposure | Rule 19 |
| Time zone or date format confusion (3/4 read as March or April) | Arrives on the wrong day | A lost night | Dates always written with the month as a word |
| Site in one language where guests are tourists | Cannot read the terms | Lost bookings | Ask which languages the guests speak |

## 6. Professional language

Hebrew and Arabic terms are the author's knowledge and were not checked with a working hotelier in either language. Arabic usage varies by region. Where a cell says "not verified", do not use a guess.

| English | Meaning | Hebrew | Arabic |
|---|---|---|---|
| Hotel | | מלון / בית מלון | فندق |
| Boutique hotel | small, individually designed | מלון בוטיק | فندق بوتيك |
| Guesthouse | a small, owner-run place to stay | בית הארחה | بيت ضيافة / نُزُل |
| Bed and breakfast | a room with breakfast | לינה וארוחת בוקר | مبيت وإفطار |
| Rural cabin or holiday unit | in Israel, the common small-accommodation form | צימר | not verified |
| Hostel | shared rooms | אכסניה | نُزُل شبابي (not verified) |
| Room | | חדר | غرفة |
| Suite | a room with a separate sitting area | סוויטה | جناح |
| Double room | one large bed | חדר זוגי | غرفة مزدوجة |
| Twin room | two separate beds | חדר עם שתי מיטות נפרדות | غرفة بسريرين منفصلين |
| Family room | sleeps parents and children | חדר משפחתי | غرفة عائلية |
| En suite | bathroom inside the room | חדר רחצה צמוד (not verified) | حمّام خاص |
| Sleeps | how many people a room takes | מתאים ל-N אורחים | يتّسع لـ N أشخاص (not verified) |
| Night | the unit sold | לילה | ليلة |
| Rate | the price for a room on a date | תעריף | سعر |
| Availability | which nights are free | זמינות / חדרים פנויים | التوفّر (not verified) |
| Booking, reservation | | הזמנה | حجز |
| Check-in / check-out | arrival and departure times | צ'ק-אין / צ'ק-אאוט; קבלת חדר / פינוי חדר | تسجيل الوصول / تسجيل المغادرة |
| Reception, front desk | | קבלה | الاستقبال |
| Breakfast included | | כולל ארוחת בוקר | يشمل الإفطار |
| Half board | breakfast and dinner | חצי פנסיון | نصف إقامة |
| Full board | all three meals | פנסיון מלא | إقامة كاملة |
| Room only | no meals | לינה בלבד | مبيت فقط (not verified) |
| Minimum stay | fewest nights bookable | מינימום לילות | حدّ أدنى لعدد الليالي (not verified) |
| High season / low season | | עונת שיא / מחוץ לעונה | موسم الذروة / خارج الموسم |
| Midweek / weekend | | אמצע שבוע / סוף שבוע | وسط الأسبوع / نهاية الأسبوع |
| Deposit | part payment in advance | מקדמה | عربون / دفعة مقدّمة |
| Cancellation policy | | מדיניות ביטול / דמי ביטול | سياسة الإلغاء |
| Non-refundable | | ללא החזר כספי | غير قابل للاسترداد |
| No-show | booked and did not arrive | אי-הגעה | عدم الحضور (not verified) |
| Occupancy | how many guests in a room; also how full the property is | תפוסה | نسبة الإشغال |
| Cot (UK), crib (US) | a baby's bed | עריסה / מיטת תינוק | سرير أطفال |
| Extra bed | | מיטה נוספת | سرير إضافي |
| Tourist tax, city tax | a local charge per person per night | מס תיירות (not verified as an Israeli term) | ضريبة سياحية (not verified) |
| Exclusive use, buyout | hiring the whole property | סגירת מתחם (not verified) | not verified |
| Channel manager | software that keeps one calendar across sales sites | not verified | not verified |
| Overbooking | more bookings than rooms | אוברבוקינג / רישום יתר | حجز زائد |
| Parking | | חניה | موقف سيارات |
| Pool | | בריכה | مسبح |

Notes on language:

- UK and US English differ: ground floor / first floor (the same floor), cot / crib, lift / elevator, en suite / private bath, half board / "breakfast and dinner included". Write for the guests the customer expects.
- "Double" and "twin" are trade words that guests confuse. Say "one large bed" or "two single beds".
- Dates: write the month as a word. Never 3/4.
- Words to avoid unless the customer said them and can back them: "luxury", "five-star", "boutique", "best", "quiet", "secluded", "sea view", "minutes from", "accessible", "eco", "sustainable", "family friendly", "pet friendly".

## 7. Legal

A checklist of questions, not legal advice. The author is not a lawyer and did not read the statutes for this file. Every item needs checking by someone qualified in the property's country before it is relied on.

### Applies almost everywhere

- **Total price.** Many jurisdictions require the first price shown to include all mandatory charges, or prohibit adding them late in the booking.
- **Cancellation.** Accommodation booked for specific dates is commonly excluded from the general right to cancel an online purchase, so the property's own terms decide. They must be shown before payment.
- **Privacy notice.** A booking collects names, contact details, dates of travel, sometimes passport details and children's ages. A notice is needed, and data should be kept no longer than the law and the booking require.
- **Guest registration.** Many countries require accommodation to record guests' identity, and some to report foreign guests to the authorities. The product does not do this and says so.
- **Payment data.** Card details are handled by a payment provider, never stored by the product.
- **Operating a place to stay** needs registration or a licence, fire-safety compliance and insurance. Short-term letting of homes is restricted in many cities. The product checks none of it.
- **Classification** (stars) is official in some countries and not in others. Showing stars without the award is misleading.
- **Reviews** must be real. Several jurisdictions now prohibit fake or selectively shown reviews explicitly.
- **Accessibility information** should be factual.
- **Marketing messages** need prior agreement. A booking confirmation and pre-arrival information are not marketing.

### Israel

- VAT on accommodation for foreign tourists has had a special (zero-rate) treatment, and its future has been under discussion. Current state, and how prices should be shown to Israeli and foreign guests: not verified.
- Prices shown to consumers must be the total including VAT (Consumer Protection Law). Not verified for accommodation specifically.
- Cancelling a distance transaction: the Consumer Protection Law has specific provisions for accommodation, including a period before the stay after which cancellation rights do not apply. The exact days and capped fee: not verified.
- Hotel star rating is run by the Ministry of Tourism and is voluntary. Whether a non-rated place may use the word "stars": not verified.
- Business licence: accommodation requires one above a certain size; small rural units have had a lighter track. Details: not verified.
- Kosher: presenting a kitchen as kosher without a certificate is prohibited under the Kosher Fraud Prohibition Law. Not verified as to who certifies.
- Accessibility: service-accessibility regulations apply to accommodation and to websites, with an accessibility statement required; exemptions by turnover. Details: not verified.
- Privacy: the Protection of Privacy Law applies; Amendment 13 came into force in August 2025. Not verified as to what a small guesthouse must do.
- Safety of pools and of rural units (railings, hot tubs): regulations exist. Not verified.

### European Union and United Kingdom

- GDPR and UK GDPR apply to booking data. Consent is needed for non-essential cookies.
- Distance-selling rules: the right to withdraw does not apply to accommodation for a specific date. Believed true in both; not verified.
- Package travel: selling a stay together with transport or another significant tourist service can make the seller an organiser with heavy duties (EU Package Travel Directive 2015/2302; UK Package Travel Regulations 2018). Whether a stay with an included dinner, a workshop or an activity counts: not verified. This matters for the offers seen in reference 3.
- Guest registration: Schengen-area accommodation must have foreign guests complete and sign a registration form. National rules differ. Not verified.
- Tourist tax: charged by many municipalities per person per night, often payable on arrival. Not verified per place.
- UK: from April 2025 the Digital Markets, Competition and Consumers Act prohibits showing a headline price without mandatory fees ("drip pricing") and prohibits fake reviews. Believed true; not verified.
- EU: the Omnibus Directive requires traders who show reviews to say whether and how they check them. Not verified.
- Short-term rental registration: an EU regulation on data collection for short-term rentals applies from 2026; many cities have their own registration numbers that must be shown. Not verified.
- European Accessibility Act, from June 2025, covers e-commerce with a microenterprise exemption. Whether a small property's booking page is in scope: not verified.
- Fire-safety law applies to all paying-guest accommodation in the UK, including small bed and breakfasts. Not verified.

### United States

- A federal rule on unfair or deceptive fees, in force from May 2025, requires short-term lodging prices to show the total including mandatory fees up front. Believed true; not verified.
- Lodging taxes are set by state, county and city and are added to the room price. Not verified per place.
- The Americans with Disabilities Act requires places of lodging to describe accessible features in enough detail and to let accessible rooms be booked in the same way as others. Not verified. One reference, Hotel San Jose, labels its links with their behaviour ("opens in a new window") and its video with "does not have audio" (observed 2026-11-21).
- Short-term rental permits are local. Not verified.
- Privacy is by state. Not verified.

### What the product does with this

- The product asks which country the property is in, and where most guests come from, before generating any legal page or price format.
- The product may generate the **structure** of booking terms, a privacy page and an accessibility statement, each marked as a draft that needs review. It never writes the cancellation terms themselves.
- The product never shows stars, never writes "licensed", "accessible" or "complies with", and never states that taxes are included unless the customer said so.

## 8. Site vs app

### Content pages (no data, no accounts)

Home, rooms, what is included, food, things to do, getting here, practical questions, gallery, offers as information, legal pages. With "email or call to book" this is a complete and honest product for a small guesthouse. Reference 4 presents itself in six paragraphs of plain text.

States still needed on content pages:

| Part | Empty | Error | Notes |
|---|---|---|---|
| Rooms | cannot be empty (mandatory fact) | broken image hidden | A room with no photograph is shown with its facts, not with someone else's picture |
| Price | "price on request" | n/a | Always says per room or per person, per night, and what is included |
| Practical questions | an unanswered question is hidden and listed for the customer | | Check-in, check-out and cancellation cannot be hidden |
| Map and directions | address and written directions always shown | if the map fails, the text and a link remain | |
| Offers, events, press | section hidden | | An offer past its end date is not shown |

### Needs data

| Part | What it needs | Empty state | Loading | Error | Save | Permissions |
|---|---|---|---|---|---|---|
| Booking request (property confirms by hand) | stores dates, guests, room wish; alerts the property | n/a | button shows "sending" and cannot be pressed twice | "Not sent - please email or call" with both | "This is a request. We will confirm by email. Nothing is booked yet." | guest sees own request through a link; property sees all |
| Availability calendar | per room type per night, from the one true calendar | no free nights in the chosen month: "Nothing free in August - nearest free dates" | a placeholder, never a blank month that reads as "fully booked" | "Could not load availability - email us" | n/a | everyone reads; only the owner writes |
| Live booking with payment | rooms, rates, restrictions, closures, existing bookings, a payment provider | dates break a rule: say which rule and offer the nearest stay that fits | | room taken meanwhile: "Those dates were just booked - nearest free dates"; payment failed: "Nothing was charged" | confirmed only after payment and save; confirmation as rule 24 | guest: own booking; staff: arrivals and departures; owner: everything |
| Change or cancel by the guest | a link in the confirmation, no password | no booking found: say so, show the contact | | link expired: show the contact | the terms stored with the booking decide the amount; nights are freed at once; the property is alerted | only through the personal link |
| Arrivals and departures list | today's and tomorrow's guests, with requests and arrival times | "No arrivals today" | | never show a stale list without saying so | each change saved at once, with who made it | staff, behind a login |
| Owner sets rates, blocks, closures | a calendar the owner can edit | | | a failed save keeps what was entered and says so | public at once | owner only |
| Bookings from outside channels | a connection that brings them into the same calendar | | | a failed sync is shown to the owner at once, in words | | owner only |
| Enquiry form (whole property, events) | stores it; alerts the property | n/a | button cannot be pressed twice | "Not sent - please email" | "received - this is an enquiry, not a booking" | visitor writes; only the property reads |
| Table, treatment or activity booking | its own hours and capacity | | | | separate from the room booking unless the customer links them | as the room booking |
| Newsletter signup | an address and proof of agreement | | | | says what will be sent and how to stop | owner only |

### Needs accounts

- The owner needs one as soon as a booking is stored or a rate is editable.
- Staff need one if someone else handles arrivals.
- Guests do not need one. A link in the confirmation is enough.

### Needs payments

- Deposits, full prepayment, card guarantees, vouchers, extras.
- Each brings refunds under the stored cancellation terms, receipts, failed-payment states, and tax handling that may differ by the guest's country.
- Default: no payments; the property takes payment by its own means after confirming.

### Using an existing booking system

Many small properties already use an outside reservation system, and several references send "Book" to one (reference 7 marks its booking links as opening in a new window). In that case the product is a content site, the main action is that link, and the product owns no availability. Ask before building a second calendar: a second calendar is the cause of double bookings. The failure mode is the link breaking silently, or the link opening the system's front page instead of this property.

## 9. References

**How these were checked.** Each URL was fetched on 2026-11-21 with a page-extraction tool that returns the page's text and image references. No browser was used and no screenshot was taken. So: section order and wording are observed; visual quality, layout and the image-to-text ratio are **not** observed, and every ratio below is an estimate from counts in the extracted text. Image counts include logos, icons and slideshow frames. Some extractions omit navigation and footers.

**Curation.** Chosen by the author from known independent hotels and guesthouses in the UK and the US, not from a search-result list. No awwwards.com category was consulted for this file (awwwards.com/websites/hotel-restaurant is the category to consult in the next pass); none of these is claimed as an award winner. All are in English, in Latin script.

**Limit.** All eight are design-conscious, higher-priced places in two countries. No budget guesthouse, no bed and breakfast with three rooms and a phone, and no property outside the UK and the US was verified. The skeletons are a ceiling for structure, not a picture of the typical customer.

Verified: 8.

| # | Site | Checked | What was observed |
|---|---|---|---|
| 1 | https://www.thepighotel.com | 2026-11-21 | UK group of country hotels built around their restaurants. Order: "come and stay a while" - one paragraph of identity - six short statements, one each for food, beds, treatments, nature, gatherings and visiting without staying - a seasonal block - the restaurant and its sourcing rule - bars and lounges for drop-in guests - locations - what can be booked - stories. No prices and no room list on the group home page; each hotel has its own pages. Extraction: 24 images, about 2,800 characters. |
| 2 | https://www.killiehuntly.scot | 2026-11-21 | Scottish farmhouse with five rooms. Order: name and one paragraph of place - Our rooms (number of rooms, the honesty bar) - Our food (three short paragraphs; meals are part of the stay) - Things to do - occasions and whole-house hire - the estate - **practical questions as expandable headings: what is included in my stay (breakfast, a set dinner at a shared table, a packed lunch, sauna); how do I book (online, or a phone number and an email); other helpful information (car charging, tell us dietary needs in advance because dinner is a set menu, check-in from and check-out by, which single room takes dogs)** - related properties - contacts by purpose. Extraction: 13 images, about 6,200 characters. |
| 3 | https://www.glebehousedevon.co.uk | 2026-11-21 | English guesthouse with a restaurant and smallholding. Order: one-line identity as the heading - one paragraph - an award with its source - four tiles (kitchen and restaurant, guesthouse, countryside experiences, sauna) - **seasonal stay-and-dine offers, each stating nights, arrival and departure days, what is included, a "from" price for two, the dates the offer runs, the dates it excludes, and that a deposit for the room is taken at booking with the rest payable at the end of the stay** - a midweek dinner price - gatherings and workshops - sustainability - a dated experiences calendar - the nearby coast path - press logos. Extraction: 68 images, about 13,300 characters. |
| 4 | https://www.coombesheadfarm.co.uk | 2026-11-21 | Cornish farm guesthouse. The home page is six plain paragraphs: the place - **the rooms (nine bed-and-breakfast rooms and a self-catered cottage) and the restaurant's opening days** - private hire in winter - the shop with days and hours - the bakery - the farm - then "what's coming up" as dated lines by month. Extraction: 3 images, about 1,800 characters. |
| 5 | https://www.therectoryhotel.com | 2026-11-21 | English village hotel, 18 bedrooms. Order: address as the first line - Welcome (one paragraph stating the number of bedrooms, the pool and the restaurant) - then **eight short blocks, each a heading and one or two sentences: restaurant, bedrooms (how many in the main house and how many in the cottage), two seasonal stays, the bar, pool and grounds with the months the pool is heated and open, gift vouchers, the cottage with a "from" price** - newsletter - social. Extraction: 43 images, about 6,000 characters. |
| 6 | https://hotelpeterandpaul.com | 2026-11-21 | New Orleans hotel, 71 rooms, in four historic buildings. Order: an offer for stays of three nights or more - "Book a room" - one-line identity - room types named by building - one paragraph - explore all rooms - offers - dining - newsletter - pool - events and weddings - programme of music and classes - city guide - "plan your stay", urging direct booking - **a list of services (pool and bar, breakfast to the room, concierge, parking and car charging, wifi)** - a link to frequent questions. Extraction: 1 image reference, about 7,100 characters. |
| 7 | https://www.sanjosehotel.com | 2026-11-21 | Austin hotel. Order: skip-navigation link - **"Book now" three times before any other content** - an advance-booking discount (book 14 days or more ahead) - the lobby shop with three products - seasonal events hire - the courtyard lounge - the garden - happenings as dated or recurring events. Links state that they open in a new window; the video states that it has no audio. Extraction: 19 images, about 5,400 characters. |
| 8 | https://thefifearms.com | 2026-11-21 | Scottish hotel, 47 rooms. A very large navigation (about us, stay by room category, eat and drink by venue, experiences, art, families, wellness, festivals, private events). Order: headline - welcome with a classification from a named guide - Stay with us (number of rooms, how they are themed, room categories as a slideshow) - eat and drink - seasonal block - experiences - art - shop - gallery - stories. Used as the ceiling: what the domain looks like when the hotel is a destination with many venues. Extraction: 191 image references, about 39,000 characters. |

Loaded and not used:

| Site | Checked | Why not |
|---|---|---|
| https://www.artistresidence.co.uk | 2026-11-21 | Loads, but the readable text in the extraction is only a list of five locations. Not enough to describe the structure. |
| https://thehoxton.com | 2026-11-21 | Loads. An international chain; the home page is a date picker and a list of cities. Outside the scope of an owner-run place. |
| https://www.casabonay.com | 2026-11-21 | Loads, but the extraction returned an old notice about limited opening and an unrendered form tag. Stale or broken; not a quality reference. |

Did not load on 2026-11-21 and therefore not listed above: thegunton-arms.co.uk, number16hotel.co.uk, kinlochlodge.com, thenewtinsomerset.com.

## 10. Skeletons

Structure only. No colours, logos, photographs or wording were taken from any reference.

### Skeleton A: the small guesthouse

For a place with a handful of rooms, often with food, where the owner confirms bookings. Default for this domain.
From references 2, 4 and 5: the plain facts of 4, the short blocks of 5, the practical questions of 2.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; one action (check availability / email to book); phone | action is the most prominent element after the name | yes |
| 1 | Opening | one sentence: what kind of place, how many rooms, where | one heading, one line; a large photograph of the place | yes |
| 2 | The rooms | each room or room type: name, sleeps, beds, bathroom, floor, one or more photographs of that room, price per night for two or "price on request" | one block per room, facts in a fixed order | yes |
| 3 | What your stay includes | breakfast, dinner, facilities; what costs extra | short list | yes |
| 4 | Food | when meals are served, whether dinner is a set menu, whether non-guests can come | a short paragraph and the days | only if there is food |
| 5 | Things to do | at the property and nearby | a few items with images | optional |
| 6 | Offers | each with nights, arrival day, what is included, price for how many, the dates it runs, exclusions | one block per offer, dated | optional, hidden when none is current |
| 7 | Good to know | check-in and check-out, late arrival, children, pets, access in facts, parking, car charging, minimum stay, cancellation and deposit | questions as headings, one or two sentences each | yes |
| 8 | How to book | the action again; how the booking is confirmed; what is paid when | action, then two sentences | yes |
| 9 | Getting here | address as text, written directions, map link, nearest station or town, phone | complete without the map | yes |
| 10 | Footer | name, address, phone, email; booking terms, privacy, accessibility statement; newsletter; social link | small | yes |

Image-to-text ratio: **estimate**, from extraction counts only (references 2, 4 and 5 returned 3 to 43 image references against roughly 1,800 to 6,200 characters; the spread is wide because some counts include slideshow frames). Images carry the persuasion: one large photograph at the top and at least one per room. Text carries every practical fact, in short blocks of one or two sentences. Not confirmed in a rendered view.

### Skeleton B: the hotel with more than rooms

For a hotel with a restaurant, events or activities that also serve people who are not staying. Use only when those exist.
From references 1, 3, 6 and 7: the "ways to visit" statements of 1, the tiles and offers of 3, the services list of 6, the repeated booking action of 7.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | navigation by what people come for: Stay, Eat, Do, Events; "Book a room" always visible; a second, quieter "Book a table" | room booking never hidden behind the other menus | yes |
| 1 | Opening | one line of identity; the booking action; a current offer if there is one | one heading, one action | yes |
| 2 | Ways to visit | tiles: stay, eat and drink, treatments or activities, gatherings, visit without staying | image and one sentence each | yes |
| 3 | Rooms | room types as cards: name, sleeps, one photograph, "from" price with what it is for; link to all rooms | card per type | yes |
| 4 | Eat and drink | each venue with its days and whether non-guests are welcome | block per venue | only if they exist |
| 5 | Offers and packages | as section 6 of Skeleton A | dated | optional |
| 6 | What is on | dated events | list by date | optional, hidden when empty |
| 7 | Services | parking, breakfast, pool with its season, wifi, and so on | a plain list | yes |
| 8 | Proof | an award or classification with its source, press with the publication named | one strong item | optional |
| 9 | Good to know and getting here | as sections 7 and 9 of Skeleton A | | yes |
| 10 | Footer | as Skeleton A, plus gift vouchers and their terms | | yes |

Image-to-text ratio: **estimate**. Image-led: references 3 and 8 returned 68 and 191 image references. Most blocks are a photograph with a heading and one sentence. Not confirmed in a rendered view.

Risk seen in references 1 and 8: when the hotel is presented as a destination, the plain facts a guest needs before booking (price, check-in time, cancellation) are several steps from the home page. Whatever the skeleton, "Good to know" stays on the home page.

## 11. Not verified

1. All Hebrew and Arabic terms in section 6: author's knowledge, not checked with a working hotelier. Cells marked "not verified" must not be filled by guessing.
2. Every legal statement in section 7. None was checked against a statute or an official source for this file. VAT for foreign tourists and cancellation rules in Israel, package-travel scope, and the price-transparency rules of 2025 in the UK and the US matter most and are the least certain.
3. Image-to-text ratios and visual quality of all references: text extraction only, no rendered view. Image counts for references 5 and 8 probably include slideshow frames.
4. awwwards.com/websites/hotel-restaurant was not consulted; design quality of the references is the author's prior judgement.
5. No budget guesthouse, no three-room bed and breakfast, and no property outside the UK and the US was verified.
6. Booking defaults in section 4 (14 nights, 12 months ahead) are estimates.
7. Sub-pages of the references (room pages, rate pages, booking flows, terms) were not fetched. No booking system behind a "Book" action was followed, so the statement that properties use outside reservation systems rests on the link labels and the author's knowledge.
8. None of the references' home pages showed cancellation terms in the extraction; where they place them was not observed.
9. Four candidate sites did not load and were not replaced by other small-guesthouse sites.
10. No references in Hebrew, Arabic or any non-Latin script. These come in a later phase.
