# Personal site

Covers: one person's own home on the web: who they are, what they write, make or think about, and how to follow or reach them. Writers, speakers, researchers, professionals, hobbyists, people between jobs. Often a blog or essays, a "now" page, a list of projects or books, a newsletter.
Does not cover: a creative showing commissioned work to win clients (use `portfolio.md`); a photographer (use `photographer.md`); a musician or band (use `musician-band.md`); a one-page offer for a single book or course (use `landing-page.md`).
Written 2026-11-22. References checked 2026-11-22. Template: [README.md](README.md).

## 1. Objects

A personal site sells **a relationship with one person, on that person's terms**. Everything follows from that: the person decides what is public and what is not, every piece of writing carries a date because a person changes, and the site must keep working for years with little care.

The customer here is a private individual publishing about themselves. That makes this the one domain where the product handles the customer's own personal data as the main content. Rule 1 and section 4 lean towards showing less.

### Person (the owner)

| Field | Required | Example (illustrative) |
|---|---|---|
| Name as shown | required | full name, first name only, or a pen name |
| One line about them | required | "Writer and walker based in a small town" |
| Short bio | optional | three or four sentences; reference 2 uses a timeline by decade |
| Long bio | optional | an About page |
| Photo | optional | the person decides; never required |
| Where they are | optional | country or city at most; never a home address |
| Languages | optional | |
| Contact method | required | a contact form, a public email, or "message me on ..." |
| What they want visitors to do | required | read, subscribe, get in touch, hire, buy a book |
| Links elsewhere | optional | social accounts, code host, other sites; reference 2 lists nine places it syndicates to |
| Pronouns | optional | only if the person gives them |

### Post (essay, article, note)

| Field | Required | Example |
|---|---|---|
| Title | required for essays, optional for short notes | |
| Date published | required | 2026-11-18 |
| Date updated | optional | shown when the post was changed after publishing |
| Body | required | text, images, quotes, links, code |
| Kind | optional | essay, note, link, quote; reference 4 splits Entries, Links, Quotes, Notes, Guides |
| Tags or categories | optional | reference 5 lists every post grouped by category |
| Summary | optional | one line for lists and sharing |
| Status | required | draft, published, unlisted, archived |
| Address | derived | permanent; does not change when the title changes |

### Now page

| Field | Required | Example |
|---|---|---|
| What the person is doing now | required | a few short paragraphs |
| Date last updated | required | the whole point is that it is current |

Reference 2 links to its "now" page from the home page and runs a directory of other people's "now" pages; the idea is common on personal sites.

### Work item (book, project, talk, product)

| Field | Required | Example |
|---|---|---|
| Title | required | |
| Kind | required | book, project, talk, podcast appearance, app, album |
| One line | required | reference 2 gives each book one line |
| Year | optional | |
| Image | optional | a cover |
| Where to get it | optional | links to sellers or the person's own shop; reference 6 lists four sellers for its book |
| Quotes about it | optional, only real, with source | reference 6 quotes two named authors about its book |
| Featured | optional | shown on the home page |

### Other objects

| Object | Fields | Notes |
|---|---|---|
| Newsletter | name, what it covers, how often, signup, sending service | References 3, 4 (digest), 5, 6, 7 all invite signup; reference 6 names two newsletters with their topics and frequency |
| Subscriber | email, consent, date, source | Personal data of other people; see Legal |
| Feed | RSS or Atom address | References 2 and 7 link to feeds |
| Archive | all posts by date or category | Reference 3 pages through 654 pages of older posts |
| Page | title, body | About, Contact, Uses, Colophon |
| Talk or appearance | title, event, date, link to video or audio | Reference 2 lists 250+ interviews, each with audio and a transcript |
| Membership | name, price, what members get | Reference 7 runs a paid membership; payments apply |
| Affiliate disclosure | text | Reference 3 states it takes part in an affiliate programme |
| Comment | author name, text, date, status | Optional; brings moderation work |
| Search | | Reference 3 has "Search this site" |

### How objects relate

