# Accountant

Covers: a practice that keeps books, prepares accounts and tax returns, runs payroll or advises on tax for people and small businesses: accountant, bookkeeper, tax adviser, payroll bureau. One person or several offices.
Does not cover: lawyers (use `lawyer.md`); financial advisers, insurance agents and lenders; accounting software sold as a product (use `landing-page.md` or `product-docs.md`).
Written 2026-11-21. References checked 2026-11-21. Template: [README.md](README.md).

## 1. Objects

An accounting practice sells **a recurring relationship built around deadlines**. A client hands over their papers, the practice files the right thing with the authority on time, and this repeats every month, quarter and year. The visitor wants to know three things: do you handle someone like me (employee, sole trader, company, landlord), what will it cost per month or per year, and how do I hand over my mess. Everything a client sends is financial and identity data.

### Practice (the business)

| Field | Required | Example (illustrative) |
|---|---|---|
| Name | required | "Carmel Accounting" |
| Kind of practice | required | accountant, tax adviser, bookkeeper, payroll |
| Professional status | required | exactly the licence or membership held, with the body |
| Who it serves | required | employees, sole traders, small companies, landlords, non-profits, a sector |
| Country and tax system it works in | required | one country, or named cross-border work |
| Address | required | office, or "online only" with a registered address |
| Phone | required | |
| Office hours | required | |
| How to start | required | call, callback form, quote request, book a meeting |
| What the first conversation is | required | length, free or priced |
| Email | optional | |
| How clients send documents | optional | in person, by upload, through an app, by post |
| Software the practice works with | optional | only named products it really supports |
| Languages | optional | |
| Regulatory and supervision statements | required where the body requires them | |

### Office (only when there is more than one)

Address, phone, hours, and the team at that office.

### Team member

| Field | Required | Example |
|---|---|---|
| Name | required | first name is enough for support staff |
| Professional title | required | exactly as licensed: certified or chartered accountant, tax adviser, bookkeeper, payroll clerk, trainee |
| Licence or membership number | optional; required where customary | |
| Role | optional | partner, manager, client contact |
| Fields | optional | sectors, kinds of client |
| Office | optional | |
| Photo, short bio | optional | with consent |

### Client type (who it is for)

| Field | Required | Example |
|---|---|---|
| Name in the visitor's words | required | "Self-employed", "Limited company", "Landlord", "Employee tax refund", "New business" |
| What the practice does for this type | required | the list of filings and services |
| Starting price or package | optional | |

### Service

| Field | Required | Example |
|---|---|---|
| Name | required | "Annual tax return", "Monthly bookkeeping", "VAT reports", "Payroll", "Year-end accounts", "Opening a business file", "Tax refund claim" |
| Category | required | Bookkeeping, Tax, Payroll, Accounts and audit, Starting up, Advice |
| What is included | required | which filings, how many transactions or payslips, meetings |
| What is not included | optional | audits by the authority, back years, penalties |
| How often | required | one-time, monthly, quarterly, yearly |
| For which client types | optional | |
| What the client must provide, and by when | optional | "bank statements and invoices by the 10th" |
| Price | optional, see rule 5 | |
| Price type | required when a price is shown | fixed per month, fixed per filing, "from", hourly, by quote, percentage of a refund where allowed |
| Tax on the price | required when a price is shown | including or excluding VAT |
| Currently offered | required, default yes | |

### Package

| Field | Required | Example |
|---|---|---|
| Name | required | "Sole trader", "Company" |
| Services included | required | a list of services above |
| Price and period | required when shown | per month |
| Limits | required when shown | turnover band, number of invoices, number of employees |
| Minimum term and notice | optional | |

### Enquiry or quote request (only when the product stores them)

| Field | Required | Example |
|---|---|---|
| Name | required | |
| Phone or email | required | |
| Client type | required | from the practice's list, plus "not sure" |
| What help is wanted | optional | from the service list |
| Rough size | optional | turnover band, number of employees; bands, not exact figures |
| Already has an accountant | optional | switching has its own steps |
| Message | optional | with a warning not to send ID numbers or documents |
| Status | required | new, answered, quote sent, meeting booked, engaged, declined |

