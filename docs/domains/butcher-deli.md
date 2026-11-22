# Butcher and delicatessen

Covers: a shop that sells meat cut to the buyer's request, and a shop that sells cured meat, cheese, prepared foods and fine groceries over a counter. Includes butchers who take holiday orders, and delis that make sandwiches and platters.
Does not cover: a deli that is mainly a sit-down eating place (use `restaurant.md`); a hatch selling one hot item (use `food-stall.md`); a packaged-food brand with no counter (use `catalogue-collection.md`).
Written 2026-11-21. References checked 2026-11-21. Template: [README.md](README.md).

## 1. Objects

A butcher sells **by weight, cut the way the buyer asks, from a supply that is limited by the animal**. A deli sells by weight or by piece from a counter. Everything else follows from that: a price has a unit, a product has a preparation, the final price is known only at the scale, and the best cuts run out before a holiday.

### Shop (the business)

| Field | Required | Example (illustrative) |
|---|---|---|
| Name | required | "Miller & Son" |
| What kind of shop | required | butcher, deli, butcher and deli, cheese and charcuterie, with or without a kitchen |
| Which animals and goods | required | beef, lamb, poultry; "no pork"; game in season; cheese; prepared food |
| Religious status | required to ask, see rule 11 | kosher with certificate, halal with certificate, neither |
| Address | required | street, number, city |
| Phone | required | orders are still mostly taken by phone in this trade |
| Opening hours, per day of the week | required | Tue-Fri 08:00-18:00, Sat 08:00-15:00, closed Sun-Mon |
| How to order | required | at the counter only; phone orders; online for collection; delivery |
| Email | optional | |
| Where the meat comes from | optional | named farms or regions, only as the customer states them |
| Payment methods | optional | |
| Parking, loading | optional | people carry heavy bags |
| Short story | optional | since when, who cuts |

### Location (only when there is more than one)

Address, phone and hours per location. Reference 1 shows three shops, each with its own address and its own row of hours. Orders are placed with, and collected from, a named location.

### Department and product

Products are grouped by department: by animal (Beef, Lamb, Pork, Poultry, Game) and by kind (Sausages and burgers, Cured and cooked, Cheese, Prepared food, Pantry, Drinks).

| Field | Required | Example |
|---|---|---|
| Name | required | "Rib of beef on the bone" |
| Department | required | Beef |
| Price | optional, see rule 3 | 44.5 |
| Price unit | required when a price is shown | per kg, per 100 g, per lb, each, per pack of 6 |
| Typical weight or size | optional | "a rib for four is about 2 kg" |
| Feeds | optional | "serves 4-6" |
| Short description | optional | what the cut is, how to cook it |
| Preparation options | optional | on or off the bone, rolled and tied, butterflied, minced, diced, sliced thick or thin |
| Origin | optional | country, region or farm, as stated by the customer |
| Breed, feed, ageing | optional | "grass-fed", "dry-aged 35 days", only as stated by the customer |
| State | optional | fresh, frozen, previously frozen, cooked, cured, smoked |
| Allergens | see rule 9 | sausages: wheat, sulphites; cheese: milk |
| Ingredients | required for made products where the law asks | sausages, marinades, pies, salads |
| Keeps for | optional | "use within 3 days, or freeze on the day" |
| Needs ordering ahead | optional | whole birds, large joints, unusual cuts |
| In season | optional | game, spring lamb, holiday birds |
| Available | required, default yes | |

### Deli counter items

| Field | Required | Example |
|---|---|---|
| Name | required | "Pastrami", "Aged gouda" |
| Sold by | required | per 100 g, per piece, per portion |
| Cut | optional | sliced thin, thick, in a piece |
| Milk and treatment (cheese) | optional | cow, sheep, goat; raw or pasteurised |
| Made here or bought in | optional | |
| Sandwich or plate (if a kitchen exists) | name, what is in it, price | A small menu; see `food-stall.md` for menu rules |
| Platter | name, serves how many, price, notice needed | |

### Order (only when the product takes orders)

| Field | Required | Example |
|---|---|---|
| Items, each with weight or number and preparation | required | "leg of lamb, about 2.5 kg, boned and rolled" |
| Collection or delivery | required | |
| Location, date and time window | required | |
| Name and phone | required | |
| Notes | optional | "for 10 people" |
| Estimated total | derived | from the price per unit and the requested weight |
| Final total | set at the scale | |
| Deposit | optional | |
| Status | required | requested, confirmed, prepared, collected or delivered, cancelled, not collected |

### Other objects

