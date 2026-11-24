# Cafe and bakery

Covers: a place that sells coffee and other drinks, bread, pastries or cakes made on the day, to eat in or take away. Includes coffee shops, neighbourhood bakeries, patisseries and cake makers who take orders.
Does not cover: a place where the main thing is a served meal at a table (use `restaurant.md`); a hatch or cart with no premises (use `food-stall.md`); a bakery brand that mainly ships packaged goods nationwide (use `clothing-shop.md` or `catalogue-collection.md` for the shop part).
Written 2026-11-21. References checked 2026-11-21. Template: [README.md](README.md).

## 1. Objects

A bakery sells **things made today, in a limited number, that run out**, and things made to order for a later day. A cafe adds a seat and a drink. Everything else follows from that: opening is early, the counter empties, and an order needs notice.

### Business

| Field | Required | Example (illustrative) |
|---|---|---|
| Name | required | "Crumb" |
| What kind of place | required | bakery, cafe, bakery-cafe, patisserie, cake studio by order only |
| Address, or "orders only, collection by arrangement" | required | street, number, city |
| Phone | required | |
| Opening hours, per day of the week | required | Tue-Fri 07:30-16:00, Sat-Sun 08:00-15:00, closed Mon |
| Closing rule | required | a fixed time, or "until sold out" |
| Eat in, take away, or both | required | "12 seats inside, take away" |
| Takes orders ahead | required | no / cakes only / anything, with how much notice |
| Email | optional | needed for orders and wholesale |
| Payment methods | optional | card only, cash and card |
| Seating, wifi, laptops, dogs, pushchairs, step-free access | optional | each only if the customer said it |
| Dietary and religious status | optional, see rule 10 | kosher dairy with certificate, vegan bakery |
| Sells wholesale | optional | to cafes and restaurants |
| Short story | optional | who bakes, since when, where the flour or coffee comes from |

### Location (only when there is more than one)

Address, phone, hours and what is sold there, repeated per location. Not every location bakes, and not every location takes orders. Each location says so.

### Product (something on the counter)

| Field | Required | Example |
|---|---|---|
| Name | required | "Country loaf", "Almond croissant" |
| Group | required | Bread, Pastry, Cake, Sandwich, Savoury |
| Price | optional, see rule 3 | 4.2 |
| Sold by | required when a price is shown | each, half, whole, per slice, per 100 g, box of 6 |
| Short description | optional | flours, filling |
| Allergens | see rule 8 | contains wheat, milk, eggs, almonds |
| Dietary tags | optional | vegan, made without gluten |
| Days baked | optional | "rye: Wednesday and Saturday only" |
| Ready from | optional | "bread out of the oven from 09:00" |
| Seasonal | optional | "December only" |
| Can be ordered ahead | optional | yes, with notice |
| Currently offered | required, default yes | |

### Drink

| Field | Required | Example |
|---|---|---|
| Name | required | "Flat white" |
| Price | optional | 3.6 |
| Size rows | optional | small / large, each with its price |
| Options | optional | oat milk +0.4, decaf, iced |
| Allergens | see rule 8 | milk; nut milks |

### Made-to-order item (cakes, platters, large orders)

| Field | Required | Example |
|---|---|---|
| Name | required | "Chocolate layer cake" |
| Sizes | required | each with how many it serves and its price |
| Notice needed | required | "7 days" |
| Choices | optional | flavour, filling, written message, candles |
| Allergens | see rule 8 | |
| How long it keeps and how to store it | optional | "keep chilled, eat within 2 days" |
| Collection or delivery | required | collection only / delivery within an area, with a fee |

### Order ahead (only when the product takes orders)

| Field | Required | Example |
|---|---|---|
| Items and quantities | required | |
| Choices and message on the cake | optional | exact text, as the visitor typed it |
| Collection date | required | |
| Collection time or time window | required | "Saturday 10:00-12:00" |
| Collection location | required when there is more than one | |
| Name and phone | required | |
| Email | optional | |
| Allergy note | optional | see Legal on health data |
| Status | required | requested, confirmed, ready, collected, cancelled, not collected |
| Paid, deposit, or pay on collection | required | |

### Other objects

