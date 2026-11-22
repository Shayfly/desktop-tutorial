# Clothing shop

Covers: a business that sells clothes, shoes and accessories to the public, from a physical shop, online, or both. Includes a one-room boutique, a market-stall label, a second-hand or vintage shop and a small brand selling its own designs.
Does not cover: a catalogue with no buying (use `catalogue-collection.md`); made-to-measure tailoring and alterations as the main business (closer to `craftsman-renovation.md` in how it works: a quote, then a job); cosmetics (use `beauty-cosmetics.md`).
Written 2026-11-21. References checked 2026-11-21. Template: [README.md](README.md).

## 1. Objects

A clothing shop sells **a specific size and colour of a garment, which it either has or does not have**. The thing the visitor looks at is the product; the thing the visitor buys is the variant. Almost every failure in this domain comes from mixing the two.

### Shop (the business)

| Field | Required | Example (illustrative) |
|---|---|---|
| Name | required | "Harbour Street Clothing" |
| What it sells and for whom | required | women's wear, menswear, children, vintage, workwear, plus sizes, modest wear |
| How people buy | required | in the shop only; online with delivery; online with collection; by message |
| Address and opening hours, if there is a physical shop | required when there is a shop | street, number, city; hours per day |
| Phone or message number | required | |
| Email for orders and returns | required when selling online | |
| Countries or areas delivered to | required when selling online | "within the country only" |
| Returns and exchange policy | required when selling online; strongly advised in a shop | see Policy below |
| Own label, or other brands, or both | optional | changes how products are described |
| Services | optional | alterations, repairs, personal shopping, gift wrap |
| Social account | optional | often where the photographs already are |
| Short story | optional | who makes the clothes, where |

### Category

| Field | Required | Example |
|---|---|---|
| Name | required | Dresses, Shirts, Trousers, Knitwear, Coats and jackets, Shoes, Accessories |
| Department | optional | Women, Men, Children, Home |
| Order | required | |

A product belongs to one main category. It may also appear in **collections**, which are curated sets that cut across categories: New in, Sale, a season, "Made in ...", Gifts.

### Product (the garment as designed)

| Field | Required | Example |
|---|---|---|
| Name | required | "Wool overshirt" |
| Category | required | Shirts |
| Price | required for anything that can be bought; see rule 4 | 145 |
| Photographs | required, at least one | front; ideally back, detail, worn |
| Description | optional | cut, feel, what it goes with |
| Material composition | required where the law asks for it (see Legal); otherwise strongly advised | 80% wool, 20% polyamide |
| Care instructions | optional | wash cold, do not tumble dry |
| Where made | optional | country; a legal question in some places |
| Fit note | optional | "runs large - take your usual size", model height and size worn |
| Size guide | optional but valuable | a table of body or garment measurements per size |
| Brand | optional | for a multi-brand shop |
| Season or collection | optional | |
| Condition | required for second-hand | new, excellent, good, flaws described and photographed |
| One of a kind | optional | vintage and sample pieces: quantity is exactly one |
| Status | required | draft, on sale, sold out, archived |

### Variant (what is actually bought)

| Field | Required | Example |
|---|---|---|
| Size | required unless one-size | S, M, L; 38, 40; 8, 10; "one size" |
| Size system | required when sizes are numbers | EU, UK, US, IL - the same number means different things |
| Colour | required when there is more than one | named in plain words; its own photographs |
| Stock quantity | required when selling online | 0 means sold out |
| Price | optional | only when it differs from the product price |
| Stock-keeping code (SKU) | optional | the shop's own code |

### Order (only when the product sells online)

| Field | Required | Example |
|---|---|---|
| Lines | required | variant, quantity, price paid per line |
| Buyer name, email, phone | required | |
| Delivery method and address, or collection | required | |
| Delivery price | required | may be zero above a threshold |
| Discount or gift card applied | optional | |
| Total, with tax shown as the law requires | required | |
| Payment status | required | pending, paid, failed, refunded, partly refunded |
| Fulfilment status | required | new, packed, sent, delivered, ready for collection, collected, cancelled |
| Tracking link | optional | |
| Return | optional | which lines, reason, received on, refund or exchange |

### Other objects