| Object | Fields | Notes |
|---|---|---|
| Holiday order book | occasion, product list with size bands (weight range, feeds how many, guide price range, price per kg), order deadline, collection dates and hours, deposit, how to order | The busiest and riskiest days of the year. Reference 4's home page is exactly this |
| Box or bundle | name, contents, weight, fixed price | A fixed price, unlike loose meat |
| Delivery rule | areas, days, minimum order, fee, how it is kept cold | Only when delivery exists |
| Class | name, date, length, price, places | Butchery classes; three references sell them |
| Supplier | farm or producer name, place, what they supply | Only as stated by the customer; reference 3 lists them |
| Certificate | kind (kosher, halal, organic, an assurance scheme), issuer, valid until | Required before the matching claim |
| Closure | date or range | Overrides weekly hours |
| Recipe or cooking guide | cut, method, time | Content; helps people buy the right cut |
| Review, award | text, source, year | Only real ones |
| Gift card | value, where it can be spent, expiry | |

## 2. Rules

1. Every product belongs to one department.
2. Every shown price has a unit: per kg, per 100 g, per lb, each, per pack. A price with no unit is not shown.
3. A price is optional, but its absence is explicit ("price at the counter", "ask us"). Blank and zero are not allowed.
4. One unit system per shop, chosen by the country (kilograms, or pounds). Units are not mixed on one list.
5. For anything sold by weight and ordered ahead, the buyer sees an estimate, the words "the final price is set by the actual weight", and by how much it may differ if the customer stated it.
6. A size band (a bird of 5-6 kg) shows its weight range, how many it feeds and its price range or price per kg. The shop may state that exact sizes cannot be guaranteed; if so, the buyer sees it before ordering.
7. A fixed-price box states its contents and total weight.
8. A product's state is not misstated: frozen or previously frozen meat is not called fresh.
9. Made products (sausages, burgers, marinades, pies, salads, sandwiches) show allergens, or the page says exactly how to get them. The page never says "free from" on its own.
10. Origin, breed, feed, ageing, "free-range", "organic" and "grass-fed" appear only as the customer stated them, per product or for the shop as a whole. They are never filled in from the domain.
11. Kosher and halal status are shown only with the certificate named. A shop that is neither does not use the words. A shop that sells no pork may say "no pork", which is a statement about stock, not a religious claim.
12. Opening hours are stated per day of the week with closed days named. A closure date overrides them.
13. An order has a named collection location, a date the location is open, and a time inside its hours.
14. A holiday order book has a deadline. After it, ordering shows "orders closed" and says what can still be bought at the counter.
15. If a deposit is taken, the buyer sees the amount, that it comes off the final bill, and what happens on cancellation, before confirming.
16. A product that needs ordering ahead states the notice. An order sooner than the notice is refused with the earliest date.
17. Delivery is offered only to stated areas on stated days. An address outside them is told so before payment.
18. Chilled goods delivered or shipped state how they are kept cold and that someone must receive them, if the customer said so.
19. Alcohol can be bought only after an age confirmation, where the shop sells it online.
20. A class has a number of places. Bookings cannot exceed it.
21. The main action is one of: find us and hours, call to order, order online. It is reachable from every page on a phone.
22. The phone number is a tappable link. The address opens a map.
23. Photographs are of this shop's own counter and products.
24. Reviews and awards are real and carry their source and year.

## 3. Mandatory facts

The product is not built until each of these has an answer from the customer. None may be guessed.

| # | Fact | The one question to ask | Why (the human reason) |
|---|---|---|---|
| 1 | Name | "What is the shop called?" | Without a name people cannot find it or recommend it. |
| 2 | What you sell | "What do you sell: which meats, and anything else such as cheese, cooked food or groceries?" | A visitor needs to know in seconds whether you have what they came for. |
| 3 | Kosher, halal, or neither | "Is the shop kosher or halal? If yes, who certifies it? If neither, do you sell pork?" | For many buyers this decides everything before price or quality. A wrong answer is a betrayal, not a mistake. |
| 4 | Address | "What is the full address, and is there somewhere to park?" | Without it people cannot arrive, and they carry heavy bags. |
| 5 | Phone | "What number do people call to order?" | In this trade the phone is the order book. Without it there are no holiday orders. |
| 6 | Opening hours | "Which days are you open, from when to when?" | Without hours people arrive at a closed door. |
| 7 | How to order | "How do people buy from you today: only at the counter, by phone, online, with delivery?" | The whole site leads to this one action. |
| 8 | Products and prices, or the decision not to show prices | "List what you want shown. For each price, is it per kilo, per 100 grams or each? If you prefer no prices, say so." | A price without a unit is an argument at the till. Hiding prices is allowed; inventing them is not. |
| 9 | Allergens in made products | "Which things do you make yourselves (sausages, burgers, marinades, salads), and what is in them: wheat, milk, egg, mustard, sulphites, nuts, sesame?" | People do not expect wheat in a sausage or mustard in a marinade. This is where someone gets hurt. |
| 10 | Who is the business legally | "What is the registered business name and number, for the legal pages?" | The privacy and terms pages must name who is responsible. |