| Object | Fields | Notes |
|---|---|---|
| Seasonal pre-order | name of the occasion, items, order deadline, collection dates, deposit | Holiday orders have their own deadline and their own collection days. Two references run one on the home page |
| Closure | date or range, reason | Holidays, annual break. Overrides the weekly hours |
| Class or workshop | name, date, length, price, places, what to bring | A booking with a date and a limited number of places |
| Gift card | value, where it can be spent, expiry, digital or in store | Involves payments |
| Wholesale enquiry | business name, contact, what and how much | A form, not an order |
| Subscription or club | what arrives, how often, price, how to stop | Bread or coffee on a schedule |
| Certificate | kind, issuer, valid until | Before any kosher, halal or organic claim |
| Review, press quote | text, source, date | Only real ones |
| Gallery item | image, caption | The counter, the bake, the room |

## 2. Rules

1. Every product belongs to one group. Sizes and "half or whole" are price rows of one product.
2. A product baked only on some days shows those days. It is not offered for collection on another day.
3. A price is optional, but its absence is explicit ("ask at the counter"). A price always says what it is for: each, per slice, whole.
4. Every price shows its currency. An option that costs extra shows its price.
5. Opening hours are stated per day of the week, with closed days named. If the counter can empty before closing, the page says so.
6. A closure date overrides the weekly hours.
7. A made-to-order item states how much notice it needs. An order for a date sooner than the notice is refused with the earliest possible date, not accepted.
8. Allergen information is shown per product, or the page says exactly how to get it. A bakery that uses nuts, sesame, wheat, eggs and milk in one room does not call any product "free from" unless the customer said so and stands behind it.
9. "Made without gluten" is not "gluten-free". "Vegan" is written only for products the customer named as vegan.
10. Kosher, halal and organic status are shown only with the certificate named. For kosher, dairy or parve status is stated if the customer gave it.
11. A collection date must be a day the collecting location is open, and the collection time inside its hours.
12. A seasonal pre-order has a deadline. After the deadline it shows "orders closed", with what to do instead.
13. The number of orders per collection day may be limited. When the limit is reached, that day shows as full.
14. The message to be written on a cake is stored and shown back exactly as typed, before the visitor confirms.
15. If a deposit or full payment is needed, and if a late cancellation is not refunded, the visitor sees it before confirming.
16. An order that is not collected stays in the record with that status.
17. A class has a number of places. Bookings cannot exceed it.
18. A gift card states where it can and cannot be spent.
19. The main action is one of: find us and hours, order ahead, see what we bake. It is reachable from every page on a phone.
20. The phone number is a tappable link. The address opens a map.
21. Photographs are of this bakery's own products. Stock photographs of bread and cake are not presented as its work.
22. Reviews and press quotes are real and carry their source.

## 3. Mandatory facts

The product is not built until each of these has an answer from the customer. None may be guessed.

| # | Fact | The one question to ask | Why (the human reason) |
|---|---|---|---|
| 1 | Name | "What is the place called?" | Without a name people cannot find it or recommend it. |
| 2 | What kind of place | "Is it a bakery, a cafe, both, or cakes by order only? Can people sit down?" | Someone looking for a table and someone looking for a loaf need different answers. |
| 3 | Where | "What is the full address? If you work from home and people only collect orders, say so." | Without it people cannot arrive. A home address may need to stay private. |
| 4 | Phone | "What number should people call or message?" | Without it people cannot ask whether there is bread left or change an order. |
| 5 | Opening hours | "Which days are you open, from when to when? Do you close when you sell out?" | Bakeries open early and empty early. Someone arriving at 15:00 for bread needs to know in advance. |
| 6 | What you make | "What is on the counter on a normal day? List it the way it is written on your labels, with prices if you want them shown." | Without it the visitor does not know whether to come. |
| 7 | Allergens | "Which of your products contain nuts, sesame, eggs, milk or wheat, and what should someone with an allergy do?" | Nuts and sesame in a bakery are the failure that can put a person in hospital. |
| 8 | Orders ahead | "Do you take orders in advance? For what, how much notice do you need, and how do people collect?" | A birthday cake ordered too late, or for a day you are closed, is a ruined birthday. |
| 9 | Who is the business legally | "What is the registered business name and number, for the legal pages?" | The privacy and terms pages must name who is responsible. |

Needed only when the product takes orders itself:

| # | Fact | The one question to ask | Why |
|---|---|---|---|
| 10 | Sizes and servings | "For each cake: which sizes, how many people does each serve, and what does each cost?" | People order by the number of guests. A cake for 8 at a party of 20 is the bakery's fault in their eyes. |
| 11 | How many orders a day | "How many orders can you make for one day?" | Without a limit, the Friday before a holiday takes more orders than the oven can bake. |
| 12 | Payment and cancellation | "Do people pay when they order, leave a deposit, or pay on collection? What if they cancel?" | A made cake nobody collects is money in the bin. The buyer must know the rule before ordering. |
| 13 | Where order alerts go | "Where should I send each new order: which phone or email, and who reads it?" | An order nobody saw is a customer at the counter on the day with no cake. |

Needed only in some cases:

| # | Fact | The one question to ask | Why |
|---|---|---|---|
| 14 | Certificate behind a claim | "You said kosher (or halal, or organic). Who issued the certificate and until when?" | People rely on it. Without a certificate the product does not write it. |
| 15 | Days baked | "Is everything baked every day, or are some things only on certain days?" | Someone who crosses town for the rye on a Tuesday needs to know it is a Wednesday bread. |

## 4. Declared defaults

Each default is shown to the customer as "we filled this in - change it if it is wrong". None of them is a fact about the business.

| Default | Value | Why it is safe | How it is marked |
|---|---|---|---|
| Group names and order | Bread, Pastry, Cakes, Savoury, Drinks (Drinks first for a cafe) | Standard structure | Editable, labelled "suggested order" |
| Which group a product falls in | by its name | Wrong placement is visible and easy to fix | Customer confirms the grouped list |
| Missing price | "Ask at the counter" | Says openly that there is no number | Listed as "no price given" |
| Missing allergen answer | "Please ask us about allergens before you buy" | Makes no claim | Listed as "allergen details not given" |
| Main action | "Find us" with hours and address | Works with zero setup | Labelled "default" |
| Ordering | off; "to order, call us" with the number | Cannot take an order nobody reads | Labelled "default: orders by phone" |
| Notice for a made-to-order item, when ordering is on and none was given | not filled: the product asks | Notice is a fact about this kitchen | Blocks turning ordering on |
| Collection windows | the opening hours of the collecting location, in 2-hour windows | Estimate | Setting, labelled "default" |
| Page order | Skeleton A below | Extracted from the references | Named as the default skeleton |
| Language and direction | the language of the conversation | The customer chose it by speaking it | Shown, changeable |
| Currency | the currency of the bakery's country | Follows from the address | Shown next to every price |
| Legal page structure | headings only | Structure is general; content is not | Marked "draft - not legal advice - review before publishing" |
| Empty optional sections | hidden | A missing gallery is better than an empty one | Listed as "not shown yet: classes, wholesale, gift cards, press" |

Never a default, whatever the customer left out: products, prices, hours, notice periods, servings, allergens, "sourdough", "organic", "wholegrain", "handmade", "baked fresh daily", "vegan", "gluten-free", "kosher", "specialty coffee", where the beans or flour come from, wifi, seating, awards, reviews, photographs.

## 5. Failure modes

| What went wrong | What the visitor sees | What it costs | Prevention |
|---|---|---|---|
| Hours are old, or a holiday is not marked | Arrives at a closed door | A lost regular | Ask for hours explicitly; closure object; prompt before holidays |
| Sold out, page says open | Arrives in the afternoon to empty shelves | A wasted trip | Rule 5; mandatory fact 5 |
| Product baked only some days, not stated | Comes for it on the wrong day | A wasted trip | Rule 2; mandatory fact 15 |
| Cake ordered with too little notice and accepted | Is told the day before that it cannot be made | A ruined occasion; the worst case in this domain | Rule 7, enforced when the order is saved |
| Collection set for a closed day | Stands outside with a party in two hours | The same | Rule 11 |
| Order saved but the bakery never told | Arrives to collect; nothing was made | The same | Mandatory fact 13; status "requested" until confirmed; test the alert at setup |
| Holiday pre-orders accepted without a limit | Collects a late or smaller order, or queues for an hour | Refunds, anger on the busiest day of the year | Rules 12-13; mandatory fact 11 |
| Cake message misspelt or cut off | A name spelt wrong on the cake, in front of guests | Remake or refund | Rule 14 |
| Size sold without servings | Cake too small for the party | Blame | Mandatory fact 10 |
| Allergen missing or wrong | Eats or serves something that harms someone | A medical emergency; liability | Rule 8; mandatory fact 7 |
| "Gluten-free" or "vegan" written by the builder | Relies on it and is harmed or misled | The same, plus loss of trust | Rule 9; never a default |
| Deposit kept, rule unclear | Feels cheated | Dispute, chargeback | Rule 15 |
| Order form open at a location that does not take orders | Orders, then is told to go across town | Lost order | Each location states what it does |
| Gift card sold online, not accepted at one shop | Refused at the till | Embarrassment, refund | Rule 18 |
| Class overbooked | Arrives to a full room | Refund and travel cost | Rule 17 |
| Stock photos | The cake does not look like the picture | Distrust | Rule 21 |
| Price shown without unit | Expects a whole cake for the price of a slice | An argument at the till | Rule 3 |
| "Order" link goes to a dead outside page | Taps, gets an error | Silent loss | Check outbound links at publish and on a schedule |