A person has posts, work items and pages. A post may have tags and appear in the archive and the feed. A work item may link to posts about it. The newsletter is separate from the site but promoted on it; subscribers belong to the newsletter, not to posts.

## 2. Rules

1. Nothing about the person is published unless the person gave it for publication. Being told something in the conversation is not permission to publish it.
2. A home address, a personal phone number, a date of birth, family members' names and children's photos are never published by default. Each needs an explicit "yes, publish this".
3. Every post shows its publication date. A changed post shows when it was updated.
4. A post's address does not change when its title changes. If it must change, the old address redirects.
5. The person is the author of everything in their own name. Text written by the builder is shown to the person for approval before publishing, and is never presented as the person's own experience, opinion or story without that approval.
6. Claims about the person (books, awards, roles, numbers of readers) are facts the person supplied. Reference 6 states a subscriber count of about 50,000; the product writes such a number only when the person gives it.
7. A quote from another person about the owner is shown only if real, with the source.
8. A "now" page shows the date it was last updated. If older than a set time, the person is prompted (section 4).
9. A public email address is shown only if the person chooses it. The default is a contact form (section 4).
10. A newsletter signup says what the person will receive and how often, and every email has a one-click unsubscribe. Reference 6 says this in plain words next to the signup.
11. Affiliate links and paid placements are disclosed on the page where they appear. Reference 3 has a site-wide statement.
12. Every image has alt text. A photo of another recognisable person needs that person's consent.
13. The site has a feed (RSS or Atom) when it has posts.
14. Archived or deleted posts disappear from the feed, the archive and search at once.
15. The main action (subscribe, contact, read the latest) is reachable from every page.
16. Comments, if any, are moderated before they appear, unless the person chooses otherwise.

## 3. Mandatory facts

The product is not built until each of these has an answer from the customer. None may be guessed.

| # | Fact | The one question to ask | Why (the human reason) |
|---|---|---|---|
| 1 | Name as shown | "What name should be on the site: full name, first name, or another name?" | People find and recommend a person by name. Some people need a pen name to stay safe. |
| 2 | One line | "If someone met you at a party, how would you say who you are in one sentence?" | The first screen must say whose site this is and why to stay. |
| 3 | The one thing visitors should do | "What should a visitor do here: read your writing, subscribe, get in touch, hire you, buy your book?" | The page leads to this action. Without it the site is a pile of pages. |
| 4 | What content exists | "What do you have already: posts, essays, books, projects, talks? Where are they now?" | A personal site with nothing in it looks abandoned. Existing work can be moved in. |
| 5 | How to be contacted | "How should people reach you? Is it all right to show an email address, or should I use a form?" | Showing an email brings spam; hiding all contact makes the site a dead end. |
| 6 | What must stay private | "Is there anything about you that must not be on the site: where you live, your employer, your family, your age?" | A personal site is found by strangers. A detail published by mistake cannot be taken back from every copy. |
| 7 | Photo | "Do you want a photo of yourself on the site? If yes, which one?" | Some people want a face; others must not show one. Never assume. |
| 8 | Who is responsible for the legal pages | "For the privacy page, should it list your own name, or a business name if you have one?" | A newsletter or contact form collects other people's data; someone must be named as responsible. |

Needed when they apply:

| # | Fact | The one question to ask | Why |
|---|---|---|---|
| 9 | Newsletter | "Do you send a newsletter, or want to? What is it about and how often will it go out?" | The signup must tell people what they will get. |
| 10 | Where emails come from | "Which service sends your newsletter, or should we set one up?" | Signups that go nowhere are lost readers and possibly a legal problem. |
| 11 | Books, products, membership | "Do you sell anything: books, prints, a membership?" | Selling adds payments and consumer law. |
| 12 | Affiliate links | "Do any of your links earn you money?" | They must be disclosed (rule 11). |
| 13 | Comments | "Do you want readers to comment on posts? Who will read and approve comments?" | Unmoderated comments fill with spam and abuse. |
| 14 | Country | "Which country do you live in?" | Some countries require a legal notice even on small sites (see Legal). |