Needed only when the product takes orders itself:

| # | Fact | The one question to ask | Why |
|---|---|---|---|
| 11 | How the final price works | "When someone orders two kilos and the piece weighs 2.3, what do they pay, and when?" | The buyer must know before ordering that the total can move. Otherwise the till feels like a trick. |
| 12 | Deposit and cancellation | "Do you take a deposit? What if they cancel or do not collect?" | A cut and trimmed joint nobody collects cannot be sold again at full price. |
| 13 | Notice and limits | "How far ahead do you need an order, and how many orders can you prepare for one day?" | Without it the day before a holiday takes more orders than the block can cut. |
| 14 | Where order alerts go | "Where should I send each new order: which phone or email, and who reads it?" | An order nobody saw is a family with no meat on the holiday. |
| 15 | Delivery | "If you deliver: where, on which days, from what order size, for what fee, and how is it kept cold?" | Meat left warm on a doorstep is a health risk and a refund. |

Needed only in some cases:

| # | Fact | The one question to ask | Why |
|---|---|---|---|
| 16 | Holiday order book | "For the holiday: which products, in which sizes, what deadline, which collection days and hours?" | It is the largest sale of the year and it cannot be redone the next day. |
| 17 | Source claims | "You said free-range (or grass-fed, organic, local, aged 35 days). Is that true of everything or of named products, and can you show it?" | These words are why people pay more. They must be true for the thing in the bag. |

## 4. Declared defaults

Each default is shown to the customer as "we filled this in - change it if it is wrong". None of them is a fact about the business.

| Default | Value | Why it is safe | How it is marked |
|---|---|---|---|
| Department names and order | by animal in the order the customer listed them, then Sausages and burgers, Cured and cooked, Cheese, Prepared food, Pantry | Standard counter order | Editable, labelled "suggested order" |
| Which department a product falls in | by its name | Wrong placement is visible and easy to fix | Customer confirms the grouped list |
| Weight unit | kilograms and grams; pounds and ounces only where the country sells that way | Follows from the address | Shown next to every price; changeable |
| Missing price | "Price at the counter" | Says openly that there is no number | Listed as "no price given" |
| Missing allergen answer | "Ask us what is in our sausages, marinades and prepared foods" | Makes no claim | Listed as "allergen details not given" |
| Main action | "Call to order", using the phone number | Works with zero setup; matches how reference 4 takes holiday orders | Labelled "default: phone" |
| Online ordering | off | Cannot take an order nobody reads | Labelled "default: orders by phone" |
| Weight note on any order | "The final price is set by the actual weight" | True of anything sold by weight | Not removable while weight-priced items are orderable |
| Page order | Skeleton A below | Extracted from the references | Named as the default skeleton |
| Language and direction | the language of the conversation | The customer chose it by speaking it | Shown, changeable |
| Currency | the currency of the shop's country | Follows from the address | Shown next to every price |
| Legal page structure | headings only | Structure is general; content is not | Marked "draft - not legal advice - review before publishing" |
| Empty optional sections | hidden | A missing gallery is better than an empty one | Listed as "not shown yet: suppliers, classes, recipes, reviews" |

Never a default, whatever the customer left out: prices, units, weights, "feeds N", hours, kosher or halal status, "no pork", origin, farm names, breed, "free-range", "grass-fed", "organic", "dry-aged", "fresh", "local", "hormone-free", "antibiotic-free", "nitrate-free", awards, reviews, photographs, delivery areas.

## 5. Failure modes