## 6. Professional language

Hebrew and Arabic terms are the author's knowledge and were not checked with a working baker or barista in either language. Arabic usage varies by region. Where a cell says "not verified", do not use a guess.

| English | Meaning | Hebrew | Arabic |
|---|---|---|---|
| Bakery | bakes and sells bread and pastry | מאפייה | مخبز |
| Patisserie, pastry shop | cakes and fine pastry | קונדיטוריה | محل حلويات |
| Cafe, coffee shop | drinks and a seat | בית קפה | مقهى / كافيه |
| Baker | the person who bakes | אופה | خبّاز |
| Pastry chef | makes cakes and pastry | קונדיטור / קונדיטורית | حلواني |
| Barista | makes the coffee | בריסטה | باريستا |
| Bread, loaf | | לחם, כיכר | خبز، رغيف |
| Sourdough | bread raised with a natural starter | לחם מחמצת | خبز العجين المخمّر (not verified) |
| Pastry (the item) | croissants, buns and similar | מאפה | معجنات |
| Viennoiserie | butter-layered pastry | מאפי בצק עלים (not verified) | not verified |
| Cake | | עוגה | كعكة / كيك |
| Whole cake, slice | how it is sold | עוגה שלמה, פרוסה | كعكة كاملة، قطعة |
| Custom cake, celebration cake | made to order for an occasion | עוגה מעוצבת / עוגה בהזמנה | كيك حسب الطلب (not verified) |
| Serves | how many people a cake feeds | מספיק ל-N סועדים (not verified) | يكفي N أشخاص (not verified) |
| Pre-order | ordering before the day | הזמנה מראש | طلب مسبق |
| Lead time, notice | how long before the date an order is needed | זמן הזמנה מראש (not verified) | not verified |
| Collection (UK), pickup (US) | the buyer comes to get it | איסוף עצמי | استلام |
| Sold out | none left today | אזל | نفدت الكمية (not verified) |
| Eat in / take away | | לשבת / לקחת | not verified / سفري (Levant) |
| Espresso, filter coffee | | אספרסו, קפה פילטר | إسبريسو، قهوة مفلترة (not verified) |
| Flat white, cappuccino, latte | milk coffees | names used as in English; in Hebrew "הפוך" is the common local order | names used as in English (not verified) |
| Plant milk | oat, soy, almond | חלב צמחי / תחליף חלב | حليب نباتي |
| Decaf | without caffeine | נטול קפאין | منزوع الكافيين |
| Roaster | the company that roasts the beans | בית קלייה | محمصة |
| Wholesale | selling to other businesses | סיטונאות | بيع بالجملة |
| Allergens | | אלרגנים | مسببات الحساسية |
| Gluten-free | | ללא גלוטן | خالٍ من الغلوتين |
| Vegan | | טבעוני | نباتي صرف (not verified) |
| Kosher dairy / parve | kosher status of a baked product | כשר חלבי / פרווה | not verified |
| Gift card, voucher | | שובר מתנה / גיפט קארד | بطاقة هدية |
| Bake schedule | which breads on which days | not verified | not verified |

Notes on language:

- UK and US English differ: collection / pickup, takeaway / to go, biscuit / cookie, wholemeal / whole wheat. Pick one by the country.
- Product names stay as the bakery writes them on its labels. Add a description; do not translate or rename.
- Words to avoid unless the customer said them and can back them: "artisan", "handmade", "homemade", "fresh daily", "sourdough", "organic", "wholegrain", "healthy", "sugar-free", "guilt-free", "best coffee".
- "Sourdough" and "wholegrain" have legal or code-of-practice meanings in some countries. The product writes them only when the customer did.

## 7. Legal

A checklist of questions, not legal advice. The author is not a lawyer and did not read the statutes for this file. Every item needs checking by someone qualified in the bakery's country before it is relied on.

### Applies almost everywhere

- **Allergens.** A food business must be able to tell a buyer which listed allergens are in each product. Food that is wrapped before the buyer chooses it is often treated more strictly than food served from an open counter.
- **Privacy notice.** Needed as soon as the site takes an order, an enquiry or a newsletter signup.
- **An allergy note on an order is health data** in many places. Default: do not store it longer than the order.
- **Terms.** Needed when orders or money are taken: notice, cancellation, deposit, uncollected orders, gift-card expiry, delivery area and fee.
- **Perishable and made-to-order goods** are commonly excluded from the right to cancel an online purchase. The exclusion and its wording differ by country.
- **Home baking for sale** is regulated: in some places allowed under limits, in others not. The product does not check it.
- **Marketing messages** need prior agreement. An order confirmation is not marketing.
- **Health and nutrition claims** ("healthy", "low sugar") are regulated.

### Israel

- A bakery or cafe requires a business licence under the Business Licensing Law, with Ministry of Health conditions. Whether baking for sale from a home kitchen can be licensed: not verified.
- Kosher: presenting a bakery as kosher without a certificate from an authorised body is prohibited under the Kosher Fraud Prohibition Law. Which bodies are authorised today: not verified.
- Passover: rules on displaying leavened products for sale during the holiday exist. What they require of a bakery, and whether a website is affected: not verified.
- Prices shown to consumers must include VAT (Consumer Protection Law). Not verified for counter labels and online lists specifically.
- Allergen labelling for packaged food exists; duties for unpackaged counter products: not verified.
- Cancelling a distance transaction: the Consumer Protection Law gives cancellation rights with exceptions for perishable goods and goods made to the buyer's order. How this applies to an ordered cake: not verified.
- Gift vouchers: rules on minimum validity exist. Details: not verified.
- Accessibility: the website of a business serving the public must be accessible and carry an accessibility statement, with exemptions for very small businesses by turnover. Thresholds: not verified.
- Privacy and marketing messages: the Protection of Privacy Law and section 30A of the Communications Law. Details: not verified.

### European Union and United Kingdom

- EU Regulation 1169/2011 lists 14 allergens and requires that information on them be available for non-prepacked food. The UK kept the list. Believed true; not verified against the text.
- UK: food packed on the premises before the buyer chooses it ("prepacked for direct sale", for example a wrapped sandwich or a boxed pastry in a chiller) must carry a full ingredient list with allergens emphasised, since October 2021. Not verified.
- "Gluten-free" is a regulated term in the EU and the UK with a limit of 20 parts per million. Believed true; not verified.
- Distance selling: the right to cancel does not apply to goods that spoil quickly or are made to the buyer's specification. Believed true in both; not verified.
- GDPR and UK GDPR apply to order data. Consent is needed for non-essential cookies.
- Displayed consumer prices must include VAT: believed true; not verified.
- UK: food businesses register with the local authority, including home bakers selling regularly. Not verified.
- European Accessibility Act, from June 2025, covers e-commerce with a microenterprise exemption. Whether a small bakery's order page is in scope: not verified.

### United States

- "Cottage food" laws let home bakers sell certain goods under limits that differ by state (what, how much, where, labelling). Not verified per state.
- Nine major allergens are named in federal law for packaged-food labelling. Not verified.
- The Americans with Disabilities Act is applied by courts to business websites. One reference, Levain Bakery, carries a link at the very top of its page to a notice of a class-action settlement under that law (observed 2026-11-21; the content of the notice was not read).
- Privacy is by state. One reference, Dominique Ansel, has a "do not sell my info" link for California in its footer (observed 2026-11-21).
- Gift-card expiry is limited by federal and state law. Not verified.

### What the product does with this