## 4. Declared defaults

Each default is shown to the customer as "we filled this in - change it if it is wrong". None of them is a fact about the person.

| Default | Value | Why it is safe | How it is marked |
|---|---|---|---|
| Page order | Skeleton A below | Extracted from the references | Named as the default skeleton |
| Contact | a contact form that sends to the person's email; the email itself not shown | Protects the person from spam and scraping; still works | Labelled "default: form, email hidden" |
| Location | not shown | Safer default for a private person | Listed as "not shown: location" |
| Photo | none | Rule 2; a photo is only used when fact 7 says yes | Listed as "not shown: photo" |
| Post list on home | the latest 5 to 10 titles with dates | References 2, 5 and 7 show recent posts as title lists | Setting, labelled "default" |
| Post order | newest first | References 3, 4 and 5 | Setting |
| Feed | on | Rule 13 | Setting |
| Comments | off | Avoids spam and moderation work until fact 13 is answered | Setting, labelled "default: off" |
| "Now" page reminder | prompt the person when the page is older than 3 months | Estimate | Setting, labelled "default" |
| Newsletter signup | hidden until facts 9 and 10 are answered | A signup that sends nowhere is a silent failure | Listed as "not shown yet: newsletter" |
| Search | on when there are more than about 30 posts | Estimate | Setting |
| Analytics | off, or a privacy-respecting count without cookies | Fewer consent questions; the person can turn on more | Setting, labelled "default" |
| Language and direction | the language of the conversation | The customer chose it by speaking it | Shown, changeable |
| Legal page structure | headings only: who runs this site, what is collected (contact form, newsletter), why, how long, your rights, contact | Structure is general; content is not | Marked "draft - not legal advice - review before publishing" |
| Empty optional sections | hidden | An empty "Talks" section looks worse than none | Listed for the customer as "not shown yet" |

Never a default, whatever the customer left out: the person's biography, roles, employer, education, books, awards, numbers of readers or followers, quotes about them, opinions, photos, location, age, family, health, beliefs, post content, "now" content, prices, newsletter frequency.

## 5. Failure modes

| What went wrong | What the visitor sees | What it costs | Prevention |
|---|---|---|---|
| A private detail published | The person's street, employer or child's name | Harassment, stalking, job trouble; cannot be fully undone | Rules 1 and 2; mandatory fact 6; review screen lists every personal detail before publishing |
| Builder writes the person's story | A bio or post with experiences the person never had | The person is embarrassed or caught out; trust lost | Rule 5; every generated sentence approved |
| Email address scraped | (the person sees it: spam floods in) | Inbox unusable; phishing | Default contact form; rule 9 |
| Undated posts | An old opinion read as current | The person is judged by views they no longer hold | Rule 3 |
| "Now" page years old | "Currently working on..." something long finished | Looks abandoned | Rule 8; reminder default |
| Broken old links | A link shared years ago leads to "not found" | Lost readers; the web's memory of the person breaks | Rule 4; redirects |
| Newsletter signup goes nowhere | "Thanks for subscribing" - no email ever arrives | Lost readers; possibly unlawful storage of emails | Facts 9 and 10; test signup at setup |
| No unsubscribe | Cannot stop the emails | Spam complaints; legal problem | Rule 10 |
| Comment spam | Posts filled with ads and abuse | Looks neglected; legal risk for hosted content | Comments off by default; rule 16 |
| Undisclosed affiliate links | Finds out later the links paid the author | Trust lost; possible regulatory issue | Rule 11 |
| Home page is a wall | Everything at once: 50 links, no idea where to start | Leaves | Skeleton A: one line, the action, a few latest items |
| Everything on other platforms | Every link leads away to social media | When a platform changes or closes, the person's work vanishes | Keep posts on the site; link out for syndication only (reference 2 says all its work lives on the site and lists the platforms it copies to) |
| Pen name leaked | Real name appears in page metadata, image files or the legal page | Exposure of a person who chose not to be named | Check metadata, file names and legal pages against fact 1 |
| Feed includes drafts or deleted posts | A reader's feed app shows a post the person withdrew | Embarrassment; a withdrawn statement keeps circulating | Rule 14 |