| What went wrong | What the visitor sees | What it costs | Prevention |
|---|---|---|---|
| Kosher or halal status wrong, implied or out of date | Buys and serves meat they would not have eaten | A betrayal of trust that spreads through a community in a day; in some places an offence | Rule 11; mandatory fact 3; certificate with a valid-until date |
| Price shown without a unit | Expects a joint for the per-kilo price | An argument at the till | Rule 2 |
| Final price higher than the online estimate, no warning | Feels overcharged | Dispute, lost customer | Rule 5; mandatory fact 11 |
| Holiday orders taken past capacity or past the deadline | Collects a smaller bird, or nothing | The worst case in this domain: a ruined holiday meal | Rules 14 and 16; mandatory facts 13 and 16 |
| Order saved but the shop never told | Arrives to collect; nothing was set aside | The same | Mandatory fact 14; status "requested" until confirmed; test the alert at setup |
| Size ordered, different size given, not explained | A bird too big for the oven or too small for the table | Complaint on the day | Rule 6 |
| Collection set for a closed day or the wrong shop | Stands at a locked door, or at the other branch | The same | Rule 13 |
| Deposit taken, rule unclear | Feels cheated on cancellation | Dispute | Rule 15 |
| Allergen in a made product not stated | A reaction to wheat, mustard or sulphites in a sausage | A medical emergency; liability | Rule 9; mandatory fact 9 |
| "Free-range", "grass-fed" or a farm name written by the builder | Pays a premium for a claim that is not true of the product | Misleading-advertising exposure; loss of trust | Rule 10; mandatory fact 17 |
| Frozen sold as fresh | Finds out at home | Distrust; a consumer-law problem | Rule 8 |
| Hours old, or holiday hours not marked | Arrives at a closed door the day before a holiday | A lost holiday sale | Closure object; prompt before holidays |
| Delivery left unattended, or to an address outside the area | Warm meat on a doorstep, or an order that never comes | Refund, health risk | Rules 17-18; mandatory fact 15 |
| Product list shows cuts that are not in today | Comes for it, it is gone | A wasted trip | "Call to check" on limited cuts; availability flag |
| Buyer does not know the cut names | Leaves the page without ordering | Silent loss | Short description and "feeds N" per product; cooking guides |
| Pounds and kilos mixed | Orders the wrong amount | Wrong order, argument | Rule 4 |
| Stock photos of meat | The counter does not look like the picture | Distrust | Rule 23 |
| "Order" link goes to a dead outside page | Taps, gets an error | Silent loss | Check outbound links at publish and on a schedule |

## 6. Professional language

Hebrew and Arabic terms are the author's knowledge and were not checked with a working butcher in either language. Cut names differ between countries, not only between languages: a cut name is never translated word for word. Where a cell says "not verified", do not use a guess.

| English | Meaning | Hebrew | Arabic |
|---|---|---|---|
| Butcher | the person | קצב | جزّار / لحّام (Levant) |
| Butcher's shop | the business | אטליז / קצבייה | ملحمة |
| Delicatessen, deli | cured meats, cheese, prepared food | מעדנייה | not verified |
| Counter | where goods are shown and served | דלפק / ויטרינה | not verified |
| Cut | a named piece of the animal | נתח | قطعة (not verified) |
| Joint (UK), roast (US) | a large piece for roasting | נתח לצלייה (not verified) | not verified |
| On the bone / boneless | | עם עצם / ללא עצם | بالعظم / بدون عظم |
| Rolled and tied | boned and bound for roasting | מגולגל וקשור (not verified) | not verified |
| Minced (UK), ground (US) | | בשר טחון | لحم مفروم |
| Diced | cut into cubes | קוביות | مكعبات |
| Beef | | בקר | لحم بقر |
| Veal | | עגל | لحم عجل |
| Lamb / mutton | | טלה / כבש | لحم خروف / لحم غنم |
| Poultry / chicken / turkey | | עופות / עוף / הודו | دواجن / دجاج / ديك رومي (حبش in the Levant) |
| Pork | | חזיר | لحم خنزير |
| Game | wild animals in season | בשר ציד (not verified) | not verified |
| Offal | liver, heart, kidneys and similar | חלקי פנים | not verified |
| Steak | | סטייק | ستيك |
| Ribeye / sirloin / fillet | common steak cuts | אנטריקוט / סינטה / פילה | not verified per region |
| Shoulder / leg / ribs / breast | | כתף / שוק / צלעות / חזה | كتف / فخذ / ضلوع (ريش in the Levant; not verified) / صدر |
| Sausage | | נקניקייה | نقانق / سجق |
| Cured meat, charcuterie | salted, dried or smoked meat | נקניקים / שרקוטרי | not verified |
| Dry-aged | hung to mature | יישון יבש / מיושן | معتّق (not verified) |
| Fresh / frozen | | טרי / קפוא | طازج / مجمّد |
| By weight, per kilo, per 100 grams | how it is priced | לפי משקל, לקילו, ל-100 גרם | بالوزن، بالكيلو، لكل 100 غرام |
| Kosher | permitted under Jewish dietary law | כשר | كوشير (not verified) |
| Kosher certificate | | תעודת כשרות | not verified |
| Glatt, mehadrin | stricter kosher grades | חלק, מהדרין | not verified |
| Koshering | salting and soaking meat | הכשרה | not verified |
| Halal | permitted under Islamic dietary law | חלאל | حلال |
| Free-range | animals with outdoor access | חופש (as in "עוף חופש") | not verified |
| Grass-fed | | ניזון ממרעה (not verified) | not verified |
| Cheese / hard / soft / raw milk | | גבינה / קשה / רכה / חלב לא מפוסטר | جبنة / قاسية / طرية / حليب غير مبستر (not verified) |
| Sliced | | פרוס | مقطّع شرائح (not verified) |
| Platter | an arranged tray for guests | מגש אירוח | صينية ضيافة (not verified) |
| Order ahead / collection | | הזמנה מראש / איסוף עצמי | طلب مسبق / استلام |
| Deposit | part payment in advance | מקדמה | عربون |