| Object | Fields | Notes |
|---|---|---|
| Policy | returns window, who pays return postage, condition required, exchange or refund, sale-item rules, delivery times and prices | The customer's own words. Shown before payment |
| Delivery option | name, price, free-above threshold, estimated days, area | |
| Discount | code or automatic, amount, conditions, start and end | Expires on its end date |
| Sale price | original price, reduced price, since when | See rule 6 |
| Gift card | value, code, balance, expiry | Involves payments and its own law |
| Shop location | address, hours, phone, services there | For shops with several branches |
| Lookbook or story | images, short text, linked products | Editorial content |
| Review | text, first name or initials, date, source | Only real |
| Waiting list entry | variant, email | "Tell me when it is back" - needs consent |

## 2. Rules

1. A product belongs to exactly one main category and any number of collections.
2. A product with sizes or colours has one variant per combination that exists. A combination that was never made is not shown as sold out; it is not shown.
3. What goes in the basket is a variant, never a product. The visitor cannot add a garment without choosing a size when sizes exist.
4. Anything that can be bought has a price. A product without a price can be shown only as "ask in the shop" and cannot be added to a basket.
5. Every price shows its currency. Whether the price includes tax, and whether delivery is extra, is stated before payment.
6. A reduced price shows the earlier price only if the product was really sold at that price. What counts as the earlier price is a legal question (see Legal).
7. A variant with zero stock cannot be bought. It is shown as sold out, in place, so the visitor sees the size exists.
8. Stock is reduced when the order is paid, not when the item enters a basket. Two buyers cannot both pay for the last piece.
9. A one-of-a-kind product has a stock of exactly one and disappears from sale when paid.
10. Numeric sizes always name their system. A size guide states whether it measures the body or the garment, and its unit.
11. Each colour has its own photographs. A photograph of the blue coat is not shown when the green variant is selected.
12. Photographs show the actual product. A supplier's or stock photograph is allowed only when it is the same item.
13. The returns policy, delivery prices and delivery times are reachable from every product page and are shown again before payment.
14. The order total the buyer confirmed is the amount charged. Nothing is added after confirmation.
15. Every paid order produces a confirmation the buyer can keep, with what was bought, what was paid and how to return it.
16. A refund goes back by the method that was used to pay, unless the buyer agreed otherwise.
17. A discount has a start, an end and conditions. Outside them it does not apply and is not advertised.
18. For second-hand items, every known flaw is described and photographed.
19. Claims about the product ("organic cotton", "made in ...", "handmade", "vegan leather", "sustainable") appear only if the customer supplied them and can back them.
20. A review is shown only if it is real, with its source.
21. A shop with a physical location shows its address and hours on the site even when it also sells online.

## 3. Mandatory facts

The product is not built until each of these has an answer from the customer. None may be guessed.

| # | Fact | The one question to ask | Why (the human reason) |
|---|---|---|---|
| 1 | Business name | "What is the shop called?" | Without a name people cannot find it or recommend it. |
| 2 | What it sells, for whom | "What do you sell, and who is it for?" | A visitor decides in seconds whether this shop is for them. |
| 3 | How people buy | "Do people buy in your shop, online, or both? Do you want the site to take orders and payment, or only to show what you have?" | This decides whether we build pages or a shop. Getting it wrong is the most expensive mistake here. |
| 4 | Contact | "What number or email should buyers use to reach you?" | A buyer with a problem and nobody to ask becomes a refund dispute. |
| 5 | Where and when, if there is a shop | "Is there a shop people can walk into? Address, and opening hours for each day." | Without it people arrive at a closed door. |
| 6 | The products | "Show me what you sell: for each item a name, a price and at least one photo." | The products are the site. Nothing here can be invented. |
| 7 | Who is the business legally | "What is the registered business name and number, and the address for returns?" | The buyer has a legal right to know who they are buying from. |

Needed only when the product sells online:

| # | Fact | The one question to ask | Why |
|---|---|---|---|
| 8 | Sizes and colours per product | "For each item: which sizes and colours exist?" | The buyer buys a size, not a garment. |
| 9 | Stock | "How many of each size and colour do you have right now, and who will update it when you sell one in the shop?" | Without it you sell a piece you no longer have. |
| 10 | Delivery | "Where do you send to, how much does it cost, and how many days does it take?" | The buyer must know the full price and the wait before paying. |
| 11 | Returns | "Can a buyer return or exchange? Within how many days, in what condition, who pays the postage, and what about sale items?" | Clothes get returned more than anything else sold online. The rule must be yours and must be legal. |
| 12 | Where order alerts go | "Where should I send each new order: which phone or email, and who packs it?" | An order nobody sees is a paid customer waiting for nothing. |
| 13 | How money is received | "Which payment service is the money paid into?" | The product never holds the customer's money and never invents an account. |
| 14 | Material composition | "What is each item made of, as written on its label?" | Buyers ask, and in many countries the law requires it. |

