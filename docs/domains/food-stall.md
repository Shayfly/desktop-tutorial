# Food stall, kiosk, food truck

Covers: a small business that sells a short menu of ready food or drink from a counter, a market stall, a kiosk or a vehicle, with little or no seating. Includes stalls that move between places and stalls that also cater events.
Does not cover: a place with tables and table service (use `restaurant.md`); a coffee shop or bakery with its own premises (use `cafe-bakery.md`); a stall that mainly sells raw meat or packed goods (use `butcher-deli.md`).
Written 2026-11-21. References checked 2026-11-21. Template: [README.md](README.md).

## 1. Objects

A stall sells **a few things, from one hatch, at a place that may change**. Everything else follows from that: the menu is short, the place and time must be stated for today, and food runs out.

### Stall (the business)

| Field | Required | Example (illustrative) |
|---|---|---|
| Name | required | "Smoke Cart" |
| What it sells, in one line | required | "Grilled cheese sandwiches", "Falafel in pita" |
| Kind of stall | required | fixed kiosk, market stall, food truck, cart, pop-up |
| Does it stay in one place or move | required | fixed / moves on a weekly pattern / moves with no pattern |
| Phone or messaging number | required | a number people can call or message |
| How people pay | required | cash only, card only, both, payment apps |
| How to order | required | walk up; pre-order by message; order through a delivery app |
| Email | optional | needed if event enquiries are taken |
| Social account | optional | often the place where today's location is announced |
| Dietary and religious status | optional, see rule 9 | vegetarian, vegan, kosher with a certificate, halal with a certificate |
| Does events and private hire | optional | yes / no |
| Short story | optional | who cooks, since when |

### Pitch (a place where the stall trades)

| Field | Required | Example |
|---|---|---|
| Name of the place | required | "Riverside Market, stall 14" |
| Address or a description people can find | required | street and number, or "car park behind the station" |
| Days and hours at this pitch | required | Sat-Sun 10:00-16:00 |
| Closing rule | required | a fixed time, or "until sold out" |
| Map link | optional | |
| Seating, shelter, toilets nearby | optional | "benches in the market hall" |
| Age limit or entry rule of the host place | optional | a bar that admits adults only |

A fixed kiosk has exactly one pitch. A market trader has a few. A food truck has a schedule.

### Schedule entry (only for a stall that moves)

| Field | Required | Example |
|---|---|---|
| Date, or day of the week | required | Friday 27 November |
| Pitch | required | name and address |
| Start and end time | required | 18:00-21:00 |
| Status | required | planned, confirmed, cancelled, sold out |
| Note | optional | "private event, not open to the public" |

### Menu item

| Field | Required | Example |
|---|---|---|
| Name | required | "Pulled pork roll" |
| Price | optional, see rule 3 | 9 |
| Size or variant rows | optional | small / regular / large, each with its own price |
| Short description | optional | what is in it |
| Group | optional | Mains, Sides, Drinks |
| Choices included in the price | optional | bread, sauce, filling |
| Extras with a price | optional | "extra cheese +1" |
| Allergens | see rule 7 | contains wheat, milk, sesame |
| Dietary tags | optional | vegetarian, vegan, made without gluten |
| Spicy level | optional | mild, hot |
| Available now | required, default yes | an item can be sold out today without being deleted |
| Seasonal or special | optional | "October only" |

### Other objects

| Object | Fields | Notes |
|---|---|---|
| Event enquiry | date, place, number of guests, kind of event, contact name, phone or email, message, status | Only when the stall does private hire. This is the only form most stalls need |
| Catering package | name, serves how many, price or "from", what is included | Optional |
| Closure or change | date, reason (weather, breakdown, holiday, private event) | Overrides the schedule |
| Review | text, first name or initials, date, source, count | Only real ones, with source |
| Certificate | kind (kosher, halal, hygiene rating, organic), issuing body, valid until | Required before the matching claim is shown |
| Gallery item | image, caption | The food and the stall itself; people look for the stall by how it looks |

## 2. Rules