Notes on language:

- UK and US cut names differ (sirloin, rump, brisket and "roast" do not mean the same piece). Israeli cuts are known by number as well as by name. The product uses the names the customer uses and adds a description.
- UK and US English differ: mince / ground, joint / roast, kilo / pound, collection / pickup.
- Words to avoid unless the customer said them and can back them: "best", "premium", "prime" (a grade in the US), "fresh", "local", "natural", "free-range", "grass-fed", "organic", "hormone-free", "antibiotic-free", "nitrate-free", "humane", "sustainable", "traditional".
- Health claims ("lean", "healthy", "high protein") are regulated in many places. Do not write them.

## 7. Legal

A checklist of questions, not legal advice. The author is not a lawyer and did not read the statutes for this file. Every item needs checking by someone qualified in the shop's country before it is relied on.

### Applies almost everywhere

- **Selling meat is licensed and inspected.** The product does not check it and never writes "licensed", "inspected" or "approved" on its own.
- **Unit pricing.** Goods sold by weight must generally show a price per unit of weight.
- **Weights.** The price charged follows a weight measured on an approved scale. An online total for weight-priced goods is an estimate unless the product is sold at a fixed price.
- **Origin, method and quality words** ("organic", "free-range", "grass-fed", a protected regional name, a grade) are regulated terms or treated as advertising claims.
- **Religious claims** are regulated or treated as consumer protection.
- **Allergens and ingredients** in made products.
- **Fresh versus frozen** must not be misdescribed.
- **Privacy notice** as soon as an order, an enquiry or a newsletter signup exists.
- **Terms** when orders or money are taken: deposits, cancellation, uncollected orders, delivery, substitution by weight.
- **Perishable goods** are commonly excluded from the right to cancel an online purchase.
- **Alcohol** sold online needs an age check.

### Israel

- A butcher's shop requires a business licence under the Business Licensing Law, with Ministry of Health and veterinary conditions. Details: not verified.
- Kosher: presenting a shop or its meat as kosher without a certificate from an authorised body is prohibited under the Kosher Fraud Prohibition Law. Which bodies are authorised today: not verified.
- Pork: selling it is restricted by municipal by-laws in many towns. Whether a website may advertise it, and where: not verified.
- Halal certification in Israel: who issues it and whether the term is protected: not verified.
- Prices must be shown including VAT, and goods sold by weight must show a price per unit (Consumer Protection Law and its price-display regulations). Thresholds and exemptions for small shops: not verified.
- Marking of meat as fresh, chilled, frozen or thawed, and of the country of origin: regulations exist. Details: not verified.
- Price control: some basic food products are under government price supervision. Whether any meat product is: not verified.
- Cancelling a distance transaction: exceptions for perishable goods. Details: not verified.
- Accessibility, privacy and marketing-message rules: as in the other food files; thresholds not verified.

### European Union and United Kingdom

- Unit pricing: EU Directive 98/6/EC and the UK Price Marking Order 2004 require the selling price and the unit price for goods sold by weight, with exemptions for some small shops. Believed true; not verified.
- Beef must be labelled with origin under EU Regulation 1760/2000; fresh pork, lamb, goat and poultry under Regulation 1337/2013. How these apply to meat sold loose over a counter, and in the UK after 2021: not verified.
- 14 allergens under EU Regulation 1169/2011 (kept by the UK); mustard, sulphites and cereals with gluten are the common ones in sausages and marinades. Believed true; not verified.
- UK: "prepacked for direct sale" items (a wrapped sandwich, packed sausages in a chiller) need a full ingredient list since October 2021. Not verified.
- "Organic" may be used only by certified operators. Believed true in both; not verified.
- Minced meat and meat preparations have composition and labelling rules (fat and collagen content, "previously frozen"). Not verified.
- Raw-milk cheese may need a notice. Not verified.
- Distance selling: no right to cancel for goods that spoil quickly. Believed true; not verified.
- UK: alcohol may not be sold to under-18s; an online seller needs an age check. Reference 6 shows an age-verification prompt on its home page (observed 2026-11-21).
- GDPR and UK GDPR apply to order data. Consent is needed for non-essential cookies.
- European Accessibility Act, from June 2025, covers e-commerce with a microenterprise exemption. Not verified for a butcher's order page.

### United States

- Meat sold at retail comes from inspected plants (federal or state). Retail butchers are regulated by state and local health codes. Not verified.
- "Prime", "Choice" and "Select" are federal grades; "organic" requires certification; "grass-fed" and "natural" have federal guidance. Not verified.
- Country-of-origin labelling rules changed in recent years for beef and pork. Current state: not verified.
- Prices are per pound; sales tax on unprepared food varies by state. Not verified.
- Shipping perishable food across state lines has its own rules. Not verified.
- The Americans with Disabilities Act is applied by courts to shop websites. Not verified.

