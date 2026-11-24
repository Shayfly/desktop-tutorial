# Restaurant

Covers: a place where people sit at a table and are served a meal: restaurants, bistros, taverns, wine bars that serve food, family restaurants, fine dining.
Does not cover: a counter with no table service (use `food-stall.md`); a place whose main product is coffee, bread or pastry (use `cafe-bakery.md`); a hotel whose restaurant is one part of it (use `hotel-guesthouse.md`, and this file for the restaurant page).
Written 2026-11-21. References checked 2026-11-21. Template: [README.md](README.md).

## 1. Objects

A restaurant sells **a table for a period of time, and a meal chosen from a menu that changes**. Everything else follows from that: a menu has a date, a table has a size, a service has a last-order time, and a reservation is one party at one table for one sitting.

### Restaurant (the business)

| Field | Required | Example (illustrative) |
|---|---|---|
| Name | required | "The Lantern" |
| Kind of food, in one line | required | "Seasonal Italian", "Grill and fish" |
| Address | required | street, number, city, floor |
| Phone | required | a number that is answered during service |
| Service hours, per day and per service | required | Tue-Sat lunch 12:00-14:30, dinner 18:00-21:45; closed Sun-Mon |
| How to get a table | required | book online, call, walk-in only, or a mix |
| Email | optional | often split: general, reservations, events |
| Price level | optional | shown through the menu, not through symbols |
| Dietary and religious status | optional, see rule 12 | kosher with certificate, halal with certificate, vegetarian kitchen |
| Access | optional | step-free entrance, accessible toilet, lift |
| Children, dogs, dress | optional | high chairs, "dogs welcome on the terrace" |
| Parking and transport | optional | nearest station, car park |
| Payment and service charge | optional | cards accepted; "a 12.5% service charge is added" |
| Short story, who cooks | optional | names of staff only with their agreement |

### Location (only when there is more than one)

Address, phone, hours, booking link and menu, repeated per location. Each location has its own menu and hours unless the customer says they are identical.

### Service (a sitting period)

| Field | Required | Example |
|---|---|---|
| Name | required | Breakfast, Lunch, Dinner, Sunday lunch, Bar |
| Days | required | Fri-Sun |
| Start and last-order time | required | 12:00, last orders 14:30 |
| Which menu is served | required | Lunch menu |

Kitchen hours and door hours are different things. The page states kitchen hours (when food can be ordered).

### Menu

| Field | Required | Example |
|---|---|---|
| Name | required | Dinner, Lunch, Set lunch, Wine list, Children, Sunday |
| When it is served | required | which service |
| Date | required for a menu that changes | "Thursday 19 November" or "sample menu" |
| Kind | required | a la carte, set menu, tasting menu, sharing |
| Price for the whole menu | required for set and tasting menus | "30 per person" |
| Note | optional | "menus change daily", service charge, how to ask about allergens |

### Menu section and dish