1. Every menu item has a name. An item with no name is not shown.
2. A menu item appears once. Sizes are price rows of one item, not separate items.
3. A price is optional, but its absence is explicit: "ask at the stall", never blank and never zero.
4. Every price shows its currency. An extra that costs money shows its price next to it.
5. An item can be marked sold out for today. A sold-out item stays on the menu, marked, and cannot be ordered.
6. If the whole stall can sell out before closing time, the hours say so in words ("from 11:00 until sold out").
7. Allergen information is either shown per item or the page says exactly how to get it ("ask us before you order"). The page never says "allergen-free" or "safe for allergies".
8. "Made without gluten" is not "gluten-free". A stall with one shared grill does not claim an item is free of an allergen unless the customer said so and stands behind it.
9. Kosher, halal, organic and similar status are shown only when the customer named the certificate and its issuer. "Kosher style" or "halal" without a certificate is not written by the product.
10. A stall that moves shows where it is on a named date. A schedule entry has a date or weekday, a place and hours, all three.
11. A schedule entry in the past is not shown as upcoming. If the newest entry is in the past, the page says "no dates published yet - message us", not last month's schedule.
12. A cancelled entry is shown as cancelled until its date has passed. It is not silently removed.
13. A fixed stall states hours per day of the week, with closed days named.
14. A pitch inside a host place with its own entry rule (age limit, ticket, market opening days) shows that rule.
15. The way to pay is stated. "Cash only" and "card only" are both things a visitor must know before queuing.
16. The main action is one of: find us today, see the menu, order ahead, book us for an event. Exactly one is the main action; the others are secondary.
17. The phone number is a tappable link. Every address opens a map.
18. Photographs of food are of this stall's food. Stock photographs are not presented as its dishes.
19. A review is shown only if it is real and carries its source. A rating shows its count and source.
20. An event enquiry is not a booking. The page says the stall will reply, and the enquiry is confirmed only when the stall confirms it.

## 3. Mandatory facts

The product is not built until each of these has an answer from the customer. None may be guessed.

| # | Fact | The one question to ask | Why (the human reason) |
|---|---|---|---|
| 1 | Name | "What is the stall called?" | Without a name people cannot find it again or tell a friend. |
| 2 | What you sell | "What do you sell? Say it the way you would shout it to someone walking past." | A visitor decides in seconds whether to come over. |
| 3 | The menu | "List everything on the board today, with the price of each." | People choose before they reach the front of the queue. A wrong price starts an argument at the hatch. |
| 4 | Fixed or moving | "Are you always in the same place, or do you move?" | It decides the whole product: an address, or a schedule. |
| 5 | Where and when | Fixed: "Where exactly, and which days and hours?" Moving: "Where will you be this week, day by day, and who updates it when it changes?" | Without it people travel to an empty pavement. |
| 6 | When you stop serving | "Do you close at a set time, or when the food runs out?" | Someone arriving at 15:00 for a stall that sold out at 14:00 does not come back. |
| 7 | Phone or message number | "What number can people message to ask where you are?" | It is the only way to check when the page is out of date. |
| 8 | How people pay | "Cash, card, or both?" | A visitor with only a card at a cash stall leaves hungry. |
| 9 | Allergens | "Which of your items contain nuts, sesame, milk, eggs, wheat, fish or soy, and what should someone with an allergy do?" | An allergic reaction is the one failure here that can put a person in hospital. |
| 10 | Who is the business legally | "What is the registered business name and number, for the legal pages?" | The privacy and terms pages must name who is responsible. |

Needed only in some cases:

| # | Fact | The one question to ask | Why |
|---|---|---|---|
| 11 | Certificate behind a claim | "You said kosher (or halal, or organic). Who issued the certificate and until when is it valid?" | The claim is a promise to people who rely on it. Without a certificate the product does not write it. |
| 12 | Events | "Do you take private events? What is the smallest event, how far do you travel, and where do I send the enquiries?" | An enquiry nobody reads is a lost wedding. |
| 13 | Order ahead | "If people can order ahead: how do you receive the order, how long does it take, and how do they pay?" | An order the stall never saw is a visitor standing at the hatch with nothing ready. |

## 4. Declared defaults

Each default is shown to the customer as "we filled this in - change it if it is wrong". None of them is a fact about the business.