- The product asks which country the bakery is in before generating any legal page.
- The product may generate the **structure** of a privacy page, terms and an accessibility statement, each marked as a draft that needs review.
- The product never writes "gluten-free", "allergen-free", "kosher", "organic", "licensed" or "complies with" on its own.

## 8. Site vs app

### Content pages (no data, no accounts)

Home, what we bake, drinks, cakes to order (as information), find us, about, classes (as information), wholesale (as information), legal pages. With a phone link this is a complete and honest product for a bakery that takes orders by phone or message.

States still needed on content pages:

| Part | Empty | Error | Notes |
|---|---|---|---|
| Product list | cannot be empty (mandatory fact) | n/a | Shows the date it was last updated |
| Price | "ask at the counter" | n/a | Always with its unit |
| Hours | cannot be empty | | "Open now" needs the time zone and the closures |
| Map | address as text always shown | if the map fails, the text and a link remain | |
| Gallery, press, classes | section hidden | broken image hidden | Never placeholders |

### Needs data

| Part | What it needs | Empty state | Loading | Error | Save | Permissions |
|---|---|---|---|---|---|---|
| Order request (bakery confirms by hand) | stores the request; alerts the bakery | no date possible yet: "Earliest collection is Thursday 26th" | dates show a placeholder, never a blank that reads as "no dates" | "Not sent - please call" with the number | status "requested"; told plainly it is not confirmed | visitor sees own order through a link; bakery sees all |
| Live order with payment | items with notice and sizes, a daily limit, open days, closures | day full: "Fully booked for Friday - nearest days" | | payment failed: "Nothing was charged - try again or call" | confirmed only after payment and save; the visitor gets a confirmation with the collection time and the cake message | visitor: own order; staff: the day's list; owner: everything |
| Seasonal pre-order | a deadline, collection days, a limit | after the deadline: "Orders for the holiday are closed" with what is still possible | | | as above | as above |
| The day's order list | orders by collection time, with choices and messages | "No orders for today" | | never show a stale list without saying so | marking "ready" and "collected" saved at once | staff, behind a login |
| Owner edits products, prices, hours, closures | an edit screen | | | a failed save keeps what was typed | public right after saving | owner only |
| Sold-out marks | a flag per product, cleared each day | | | | resets at the next opening | owner or staff |
| Class booking | dates, places, price | "No dates yet - leave your email" only if the customer wants a list | | | place is held only after the server saved it | visitor: own booking; owner: all |
| Wholesale or event enquiry | stores it; alerts the bakery | n/a | button cannot be pressed twice | "Not sent - please email" | "received - we will reply" | visitor writes; only the bakery reads |
| Newsletter signup | an address and proof of agreement | | | | says what will be sent and how to stop | owner only |

### Needs accounts

- The owner needs one as soon as anything is editable or any order is stored.
- Staff need one if someone else works the order list.
- Visitors do not need one to order. A phone number and a link are enough. An account is justified only for a subscription or a loyalty scheme.

### Needs payments

- Orders paid in advance, deposits, gift cards, classes, subscriptions, delivery or shipping.
- Each brings refunds, receipts, failed-payment states and the cancellation law of the country.
- Default: no payments; pay on collection. Payment is added only when the customer asks and has stated the cancellation rule (mandatory fact 12).

### Shipping is a different business

References 6 and 7 are shop-led: the home page sells boxes shipped nationwide. That needs stock, postage, delivery promises and returns. It is a shop that happens to bake. If the customer wants it, use the shop domain for that part and keep this file for the counter and the collection orders.

### Using existing channels

Reference 1 sends nationwide shipping to an outside marketplace, and reference 7 sends local delivery to outside delivery services. Where the customer already takes orders that way, the product links to it and owns no order data. The failure mode is the link breaking silently (section 5).

## 9. References

**How these were checked.** Each URL was fetched on 2026-11-21 with a page-extraction tool that returns the page's text and image references. No browser was used and no screenshot was taken. So: section order and wording are observed; visual quality, layout and the image-to-text ratio are **not** observed, and every ratio below is an estimate from counts in the extracted text. Image counts include logos and icons. Some extractions omit navigation and footers.

**Curation.** Chosen by the author from well-known bakeries in the US, the UK and Australia, not from a search-result list. No awwwards.com category was consulted; none is claimed as an award winner. All are in English, in Latin script.