## 6. Professional language

Hebrew and Arabic terms are the author's knowledge and were not checked with native writers in either language. Where the cell says "not verified", do not use a guess.

| English | Meaning | Hebrew | Arabic |
|---|---|---|---|
| Personal site, personal website | one person's own site | אתר אישי | موقع شخصي |
| Homepage | the first page | דף הבית | الصفحة الرئيسية |
| About page | who the person is | אודות | من أنا / نبذة عني |
| Bio | a short description of a person | ביו / תיאור קצר | نبذة شخصية / سيرة ذاتية مختصرة |
| Blog | a dated series of posts | בלוג | مدونة |
| Post | one dated entry | פוסט / רשומה | تدوينة / منشور |
| Essay | a longer considered piece | מסה | مقالة |
| Note | a short post | פתק / רשימה קצרה (not verified as usage) | ملاحظة |
| Archive | all past posts | ארכיון | أرشيف |
| Tag, category | a label grouping posts | תגית, קטגוריה | وسم، تصنيف |
| Feed, RSS | a machine-readable list of new posts | פיד, RSS | خلاصة (not verified), RSS |
| Newsletter | regular email to subscribers | ניוזלטר / עלון | نشرة إخبارية / نشرة بريدية |
| Subscribe, unsubscribe | join or leave a list | להירשם, להסיר / ביטול הרשמה | اشترك، إلغاء الاشتراك |
| Now page | what the person is doing at present | עמוד "עכשיו" (not verified as usage) | not verified |
| Contact form | a form that sends a message | טופס יצירת קשר | نموذج اتصال |
| Pen name | a name used instead of the real name | שם עט | اسم مستعار |
| Syndicate | publish copies elsewhere | הפצה (not verified for this sense) | not verified |
| Permalink | a post's permanent address | קישור קבוע | رابط دائم |
| Affiliate link | a link that pays a commission | קישור שותפים | رابط تسويق بالعمولة (not verified) |
| Speaking, talks | public talks | הרצאות | محاضرات |
| Membership | paid access to extra content | מנוי / חברות | عضوية / اشتراك |
| Colophon | how the site was made | קולופון (not verified as web usage) | not verified |

Notes on language:

- A personal site speaks in the first person ("I write about..."), unless the person prefers the third person. Ask; do not switch between them on one page.
- Words to avoid unless the person said them and can back them: "thought leader", "visionary", "expert", "renowned", "influencer", "bestselling" (allowed only with the list named), follower or reader counts.
- Reference 2 states that everything on it was written without AI. A claim like that is the person's to make; the product never adds it, and never removes it.

## 7. Legal

A checklist of questions, not legal advice. The author is not a lawyer and did not read the statutes for this file. Every item needs checking by someone qualified in the person's country before it is relied on.

### Applies almost everywhere

- **The person's own data.** Publishing one's own details is the person's choice, but the product should not encourage over-sharing (rules 1 and 2). Information about other people in posts (friends, family, colleagues) can raise privacy and defamation questions.
- **Privacy notice.** Needed as soon as the site collects other people's data: a contact form, a newsletter, comments, analytics with cookies.
- **"Household" exemption.** Data-protection laws often exempt purely personal or household activity. A public website that collects visitors' data is generally believed not to fall under it. Not verified.
- **Newsletter consent.** Marketing or regular emails need prior agreement and an easy unsubscribe in most places.
- **Affiliate links and sponsored posts** must be disclosed in many jurisdictions.
- **Copyright.** Quoting others is allowed within limits (fair use, fair dealing, quotation exceptions) that differ by country. Images from elsewhere need permission. Not verified per jurisdiction.
- **Defamation.** A personal site is publishing. Statements about named people can be defamatory. Not legal advice; the product does not judge content but should not generate claims about third parties.
- **Comments.** Hosting other people's comments may bring responsibility for removing unlawful content once notified. Not verified per jurisdiction.