| Default | Value | Why it is safe | How it is marked |
|---|---|---|---|
| Main action | "Find us" for a moving stall; "See the menu" for a fixed one | Follows from mandatory fact 4; matches references 1 and 5 | Labelled "default main action" |
| Menu groups | none when there are 8 items or fewer (estimate); otherwise Mains, Sides, Drinks | A short board needs no headings | Editable, labelled "suggested" |
| Missing price | "Ask at the stall" | Says openly that there is no number | Listed in the customer's review as "no price given" |
| Missing allergen answer | "Ask us about allergens before you order" | Makes no claim | Listed as "allergen details not given" |
| Page order | Skeleton A below | Extracted from the references | Named as the default skeleton |
| Schedule display | the next 7 days, today first | A visitor asks "where are you today" | Setting, labelled "default" |
| Past schedule entries | hidden on the day after | Old dates mislead | Not changeable |
| Sold-out display | item stays visible, marked "sold out today" | Shows the stall has it on other days | Setting |
| Language and direction | the language of the conversation | The customer chose it by speaking it | Shown, changeable |
| Currency | the currency of the stall's country | Follows from the pitch address | Shown next to every price |
| Events section | hidden | Not every stall does events | Listed as "not shown: events" |
| Legal page structure | headings only | Structure is general; content is not | Marked "draft - not legal advice - review before publishing" |
| Empty optional sections | hidden | A missing gallery is better than an empty one | Listed for the customer as "not shown yet" |

Never a default, whatever the customer left out: prices, the menu, locations, dates, hours, allergen content, "kosher", "halal", "vegan", "organic", "homemade", "fresh daily", "local", "award-winning", hygiene ratings, reviews, photographs of food.

## 5. Failure modes

| What went wrong | What the visitor sees | What it costs | Prevention |
|---|---|---|---|
| Schedule is out of date | Travels to a place where the stall is not | A lost customer who tells others; the worst case in this domain | Rules 10-11; mandatory fact 5 names who updates it; show "last updated" |
| Stall sold out early | Arrives inside the stated hours, nothing left | A wasted trip | Rule 6; mandatory fact 6 |
| Cancelled for weather or breakdown, page unchanged | Stands in the rain at an empty pitch | Anger, public complaint | Closure object; one-tap "not trading today" for the owner |
| Price on the page is old | Pays more than the page said | An argument at the hatch | Date on the menu; prompt the customer to confirm prices on a schedule |
| Allergen missing or wrong | Eats something that harms them | A medical emergency; legal liability | Rules 7-8; mandatory fact 9; never write "free from" as a default |
| "Vegan" or "halal" written without basis | Relies on it and is misled | Loss of trust; in some places an offence | Rule 9; mandatory fact 11 |
| Cash only, not stated | Reaches the front of the queue and cannot pay | Lost sale, held-up queue | Rule 15 |
| Market closed that day, stall hours say open | Arrives at locked gates | Wasted trip | Rule 14; ask "does the market have its own opening days?" |
| Address is a market name only | Cannot find the stall among fifty | Gives up | Ask "how do people find you inside the market?"; photo of the stall front |
| Event form goes nowhere | Sends an enquiry, never hears back | A lost booking worth many days of trade | Mandatory fact 12; test the alert at setup; show "we reply within N days" only if the customer said N |
| Enquiry read as a confirmed booking | Believes the truck is coming | A ruined party | Rule 20 |
| Order-ahead accepted while closed or sold out | Pays or waits for food that will not be made | Refund, anger | Ordering is off outside trading hours and for sold-out items |
| Delivery-app link is dead | Taps "order", lands on an error | Silent loss | Check outbound links at publish and on a schedule |
| Stock food photos | The food handed over does not look like the picture | Distrust | Rule 18 |
| Seasonal stall still shows last season | Looks abandoned, or shows a menu that no longer exists | Lost trust | Ask for the season dates; show "back in spring" |

## 6. Professional language

Hebrew and Arabic terms are the author's knowledge and were not checked with a working trader in either language. Arabic usage varies by region; terms given are standard or Levantine. Where a cell says "not verified", do not use a guess.