### What the product does with this

- The product asks which country the shop is in before generating any legal page, unit or price format.
- The product may generate the **structure** of a privacy page, terms and an accessibility statement, each marked as a draft that needs review.
- The product never writes "kosher", "halal", "organic", "free-range", "inspected", "licensed" or "complies with" on its own.

## 8. Site vs app

### Content pages (no data, no accounts)

Home, what we sell (with or without prices), where the meat comes from, the holiday order guide as information, cooking guides, find us, about, legal pages. With a phone link this is a complete and honest product. Reference 4 takes its whole holiday trade this way: a full guide on the page, and orders in person or by phone only.

States still needed on content pages:

| Part | Empty | Error | Notes |
|---|---|---|---|
| Product list | may be short; never empty (mandatory fact 2 gives at least the departments) | n/a | Shows the date it was last updated |
| Price | "price at the counter" | n/a | Always with its unit |
| Hours | cannot be empty | | "Open now" needs the time zone and the closures |
| Holiday guide | hidden out of season | | After the deadline: "orders closed" |
| Map | address as text always shown | if the map fails, the text and a link remain | |
| Suppliers, recipes, reviews | section hidden | broken image hidden | Never placeholders |

### Needs data

| Part | What it needs | Empty state | Loading | Error | Save | Permissions |
|---|---|---|---|---|---|---|
| Order request (shop confirms by hand) | stores the request with weights and preparation; alerts the shop | nothing orderable yet: "Call us to order" with the number | | "Not sent - please call" with the number | status "requested"; told plainly it is not confirmed and that the final price is by weight | visitor sees own order through a link; shop sees all |
| Holiday order book | products with size bands, a deadline, collection slots, a daily limit, deposit | after the deadline: "Orders are closed - here is what we will have at the counter" | slots show a placeholder, never a blank that reads as "full" | slot filled meanwhile: "That time just filled - nearest free times" | confirmed only after the server saved it; the buyer gets a confirmation with product, size band, shop, date and time | visitor: own order; staff: the collection list by day and hour; owner: everything |
| Online shop with fixed prices (boxes, packs) | stock or a daily limit, delivery rules, payment | out of stock: "Back on Thursday" only if the customer said so; otherwise "not available now" | | payment failed: "Nothing was charged" | order number and what happens next | visitor: own order; owner: all |
| Online shop with weight-priced goods | an estimate, then a final amount after cutting | | | | the buyer agreed to a range before ordering; the final amount is sent before or at collection | as above |
| The day's cutting and collection list | orders by collection time, with preparation notes | "No orders for today" | | never show a stale list without saying so | "prepared" and "collected" saved at once | staff, behind a login |
| Owner edits products, prices, hours, closures | an edit screen | | | a failed save keeps what was typed | public right after saving | owner only |
| Class booking | dates, places, price | "No dates yet" | | | a place is held only after the server saved it | visitor: own booking; owner: all |
| Newsletter signup | an address and proof of agreement | | | | says what will be sent and how to stop | owner only |

### Needs accounts

- The owner needs one as soon as anything is editable or any order is stored.
- Staff need one if someone else works the collection list.
- Visitors do not need one to place an order. An account is justified only for repeat orders or a regular delivery.

### Needs payments

- Deposits on holiday orders, fixed-price boxes, delivery orders, classes, gift cards.
- Weight-priced goods are the hard case: the amount is not known when the order is placed. The safe patterns are a deposit with the balance at collection, or a fixed-price pack.
- Default: no payments; pay at the counter. Added only when the customer asks and has stated the deposit and cancellation rule (mandatory fact 12).

### Delivery is a second business

References 2, 6 and 7 are shop-led with nationwide delivery. That needs cold packing, courier days, a missed-delivery rule and returns for food that cannot be returned. If the customer does not already do this, do not offer it as a feature. Start with collection.

## 9. References

**How these were checked.** Each URL was fetched on 2026-11-21 with a page-extraction tool that returns the page's text and image references. No browser was used and no screenshot was taken. So: section order and wording are observed; visual quality, layout and the image-to-text ratio are **not** observed, and every ratio below is an estimate from counts in the extracted text. Image counts include logos, icons and product thumbnails. Some extractions omit navigation and footers.

**Curation.** Chosen by the author from well-known butchers and delis in London and New York, not from a search-result list. No awwwards.com category was consulted; none is claimed as an award winner. All are in English, in Latin script.

**Limit.** All eight are in two cities. None is a kosher or halal butcher, although that is the first question in this domain for many customers (the one kosher-style deli, reference 8, makes no certification claim in the extraction). No cheese-only shop and no supermarket-counter butcher was verified.