## 4. Declared defaults

Each default is shown to the customer as "we filled this in - change it if it is wrong". None of them is a fact about the business.

| Default | Value | Why it is safe | How it is marked |
|---|---|---|---|
| Category names and order | Tops, Shirts, Knitwear, Trousers, Dresses and skirts, Coats and jackets, Shoes, Accessories | Common across the references' menus | Editable list, labelled "suggested" |
| Which category a product falls in | by the product's name | Wrong placement is visible and easy to fix | Customer confirms the grouped list |
| Collections | "New in" (newest first) and, when anything is reduced, "Sale" | Follows from data the customer gave | Labelled "automatic" |
| Product order in a category | newest first | Neutral | Setting, labelled "default" |
| Main action when the customer did not choose selling online | "Ask about this item" by message or phone, with the product name filled in | Works with zero setup and promises nothing | Labelled "default: enquiry, not checkout" |
| Product page order | photographs, name, price, colour, size, action, description, material and care, delivery and returns | Domain knowledge; product pages of the references were not fetched | Labelled "default layout" |
| Sold-out display | size shown, struck out, cannot be chosen | Rule 7 | Fixed behaviour, explained to the customer |
| Low-stock message | none | "Only 2 left" is a pressure claim that must be true at every moment | Off unless the customer turns it on |
| Size guide | hidden until the customer supplies measurements | A generic size chart is an invented fact | Listed as "not shown yet: size guide" |
| Page order | Skeleton A below | Extracted from the references | Named as the default skeleton |
| Language and direction | the language of the conversation | The customer chose it | Shown, changeable |
| Currency | the currency of the shop's country | Follows from the address | Shown next to every price |
| Legal page structure | headings only: privacy, terms of sale, delivery, returns | Structure is general; content is not | Marked "draft - not legal advice - review before publishing" |
| Empty optional sections | hidden | | Listed for the customer as "not shown yet" |

Never a default, whatever the customer left out: prices, sizes, stock, material composition, country of origin, the returns window, delivery prices and times, free-delivery thresholds, discounts, "sustainable", "organic", "handmade", reviews, ratings, model measurements, and the earlier price of a reduced item.

## 5. Failure modes

| What went wrong | What the visitor sees | What it costs | Prevention |
|---|---|---|---|
| Sold in the shop, still on the site | Pays, then gets "sorry, we do not have it" | A refund, a lost buyer, a bad review | Mandatory fact 9; one stock number for shop and site, or a daily prompt |
| Two buyers pay for the last piece | One gets an apology | As above | Rule 8, enforced at payment on the server |
| Wrong size because the chart was generic | The garment does not fit | A return the shop pays for | No default size guide; fit note; size system named (rule 10) |
| Size number without a system | Orders a UK 10 expecting a US 10 | A return | Rule 10 |
| Photo shows another colour | Receives a colour they did not expect | A return and distrust | Rule 11 |
| Returns policy unclear or hidden | Finds out after buying that sale items cannot be returned | A dispute, a chargeback | Rule 13; mandatory fact 11 |
| Delivery cost appears at the last step | Abandons the basket | A lost sale, unseen | Delivery price visible from the product page |
| Order paid, shop never told | Waits; nothing arrives | The worst case when selling online | Mandatory fact 12; test order at setup; unfulfilled orders flagged after a set time |
| Payment taken, order not saved | Charged, with no confirmation | A chargeback and a frightened buyer | Order saved before payment is confirmed; reconcile payments against orders |
| Confirmation never arrives | Not sure the order went through; orders again | A double order, a refund | Confirmation on screen as well as by message (rule 15) |
| Expired discount still advertised | Code refused at checkout | Annoyance | Rule 17 |
| "Was" price that never was | Feels tricked; in some places unlawful | A fine, distrust | Rule 6 |
| Flaw on a second-hand item not shown | Receives a stained garment | A refund and a review | Rule 18 |
| Composition missing or wrong | An allergic or simply careful buyer cannot decide, or is misled | A lost sale; a labelling problem | Mandatory fact 14 |
| Shop hours old | Arrives at a closed shop | A lost visit | Ask hours explicitly; show "last updated" |
| Site sells abroad without meaning to | An order from a country the shop cannot send to | A refund and postage loss | Delivery areas are an explicit list |
| "Back in stock" message sent without consent | An unwanted message | A complaint | Consent on the waiting list |