| English | Meaning | Hebrew | Arabic |
|---|---|---|---|
| Stall | a counter in a market or on the street | דוכן | بسطة / كشك |
| Kiosk | a small fixed booth | קיוסק | كشك |
| Food truck | a vehicle that cooks and serves | פודטראק / משאית אוכל | عربة طعام / فود ترك (loanword; not verified) |
| Cart | a hand-pushed or towed unit | עגלה | عربة |
| Pitch | the spot where a trader stands | not verified | not verified |
| Street food | food sold to eat standing or walking | אוכל רחוב | أكل شوارع (not verified) |
| Menu | the list of what is sold | תפריט | قائمة الطعام / منيو |
| Dish, portion | one item as served | מנה | طبق / وجبة |
| Side | a small item next to the main one | תוספת | طبق جانبي (not verified) |
| Extra, topping | added for a charge | תוספת בתשלום | إضافة |
| Special | an item for today or this week only | מנת היום / ספיישל | طبق اليوم |
| Sold out | none left today | אזל | نفدت الكمية (not verified) |
| Takeaway (UK), to go (US) | food to carry away | טייק אוויי | سفري (Levant) / تيك أواي |
| Pre-order | ordering before arriving | הזמנה מראש | طلب مسبق |
| Delivery | brought to the buyer | משלוח | توصيل |
| Queue (UK), line (US) | people waiting | תור | طابور / دور |
| Cash only | no cards | מזומן בלבד | نقداً فقط |
| Allergens | ingredients that cause allergic reactions | אלרגנים | مسببات الحساسية |
| Vegetarian | no meat or fish | צמחוני | نباتي |
| Vegan | no animal products | טבעוני | نباتي صرف (not verified) |
| Gluten-free | no gluten | ללא גלוטן | خالٍ من الغلوتين |
| Kosher | permitted under Jewish dietary law | כשר | كوشير (not verified) |
| Kosher certificate | the document behind the claim | תעודת כשרות | not verified |
| Halal | permitted under Islamic dietary law | חלאל | حلال |
| Catering, private hire | serving at someone's event | קייטרינג / אירועים פרטיים | تموين حفلات (not verified) |
| Trader | the person running a stall | בעל דוכן | صاحب البسطة (not verified) |
| Street trading licence | permission to sell in a public place | רישיון רוכלות (not verified) | not verified |
| Hygiene rating | an inspection score shown to the public | not verified | not verified |
| Residency | a stall trading inside a bar or food hall for a period | not verified | not verified |

Notes on language:

- Visitors ask "where are you today?" and "what do you have?". The trade says "pitch", "service" and "covers"; do not put trade words on the page.
- UK and US English differ: takeaway / to go, queue / line, chips / fries, stall / stand.
- Words to avoid unless the customer said them and can back them: "best in town", "authentic", "homemade", "fresh daily", "healthy", "free from", "guilt-free", "award-winning".
- "Gluten-free", "allergy-safe" and "suitable for coeliacs" are claims with consequences. Use "made without" only when the customer chose it.

## 7. Legal

A checklist of questions, not legal advice. The author is not a lawyer and did not read the statutes for this file. Every item needs checking by someone qualified in the stall's country before it is relied on.

### Applies almost everywhere

- **Selling food needs registration or a licence**, and selling in a public place usually needs a further permission. The product does not check either. It never writes "licensed" or "approved" unless the customer supplied the detail.
- **Allergens.** Most jurisdictions require a food business to be able to tell a buyer which listed allergens are in each item. How (written, spoken, on a label) differs.
- **Privacy notice.** Needed as soon as the site collects a name and a phone number or email (an event form, an order). A menu-and-location page with no form collects nothing itself, but analytics and embedded maps may.
- **Terms.** Needed when money or orders are taken online: refunds, what happens when the stall cannot trade, deposits for events.
- **Religious and dietary claims** are regulated or treated as consumer-protection matters in many places.
- **Reviews** must be real.

### Israel

- A food business requires a business licence under the Business Licensing Law, with Ministry of Health conditions. How this applies to a mobile food truck, and whether municipalities issue permits for them: not verified.
- Street peddling requires a municipal permit. Details: not verified.
- Kosher: presenting a food business as kosher without a certificate from an authorised body is prohibited under the Kosher Fraud Prohibition Law. Which bodies are authorised today, after the kashrut reforms: not verified.
- Allergens: labelling rules for packaged food exist. What an unpackaged street-food seller must disclose, and how: not verified.
- Prices shown to consumers must include VAT (Consumer Protection Law). Not verified for menu boards specifically.
- Accessibility: a website of a business serving the public must be accessible and carry an accessibility statement, with exemptions for very small businesses by turnover. Thresholds: not verified.
- Privacy: the Protection of Privacy Law applies to an enquiry form. What it requires of a one-person stall: not verified.

### European Union and United Kingdom