A menu has sections in order (Starters, Mains, Desserts, or the restaurant's own words). A dish belongs to one section of one menu.

| Field | Required | Example |
|---|---|---|
| Name | required | "Pici cacio e pepe" |
| Price | optional, see rule 3 | 13.5 |
| Short description | optional | main ingredients |
| Allergens | see rule 9 | contains wheat, milk |
| Dietary tags | optional | vegetarian, vegan |
| For how many | optional | "for two" |
| Supplement | optional | "+6 on the set menu" |
| Size or measure rows | optional; needed for drinks | glass 125 ml / carafe / bottle, each with its price |
| Strength | optional; drinks | 13% |
| Available | required, default yes | a dish can be off today |

### Reservation (only when the product takes bookings)

| Field | Required | Example |
|---|---|---|
| Date and time | required | |
| Party size | required | 4 |
| Name | required | |
| Phone | required | to confirm or to say the table is ready |
| Email | optional | |
| Notes | optional | high chair, wheelchair, occasion |
| Allergy note | optional | the guest's own words; see Legal on health data |
| Seating wish | optional | terrace, counter |
| Status | required | requested, confirmed, seated, completed, cancelled by guest, cancelled by restaurant, no-show |
| Deposit or card hold | optional | |

### Other objects

| Object | Fields | Notes |
|---|---|---|
| Booking rules | how far ahead, largest party bookable online, how long a table is held, how long a party keeps the table, whether tables are kept for walk-ins | Reference 2 states all of these in plain sentences |
| Closure | date or range, reason | Holidays, private hire, staff break. Overrides the weekly hours |
| Private dining or group offer | room or area, capacity, set menus, minimum spend, enquiry contact | An enquiry, not a booking |
| Event | date, name, price, how to book | Guest chefs, wine dinners, holidays |
| Gift voucher | value, expiry, how to redeem | Involves payments |
| Certificate | kind, issuer, valid until | Required before the matching claim is shown |
| Review or award | text, source, year | Only real ones, with source and year |
| Gallery item | image, caption | The room and the food. People in photos need to have agreed |

## 2. Rules

1. Every dish belongs to exactly one section of one menu. The same dish on two menus is two entries, each with its own price.
2. A menu states when it is served. A menu with no service attached is not shown.
3. A dish price is optional on an a la carte menu, but its absence is explicit ("market price", "ask us"). Blank and zero are not allowed.
4. A set or tasting menu shows one price for the menu and whether it is per person. Dishes inside it show a price only if they carry a supplement.
5. Every price shows its currency once per menu at least. A drink sold by measure shows the measure next to each price.
6. A menu that changes carries either a date or the words "sample menu". A dated menu older than the customer's stated change cycle is shown as a sample, not as today's.
7. If a service charge or cover charge is added, the menu says so, with the amount.
8. Whether prices include tax follows the country (see Legal). The page does not mix inclusive and exclusive prices.
9. Allergen information is shown per dish, or the menu says exactly how to get it. The page never says a dish is "safe" or "free from" on its own.
10. Service hours are stated per day and per service, with closed days named, in the restaurant's local time. Last-order time is stated when it differs from closing time.
11. A closure date overrides the weekly hours. No table is offered on a closed date.
12. Kosher, halal and similar status are shown only with the certificate named. Whether the kitchen is open on the Sabbath or on religious holidays follows from this and is stated in the hours.
13. A reservation has a date, a time, a party size, a name and a phone number.
14. A reservation may only be made inside a service, on an open day, not in the past, and not later than the last-booking time for that service.
15. A party larger than the stated online limit is sent to a phone number or an enquiry form, not refused silently.
16. Confirmed reservations for one time may not exceed what the restaurant said it can seat. If the customer gave no capacity, the product takes requests, not confirmed bookings.
17. If a card hold, a deposit or a no-show fee exists, the guest sees it before confirming.
18. If tables are held for a limited time, or must be given back after a set period, the guest is told at booking.
19. A cancelled or no-show reservation frees its table. The record stays.
20. A private-dining enquiry is not a booking until the restaurant confirms it.
21. The main action is one of: book a table, call, see the menu. It is reachable from every page on a phone.
22. The phone number is a tappable link. The address opens a map.
23. A review, award or rating is shown with its source and year. No invented quotes.
24. Photographs of dishes are of this kitchen's dishes.
25. Alcohol is not promoted to children, and an age notice follows the country's rules.

## 3. Mandatory facts

The product is not built until each of these has an answer from the customer. None may be guessed.

| # | Fact | The one question to ask | Why (the human reason) |
|---|---|---|---|
| 1 | Name | "What is the restaurant called?" | Without a name people cannot find it or recommend it. |
| 2 | Kind of food | "What kind of food do you cook? One sentence, as you would say it to a guest." | A visitor decides in seconds whether this is where they want to eat tonight. |
| 3 | Address | "What is the full address, and how do people find the door?" | Without it people cannot arrive. |
| 4 | Phone | "What number do guests call, and when is it answered?" | Without it people cannot say they are late or ask about a big table. |
| 5 | Service hours | "Which days are you open, and when does the kitchen take orders for lunch and for dinner on each?" | Without it people arrive when the kitchen is closed. |
| 6 | How to get a table | "How do guests get a table today: an online system, the phone, or do they just walk in?" | The whole site leads to this one action. If it is wrong, the site produces nothing. |
| 7 | The menu | "Send me the current menu with prices. If it changes often, tell me how often and who will update it." | The menu is the reason people open the site. An old menu is a broken promise. |
| 8 | Allergens | "How do you want guests with allergies to get the information: per dish on the menu, or by asking the staff?" | A wrong answer here can put a guest in hospital. |
| 9 | Service charge | "Do you add a service charge or a cover charge? How much?" | A bill higher than the menu said feels like a trick. |
| 10 | Who is the business legally | "What is the registered business name and number, for the legal pages?" | The privacy and terms pages must name who is responsible. |

Needed only when the product takes reservations itself:

| # | Fact | The one question to ask | Why |
|---|---|---|---|
| 11 | Capacity | "How many guests can you seat at one time, and what is the largest table you take online?" | Without it forty people are booked into a room for twenty. |
| 12 | Booking rules | "How far ahead can people book, how long do you hold a late table, and do you need the table back after a set time?" | The guest must know before booking, not at the door. |
| 13 | No-shows and deposits | "What happens when a booked table does not come? Do you take a card or a deposit?" | The guest must agree to it in advance, and you must be able to stand behind it. |
| 14 | Where booking alerts go | "Where should I send each new booking: which phone or email, and who reads it during service?" | A booking nobody saw is a family standing at the door with no table. |

Needed only in some cases:

| # | Fact | The one question to ask | Why |
|---|---|---|---|
| 15 | Certificate behind a claim | "You said kosher (or halal). Who issued the certificate and until when?" | People rely on it for religious reasons. Without a certificate the product does not write it. |
| 16 | Private dining | "Do you take groups or private events? For how many, and who answers the enquiries?" | An unanswered enquiry is the most valuable booking lost. |

## 4. Declared defaults

Each default is shown to the customer as "we filled this in - change it if it is wrong". None of them is a fact about the business.

| Default | Value | Why it is safe | How it is marked |
|---|---|---|---|
| Main action | "Call to book", using the phone number | Works with zero setup | Labelled "default: phone" |
| Section names and order | the customer's own headings in the order given; if none: Starters, Mains, Sides, Desserts, Drinks | Standard order | Editable, labelled "suggested" |
| Menu label when no date was given | "Sample menu" | Promises nothing about today | Shown on the menu |
| Missing dish price | "Ask us" | Says openly that there is no number | Listed for the customer as "no price given" |
| Missing allergen answer | "Please tell us about any allergy before you order" | Makes no claim | Listed as "allergen details not given" |
| Page order | Skeleton A below | Extracted from the references | Named as the default skeleton |
| Booking mode | request, confirmed by the restaurant by hand | Cannot overbook | Labelled "default: we confirm each booking" |
| Booking slot step | 15 minutes | Estimate | Setting, labelled "default" |
| Earliest booking | 2 hours ahead | Estimate | Setting |
| Latest booking | 60 days ahead | Estimate; reference 7 states 60 days, reference 2 states one month | Setting |
| Largest party bookable online | 6 | Estimate; reference 2 states 6 | Setting; larger parties see the phone number |
| Language and direction | the language of the conversation | The customer chose it by speaking it | Shown, changeable |
| Currency | the currency of the restaurant's country | Follows from the address | Shown on every menu |
| Legal page structure | headings only | Structure is general; content is not | Marked "draft - not legal advice - review before publishing" |
| Empty optional sections | hidden | A missing gallery is better than an empty one | Listed as "not shown yet: gallery, events, private dining, press" |

Never a default, whatever the customer left out: dishes, prices, hours, capacity, service charge, allergens, "kosher", "halal", "vegan options", "gluten-free options", "family friendly", "accessible", awards, stars, reviews, the chef's name, photographs of food.

## 5. Failure modes

| What went wrong | What the visitor sees | What it costs | Prevention |
|---|---|---|---|
| Menu on the site is old | Comes for a dish that is gone, or pays more than the site said | Disappointment at the table; in some places a legal problem | Rule 6; date or "sample menu"; mandatory fact 7 names who updates |
| Hours show the door, not the kitchen | Arrives at 21:50, the kitchen closed at 21:45 | A turned-away guest | Rule 10; ask for last-order times |
| A holiday or private hire is not marked | Arrives at a closed or fully hired room | A wasted evening | Closure object; rule 11 |
| Booking saved but the restaurant never told | Arrives; no table, no record | The worst case in this domain | Mandatory fact 14; status "requested" until confirmed; test the alert at setup |
| Overbooking | Waits forty minutes with a confirmed booking | A guest who does not return, and says so publicly | Rule 16; default is request mode |
| Booking button leads to a dead outside page | Taps, gets an error | Silent loss; the customer never finds out | Check outbound links at publish and on a schedule |
| Large party tries to book online and fails with no explanation | Gives up | The most valuable tables lost | Rule 15 |
| Service charge not stated | Bill is higher than expected | An argument, a bad review | Rule 7; mandatory fact 9 |
| Allergen wrong or missing | Eats something that harms them | A medical emergency; liability | Rule 9; mandatory fact 8 |
| "Vegan options" or "gluten-free" written by the builder | Arrives and finds one side salad, or cross-contamination | Distrust; possible harm | Never a default |
| Kosher or halal implied without a certificate | Relies on it and is misled | Loss of trust; in some places an offence | Rule 12; mandatory fact 15 |
| Table time limit not stated | Is asked to leave mid-dessert | Humiliation, a bad review | Rule 18 |
| No-show fee charged without notice | Sees a charge on the card | Dispute, chargeback | Rule 17 |
| Menu is only a PDF or an image | Cannot read it on a phone; a screen reader reads nothing | Lost guests; an accessibility failure | Menu is text. A PDF may be offered in addition |
| Phone not tappable, or answered only during service | Calls at 10:00, no answer, no stated hours | Lost booking | Rule 22; state when the phone is answered |
| Stock food photos | The plate does not look like the picture | Distrust | Rule 24 |
| Site in one language in a tourist area | Cannot read the menu | Lost tables | Ask which languages the guests speak |

## 6. Professional language

Hebrew and Arabic terms are the author's knowledge and were not checked with a working restaurateur in either language. Arabic usage varies by region; terms given are standard or Levantine. Where a cell says "not verified", do not use a guess.

| English | Meaning | Hebrew | Arabic |
|---|---|---|---|
| Restaurant | the business | מסעדה | مطعم |
| Menu | the list of dishes | תפריט | قائمة الطعام / منيو |
| Dish | one item | מנה | طبق |
| Starter (UK), appetizer (US) | first course | מנה ראשונה | مقبلات |
| Main course (UK), entree (US) | the central dish | מנה עיקרית | طبق رئيسي |
| Side | served next to the main | תוספת | طبق جانبي (not verified) |
| Dessert, pudding (UK) | sweet course | קינוח | حلويات / تحلية |
| A la carte | each dish chosen and priced alone | א-לה-קארט | حسب الطلب (not verified) |
| Set menu, prix fixe | several courses for one price | תפריט קבוע (not verified) | قائمة ثابتة (not verified) |
| Tasting menu | many small courses chosen by the kitchen | תפריט טעימות | قائمة تذوق |
| Business lunch | a weekday lunch deal | עסקית | not verified |
| Dish of the day, special | not on the printed menu | מנת היום / ספיישל | طبق اليوم |
| Sharing plates | dishes for the middle of the table | מנות לחלוקה (not verified) | not verified |
| Reservation, booking | a held table | הזמנת מקום / הזמנת שולחן | حجز |
| Walk-in | arriving without a reservation | ללא הזמנה מראש | بدون حجز |
| Party | the group at one table | not verified | not verified |
| Covers | number of guests served | סועדים | not verified |
| Service | a sitting period (lunch, dinner) | סרוויס (trade slang; not verified) | not verified |
| Last orders | latest time the kitchen takes an order | הזמנה אחרונה (not verified) | آخر طلب (not verified) |
| No-show | booked and did not come | not verified | not verified |
| Service charge | a percentage added to the bill | דמי שירות | رسوم الخدمة |
| Tip | money given to staff by choice | טיפ / תשר | بقشيش / إكرامية |
| Bill (UK), check (US) | what the guest pays | חשבון | حساب / فاتورة |
| Corkage | a fee for bringing your own wine | דמי חליצה | not verified |
| Wine list | the list of wines | תפריט יינות | قائمة النبيذ (not verified) |
| By the glass | wine sold per glass | בכוס | بالكأس (not verified) |
| Chef | head of the kitchen | שף | شيف / طاهٍ |
| Waiter, server | serves the table | מלצר / מלצרית | نادل |
| Host | seats the guests | מארח / מארחת | not verified |
| Private dining | a room or area for one group | חדר פרטי / אירוע פרטי | not verified |
| Allergens | ingredients that cause allergic reactions | אלרגנים | مسببات الحساسية |
| Vegetarian / vegan | no meat or fish / no animal products | צמחוני / טבעוני | نباتي / نباتي صرف (not verified) |
| Kosher / kosher certificate | permitted under Jewish dietary law / the document | כשר / תעודת כשרות | كوشير (not verified) / not verified |
| Halal | permitted under Islamic dietary law | חלאל | حلال |
| Takeaway (UK), to go (US) | food to carry away | טייק אוויי | سفري (Levant) |
| Delivery | brought to the guest | משלוח | توصيل |

Notes on language:

- UK and US English differ: starter / appetizer, main / entree, pudding / dessert, bill / check, booking / reservation. Pick one by the restaurant's country.
- The restaurant's own section names stay as given, even in another language ("Antipasti", "Mezze"). Do not translate dish names; add a description instead.
- Words to avoid unless the customer said them and can back them: "best", "authentic", "homemade", "fresh", "local", "farm to table", "organic", "sustainable", "award-winning", "Michelin" in any form.
- "Gluten-free", "nut-free" and "allergy-friendly" are claims with consequences. The product does not write them.

## 7. Legal

A checklist of questions, not legal advice. The author is not a lawyer and did not read the statutes for this file. Every item needs checking by someone qualified in the restaurant's country before it is relied on.

### Applies almost everywhere

- **Privacy notice.** Needed as soon as the site collects a name and a phone number (a booking, an enquiry, a newsletter). Reference 1 states under its newsletter field that subscribing means agreeing to receive promotional content under its privacy policy (observed 2026-11-21).
- **Allergy notes are health data** in many places, which is more strictly protected. Default: the booking form asks the guest to tell the staff; if a note field exists, it is kept only as long as the booking.
- **Allergens.** A restaurant must be able to tell a guest which listed allergens are in each dish. The form differs by country.
- **Prices.** Whether menu prices must include tax, and how a service charge must be disclosed, is set by law in most places.
- **Alcohol.** Selling it needs a licence; promoting it has age rules.
- **Terms.** Needed when the product takes deposits, card holds, vouchers or prepaid events: cancellation, no-show fee, refund, voucher expiry.
- **Marketing messages** need prior agreement. A booking confirmation is not marketing.
- **Reviews and awards** must be real and current.

### Israel

- A restaurant requires a business licence under the Business Licensing Law, with Ministry of Health conditions. Details: not verified.
- Kosher: presenting a restaurant as kosher without a certificate from an authorised body is prohibited under the Kosher Fraud Prohibition Law. Which bodies are authorised today: not verified.
- Prices shown to consumers must include VAT (Consumer Protection Law). Not verified for menus specifically.
- Service: whether a mandatory service charge is allowed, and how tips must be handled for wages and tax: not verified.
- Calorie and nutrition labelling duties for restaurant chains: not verified.
- Allergen disclosure duties for restaurants: not verified.
- Accessibility: the website of a business serving the public must be accessible and carry an accessibility statement, with exemptions for very small businesses by turnover. Thresholds and current standard version: not verified.
- Privacy: the Protection of Privacy Law applies to booking data; Amendment 13 came into force in August 2025. What it requires of a single restaurant: not verified.
- Marketing messages: prior consent under section 30A of the Communications Law. Details: not verified.
- Gift vouchers: rules on minimum validity exist. Details: not verified.
- Sale of alcohol to minors is prohibited and a notice is required on premises. Whether a website needs anything: not verified.

### European Union and United Kingdom

- EU Regulation 1169/2011 lists 14 allergens and requires that information on them be available for non-prepacked food, including restaurant dishes; member states decide the form. The UK kept the list. Believed true; not verified against the text.
- UK, England: businesses with 250 or more employees must show calories on menus, since April 2022. Small restaurants are outside it. Not verified.
- UK: from 2024-2025, tips and service charges must be passed to staff in full under the Employment (Allocation of Tips) Act. What must be said on a menu: not verified.
- UK: a discretionary service charge must be shown clearly before ordering under consumer-protection rules. Not verified.
- Displayed consumer prices must include VAT: believed true in both; not verified.
- UK: the Food Hygiene Rating must be displayed in Wales and Northern Ireland, and is voluntary in England. Not verified.
- GDPR and UK GDPR apply to booking data. Consent is needed for non-essential cookies. Reference 4 states on its page that it uses cookie-free analytics (observed 2026-11-21).
- Distance-selling cancellation rights have an exception for catering and leisure services booked for a specific date. Whether a prepaid restaurant booking falls under it: not verified.
- European Accessibility Act, from June 2025, with a microenterprise exemption. Whether a restaurant booking page is in scope: not verified.

### United States

- Menu prices usually exclude sales tax and tip. Some states and cities regulate added service fees and require them to be disclosed up front. Not verified per place.
- Federal menu-labelling rules require calories on menus of chains with 20 or more locations. Not verified.
- Nine major allergens are named in federal law for packaged food; restaurant duties come from state and local food codes. Not verified.
- The Americans with Disabilities Act is applied by courts to restaurant websites in many cases. Reference 7 ends its page with a line offering help by phone to anyone having trouble using the site (observed 2026-11-21).
- Liquor licensing is by state and locality. Not verified.

### What the product does with this

- The product asks which country the restaurant is in before generating any legal page or price format.
- The product may generate the **structure** of a privacy page, terms and an accessibility statement, each marked as a draft that needs review.
- The product never writes "licensed", "kosher", "halal", "allergen-free" or "complies with" on its own.

## 8. Site vs app

### Content pages (no data, no accounts)

Home, menus, about, find us, private dining information, gallery, press, legal pages. With a phone link, or a link to an outside booking system, this is a complete and honest product. References 4 and 5 are exactly this.

States still needed on content pages:

| Part | Empty | Error | Notes |
|---|---|---|---|
| Menu | cannot be empty (mandatory fact) | n/a | Text, not only a PDF. Dated or marked "sample" |
| Dish price | "ask us" | n/a | Never blank |
| Hours | cannot be empty | | "Open now" needs the restaurant's time zone and the closures |
| Map | address as text always shown | if the map fails, the text and a link remain | |
| Gallery, press, events | section hidden | broken image hidden | Never placeholders |

### Needs data

| Part | What it needs | Empty state | Loading | Error | Save | Permissions |
|---|---|---|---|---|---|---|
| Menu the owner updates | an edit screen for dishes, prices, availability and the menu date | n/a | | a failed save keeps what was typed and says so | public right after saving; the menu date updates | owner and named staff |
| Booking request (restaurant confirms by hand) | stores the request; alerts the restaurant | no service that day: "We are closed on Mondays - choose another day" | times show a placeholder, never a blank that reads as "full" | "Could not send - please call" with the number | status "requested"; the guest is told plainly it is not confirmed yet | guest sees own request through a link; restaurant sees all |
| Live booking (instant confirmation) | services, capacity, booking rules, closures, existing reservations | fully booked: "Nothing at that time - nearest free times" and "we keep tables for walk-ins" only if the customer said so | same | if the time was taken meanwhile: "That time was just taken - here are the nearest" | confirmed only after the server saved it; the guest gets a confirmation to keep | guest: own booking; staff: the day's list; owner: everything |
| Cancel or change by the guest | a link in the confirmation, no password | no upcoming booking: say so | | link expired: show the phone | cancelling frees the table at once and alerts the restaurant | only through the personal link |
| The day's reservation list | bookings by service, with party size and notes | "No bookings for dinner yet" | | never show a stale list without saying it is stale | each change saved at once, with who changed it | staff, behind a login |
| Private-dining enquiry | stores the enquiry; alerts the events contact | n/a | button cannot be pressed twice | "Not sent - please email" with the address | "received - this is an enquiry, not a booking" | visitor writes; only the restaurant reads |
| Newsletter signup | an address and proof of agreement | n/a | | "Not saved - try again" | says what will be sent and how to stop | owner only |
| Closures | dates the owner sets | n/a | | | public at once; no tables offered | owner only |

### Needs accounts

- The owner needs one as soon as the menu is editable or a booking is stored.
- Staff need one if a host manages the reservation list.
- Guests do not need one. A phone number and a link are enough.

### Needs payments

- Deposits or card holds for bookings, prepaid tasting menus and events, gift vouchers, online ordering for collection or delivery.
- Each brings refunds, receipts, failed-payment states and the cancellation law of the restaurant's country.
- Default: no payments. Added only when the customer asks and has stated the policy (mandatory fact 13).

### Using an existing booking system

References 5 and 7 name an outside reservation service on the page, and the extractions of references 2, 4 and 6 contain the name of one as well. Where the customer already uses one, the product is a content site, the main action is that link, and the product owns no reservation data. Ask before building a second reservation book: two books mean double bookings.

## 9. References

**How these were checked.** Each URL was fetched on 2026-11-21 with a page-extraction tool that returns the page's text and image references. No browser was used and no screenshot was taken. So: section order and wording are observed; visual quality, layout and the image-to-text ratio are **not** observed, and every ratio below is an estimate from counts in the extracted text. Image counts include logos and icons. Some extractions omit navigation and footers.

**Curation.** Chosen by the author from well-known independent restaurants in London, New York and San Francisco, not from a search-result list. No awwwards.com category was consulted for this file (awwwards.com/websites/hotel-restaurant is the category to consult in the next pass); none of these is claimed as an award winner. All are in English, in Latin script.

**Limit.** All eight are established, critically noticed restaurants in three big cities. No neighbourhood family restaurant, no restaurant outside the UK and the US, and no delivery-led restaurant was verified. The skeletons are a ceiling for structure, not a picture of the typical customer.

Verified: 8.

| # | Site | Checked | What was observed |
|---|---|---|---|
| 1 | https://www.stjohnrestaurant.com | 2026-11-21 | London restaurant group with bakery, wine and shop. Order: four location links at the top - a three-sentence statement - Restaurants (one paragraph) - Bakeries (one paragraph) - About - Wines - Shop - social - newsletter with a privacy sentence under the field - footer links (restaurants, bakery, wine, shop, gift cards, careers, private events). Text-led; menus and booking are on the location pages. Extraction: 8 images, about 5,900 characters. |
| 2 | https://thepalomar.co.uk | 2026-11-21 | One London restaurant. Order: address as the first line, linked - welcome and a five-paragraph description - Menus (two paragraphs on food, one on wine, one on the bar) - Events with brochure, online booking and enquiry actions - **Reservations and walk-ins**: how far ahead tables can be booked by party size, that tables are always kept for walk-ins, set menus for groups of 7 to 14 - careers - Find us with four separate email contacts by purpose - opening hours with nearest stations - newsletter. A set-lunch price appears once. Extraction: 13 images, about 6,600 characters. |
| 3 | https://www.padella.co | 2026-11-21 | London pasta bar. **The home page is the menu**: a date as the heading, then sections (antipasti, pasta, pudding, ice cream, aperitivi, beer, softs, wine, espresso, digestivi), each dish one line with its price; drinks carry measure and strength; one line says an extra is charged. A two-sentence About comes last. The date shown was two days before the check. Extraction: 8 images, about 2,800 characters. |
| 4 | https://www.thequalitychophouse.com | 2026-11-21 | One London restaurant, one short page. Order: name - address - phone - email - social - **kitchen hours per day and per service** - mailing list - three sentences of history - two staff roles - the parent group with sister restaurants - privacy link - a note that analytics are cookie-free. Extraction: 5 images, about 1,700 characters. |
| 5 | https://www.estelanyc.com | 2026-11-21 | One New York restaurant, one page of five headed blocks: About (three sentences, one accolade, two staff roles) - Hours and location (dinner, lunch and midday as separate rows) - Reservations (names the outside booking service; separate emails for questions, buy-outs and press) - Menus ("subject to change", links to wine list, lunch, dinner). Extraction: 9 images, about 3,400 characters. |
| 6 | https://www.rochellecanteen.com | 2026-11-21 | One London restaurant. Order: one sentence on the cooking - **opening times by service, including the time guests must leave** - "wheelchair accessible" - two actions (make a reservation, buy a gift voucher) - welcome - about - team listed by role - book a table - address - copyright. Extraction: 1 image, about 2,700 characters. |
| 7 | https://www.zunicafe.com | 2026-11-21 | One San Francisco restaurant. Order: address and phone at the very top - a seasonal pre-order notice with pickup dates - a product collaboration - **Reservations**: service hours, the phone hours for booking, an outside booking link, a rule for parties of seven or more, "up to 60 days in advance", the year's holiday closures listed by date - About - Menus (described in prose, "change daily") - Hours and location again - a closing line offering phone help to anyone having trouble with the site. Extraction: 26 images, about 9,400 characters. |
| 8 | https://www.dishoom.com | 2026-11-21 | UK restaurant group, many locations. Order: a quotation as headline - "view menus" - a long story of the idea with captioned photographs - seasonal menus and the shop - the food by time of day - list of locations - recipes - awards with source and year - newsletter - gift voucher. Story-led; booking is per location. Used as the ceiling: what the domain looks like for a group with a brand. Extraction: 64 images, about 21,000 characters. |

Loaded and not used:

| Site | Checked | Why not |
|---|---|---|
| https://www.chezpanisse.com | 2026-11-21 | Loads, but the extraction returned an empty shell (about 360 characters). Does not count under rule 4. |
| https://www.gramercytavern.com | 2026-11-21 | Loads, but the extraction returned only two sentences and a "view menus" link. Not enough. |
| https://noma.dk | 2026-11-21 | Loads. The page is a long announcement letter, a reservation-updates signup and two shops. Too unusual to extract a skeleton from. |

Did not load on 2026-11-21 and therefore not listed above: bratrestaurant.com.

## 10. Skeletons

Structure only. No colours, logos, photographs or wording were taken from any reference.

### Skeleton A: the one-page restaurant

For a single restaurant whose site has one job: tell people what it is, when it is open, and how to get a table. Default for this domain.
From references 2, 4, 5, 6 and 7: the facts-first order of 4 and 5, the reservations block of 2 and 7, the hours of 6.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; one action (book / call); address or neighbourhood in one line | action is the most prominent element after the name | yes |
| 1 | Opening | one or two sentences on the kind of food and the place | one heading, short text, no slogans | yes |
| 2 | Hours | per day and per service, last orders, closed days, dated closures | a small table; today's row can be marked | yes |
| 3 | Reservations | the main action; how far ahead; largest party online; walk-ins; time limits and deposits if any; who to contact for a large party | action first, rules as short sentences under it | yes |
| 4 | Menus | each menu named with when it is served; dishes as one line each with price; the date or "sample menu"; service charge; how to ask about allergens | menu name over section over dish; price at the end of the line | yes |
| 5 | The room and the food | photographs | images only | optional, hidden when empty |
| 6 | About | history, the kitchen, the team by role | one heading, a few lines | optional |
| 7 | Groups and private dining | capacity, set menus, enquiry action | short | only if offered |
| 8 | Find us | address as text, map link, phone and when it is answered, nearest transport, access notes | complete without the map | yes |
| 9 | Footer | name, address, phone; newsletter with what will be sent; privacy, terms, accessibility statement; social link | small | yes |

Image-to-text ratio: **estimate**, from extraction counts only (references 4, 5 and 6 returned 1 to 9 images against roughly 1,700 to 3,400 characters; reference 2 returned 13 against 6,600). Text-led: a few strong photographs, and words for everything practical. A restaurant with no good photograph can open with text alone. Not confirmed in a rendered view.

### Skeleton B: the menu is the page

For a restaurant with a short menu that changes often and takes no reservations, or takes them elsewhere.
From reference 3.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; address; hours in one line; how to get a table ("no reservations - walk in") | all on the first screen | yes |
| 1 | Today's menu | the date as the heading; sections in order; each dish one line with its price; drinks with measure | date, then section, then dish and price | yes |
| 2 | Notes | service charge, extras, how to ask about allergens | small, directly under the menu | yes |
| 3 | About | two or three sentences | short | optional |
| 4 | Find us | address, map link, phone, hours per day | | yes |
| 5 | Footer | legal pages, social link | small | yes |

Image-to-text ratio: **estimate** (reference 3 returned 8 images against about 2,800 characters, almost all of it the menu). Almost entirely text. Not confirmed in a rendered view.

Risk: this skeleton is only honest if someone updates the menu. If the customer cannot name who updates it and how often, use Skeleton A with a "sample menu".

## 11. Not verified

1. All Hebrew and Arabic terms in section 6: author's knowledge, not checked with a working restaurateur. Cells marked "not verified" must not be filled by guessing.
2. Every legal statement in section 7. None was checked against a statute or an official source for this file.
3. Image-to-text ratios and visual quality of all references: text extraction only, no rendered view.
4. awwwards.com/websites/hotel-restaurant was not consulted; design quality of the references is the author's prior judgement.
5. No neighbourhood or family restaurant, no restaurant outside London, New York and San Francisco, and no delivery-led restaurant was verified.
6. Booking defaults in section 4 (15-minute step, 2 hours ahead, party of 6) are estimates; two of them lean on one reference each.
7. Sub-pages of the references (menu pages, location pages, booking flows) were not fetched. The outside booking systems named on the pages were not followed.
8. Footer and legal links: several extractions did not include footers, so their absence in this file proves nothing.
9. Whether the date on reference 3's menu was current or served from an older copy of the page.
10. No references in Hebrew, Arabic or any non-Latin script. These come in a later phase.