Verified: 8.

| # | Site | Checked | What was observed |
|---|---|---|---|
| 1 | https://www.turnerandgeorge.co.uk | 2026-11-21 | London butcher with an online shop and three counters. Order: cart - two claims as tiles (cut to order; where the beef comes from) - who the two founders are, by trade (butcher and chef) - newsletter with a first-order discount - two more claims (provenance; dry-aged in house) - **customer favourites as four product cards, each a name and a price or a "from" price** - two reviews with their source named - **three locations, each with address and a row of hours per group of days, closed days named** - three recipes. Extraction: 20 images, about 7,300 characters. |
| 2 | https://www.hgwalter.com | 2026-11-21 | London butcher, shop-led. Order: **ten product cards, each a one-line description and a price** - three claims (trusted by chefs; nationwide delivery; cut fresh, not frozen) - a seasonal block - more product rows - social - press - footer in four groups (shop, about, information, keep in touch) with the line that allergens are listed in bold under each product with the ingredients. Extraction: 99 images, about 18,000 characters. |
| 3 | https://www.dicksonsfarmstand.com | 2026-11-21 | New York butcher in a market hall. Navigation lists the ways to buy separately: location, events, order dried meats, order meat and groceries, order lunch and dinner, classes, catering, farms, articles, gift certificates. Order: a seasonal holiday block of four products with "from" prices - meat and groceries - lunch and dinner - classes - gift certificates - **Our farms: a paragraph, then every supplier by name and place with what and how much each supplies per week, and the abattoir named** - book a class. Extraction: 12 images, about 6,800 characters. |
| 4 | https://www.flockandherd.com | 2026-11-21 | London neighbourhood butcher. On the day the home page was **the holiday order guide**: what is offered - a notice that orders are taken only in person or by phone at the shop of collection, not online - the order deadline - "place your order at the shop from which you will collect" - a fixed deposit, taken off the final bill - **collection dates with hours for each day, and closed days** - a statement that sizes cannot be guaranteed - then per product a short sourcing paragraph and **a size table: size name, weight range, feeds how many, cost range, price per kg** - other products - cheese boxes - a note on bird flu and the farms - footer (about, services, contact, newsletter). Extraction: 24 images, about 10,500 characters. |
| 5 | https://www.the-meathook.com | 2026-11-21 | New York butcher and grocery, three shops. Order: **three lines at the very top, one per shop: street address, city, "open daily" with hours** - one paragraph on whole-animal butchery and the farmers - five things sold, one line each - email signup - social - footer links (about, sourcing, order, classes and events, gift cards, careers) - the three shops again with phone numbers. No prices on the home page. Extraction: 17 images, about 5,700 characters. |
| 6 | https://www.thegingerpig.co.uk | 2026-11-21 | London butcher group with an online shop. Order: basket - seasonal block - a bake-at-home product - a course combining a butchery demonstration with a meal - butchery classes - the story - shop by cooking style - award winners - a statement on ethical butchery - wines - by department - our shops - "our butchers recommend" product row - footer groups (departments, information, legal) - newsletter - **an age-verification prompt for products containing alcohol**. Extraction: 113 images, about 14,800 characters. |
| 7 | https://www.linastores.co.uk | 2026-11-21 | London Italian delicatessen that grew restaurants. Order: one line of identity with the founding year - two paragraphs - "shop now" - **locations as tiles, each labelled Delicatessen, Restaurant, or both, with its neighbourhood** - our restaurants - our delicatessens (what the counter sells: cured meats, cheese, antipasti, fresh pasta, sandwiches, hampers; popular products also online for nationwide delivery) - the bar. Extraction: 14 images, about 5,600 characters. |
| 8 | https://www.katzsdelicatessen.com | 2026-11-21 | New York delicatessen, shop-led. Navigation: shipping, catering, in-store menu, second location, location and hours, groups and private events. Order: one paragraph of identity with the founding year - "order now" - **three rows of cards, one per way of buying: nationwide shipping (gift boxes with prices), in-store menu and local delivery (dishes with prices), catering (packages with "serves N+" and "starting at" prices)** - a numbered best-seller list. Used as the ceiling for a deli with three sales channels. Extraction: 43 images, about 9,200 characters. |

Loaded and not used:

| Site | Checked | Why not |
|---|---|---|
| https://www.lidgates.com | 2026-11-21 | Loads. A large online shop (about 42,600 characters, 267 image references). Structure is the same as reference 2; left out to avoid a fourth shop-led example. |
| https://www.russanddaughters.com | 2026-11-21 | Loads, but the extraction returned only a "ways to order" list and navigation (about 2,000 characters). Useful as one observation: an accessibility link is the first item on the page, and phone ordering is listed first among the ways to order. Not enough for a structure. |