- EU Regulation 1169/2011 lists 14 allergens and requires that information on them be available for non-prepacked food; member states decide the form. The UK kept the same list. Believed true; not verified against the text.
- UK: food packed on the premises before the buyer chooses it ("prepacked for direct sale") must carry a full ingredient list with allergens emphasised, since October 2021. Whether a given stall's wrapped items fall under it: not verified.
- UK: food businesses register with the local authority and are inspected under the Food Hygiene Rating Scheme. Displaying the rating is mandatory in Wales and Northern Ireland and voluntary in England: not verified.
- UK: street trading needs a licence or consent from the local council in most areas; markets have their own rules. Not verified.
- GDPR and UK GDPR apply to enquiry and order data. Consent is needed for non-essential cookies. One reference, Yum Bun, shows a cookie notice on its home page (observed 2026-11-21).
- Displayed consumer prices must include VAT: believed true in both; not verified.

### United States

- Mobile food vending is regulated by city and county: health permit, vending permit, commissary rules, where a truck may park. No single rule. Not verified per place.
- Federal law names nine major food allergens (sesame was added in 2023) for packaged-food labelling. Duties of an unpackaged-food vendor come from state and local food codes. Not verified.
- Sales tax on prepared food varies by state and city; menu prices usually exclude it. Not verified.
- The Americans with Disabilities Act is applied by courts to business websites in many cases. Not verified.

### What the product does with this

- The product asks which country and city the stall trades in before generating any legal page.
- The product may generate the **structure** of a privacy page and terms, each marked as a draft that needs review.
- The product never writes "licensed", "inspected", "kosher", "halal", "allergen-free" or "complies with" on its own.

## 8. Site vs app

### Content pages (no data, no accounts)

Home, menu, where to find us, about, event information, gallery, legal pages. For a fixed kiosk this is a complete and honest product: the menu, the address, the hours, the phone.

States still needed on content pages:

| Part | Empty | Error | Notes |
|---|---|---|---|
| Menu | cannot be empty (mandatory fact) | n/a | Shows the date it was last updated |
| Price | "ask at the stall" | n/a | Never blank |
| Hours | cannot be empty | | "Open now" needs the stall's time zone |
| Map | address as text always shown | if the map fails, the text and a link remain | |
| Gallery, reviews, events | section hidden | broken image hidden | Never placeholders |

### Needs data

| Part | What it needs | Empty state | Loading | Error | Save | Permissions |
|---|---|---|---|---|---|---|
| Schedule (moving stall) | dated entries the owner can change from a phone | "No dates published yet - message us" with the number | placeholder rows, never a blank that reads as "not trading" | "Could not load the schedule - message us" | a change is public at once; shows "updated today at 09:10" | owner writes; everyone reads |
| "Not trading today" switch | one flag with a date and an optional reason | n/a | | if the save fails, the owner is told plainly | applies to today only and clears itself | owner only |
| Sold-out marks | a flag per item, cleared each day | n/a | | a failed save says so | resets at the start of the next trading day | owner or staff |
| Event enquiry form | stores the enquiry; alerts the stall | n/a | button shows "sending" and cannot be pressed twice | "Not sent - please call or message" with the number | visitor sees "received - this is an enquiry, not a booking" | visitor writes; only the stall reads |
| Order ahead | menu with availability, a pickup time, a way to tell the stall | closed or sold out: ordering is off and says why | | "Order not placed - nothing was charged" | confirmed only after the stall's system has it; the visitor gets an order number | visitor sees own order; stall sees all |
| Owner edits menu and prices | an edit screen that works on a phone, one-handed | | | a failed save keeps what was typed | public right after saving | owner only |

### Needs accounts

- The owner needs one as soon as anything is editable. For a moving stall this is from day one, because the schedule changes weekly.
- Staff need one only if someone else marks items sold out.
- Visitors never need one. Ordering works with a name and a phone number.

### Needs payments

- Paying for an order ahead, and deposits for events.
- Each brings refunds, receipts, failed-payment states and the rule for a day the stall cannot trade.
- Default: no payments. Visitors pay at the hatch.

### Using existing channels

References 4 and 6 send ordering to an outside ordering or delivery service, and reference 7 to its own mobile app. Where the customer already takes orders that way, the product links to it and owns no order data. The failure mode is the link breaking silently (section 5).

Many moving stalls announce today's location on a social account. The product does not copy from it automatically. It asks the customer whether the site or the social account is the source of truth, and says so on the page.

## 9. References

**How these were checked.** Each URL was fetched on 2026-11-21 with a page-extraction tool that returns the page's text and image references. No browser was used and no screenshot was taken. So: section order and wording are observed; visual quality, layout and the image-to-text ratio are **not** observed, and every ratio below is an estimate from counts in the extracted text. Image counts include logos and icons. Some extractions omit navigation and footers, so "no legal links seen" means not seen in the extraction, not absent from the site.