## 6. Professional language

Hebrew and Arabic terms are the author's knowledge and were not checked with a working retailer in either language. Where a cell says "not verified", do not use a guess.

| English | Meaning | Hebrew | Arabic |
|---|---|---|---|
| Clothing shop (US: store), boutique | the business | חנות בגדים / בוטיק | محل ملابس / بوتيك |
| Garment, piece, item | one product | פריט / בגד | قطعة |
| Collection | the season's set, or a curated set | קולקציה | مجموعة / كولكشن |
| New in, new arrivals | most recent products | חדש באתר / הגיע עכשיו | وصل حديثاً |
| Size | | מידה | مقاس |
| Size guide, size chart | measurements per size | טבלת מידות | جدول المقاسات |
| One size | fits a range | מידה אחת | مقاس واحد |
| Fit | how it sits: slim, regular, relaxed, oversized | גזרה | قَصّة (not verified) |
| Colour (US: color), colourway | | צבע | لون |
| Fabric, material | | בד | قماش |
| Composition | fibre percentages | הרכב הבד | تركيب القماش (not verified) |
| Care instructions | washing and drying | הוראות כביסה | تعليمات الغسيل |
| Cotton, wool, linen, silk, leather | common materials | כותנה, צמר, פשתן, משי, עור | قطن، صوف، كتان، حرير، جلد |
| In stock, out of stock, sold out | | במלאי, אזל מהמלאי | متوفر، نفذت الكمية |
| Basket (UK), cart (US), bag | what the buyer has chosen | סל קניות / עגלה | سلة التسوق |
| Checkout | the paying step | קופה / תשלום | الدفع |
| Delivery (UK), shipping (US) | sending the order | משלוח | توصيل / شحن |
| Collection, pick-up | fetching the order from the shop | איסוף עצמי | استلام من المحل (not verified) |
| Return | sending it back for money | החזרה | إرجاع |
| Exchange | swapping for another size or item | החלפה | استبدال |
| Refund | money back | החזר כספי | استرداد المبلغ |
| Store credit | value kept for a later purchase | זיכוי | رصيد (not verified) |
| Sale | reduced prices | מבצע / סייל | تنزيلات / تخفيضات |
| Discount code | | קוד הנחה / קופון | كود خصم |
| Gift card, voucher | | שובר מתנה / גיפט קארד | بطاقة هدية |
| Pre-order | paying before the item is made or arrives | הזמנה מוקדמת | طلب مسبق |
| Second-hand, vintage, pre-loved | used clothing | יד שנייה / וינטג' | مستعمل (vintage: not verified) |
| Alterations | changing a garment to fit | תיקונים | تعديل (not verified) |
| Lookbook | styled photographs of a collection | לוקבוק | not verified |
| SKU | the shop's code for one variant | מק"ט | not verified |
| Wholesale | selling to other shops | סיטונאות | بيع بالجملة |
| Receipt | proof of purchase | קבלה / חשבונית | فاتورة / إيصال |

Notes on language:

- Buyers say "do you have it in my size". The trade says "variant" and "SKU". The site uses the buyer's words; the owner's screens can use the trade's.
- UK and US English differ: basket/cart, delivery/shipping, trousers/pants, jumper/sweater, trainers/sneakers, colour/color. "Pants" means underwear in the UK. Pick one by country.
- Size labels are not translatable. Never convert sizes between systems unless the customer supplies the conversion.
- Words to avoid unless the customer said them and can back them: "sustainable", "eco", "ethical", "organic", "handmade", "luxury", "genuine leather", "limited edition", "last chance", "only X left", "best price".

## 7. Legal

A checklist of questions, not legal advice. The author is not a lawyer and did not read the statutes for this file. Selling online to consumers is one of the most regulated things a small business does. Every item needs checking by someone qualified in the shop's country, and in each country it sells to.

### Applies almost everywhere