**Limit.** All eight are bakeries with several shops, a school or a shipping business. **No pure coffee shop and no single-shop neighbourhood bakery was verified**: the one coffee-led candidate loaded with almost no content (see the rejected list). The cafe half of this file therefore rests on the author's knowledge, not on references.

Verified: 8.

| # | Site | Checked | What was observed |
|---|---|---|---|
| 1 | https://tartinebakery.com | 2026-11-21 | San Francisco and Los Angeles bakery group. Order: a one-line welcome - "happenings": jobs, nationwide shipping through an outside marketplace - **special-order cakes, with the notice period stated in the sentence (seven days)** - pre-order cakes and tarts - gift cards, naming where they can be redeemed - a film - who we are - a press quote - the book. Each block is a heading and one or two sentences. Extraction: 9 images, about 1,500 characters. |
| 2 | https://e5bakehouse.com | 2026-11-21 | London bakery with a mill, a school and a second site. Order: name - a three-paragraph story (how it began, how it sources, a thank-you to photographers) - six tiles: gift certificates, online school, farm produce, in-person school, online shop, the second bakehouse - a seasonal gifts block saying which vouchers are digital and which are sold only in store - email and locations. Extraction: 15 images, about 4,000 characters. |
| 3 | https://www.flourbakery.com | 2026-11-21 | Boston bakery-cafe group. Order: a two-sentence statement - catering with an order action - cakes - a holiday pre-order "for pickup or local delivery" in a named week - a rewards app ("skip the line") - a monthly take-home dinner club - jobs - **Where to find us**, with a "see all bakeries" action and a tile per bakery. Each block is a heading, one sentence and one action. Extraction: 23 images, about 4,200 characters. |
| 4 | https://www.pophamsbakery.com | 2026-11-21 | London bakeries with a homeware shop. Order: "Bakery and homeware" - name - three paragraphs (what it is, how it began, coffee and makers) - a statement about people - gift card, saying it can be spent across bakeries and shops, digital or in store - a packaged biscuit range - a pasta kit sold from one named shop - footer menu (search, FAQs, locations, careers) - newsletter. No prices and no hours on the home page. Extraction: 23 images, about 4,200 characters. |
| 5 | https://lunecroissanterie.com | 2026-11-21 | Australian croissant bakery, nine shops. Order: a video with a skip control - "order now" - a five-line statement - one paragraph - **a list of the nine shops, each a name and a street address with entry directions** ("entry via ... lane") - contact. Almost nothing else. Extraction: 1 image reference (the video), about 1,600 characters. |
| 6 | https://www.breadahead.com | 2026-11-21 | London bakery and baking school, with a New York school. Order: newsletter - gift vouchers for workshops - a youth baking project - the New York school - **six workshops as cards, the first with a "from" price** - plan your visit (locations, courses, vouchers, story). On this page the school leads and the bakery counter is one link. Extraction: 11 images, about 3,300 characters. |
| 7 | https://www.dominiqueansel.com | 2026-11-21 | New York and Hong Kong pastry shops. Order: region selector - five promotional tiles - **the monthly pastry available for pre-order, with flavour and the collection start date** - local delivery through outside services - a new shop with address and daily hours - a cookbook - a workshop cafe - nationwide shipping - an online class - social feed - newsletter - footer with cookie policy, privacy policy, terms of use and a California privacy link. Extraction: 28 images, about 24,500 characters, much of it the social feed. |
| 8 | https://www.levainbakery.com | 2026-11-21 | New York cookie bakery, shop-led. Order: a link to an accessibility-law settlement notice - cart with upsell items - shipping offers - a new product - "made in NYC / baked fresh daily / shipped same-day" - best-sellers as product cards - same-day delivery or pickup - gifts, corporate gifts, events, catering - press quotes with the publication named - the founding story. Used as the ceiling: what the domain becomes when shipping leads. Extraction: 41 images, about 9,100 characters. |

Loaded and not used:

| Site | Checked | Why not |
|---|---|---|
| https://www.monmouthcoffee.co.uk | 2026-11-21 | Loads, but the extraction returned one blog teaser (about 350 characters). Not enough to describe the structure. This was the only coffee-led candidate. |
| https://www.thedustyknuckle.com | 2026-11-21 | Loads. On the day the home page was a merchandise drop for the bakery's youth programme, with no bakery structure in the extraction. |

## 10. Skeletons

Structure only. No colours, logos, photographs or wording were taken from any reference.