## 10. Skeletons

Structure only. No colours, logos, photographs or wording were taken from any reference.

### Skeleton A: the counter

For a butcher or deli whose trade is at the counter and on the phone. Default for this domain.
From references 1, 3, 4 and 5: the top-of-page shop lines of 5, the hours rows of 1, the holiday guide and size table of 4, the supplier list of 3.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; one action (call to order / find us) | action is the most prominent element after the name | yes |
| 1 | Opening | one sentence: what kind of shop, where; kosher or halal status with the certifier, if any; today's hours | status, if any, is on the first screen, not in the footer | yes |
| 2 | Holiday orders | appears only in season, above everything else: what, the deadline, how to order, deposit, collection days and hours, then a size table per product (size, weight range, feeds, price range, price per kg) | deadline and how-to-order first; tables after | optional, dated |
| 3 | What we sell | departments in order; each product on one line: name, short note, price with unit or "price at the counter" | department heading over rows | yes |
| 4 | Made here | sausages, burgers, marinades, prepared food, with ingredients or how to ask about allergens | under the list, not in the footer | yes if anything is made in the shop |
| 5 | Where it comes from | farms or regions, as the customer stated them | a short paragraph or a list of names and places | optional, hidden when empty |
| 6 | How to order | what needs notice, how much, by phone or at the counter, how collection works | short sentences | yes |
| 7 | Cooking help | guides or recipes by cut | a few links | optional |
| 8 | What customers say | real reviews with source | at most three | optional, hidden when empty |
| 9 | Find us | per shop: address as text, map link, phone, hours per day with closed days named, parking | complete without the map | yes |
| 10 | Footer | name, phone, address; privacy, terms, accessibility statement; social link | small | yes |

Image-to-text ratio: **estimate**, from extraction counts only (references 3, 4 and 5 returned 12 to 24 images against roughly 5,700 to 10,500 characters). Text-led: the list, the prices and the order rules are text and tables. A few photographs of the counter and the people carry the trust. Not confirmed in a rendered view.

### Skeleton B: the counter with an online shop

For a shop that already delivers or sells boxes online. Use only when that operation exists.
From references 1, 2, 6 and 8: the product cards of 1 and 2, the channel rows of 8, the department navigation of 6.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | departments as navigation; basket; "our shops" always visible | the way to the counter is never hidden behind the shop menu | yes |
| 1 | Opening | one line of identity; religious status if any; one action (shop) and one quieter (find a shop) | two actions | yes |
| 2 | Promises | three or four short claims, each one the customer actually made (cut to order, delivery area, where the meat comes from) | one line each | optional; none are defaults |
| 3 | Seasonal block | the current holiday range with its deadline | one block, dated | optional |
| 4 | Favourites | product cards: image, name, price with unit or "from" | card per product | yes |
| 5 | Ways to buy | one row per channel that exists: collect from a shop, local delivery, nationwide delivery, catering or platters | row per channel, with its own rules | yes |
| 6 | Who we are | the trade of the people behind it; sourcing | a short paragraph | optional |
| 7 | Reviews | with source | two or three | optional, hidden when empty |
| 8 | Our shops | per shop: address, hours rows, phone | | yes |
| 9 | Footer | groups: shop, about, information, legal; delivery and returns; how allergens are shown; newsletter | | yes |

Image-to-text ratio: **estimate**. Image-led: references 2 and 6 returned 99 and 113 image references, most of them product thumbnails. Most blocks are an image with a name and a price. Not confirmed in a rendered view.

Risk seen in references 2, 6 and 8: when the shop leads, opening hours and the phone are several steps away. A customer whose income is the counter should use Skeleton A.

## 11. Not verified

1. All Hebrew and Arabic terms in section 6: author's knowledge, not checked with a working butcher. Cut names in particular differ by country and region. Cells marked "not verified" must not be filled by guessing.
2. Every legal statement in section 7. None was checked against a statute or an official source for this file. Rules on kosher and halal claims, pork sales and unit pricing in Israel matter most and are the least certain.
3. Image-to-text ratios and visual quality of all references: text extraction only, no rendered view.
4. No awwwards.com category was consulted; design quality of the references is the author's prior judgement.
5. **No kosher butcher and no halal butcher reference was verified.** No cheese-only shop. All eight references are in London or New York.
6. Sub-pages of the references (product pages, order flows, delivery terms, shop pages) were not fetched; observations are of home pages only.
7. Whether references that show prices show a unit next to each price: the extraction shows amounts on product cards, and the unit was not always in the extracted text.
8. Footer and legal links: several extractions did not include footers, so their absence in this file proves nothing.
9. No references in Hebrew, Arabic or any non-Latin script. These come in a later phase.