- **Who is selling.** The site names the legal seller, a contact route and a postal address.
- **Price clarity.** The full price, including tax and delivery, is known before payment.
- **Cancellation of online purchases.** Most jurisdictions give a consumer some right to cancel a distance purchase. The length, the exceptions and who pays the return postage differ.
- **Faulty goods.** Rights for a faulty item are separate from a change-of-mind return and usually cannot be removed by a policy.
- **Labelling.** Fibre composition, care and origin labelling rules exist in many places and often apply to the online listing as well as the sewn-in label.
- **Privacy notice.** Needed as soon as there is a contact form, a newsletter or an order.
- **Card data.** The product never stores card numbers. Payment happens with a payment service.
- **Marketing messages** need prior agreement. An order confirmation is not marketing; a "back in stock" or "you left something in your basket" message may be.
- **Reviews and environmental claims** must be true. "Green" claims are an active enforcement area in several places.
- **Children's clothing** has extra safety rules (cords, flammability of nightwear) in many places. Not verified per place.

### Israel

- Distance selling: the Consumer Protection Law is understood to let a consumer cancel within 14 days of receiving the goods, with a capped cancellation fee. Exceptions and the exact fee: not verified.
- In-shop returns: the cancellation-of-transaction regulations are understood to cover clothing and footwear for a short period if unworn and with the tag. The exact period and conditions: not verified.
- A shop must display its returns policy. Not verified for online display.
- Displayed prices include VAT. Believed true; not verified.
- Labelling: a consumer-protection order on marking goods is understood to require composition, care, country of origin and importer details in Hebrew. Not verified.
- Gift cards and credit notes: rules on minimum validity exist. Details: not verified.
- Sale prices: rules on presenting a "before" price exist. Details: not verified.
- Website accessibility duty and statement, Israeli Standard 5568, exemptions by turnover: thresholds not verified.
- Privacy: Protection of Privacy Law, Amendment 13 in force since August 2025. Not verified in detail.
- Marketing by SMS or email needs prior consent (section 30A of the Communications Law). Not verified in detail.

### European Union and United Kingdom

- 14-day right to cancel an online purchase: EU Consumer Rights Directive; in the UK the Consumer Contracts Regulations 2013. Exceptions include goods made to the buyer's specification. Believed true; not verified.
- Faulty goods: a two-year legal guarantee in the EU; in the UK the Consumer Rights Act 2015 with a short-term right to reject. Not verified.
- Fibre composition must be stated: EU Textile Regulation 1007/2011, and corresponding UK rules. Whether it must appear on the product page: believed yes for online sales; not verified.
- EU price-reduction announcements must refer to the lowest price of the previous 30 days (the "Omnibus" changes to the Price Indication Directive). Not verified.
- EU General Product Safety Regulation (applies from December 2024) is understood to require a responsible person in the EU for products sold there, including by small sellers from outside. Not verified.
- VAT on cross-border sales to EU consumers, and customs after the UK left the EU: needs an accountant. Not verified.
- GDPR and UK GDPR; cookie consent for non-essential cookies. Two references showed a country or cookie prompt on the home page (observed 2026-11-21).
- European Accessibility Act: applies from June 2025 to e-commerce services, with an exemption for microenterprises. Whether a given shop is in scope: not verified.

### United States

- No general federal right to return a purchase. The shop's posted policy governs; some states require the policy to be posted. Not verified per state.
- The Federal Trade Commission rule on mail, internet and telephone orders is understood to require shipping within the stated time, or 30 days, or offering a refund. Not verified.
- Fibre content, country of origin and care labels are required by FTC rules. Origin and fibre content are understood to be required in online descriptions too. Not verified.
- Sales tax depends on the state and on sales volume into that state. Needs an accountant.
- "Made in USA" claims have a specific FTC standard. Not verified.
- Children's sleepwear has flammability rules. Not verified.
- The Americans with Disabilities Act is applied by courts to shop websites in many cases. Not verified.

### What the product does with this

- It may generate the **structure** of privacy, terms of sale, delivery and returns pages, each marked as a draft. The returns terms themselves come from the customer (mandatory fact 11).
- It never writes a returns window, a guarantee or a "complies with" statement on its own.
- It asks which country the shop is in, and which countries it sells to, before generating any legal page or turning on checkout.

## 8. Site vs app