### Skeleton A: the neighbourhood bakery or cafe

For one or a few shops whose site has one job: say what is baked, when the door is open, and how to order a cake. Default for this domain.
From references 1, 3 and 5: the short blocks of 1 and 3, the shop list of 5, the order blocks of 1 and 3. The product list and the hours block are not from the references' home pages; they follow from mandatory facts 5 and 6.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; one action ("Find us" or "Order ahead") | action is the most prominent element after the name | yes |
| 1 | Opening | one sentence: what kind of place, where; today's hours in one line, with "until sold out" if true | one heading, one line of facts | yes |
| 2 | What we bake | groups in order; each product on one line: name, short note, price with unit; days baked where they differ | group heading over rows | yes |
| 3 | Drinks | short list with prices and milk options | compact | only for a cafe |
| 4 | Allergens | per product, or one plain sentence on how to ask | directly under the lists | yes |
| 5 | Order ahead | what can be ordered, the notice needed, how to collect, one action | heading, two sentences, one action | only if orders are taken |
| 6 | Seasonal block | the current holiday order, with deadline and collection days | appears only in season, above section 2 while it runs | optional |
| 7 | The bake and the room | photographs | images only | optional, hidden when empty |
| 8 | About | who bakes, since when | one paragraph | optional |
| 9 | Find us | per shop: address as text with entry note, map link, phone, hours per day, what this shop does (bakes, seats, takes orders) | complete without the map | yes |
| 10 | Footer | name, phone, address; gift cards, wholesale, jobs if they exist; privacy, terms, accessibility statement; social link | small | yes |

Image-to-text ratio: **estimate**, from extraction counts only (references 1, 3 and 4 returned 9 to 23 images against roughly 1,500 to 4,200 characters). Roughly one image per short block: each block is an image, a heading, one sentence and one action. Not confirmed in a rendered view.

### Skeleton B: the bakery with more than a counter

For a bakery that also runs classes, sells vouchers or sends orders further than its street. Use only when those things exist.
From references 2, 6 and 7; the tile grid is from 2, the workshop cards from 6, the pre-order block from 7.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | navigation in groups: Bakery, Order, Classes, Shop; "Find us" always visible | the way to the shops is never hidden behind the shop menu | yes |
| 1 | Opening | one sentence; two actions: find us, order | two actions | yes |
| 2 | What is on now | the current pre-order or seasonal item, with dates | one block, dated | optional |
| 3 | Ways in | tiles: the bakery, order ahead, classes, gift vouchers, online shop | one tile each, image and label | yes |
| 4 | Classes | upcoming dates as cards: name, date, price or "from", places left | card per class | only if offered |
| 5 | Story | how it began, how it sources | two or three paragraphs | optional |
| 6 | Find us | as section 9 of Skeleton A | | yes |
| 7 | Footer | as Skeleton A, plus delivery, returns and voucher terms | | yes |

Image-to-text ratio: **estimate** (references 2 and 6 returned 15 and 11 images against roughly 4,000 and 3,300 characters; reference 7 returned 28). Image-led tiles and cards. Not confirmed in a rendered view.

Risk seen in references 6 and 8: when the school or the shipping shop leads, the opening hours of the actual counter are several steps away. If most of the customer's income is the counter, use Skeleton A.

## 11. Not verified

1. All Hebrew and Arabic terms in section 6: author's knowledge, not checked with a working baker or barista. Cells marked "not verified" must not be filled by guessing.
2. Every legal statement in section 7. None was checked against a statute or an official source for this file.
3. Image-to-text ratios and visual quality of all references: text extraction only, no rendered view.
4. No awwwards.com category was consulted; design quality of the references is the author's prior judgement.
5. **No coffee-shop reference and no single-shop bakery reference was verified.** Sections on drinks, seating and the cafe side rest on the author's knowledge.
6. None of the references showed a product list with prices or opening hours on its home page in the extraction; those parts of Skeleton A come from the mandatory facts, not from the references.
7. The 2-hour collection window in section 4 is an estimate.
8. Sub-pages of the references (menus, order flows, location pages, class booking) were not fetched. Outside marketplaces and delivery services named on the pages were not followed.
9. The content of the settlement notice linked from reference 8 was not read.
10. No references in Hebrew, Arabic or any non-Latin script. These come in a later phase.