### Israel

- Privacy: the Protection of Privacy Law applies to stored data such as newsletter lists. Amendment 13 came into force in August 2025. Whether and how it applies to an individual's site: not verified.
- Marketing messages: section 30A of the Communications Law (the "spam law") requires prior consent for advertising messages. Whether a personal newsletter counts as advertising depends on its content: not verified.
- Accessibility: the duty to make websites accessible applies to those providing a service to the public. Whether a private person's non-commercial site is covered: not verified, believed not.
- Defamation: the Prohibition of Defamation Law applies to online publication. Not verified in detail.

### European Union and United Kingdom

- GDPR (EU) and UK GDPR apply to newsletter lists and contact forms on a public site; the household exemption is believed not to cover them. Non-essential cookies need consent (ePrivacy rules in the EU, PECR in the UK).
- Germany: a legal notice (Impressum) with the operator's name and an address is believed to be required for sites that are not purely private, which can include a personal blog with ads or affiliate links. This conflicts with keeping a home address private; a service address is sometimes used. The duty is believed to have moved from the Telemedia Act to the Digital Services Act (Digitale-Dienste-Gesetz) in 2024. Not verified.
- UK: the Digital Markets, Competition and Consumers Act 2024 is believed to ban fake reviews and undisclosed paid endorsements from April 2025. Not verified for personal sites.
- Accessibility law for private individuals: believed not to apply. Not verified.

### United States

- The FTC requires disclosure of material connections in endorsements, including affiliate links (Endorsement Guides). Believed correct; not verified for this file.
- CAN-SPAM applies to commercial email and requires a valid physical postal address in each message; people often use a post-office box to keep a home address private. Not verified.
- Children: COPPA applies to sites directed at children under 13 that collect their data. Not verified.
- Privacy law is by state. Small personal sites are usually below thresholds. Not verified.

### What the product does with this

- The product may generate the **structure** of a privacy page. It marks it as a draft that needs review.
- The product never states that the site "complies with" a named law.
- The product asks which country the person lives in before generating any legal page, and warns about a legal-notice duty where one is believed to exist, without publishing an address unless the person decides to.
- The product never generates statements about real third parties.

## 8. Site vs app

### Content pages (no data, no accounts)

Home, about, posts, archive, work items, talks, now page, contact details, legal pages. A static site with a feed and a mail link is a complete and honest product. Reference 5 is essentially a list of every post on one page.

States still needed on content pages:

| Part | Empty | Error | Notes |
|---|---|---|---|
| Latest posts | section hidden; the home page leads with the one line and the action | | Never "No posts yet" on the public site |
| Archive | hidden until there are posts | | Grouped by year or category |
| Work items | section hidden | missing cover hidden, title shown | |
| Now page | not published until written | | Date always shown |
| Photo | hidden when not given | broken image hidden | |
| Talks | section hidden | broken video embed shows a link instead | |

### Needs data

| Part | What it needs | Empty state | Loading | Error | Save | Permissions |
|---|---|---|---|---|---|---|
| Contact form | stores name, email, message; sends to the person | n/a | "sending", cannot be pressed twice | "Not sent - please try again later" (no email shown if the person chose to hide it) | visitor sees "Sent" and whether to expect a reply | visitor writes; only the person reads |
| Newsletter signup | a sending service, consent record | n/a | | "Could not subscribe - try again" | "Check your email to confirm" where double opt-in is used | visitor writes own; only the person reads the list |
| Comments | stored comments, moderation queue | "No comments yet" (only when comments are on) | | "Comment not posted" keeping the text | visitor sees "Waiting for approval" | visitor writes own; the person approves and deletes |
| Search | an index of published posts | "Nothing found" with a link to the archive | | "Search not available" with the archive link | | anyone |
| Person edits content | an editor for posts and pages with drafts | "No posts yet - write your first" | | a failed save says so and keeps what was typed | published at once; drafts never visible publicly | the person only |
| Private or unlisted posts | a secret link | | | | | anyone with the link; never in the feed, archive or search |
| Membership | accounts, payments, gated posts | | | payment failure explained, access unchanged | access only after payment succeeds | members see gated posts; the person sees members |