This domain has the sharpest line between a site and an app. A boutique that sells in person needs pages. The moment the site takes money, it needs stock, orders, payment, emails and a person who packs. Ask mandatory fact 3 first and build the smaller thing unless the customer chose the larger.

### Content pages (no data, no accounts)

Home, about, lookbook or collection pages, shop address and hours, services, contact, policies, legal pages. A product showcase with "ask about this item" also fits here, as long as it does not show stock or take payment.

| Part | Empty | Error | Notes |
|---|---|---|---|
| Product showcase | "New pieces are on their way - visit the shop or message us" | a broken image is hidden, not shown as a broken icon | No stock shown; "ask us if it is still available" |
| Lookbook | section hidden | | |
| Shop details | cannot be empty when there is a shop | | "Open now" needs the shop's time zone |
| Reviews | section hidden | | Never placeholders |

### Needs data

| Part | What it needs | Empty state | Loading | Error | Save | Permissions |
|---|---|---|---|---|---|---|
| Catalogue with live stock | products, variants, stock | category with no products: "Nothing here right now" with a link to all products, never a blank grid | product cards show placeholders of the right size so the page does not jump | "Could not load the products - try again" with a retry | n/a | everyone reads; owner writes |
| Search and filters (size, colour, category) | the catalogue | "No results for this search" with the filters shown and a "clear filters" action; reference 1 shows suggested collections on its no-results state | results area shows it is working | filters keep their state after an error | n/a | everyone |
| Basket | chosen variants, kept between visits on the same device | "Your bag is empty" with a link to new arrivals; four of the six references show an explicit empty-basket text | quantity change shows it is being applied | an item that sold out while in the basket is marked, not silently removed | saved on every change | the visitor only |
| Checkout | buyer details, delivery option, payment service | n/a | the pay button shows "processing" and cannot be pressed twice | payment refused: the reason in plain words, basket kept, nothing charged twice; stock gone at the last moment: say which item | the order is saved before payment is confirmed; the buyer sees a confirmation they can keep | the buyer sees only their own order |
| Order status for the buyer | order with fulfilment status, tracking | "No orders yet" | | link expired: show the contact route | | through a personal link or an account |
| Returns request | order, lines, reason | "Nothing to return - this order is outside the return window", with the policy | | | request saved; buyer sees what happens next and who pays postage | buyer: own orders; owner: all |
| Owner's order list | all orders | "No orders yet" | | never show a stale list without saying so | every status change saved with who made it | owner and staff, behind a login |
| Owner edits products and stock | an edit screen, image upload | "No products yet - add your first" | image upload shows progress | a failed save says so and keeps what was typed | visible on the public site right after saving | owner and staff |
| Discount codes and gift cards | codes, balances, validity | | | "This code has expired" or "does not apply to these items", stated plainly | balance reduced only when the order is paid | owner creates; buyer redeems |
| Back-in-stock waiting list | variant, email, consent | | | | "We will email you once" | owner sees counts, not a marketing list |
| Newsletter signup | email, consent, a sending service | | | "Not saved - try again" | double opt-in where the law expects it | |

### Needs accounts

- The owner always needs one when anything is editable or any order is stored.
- Staff need them when more than one person packs or edits.
- Buyers should be able to buy as a guest. An account is justified for order history, saved addresses or a loyalty scheme. Two references show "sign in" in the header next to the basket.

### Needs payments

- Any online sale. Also gift cards, deposits on pre-orders.
- Each brings failed payments, refunds, partial refunds, receipts or tax invoices, and the consumer law of every country sold to.
- Default: no payments. Turned on only when the customer answered mandatory facts 8 to 13.

### Using an existing shop platform

Every one of the references runs a full online shop, and several show signs of a standard hosted shop platform. A customer who already has one keeps it: the product is then a content site that links to it, or nothing at all. Building a second checkout next to an existing one creates two stock numbers, which is failure mode 1.

Services seen in the references that are **not** defaults and each need their own answers from the customer: try-before-you-buy with payment taken after a trial period (references 4 and 5), repairs and alterations in store (reference 3), a resale or take-back scheme (references 1 and 3), a loyalty scheme (reference 5).

## 9. References

**How these were checked.** Each URL was fetched on 2026-11-21 with a page-extraction tool that returns the page's text and image references. No browser was used and no screenshot was taken. Section order and wording are observed; visual quality, layout and the image-to-text ratio are **not** observed, and every ratio below is an estimate from counts in the extracted text. Image counts include logos, icons and navigation thumbnails; the tool appears to cap at 100. Only home pages were fetched: no product page, category page or checkout was observed.