**Curation.** Chosen by the author from known street-food businesses in the US and the UK, not from a search-result list. No awwwards.com category was consulted; none is claimed as an award winner. All are in English, in Latin script.

**Limit.** Several of these began as one truck or stall and are now small groups. One (reference 7) is a franchise. No single-cart business with a one-page site was verified.

Verified: 7.

| # | Site | Checked | What was observed |
|---|---|---|---|
| 1 | https://kogibbq.com | 2026-11-21 | Los Angeles food trucks. Order: one paragraph pitching the trucks for private events with a "book" action and a list of event kinds - then **Schedule**: a dated week, and under each weekday a list of stops, each with a place name, a street address as a link, and hours. One stop carries an age-limit note for its host venue. The dated week shown was 27 October to 1 November 2026, three weeks before the check: an example of the stale-schedule failure. No prices on the home page. Extraction: 5 images, about 4,500 characters. |
| 2 | https://www.kappacasein.com | 2026-11-21 | Cheesemaker with a hot-food stall at a London market. Order: one-line identity with founding year - two location links - two tiles (Cheeses, Hot Food), each with two short labels - a four-sentence history - contact form with visible success and failure messages - footer with wholesale and media links. No prices and no hours on the home page. Extraction: 8 images, about 2,500 characters. |
| 3 | https://www.oinkhogroast.co.uk | 2026-11-21 | Edinburgh hog-roast counters, three shops. Order: a top banner with hours ("every day from 11am until sell out") - a quoted review as headline with a "how to order" action - **the menu as four numbered steps**: choose a size (three sizes, each with weight and price), choose bread, choose stuffing, choose sauce, extras priced each - a no-bread variant with price - catering in three sizes by number of people served - three shop tiles leading to "find us and menus" - a review count with source and three reviews - the farm story - the hours again. Extraction: 22 images, about 5,600 characters. |
| 4 | https://www.yumbun.com | 2026-11-21 | London bao seller, two food-hall counters. Order: cookie notice - navigation (buns, menu, two locations, about, jobs) - headline - five items by name with images, no prices, and a "view menus" action - story - sourcing statements - **Visit us**: per location, the unit address, hours per group of days, a delivery-app note, an email and a menu link. Extraction: 35 images, about 8,200 characters. |
| 5 | https://www.mscheezious.com | 2026-11-21 | Miami grilled-cheese food truck at a fixed site. Order: one paragraph on what and where - **Location, phone, email, hours** as four plain blocks at the top - the full menu on the home page, each item a name and a one-line description, grouped (sandwiches, build your own, sides, drinks) - catering and an events form for the truck - contact - press. No prices seen in the extraction. Extraction: 12 images, about 16,000 characters, most of it menu. |
| 6 | https://veracruzallnatural.com | 2026-11-21 | Austin taco business that began as a truck, seven locations. Home page is five short action blocks: order now - our story - our menu - we deliver - come find us (one sentence and a "see locations" action) - the founders (one paragraph). Very little text. Extraction: 18 images, about 4,800 characters including repeated navigation. |
| 7 | https://www.cousinsmainelobster.com | 2026-11-21 | US franchise of lobster-roll trucks and restaurants. Order: a seven-slide carousel of offers - "three ways": find a truck nearby, find a restaurant, shop - four menu items with descriptions and no prices - sourcing by named harbour - catering - mobile app ordering and rewards - franchise sales. Truck location is a search, not a list. Used as the ceiling: what the domain looks like at franchise scale. Extraction: 84 images, about 20,600 characters. |

Loaded and not used:

| Site | Checked | Why not |
|---|---|---|
| https://www.wafelsanddinges.com | 2026-11-21 | Loads, but the extraction returned only headings (about 1,000 characters). Not enough to describe the structure. |
| https://www.luardos.co.uk | 2026-11-21 | Loads, but the content is now a catering-quotes lead page, not the burrito van the author expected. Not the business's own site in the sense of the rules. |
| https://www.nomnomtruck.com | 2026-11-21 | Loads. A blog-style site whose newest visible post is from 2010 with a 2025 copyright line. Shows what an abandoned truck site looks like; not a quality reference. |
| https://gourdoughs.com | 2026-11-21 | Loads, but the extraction returned three lines. Not enough. |
| https://www.theathenian.co.uk | 2026-11-21 | Loads. States 30+ locations; a chain. Navigation only in the extraction. |
| https://www.bleeckerburger.co.uk | 2026-11-21 | Loads. Began as a truck; now nine restaurant sites, and the home page is locations plus news. Belongs with restaurants. |