### Needs accounts

- The person needs one as soon as anything is editable in the product.
- Readers never need one to read public posts.
- Members need one only if the person runs a paid membership (reference 7 does).

### Needs payments

- Only for books sold directly, a membership, paid newsletters or donations.
- Default: no payments. Links to outside sellers (reference 6 links to four) need none.

### Using existing platforms

Many people already write on a newsletter or blogging platform or on social media. Ask before rebuilding: the site can import posts, or link to the platform for the newsletter while keeping posts on the person's own domain. The failure mode is a personal site that is only a list of links to accounts the person does not control.

## 9. References

**How these were checked.** Each URL was fetched on 2026-11-22 with a page-extraction tool that returns the page's text and image references. No browser was used and no screenshot was taken. So: section order and wording are observed; visual quality, layout and the image-to-text ratio are **not** observed, and every ratio below is an estimate from the extracted text. Image counts include logos and icons.

**Curation.** Chosen by the author from long-running personal sites of writers and technologists with a public profile, not from a search-result list. No awwwards.com category was consulted; none is claimed as an award winner. All six are in English, in Latin script. These are public figures' own sites; the file records structure only and no personal details beyond what each site's owner publishes about their work.

**Limit.** All six belong to people who are known writers or speakers. No site of a private person with a small audience (a professional between jobs, a hobbyist) was verified. Several are deliberately plain in design; they were chosen for structure, not for visual polish.

Verified: 6.

| # | Site | Checked | What was observed |
|---|---|---|---|
| 1 | https://jvns.ca | 2026-11-22 | Programmer and zine author's blog. Order: name - navigation (about, talks, projects, social accounts, code host) - one-line welcome and a link to subscribe to a weekly digest - a link to her zine shop - "most recent 10 posts" as a run of titles - every post ever written, grouped by category. Text only; no images in the extraction. About 27,000 characters, almost all post titles. |
| 2 | https://sive.rs | 2026-11-22 | Writer and entrepreneur's site. Order: a statement that everything is written without AI - "me in 10 seconds": a one-line identity and a four-line timeline by period - links to an about page and a now page - contact invitation with a promise to reply - newest articles (five titles) - books, each with a cover and one line - interviews (250+ with transcripts) - projects, each with one line - short posts mirrored from social media - "want more?" (search, podcasts, feeds, random page) - list of nine places it syndicates to. 11 images (book covers). |
| 3 | https://austinkleon.com | 2026-11-22 | Author's blog. Order: name and a banner for a new book with a "buy" link - welcome line with a newsletter invitation - latest posts in full, newest first - pagination (654 pages of older posts) - recent posts list - "more about me" (books written, newsletter, books read, social accounts) - site search - an affiliate-programme disclosure. 11 images. |
| 4 | https://simonwillison.net | 2026-11-22 | Technologist's weblog. Navigation: Entries, Links, Quotes, Notes, Guides, Elsewhere. Order: a date heading, then that day's entries in full, then the previous day; long posts mix text, code, quotes and images. About 33,000 characters, 30 images. |
| 5 | https://www.robinsloan.com | 2026-11-22 | Novelist's site. Order: name and a short self-description - novels and other ventures (a stationery company, an olive-oil producer) - newsletter with its unusual frequency stated - blog with its topics stated - a live count of library holds for the novels - a directory of everything on the site: basics (about, contact, social, feed), archives, novels, novellas, special projects, short stories, notable essays, with stars on favourites. 1 image. About 2,600 characters. |
| 6 | https://craigmod.com | 2026-11-22 | Writer and photographer's site. Order: two newsletters, each with its topic and frequency, a subscriber estimate and a one-click-unsubscribe promise - best-of-year mentions for his latest book - the book with two quotes from named authors and four seller links - fine editions from his own publishing arm with page counts and "purchase online" - a photo and a short first-person bio - his membership programme - popular essays - recent essays, each a title and one line. 9 images. |