**Curation.** Chosen by the author from UK and US clothing labels with their own shops and sites, not from a search-result list. No awwwards.com category was consulted; none of these is claimed as an award winner. All are in English, in Latin script.

**Limit.** All six are established brands that design their own clothes and run their own online shops, in the UK and the US. No single neighbourhood boutique, no multi-brand shop, no second-hand shop and no shop without online selling was verified. The skeletons are a ceiling for structure, not a picture of the typical customer.

Verified: 6.

| # | Site | Checked | What was observed |
|---|---|---|---|
| 1 | https://www.toa.st | 2026-11-21 | UK label, women, men and home. A bar at the very top states the free-delivery threshold and free returns. Navigation by department (New in, Women, Men, Home), each opening into clothing types and then fabrics (cashmere, cord, denim, linen); also "Reworn" and "Renewed" resale lines and gift cards. Home page has three "shop new in" tiles, a magazine section with dated articles, a newsletter offer with a first-order discount, and a delivery-country confirmation prompt. The search no-results state suggests popular collections and useful pages. Extraction: 46 images, about 5,000 characters, mostly navigation. |
| 2 | https://communityclothing.co.uk | 2026-11-21 | UK label. Top bar states an extended returns period with an end date. Navigation is a flat list of about twenty-five garment types, plus "Shop by regions" (where each item is made), a bargain section and "Back in stock". Product cards carry labels such as "Sale", "Sold out", "In stock", "Save up to". Lower on the page: long first-person blog entries about individual garments and factories. Extraction: 100 images (cap), about 7,200 characters. |
| 3 | https://oliverspencer.co.uk | 2026-11-21 | London menswear label. Editorial order: a season film - a gift block - then one block per category (outerwear, tailoring, shirts), each with one image, a heading and one or two sentences that say something concrete (where it is made, that jackets and trousers are sold separately) - a journal entry - "Our shops" with one named shop and its services (fittings, alterations, repairs, checking shop stock on a product page) - seasonal highlights as named products - about, responsibility, stores. Extraction: 100 images (cap), about 3,500 characters. |
| 4 | https://www.margarethowell.co.uk | 2026-11-21 | UK label. Header: sign in, bag ("No items in your bag"), orders, wish list, customer services. Home: gift ideas and "shop" tiles by category for two lines - two shop-finder links - mailing list with a privacy-policy link - a "try before you buy" service explained in steps (delivery, a five-day trial, payment only for what is kept; a concierge appointment in one city) - a help block with live chat, email and phone, each with hours and a response time. Extraction: 10 images, about 2,000 characters. |
| 5 | https://www.studionicholson.com | 2026-11-21 | London label. Order: an editorial music feature - newsletter with a first-order discount and a pointer to terms - concierge and try-before-you-buy in three numbered steps - a seasonal outerwear block - a gifts selection with product cards showing name and price - new in - stores in four cities - loyalty scheme - accepted payment methods listed. Extraction: 37 images, about 1,800 characters. |
| 6 | https://www.everlane.com | 2026-11-21 | US label. Top bar: free-shipping threshold; the empty bag says "Your bag is empty", offers new arrivals and best sellers, and shows the amount left to reach free shipping and the returns window. Home: a priced campaign ("starting at" a stated price) - shop women / shop men - a short statement of what the brand stands for - gift guide - favourites - "visit one of our stores" with a store finder - impact report. Extraction: 30 images, about 2,800 characters. |

Loaded and not used:

| Site | Checked | Why not |
|---|---|---|
| https://www.folkclothing.com | 2026-11-21 | Loads, and is the brand's own shop, but the extraction returned only product names, a free-shipping line and an empty-cart text (about 580 characters). Not enough to describe the structure. |
| https://www.asket.com | 2026-11-21 | Loads. Extraction returned one product, one paragraph about the permanent collection and a line about stores (about 390 characters). Too thin. |
| https://www.youmustcreate.com | 2026-11-21 | Loads. Extraction returned a season statement, lookbook and new-arrivals links and "Your bag is empty" (about 290 characters, one image). Too thin. |

Tried and did not load (not counted): universalworks.co.uk, paynterjacket.com, lfmarkey.com, noahny.com, sezane.com.