### Other objects

| Object | Fields | Notes |
|---|---|---|
| Deadline | what, for whom, date, tax year, source | A fact about the law, not about the practice; see rule 10 |
| Article, guide | title, text, author, date, tax year, country | General information; goes stale every budget |
| Calculator | inputs, formula, tax year, source of the rates | Wrong rates mislead; off by default |
| Document checklist | per service: what to bring | Useful, low risk |
| Review, case story | text, first name or business name with consent, date, source | Real only |
| Recognition, software partner status | body, year | Real only |
| Engagement letter | scope, fee, responsibilities | Signed at onboarding; outside the public site |
| Client documents, ledgers, returns | | Confidential. App only; see section 8 |

## 2. Rules

1. Every professional title is exactly what the person or practice holds. A bookkeeper is not called an accountant where "accountant" is licensed; "chartered", "certified" and "tax adviser" are used only by those who hold them.
2. The site says which country's tax and accounting it handles. It does not suggest it can file elsewhere.
3. No result is promised: no "guaranteed refund", "we will cut your tax by", "audit-proof", "pay zero tax". A figure of money saved for clients is shown only with its basis and period.
4. Every service says what is included and how often. "Bookkeeping" alone is not a service description.
5. A price is optional but its absence is explicit: "by quote". Never blank, never zero.
6. A shown price states its period, whether tax is included, and the limits it assumes (turnover, transactions, employees). A "from" price says what moves it.
7. A package lists exactly which filings it covers. What costs extra is listed next to it.
8. "Free consultation" or "free quote" is written with its real limits.
9. A percentage-of-refund fee is shown only where it is lawful and with the percentage.
10. A tax rate, threshold or deadline is published only with its tax year, its country and a source the customer gave, and is reviewed every year. Without those it is not published.
11. Everything published as information is general, dated, and says it is not personal tax advice.
12. A public form never asks for an ID or tax number, bank details, passwords to tax-authority accounts, or documents.
13. Documents travel only through a channel built for them (upload inside a login, or the practice's own system), never as attachments to a public form's email.
14. No client is identifiable in public without written consent. Business clients' logos and names need the same consent.
15. A review is real and carries its source.
16. A software product, bank or authority is named as a "partner" only if a real partnership exists.
17. The practice's responsibility and the client's are both stated where a deadline is mentioned: the practice files on time if the client delivers by the stated date.
18. Messages and reminders carry no figures and no tax details in the subject or preview.
19. The main action is reachable from every page on a phone; the phone number is tappable; the address opens a map.
20. Stock photographs of people are not presented as the team or the clients.

## 3. Mandatory facts

The product is not built until each has an answer. None may be guessed.

| # | Fact | The one question to ask | Why (the human reason) |
|---|---|---|---|
| 1 | Name | "What is the practice called?" | People are referred by name. |
| 2 | What you are | "Are you an accountant, a tax adviser, a bookkeeper? Which licence or membership do you hold, and from which body?" | People trust a title, and using the wrong one can be an offence. |
| 3 | Who you serve | "Who are your clients: employees, self-employed, companies, landlords, a particular trade?" | A visitor must see themselves in the first line. |
| 4 | Country | "In which country do you file? Any cross-border work?" | Tax is national; the wrong country is the wrong accountant. |
| 5 | Services | "What do you do for a client through the year? List it as you would explain it to a new client." | People do not know what they need; they recognise it when they read it. |
| 6 | Fees, or the decision not to show them | "How do you charge: per month, per return, by the hour? Do you want prices or packages on the site?" | An open-ended bill is the main fear. Hiding is allowed; inventing is not. |
| 7 | The first step | "What happens when someone contacts you? Is the first conversation free? How long?" | The whole site leads to this step. |
| 8 | Where | "Where is the office? Do you work with clients fully online?" | Some people want to hand over a folder in person; others never want to come. |
| 9 | Phone and hours | "What number do people call, and when is it answered?" | A letter from the tax authority makes people want a human today. |
| 10 | How papers reach you | "How do clients give you their documents today?" | It decides whether the product needs an upload at all. |
| 11 | Who is the business legally | "What is the registered name and number, which body supervises you, and who handles privacy requests?" | Clients' financial records must have a named, responsible holder. |

Needed only when the product stores enquiries, documents or bookings:

| # | Fact | The one question to ask | Why |
|---|---|---|---|
| 12 | Where enquiries go | "Where should each enquiry arrive, and who answers?" | An enquiry in January that is answered in March has already missed the deadline. |
| 13 | What a package assumes | "For each price: up to what turnover, how many invoices or employees?" | Without limits a fixed fee becomes an argument. |
| 14 | Existing systems | "Do you already use accounting or practice software with a client portal?" | Clients should not upload the same papers to two places. |
| 15 | Meeting times | "When do you hold first meetings, and how long are they?" | For booking. |

## 4. Declared defaults

Each default is shown to the customer as "we filled this in - change it if it is wrong".

| Default | Value | Why it is safe | How it is marked |
|---|---|---|---|
| Main action | "Call us" or "Request a callback" | Works with zero setup | "default" |
| Client-type headings | Self-employed, Companies, Individuals | Descriptive; the lists under them come from the customer | Editable; an empty type is hidden |
| Service categories | Bookkeeping, Tax, Payroll, Accounts, Starting up | Descriptive | Editable |
| Missing price | "By quote" | Says openly there is no number | Listed as "no price given" |
| "How it works" steps | get in touch, a short conversation, a fixed quote | Seen in the references; true only if the customer confirms | "Default steps - confirm they match what you do" |
| Form fields | name, phone or email, client type, what help | The least needed to call back | List the customer can cut |
| Form warning | "Please do not send ID numbers, bank details or documents through this form." | Rule 12 | Default text |
| Information notice | "General information, not personal tax advice", with a date | Rule 11 | Default text |
| Deadlines, rates, calculators | none | They are facts about the law that change yearly | "Not created - add your own with a tax year and a source" |
| Reviews, client names, savings figures | hidden | Must be real and consented | "Off until you provide them" |
| Page order | Skeleton A below | From the references | Named as default |
| Language, direction, currency | from the conversation and address | | Shown |
| Legal page structure | headings only | | "Draft - review before publishing" |

Never a default: titles, licences, memberships, supervision statements, services, prices, package limits, tax rates, thresholds, deadlines, savings figures, number of clients, software partnerships, years of experience, awards, any statement about tax law.

## 5. Failure modes

| What went wrong | What the visitor sees | What it costs | Prevention |
|---|---|---|---|
| Old tax rate or deadline on the site | Relies on it; files late or budgets wrong | A penalty for the reader; the practice blamed | Rule 10; nothing without a tax year and a yearly review |
| Seasonal banner left up | "File before 31 January" shown in June | Looks abandoned | Banners carry an end date |
| Fixed fee without limits | Bill rises when the business grows | Dispute | Rules 6, 7; mandatory fact 13 |
| "From" price read as the price | Quote is double | Distrust | Rule 6 |
| Package unclear on what is included | Assumes the personal return is in the company package | Missed filing, penalty, argument | Rule 7 |
| Savings promised | Expects a refund that does not come | Complaint; professional-conduct issue | Rule 3 |
| Title overstated | Believes a licensed accountant signs the accounts | A false claim; an offence where the title is protected | Rule 1 |
| Enquiry not answered | Goes elsewhere, or misses a deadline waiting | A lost client; the customer never knows | Mandatory fact 12; test the alert |
| ID number and payslips emailed through the form | Identity documents sit in an inbox | A data-protection problem | Rules 12, 13 |
| Upload fails silently | Client believes the papers were delivered | A missed deadline | Upload confirms each file by name; failure says so |
| Client delivers late, practice blamed | "You said you file on time" | Dispute | Rule 17 |
| Switching not explained | Stays with a bad accountant out of fear of the paperwork | Lost clients | A short "switching to us" block from the customer's own process |
| Software named that the practice dropped | Buys the wrong software | Annoyance | Rule 16; dated list |
| Team member left, still listed | Asks for someone who is gone | Looks neglected | Profile can be hidden |
| Jargon | Does not recognise their own situation | Lost clients | Client types in the visitor's words |
| Calculator with last year's bands | A wrong number with the practice's name on it | Harm and blame | Calculators off by default; tax year shown on the result |

## 6. Professional language

Hebrew and Arabic terms are the author's knowledge, not checked with a practising accountant in either language. Tax terms are specific to each country; the Hebrew terms are Israeli usage. "Not verified" means do not use a guess.

| English | Meaning | Hebrew | Arabic |
|---|---|---|---|
| Accountant (licensed) | | רואה חשבון | محاسب قانوني |
| Accounting firm | | משרד רואי חשבון | مكتب محاسبة |
| Tax adviser | | יועץ/ת מס | مستشار ضريبي |
| Bookkeeper | | מנהל/ת חשבונות | محاسب / ماسك دفاتر (not verified) |
| Bookkeeping | | הנהלת חשבונות | مسك الدفاتر |
| Payroll | | חשבות שכר / שכר | الرواتب |
| Payslip | | תלוש שכר | قسيمة راتب / كشف راتب |
| Client | | לקוח/ה | عميل / زبون |
| Self-employed, sole trader | | עצמאי/ת | مستقل (not verified) |
| Small exempt business (Israel) | below the VAT threshold | עוסק פטור | not verified |
| VAT-registered business (Israel) | | עוסק מורשה | مشتغل مرخّص (not verified) |
| Limited company | | חברה בע"מ | شركة محدودة |
| Non-profit association | | עמותה | جمعية |
| Opening a business file | registering with the tax authorities | פתיחת תיק | فتح ملف (not verified) |
| Income tax | | מס הכנסה | ضريبة الدخل |
| VAT | | מע"מ | ضريبة القيمة المضافة |
| National insurance (Israel) | social-security contributions | ביטוח לאומי | التأمين الوطني |
| Tax authority | | רשות המסים | سلطة الضرائب |
| Annual tax return | | דוח שנתי | إقرار ضريبي سنوي |
| Periodic report | monthly or bi-monthly filing | דוח תקופתי | not verified |
| Advance payments | tax paid during the year | מקדמות | سلف ضريبية (not verified) |
| Withholding tax | | ניכוי במקור | خصم من المصدر |
| Tax refund | | החזר מס | استرداد ضريبي |
| Statement of assets | declaration of wealth | הצהרת הון | not verified |
| Financial statements | | דוחות כספיים | القوائم المالية |
| Balance sheet | | מאזן | الميزانية العمومية |
| Profit and loss | | דוח רווח והפסד | بيان الأرباح والخسائر |
| Audit | | ביקורת | تدقيق |
| Tax assessment | the authority's decision on tax due | שומה | ربط ضريبي (not verified) |
| Invoice / receipt | | חשבונית / קבלה | فاتورة / إيصال |
| Deductible expense | | הוצאה מוכרת | مصروف معترف به (not verified) |
| Tax year | | שנת מס | السنة الضريبية |
| Retainer, monthly fee | | ריטיינר | not verified |
| Fee | | שכר טרחה | أتعاب |
| Power of attorney to the tax authority | lets the practice act for the client | ייפוי כוח | توكيل |

Notes on language:

- UK: "chartered accountant", "sole trader", "limited company", "self assessment", "VAT", "HMRC". US: "CPA", "sole proprietor", "LLC", "sales tax", "IRS". Israel: the terms in the table. Tax vocabulary does not translate between countries; never carry one country's terms into another.
- Visitors say "my taxes", "my books", "a refund", "I opened a business". Use their words as headings and the formal name second.
- Words to avoid: "guaranteed refund", "pay less tax" as a promise, "audit-proof", "loopholes", "tax-free" without context, "certified" or "chartered" without the status, "cheapest".
- The product does not write tax explanations. It lays out what the practice supplies, with a date and a tax year.

## 7. Legal

A checklist of questions, not legal advice. The author is not a lawyer or an accountant and read no statute or professional rule for this file. Everything needs checking by the customer, who is the professional here, for their own country.

### Applies almost everywhere

- **Titles and reserved work.** Some titles (certified, chartered, licensed tax adviser) and some work (statutory audit, representing clients before the tax authority) are reserved by law. Other work (bookkeeping) is often open to anyone.
- **Anti-money-laundering.** Accountants and tax advisers are commonly required to identify clients and report suspicions, and to be supervised for it. This happens at engagement.
- **Confidentiality** is a professional duty, with exceptions the law imposes.
- **Financial and identity data.** Returns, payslips, bank statements and ID numbers are high-risk data. A privacy notice, retention periods (tax records are kept for years by law) and secure transfer are needed.
- **Advertising** is subject to consumer law and to the professional body's code: no misleading claims about savings, fees or status.
- **Engagement letter.** Scope, fees and each side's responsibilities are set out in writing in most professional frameworks.
- **Professional indemnity insurance** is required by many bodies; some require stating it.

### Israel

- Auditors Law (1955): "roeh heshbon" is a licensed title, and audit is reserved. Conduct rules on advertising and soliciting clients exist under it; whether and how advertising is restricted today: not verified.
- Law Regulating the Practice of Representation by Tax Consultants (2005): tax advisers are licensed and may represent clients before the tax authorities. Scope: not verified.
- Bookkeepers are graded by training but, as far as the author knows, the occupation is not licensed. Not verified.
- Anti-money-laundering duties for accountants acting as business-service providers. Scope and current state: not verified.
- Record-keeping: tax rules require keeping books for several years (believed seven). Not verified.
- Privacy law (Amendment 13, in force August 2025) and data-security regulations apply to databases of clients' financial data. What a small office must do: not verified.
- Accessibility statement, consent for advertising messages, prices to consumers including VAT: as in other domain files; not verified for this profession.

### European Union and United Kingdom

- UK: "accountant" is not a protected title; "chartered accountant" and similar are. Anyone providing accountancy services by way of business must be supervised for anti-money-laundering by a professional body or by the tax authority. Statutory audit is reserved to registered auditors. Not verified.
- One reference carries a footer statement that the group and its subsidiaries are authorised and regulated by a chartered institute; another carries a regulator statement for its legal-services arm (observed 2026-11-21).
- UK: Making Tax Digital requires digital records and software filing for VAT and, in stages, for income tax of sole traders and landlords above income thresholds. Two references explain it on their home pages (observed 2026-11-21). Thresholds and dates: not verified.
- GDPR / UK GDPR; cookie consent. One reference shows a cookie-consent manager and an accessibility-settings tool on its home page (observed 2026-11-21).
- EU: the profession is regulated very differently by member state (tax advice is reserved in Germany, open in others). Not verified.

### United States

- "CPA" is a state licence. Enrolled agents are federally licensed. Paid return preparers need a preparer identification number; conduct before the tax authority is governed by Circular 230. Not verified.
- Tax-return information may not be disclosed or used without consent (Internal Revenue Code section 7216). Financial institutions including tax preparers must have a written information-security plan (FTC Safeguards Rule). Not verified.
- State rules on firm names, advertising and contingent fees. Not verified.

### What the product does with this

- Asks the country and the exact professional status before generating any page.
- Never publishes a rate, threshold or deadline of its own.
- Never states that the site "complies with" a named law, and never writes a claim about tax savings.
- Marks every legal page as a draft for review.

## 8. Site vs app

### Content pages (no data, no accounts)

Home, who we work with, services, packages and fees, how it works, switching to us, team, guides, contact, legal and regulatory pages. With a phone link as the action, this is a complete product and holds no client data.

| Part | Empty | Error | Notes |
|---|---|---|---|
| Client types | cannot be empty (at least one) | | In the visitor's words |
| Services | cannot be empty | | Each with what is included |
| Packages and fees | "By quote - call us" | | Limits shown with every price |
| Team | hidden; for one person, About instead | missing photo: initials | Real titles |
| Guides | hidden | | Each with date, tax year, country |
| Deadlines, calculators | hidden | | Off by default |
| Reviews, client logos | hidden | | Never placeholders |
| Regulatory statements | cannot be empty where required | | Footer |
| Hours, map | office hours cannot be empty | text address remains | "Online only" is a valid answer for the address |

### Needs data

| Part | What it needs | Empty state | Loading | Error | Save | Permissions |
|---|---|---|---|---|---|---|
| Callback or enquiry form | contact details, client type; alerts the practice | n/a | "sending", no double press | "Not sent - please call", with the number; what was typed is kept | "Received", and the answer time the practice gave | visitor writes; only the practice reads |
| Quote request | client type, services wanted, size bands | n/a | | as above | "We will send a quote", never an automatic price unless the practice gave a full price table | as above |
| Instant quote | a complete price table with limits | combination not covered: "we will quote this by hand" | | | the quote shows its assumptions and a date | visitor sees own quote |
| Book a first meeting | times, length | "No times this week - call us" | placeholder, never an empty calendar that reads as "full" | "Could not load times - call us" | "requested" until confirmed | visitor sees own request |
| Document upload | client accounts, secure storage | "Nothing uploaded yet", with what is expected and by when | progress per file | a failed file is named and can be retried; never a silent failure | each file confirmed by name, with date; the practice is alerted | a client sees only their own files; staff see their clients; owner sees all; every access logged |
| Client area (what is due, what was filed, what is missing) | accounts; the practice keeps it current | "Nothing due right now" | | never show an old status as current; show "last updated" | changes record who made them | as above |
| Practice edits content | edit screen | | | failed save says so | live after saving | owner or manager |
| Newsletter | email, consent | | | | confirmation | unsubscribe in every message |

### Needs accounts

- The practice, once anything is stored or editable.
- Visitors need no account to enquire, ask for a quote or book a meeting.
- Clients need accounts for document upload and a client area. This holds identity and financial records and must be built to that standard, or not built: three references send clients to their own app or a login (observed 2026-11-21).

### Needs payments

- Monthly subscription for a package; one-time fee for a return; paid consultation.
- Brings invoices with tax, failed and retried payments, cancellation and notice periods.
- Default: no payments. Recurring fees are usually collected by standing order.

### Using an existing system

Most practices already use accounting and practice software, and many of those include a client portal and document capture. If the customer has one, the product is a content site with a "client login" link to it, and holds no client documents. Ask first (mandatory fact 14).

## 9. References

**How these were checked.** Each URL was fetched on 2026-11-21 with a page-extraction tool that returns text and image references. No browser, no screenshot. Section order and wording are observed; visual quality and image-to-text ratio are not, and every ratio is an estimate from counts in the extracted text. Names of individual staff and clients that appear on the sites are left out.

**Curation.** Chosen by the author from known UK and US practices and online accounting services, not from a search-result list. No awwwards.com category was consulted. All in English, Latin script. Home pages only.

**Limit.** Seven of eight are UK practices; one is a US bookkeeping company. References 1, 2 and 4 are subscription services built around their own software. No one-person practice was verified.

Verified: 8.

| # | Site | Checked | What was observed |
|---|---|---|---|
| 1 | https://www.mazumamoney.co.uk | 2026-11-21 | UK subscription accountants for sole traders, freelancers and small companies. Order: a blunt headline - one line saying who it is for - "subscriptions from" a monthly price plus VAT - "What makes us different" in three blocks (we do the bookkeeping, software included, we built it) - the app in three one-word steps (photograph, send, done) - audiences - "Support tailored to you": four cards by legal form (sole trader, limited company, partnership, LLP), each listing the exact filings covered - founder - client quotes - team - a "switch to us" closing action. Extraction: about 19 image references, about 8,700 characters. |
| 2 | https://www.crunch.co.uk | 2026-11-21 | UK online accountants. Header: Log in, Get a quote, Contact sales. Order: headline - one line listing what is handled - an explainer of a coming tax-filing change - a line stating a total of tax saved for clients this year, with "get an instant quote" - three points (fixed-fee pricing, tax savings, checked returns) - awards - "Real regulated accountants at every stage": service blocks - a video overview - three client stories under first names - knowledge hub. Extraction: no image references returned, about 4,000 characters. |
| 3 | https://www.taxassist.co.uk | 2026-11-21 | UK network of local accountants for small businesses. Order: headline with "fixed-fee" in the first sentence - a seasonal prompt about the tax-return deadline - "Businesses" / "Personal" split - "Fixed fees and flexible packages": three cards (sole traders, landlords, limited companies), each with "what's included" - "Join us in three easy steps": get in touch, chat to an expert, get a fixed quote - extra benefits - closing action - latest finance news. Extraction: about 34 image references, about 7,300 characters. |
| 4 | https://pilot.com | 2026-11-21 | US bookkeeping, tax and advisory for startups and small businesses. Header: Sign in, Get started. Order: a headline phrased as a question to the founder - a count of client companies - the three services in one sentence - "people and software" - advisers introduced by background - who it is for (company stages) - the client's own questions, quoted ("we keep running out of cash...") - free resources - three ways to buy. Extraction: about 71 image references, about 12,900 characters. |
| 5 | https://www.thp.co.uk | 2026-11-21 | Chartered accountants with four offices in and around London. Order: welcome with a team carousel, each person with their office - a plain-spoken introduction that says most accountants' sites look alike - four "we can" statements (simplify finances, manage processes, advise, set up and train on software) - named software - budget and fiscal-event pages - the four offices - blog with dated posts - case studies. Persistent tools: call us, request a callback, request a free consultation, request a quote, chat to a human, an accessibility-settings panel, a cookie-consent manager. Extraction: about 40 image references, about 18,500 characters. |
| 6 | https://www.raffingers.co.uk | 2026-11-21 | The address of a former independent East London firm now shows the local-office page of the accountancy group that the firm joined. Kept because it is the nearest verified example of a single-office page. Order: "Accountants in [place]" - a callback form at the top - two paragraphs about the office - get in touch - the office team: sixteen people listed by name - what the office specialises in (services, industries) - "Book a meeting", described as a free no-obligation chat - the office phone - latest insights - a second callback form - footer with the professional-body regulation statement and company number. Extraction: about 47 image references, about 12,800 characters. |
| 7 | https://www.accountsandlegal.co.uk | 2026-11-21 | UK firm combining accounting, legal and HR services for small businesses. Order: headline - get in touch - "the right expertise, all in one place" - a managed finance function - "Our services": about thirty cards across accounting, tax, legal and HR - "What's so special about us" (a review claim, a software specialism, a candid third point) - jobs - client quotes with business names - a software-vendor award with its year - free advice - closing action. The navigation carries a large guide library. Footer: a regulator statement for the legal arm. Extraction: about 117 image references, about 22,200 characters. |
| 8 | https://www.blickrothenberg.com | 2026-11-21 | Large London accounting and tax firm. The navigation is very large: each menu mixes service lists with a featured news item; languages offered include Chinese, German and Spanish. Order: welcome - budget coverage - a tax podcast - latest updates and insights, dated - services. Useful as the expertise-first pattern; not a model for a small practice. Extraction: about 26 image references, about 29,100 characters, most of it navigation. |

## 10. Skeletons

Structure only. No colours, logos, photographs or wording were taken from any reference.

### Skeleton A: the practice for small clients (package-first)

For a practice serving self-employed people, small companies and individuals. The site has one job: the visitor recognises their own situation, sees what is included and roughly what it costs, and asks for a quote or a call. Default for this domain.
From references 1, 2, 3, 6: the by-legal-form cards with exact filings from 1 and 3, the three steps of 3, the switching action of 1, the callback form and office team of 6.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; one action (call / get a quote); "client login" only if a real one exists | action prominent | yes |
| 1 | Opening | one sentence: what you are (real title), who you serve, where; the main action; a starting price only if the customer gave one | one heading, one line, one action | yes |
| 2 | Who we work with | one card per client type in the visitor's words; each lists the filings and services covered, and a price or "by quote" | cards of equal weight; lists, not paragraphs | yes |
| 3 | What is included, what is not | for packages: inclusions, limits, extras | table | required when a price is shown |
| 4 | How it works | three steps the customer confirmed: contact, conversation, quote; then how papers are handed over | numbered | yes |
| 5 | Switching to us | what the client has to do, and what the practice does | short | optional |
| 6 | The people | names, real titles, memberships; for one person, an About block | faces with consent | optional |
| 7 | What clients say | real quotes with source | at most three | optional, hidden when empty |
| 8 | Guides | dated, with tax year | list | optional, hidden when empty |
| 9 | Contact | callback or quote form with the no-documents warning; phone; office hours; address or "online only" | form and phone side by side | yes |
| 10 | Footer | registered name and number, professional body and supervision statements, privacy, terms, accessibility statement | small | yes |

Image-to-text ratio: **estimate**, from extraction counts only (references 1, 2 and 3 returned 0 to 34 image references against 4,000 to 8,700 characters). Text-led: roughly one image or illustration per three or four text blocks, and the cards are text. Not confirmed in a rendered view.

### Skeleton B: the advisory firm (expertise-first)

For a firm with several partners serving larger businesses and private clients, where visitors look for a field or a person.
From references 5, 7, 8: the plain introduction and offices of 5, the grouped service cards of 7, the insights of 8.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; navigation: services, sectors or client types, people, insights, contact; phone | | yes |
| 1 | Opening | two sentences: what the firm is and for whom; one action | | yes |
| 2 | Services | grouped (accounts and audit, tax, payroll, advice), each group a short list linking to its page | groups as headings | yes |
| 3 | Who we work with | sectors or client types | list | optional |
| 4 | People | partners first, with titles and fields; by office when there are several | | yes |
| 5 | Insights | three recent dated items; budget or deadline coverage when current | cards | optional, hidden when empty |
| 6 | Offices | address, phone and hours per office | each complete on its own | yes |
| 7 | Contact | callback, consultation or quote request | | yes |
| 8 | Footer | as Skeleton A | | yes |

Image-to-text ratio: **estimate**. Text-led on reference 8 (26 image references against 29,000 characters); more image-led on 5 and 7 (40 and 117, mostly portraits, icons and article thumbnails). Not confirmed in a rendered view.

Risk seen in references 7 and 8: a navigation with dozens of services and guides hides the first step. For a small practice use Skeleton A and list services under client types.

## 11. Not verified

1. All Hebrew and Arabic terms in section 6: author's knowledge, not checked with a practising accountant. Arabic tax terms vary by country.
2. Every legal and professional statement in section 7. None was checked against a statute, a professional body's code or a tax authority's page. Protected titles, supervision duties, record-retention periods and filing thresholds are the least certain.
3. Image-to-text ratios and visual quality of all references: text extraction only.
4. No awwwards.com category was consulted; design quality is the author's prior judgement, and reference 6 is included for structure, not design.
5. No one-person practice reference was verified, and none outside the UK and US.
6. Reference 6: the change of ownership is inferred from the page content at that address, not checked elsewhere.
7. Sub-pages (pricing pages, quote flows, client logins) were not fetched. The package limits and terms of the references are not known.
8. The savings figure on reference 2 and the review and award claims on reference 7 are the sites' own claims, not checked.
9. The claim that most practices already use software with a client portal is the author's belief, supported only by the login links seen on three references.
10. No references in Hebrew, Arabic or any non-Latin script.