Loaded and not used:

| Site | Checked | Why not |
|---|---|---|
| https://paulgraham.com | 2026-11-22 | Loads, but the extraction returned about 180 characters, including the words "Menu" and "Cart", which do not match the site as known. Treated as an unreliable extraction and not used. |
| https://seths.blog | 2026-11-22 | Loads, but the extraction returned one post's text only, with no navigation or other sections. Not enough to describe the structure. |

## 10. Skeletons

Structure only. No colours, logos, photographs or wording were taken from any reference.

### Skeleton A: the personal home page (writer-first)

For a person whose site has one job: tell visitors who they are and get them to read, subscribe or get in touch. Default for this domain.
From references 2, 5 and 6: the "who in ten seconds" of 2, the newsletter block with frequency of 5 and 6, the directory of 5, the latest-posts list of 1 and 2.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | the person's name; links: Writing, About, Contact (and Now if it exists) | name is the largest text | yes |
| 1 | Who | one line from fact 2; optionally three or four lines of timeline or bio | one heading, one line | yes |
| 2 | The main action | subscribe (with topic and frequency), or get in touch, or read the latest - from fact 3 | one block | yes |
| 3 | Latest writing | 5 to 10 post titles with dates | list, newest first | optional, hidden when empty |
| 4 | Work | books, projects or talks, each a title and one line, with a cover if given | short list or small tiles | optional, hidden when empty |
| 5 | Now | a link to the now page with its date | one line | optional |
| 6 | Everything else | a short directory: archive, feed, links elsewhere | list | optional |
| 7 | Footer | name; contact link; feed; privacy page if anything is collected; disclosure if affiliate links exist | small | yes |

Image-to-text ratio: **estimate**, from extraction counts only. Text-led: references 1, 4 and 5 returned 0 to 1 images on the home page apart from post images; references 2 and 6 about 10, mostly book covers. Roughly one image (a cover or a portrait) per section at most; the first screen is text. Not confirmed in a rendered view.

### Skeleton B: the blog (stream-first)

For a person who posts often and whose readers come for the latest posts. Use when the person writes at least weekly (estimate); otherwise Skeleton A.
From references 3 and 4: full posts on the home page of 3 and 4, date headings of 4, pagination and "more about me" of 3.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; navigation by post kind (essays, notes, links) or by topic | | yes |
| 1 | Welcome line | one line and the subscribe action | small, above the stream | yes |
| 2 | Stream | the latest posts in full or as long excerpts, each with title and date; grouped under date headings | post title, date, body | yes |
| 3 | Pagination | older posts | links | yes when more than one page |
| 4 | Side or bottom block | about in two lines, recent posts, tags, search, links elsewhere | small | optional |
| 5 | Footer | as Skeleton A | small | yes |

Image-to-text ratio: **estimate**. Text-led; images appear inside posts as the person adds them (reference 4: 30 images in about 33,000 characters). Not confirmed in a rendered view.

## 11. Not verified

1. All Hebrew and Arabic terms in section 6: author's knowledge, not checked with native writers in either language. Cells marked "not verified" must not be filled by guessing.
2. Every legal statement in section 7. None was checked against a statute or an official source for this file. Items marked "not verified" are the least certain; the rest are also unconfirmed.
3. Image-to-text ratios and visual quality of all references: text extraction only, no rendered view.
4. No awwwards.com category was consulted; design quality of the references is the author's prior judgement.
5. No site of a private person with a small audience was verified; all six are public writers.
6. Defaults in section 4 (3-month now-page reminder, search above 30 posts, Skeleton B at weekly posting) are estimates, not taken from a source.
7. The paulgraham.com extraction looked wrong (section 9); the site itself was not checked in a browser.
8. Only home pages were fetched; post pages, about pages and now pages of the references were not.
9. The brief asked for references dated 2026-11-21. The fetches ran on 2026-11-22, and that is the date recorded.
10. No references in Hebrew, Arabic or any non-Latin script. These come in a later phase.