## 10. Skeletons

Structure only. No colours, logos, photographs or wording were taken from any reference.

### Skeleton A: the shop (product-first)

For a shop that sells online and wants the visitor among the products quickly. Default when the customer chose online selling.
From references 1, 2 and 6; the top bar is from all three, the empty-basket behaviour from 6, the "made in" grouping from 2.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Top bar | one line: delivery price or threshold, and the returns promise - only what the customer stated | smallest text on the page, always first | required when selling online |
| 1 | Header | name; navigation by department or category; search; basket with a count | basket always visible | yes |
| 2 | Opening | one image or campaign with one line and one action into the products | one heading, one action | yes |
| 3 | Ways in | three to six tiles: new in, main categories or departments | image with a label | yes |
| 4 | Products | a grid of new or featured products: image, name, price, colours available, sold-out mark | image first, then name, then price | yes |
| 5 | The shop's story | who makes it, where, why - a few sentences and a link | short text beside one image | optional |
| 6 | Visit us | shop address, hours, services in the shop | complete without a map | required when there is a physical shop |
| 7 | Newsletter | email, consent, what they will receive | one field | optional |
| 8 | Footer | delivery, returns, size guide, contact with hours, privacy, terms, accessibility statement; payment methods accepted | grouped links | yes |

Image-to-text ratio: **estimate**, from extraction counts only (references 1, 2 and 6 returned 30 to 100 images against roughly 2,800 to 7,200 characters, much of the text being navigation). Image-led: most blocks are an image with a name and a price. Running text is confined to the story block and the policies. Not confirmed in a rendered view.

Product page (not observed in the references; domain knowledge, marked as a default in section 4): photographs - name - price - colour choice - size choice with sold-out sizes shown - size guide link - add to basket - description - composition and care - delivery and returns summary.

### Skeleton B: the label (story-first)

For a small label or boutique with few pieces, where the reason to buy is the maker's point of view. Also the right skeleton for a shop that does **not** sell online: the product blocks then lead to "ask about this piece" and section 6 carries the weight.
From references 3, 4 and 5.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; short navigation; basket if selling online | quiet | yes |
| 1 | Season or statement | one image or film and one sentence about this season or this shop | one heading | yes |
| 2 | Category blocks | one block per category: one image, a heading, one or two concrete sentences (what it is made of, where, how it is sold), one link | alternating image and text; three to five blocks | yes |
| 3 | Selected pieces | a short row of named products with prices | small grid | optional |
| 4 | Services | fittings, alterations, repairs, try at home - only what the shop really does, in steps | numbered steps where there is a process | optional |
| 5 | Journal | one or two entries | heading and a line each | optional, hidden when empty |
| 6 | Our shop | address, hours, phone, what can be done there | this block is the main action for a shop without online selling | required when there is a shop |
| 7 | Help | how to reach the shop, with hours and a response time | plain list | yes |
| 8 | Footer | as Skeleton A | | yes |

Image-to-text ratio: **estimate**. References 3 and 5 returned 37 to 100 images against 1,800 to 3,500 characters; reference 4 returned 10 images against 2,000. Each block is one large image with two or three lines. Fewer products on the home page than Skeleton A, and more sentences per block. Not confirmed in a rendered view.

## 11. Not verified

1. All Hebrew and Arabic terms in section 6: author's knowledge, not checked with a working retailer. Cells marked "not verified" must not be filled by guessing.
2. Every legal statement in section 7. None was checked against a statute or an official source. Cancellation periods, labelling duties and price-reduction rules in particular must be checked per country before checkout is turned on.
3. Image-to-text ratios and visual quality of all references: text extraction only, no rendered view. Image counts of 100 are the tool's cap, not a real count.
4. No awwwards.com category was consulted; design quality of the references is the author's prior judgement.
5. Only 6 references verified, all established own-label brands in the UK and US. No neighbourhood boutique, multi-brand shop, second-hand shop or shop without online selling.
6. No product page, category page, size guide, basket or checkout of any reference was fetched. The product-page order in sections 4 and 10 is domain knowledge, not an observation.
7. The statement that references run on a hosted shop platform is inferred from wording in the extracted pages; it was not confirmed.
8. Free-delivery thresholds, return periods and discounts mentioned in the reference notes are what the pages stated on the day.
9. No references in Hebrew, Arabic or any non-Latin script. These come in a later phase.