Did not load on 2026-11-21 and therefore not listed above: thecinnamonsnail.com, themeatwagon.co.uk, motherclucker.co.uk.

## 10. Skeletons

Structure only. No colours, logos, photographs or wording were taken from any reference.

### Skeleton A: the stall you have to find

For a truck, cart or market trader. Default for this domain when the stall moves or trades only on some days.
From references 1, 3, 4 and 5: the schedule of 1, the top-of-page facts of 5, the per-location block of 4, the "until sold out" line of 3.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; one action ("Find us today") | action is the most prominent element after the name | yes |
| 1 | Opening | one line: what is sold; one line: where it is today, or the next date | the place and time are as large as the name | yes |
| 2 | Where and when | fixed: address, hours per day, closing rule. Moving: the next 7 days, each with place, address link, hours, status | today first; cancelled entries marked, not removed | yes |
| 3 | Menu | every item on one line: name, short description, price or "ask at the stall"; sold-out mark; how to pay | a short board needs no group headings | yes |
| 4 | Allergens | per item, or one plain sentence on how to ask | directly under the menu, not in the footer | yes |
| 5 | The food and the stall | photographs of the food and of the stall front | images only | optional, hidden when empty |
| 6 | Who we are | one short paragraph | one heading, a few lines | optional |
| 7 | Book us for an event | what is offered, smallest event, enquiry form or contact | one heading, short text, one action | only if the stall does events |
| 8 | What people say | real reviews with source and count | at most three | optional, hidden when empty |
| 9 | Footer | name, phone, payment methods, social link, legal pages | small | yes |

Image-to-text ratio: **estimate**, from extraction counts only (references 1, 2 and 5 returned 5 to 12 images against roughly 2,500 to 16,000 characters). Text-led: the schedule and the menu are text. One strong image at the top and a short gallery are enough. Not confirmed in a rendered view.

### Skeleton B: the menu you build

For a stall that sells one thing with choices (a roll, a bowl, a wrap) from a fixed place.
From reference 3, with the location tiles of 3 and 4.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; hours in one line, including "until sold out" if true | hours visible before any scrolling | yes |
| 1 | Opening | one line saying what the one thing is; action "how to order" | one heading, one action | yes |
| 2 | How to order | numbered steps: size with price, then each choice, then extras with their price | step number, step name, options; price only where money changes | yes |
| 3 | Variants | the same thing without bread, for children, and so on, with price | short rows | optional |
| 4 | Allergens | per choice, or how to ask | under the steps | yes |
| 5 | Where | one tile per location: address, hours, map link | tile per place | yes |
| 6 | Catering | packages by number of people served | name, serves N, price or "from" | optional |
| 7 | Proof | review count with source, a few reviews | one line of numbers, then quotes | optional, hidden when empty |
| 8 | Story | where the food comes from | one paragraph | optional |
| 9 | Footer | as Skeleton A | | yes |

Image-to-text ratio: **estimate** (reference 3 returned 22 images against about 5,600 characters). Roughly one image per step or tile. Not confirmed in a rendered view.

## 11. Not verified

1. All Hebrew and Arabic terms in section 6: author's knowledge, not checked with a working trader. Cells marked "not verified" must not be filled by guessing.
2. Every legal statement in section 7. None was checked against a statute or an official source for this file.
3. Image-to-text ratios and visual quality of all references: text extraction only, no rendered view.
4. No awwwards.com category was consulted; design quality of the references is the author's prior judgement.
5. No single-cart business with a one-page site was verified. No reference from outside the US and the UK.
6. Footer and legal links of the references: several extractions did not include footers, so their absence in this file proves nothing.
7. The "8 items or fewer" threshold for menu groups and the 7-day schedule window in section 4 are estimates.
8. Sub-pages of the references (menu pages, location pages, event forms) were not fetched; observations are of home pages only. The targets of "order" links were not followed.
9. The statement that moving stalls announce locations on social accounts is the author's knowledge, not observed in the extractions.
10. Three candidate sites did not load and were not replaced by other single-truck sites.
11. No references in Hebrew, Arabic or any non-Latin script. These come in a later phase.
