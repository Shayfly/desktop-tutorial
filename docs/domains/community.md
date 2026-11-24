# Community

Covers: a group of people who keep coming together around a shared interest, place or cause: a club, a residents' group, a local running or repair group, a meetup series, a network of local chapters, an online forum.
Does not cover: a single event (use `event.md`); an organisation whose main page asks for donations (use `nonprofit.md`); selling courses or classes (use `tutor-courses.md`); a sports trainer's business (use `fitness-trainer.md`).
Written 2026-11-22. References checked 2026-11-22 (the brief named 2026-11-21; the fetches ran on 2026-11-22). Template: [README.md](README.md).

## 1. Objects

A community sells nothing; it offers **belonging, on a rhythm**. A newcomer asks three questions: what is this, is it for someone like me, and when and where is the next time I can just turn up. Everything else (membership, chapters, forums) exists to answer those questions again every week and to keep people coming back. The most important object is the next gathering, and the most important failure is a newcomer arriving at a gathering that no longer happens.

### Community (the group)

| Field | Required | Example (illustrative) |
|---|---|---|
| Name | required | "Riverside Repair Group" |
| What we do | required | one sentence: "we fix broken things together, once a month" |
| Who it is for | required | "anyone"; "women in tech"; "parents of under-5s"; "men over 50" |
| Where | required | town or area; "online" |
| How to join | required | just come, register once, apply, pay a membership |
| Cost | required | free, free with optional donation, membership fee |
| Contact | required | email or message number of an organiser role, not necessarily a personal number |
| Organiser (legal or responsible body) | required | an association, a company, or a named volunteer role |
| Code of conduct | optional, strongly advised | |
| Safeguarding contact | required when children or adults at risk take part | see Legal |
| Languages | optional | |
| Social or chat group link | optional | many communities live in a messaging group |

### Chapter (local group, only when there is more than one)

| Field | Required | Example |
|---|---|---|
| Name or place | required | "North district" |
| Where it meets | required | venue name and address, or "online" |
| When it meets | required | "first Saturday of the month, 10:00-13:00" |
| Local contact | required | role email |
| Status | required | active, paused, closed |
| Start your own | optional | how to open a new chapter |

### Gathering (a recurring or one-off meeting)

| Field | Required | Example |
|---|---|---|
| Title | required | "Monthly repair session" |
| Date and time | required | |
| Recurrence | optional | weekly, monthly on a weekday rule |
| Place | required | linked venue or online link (online links shown only to registered people, see rule 9) |
| What to bring | optional | "trainers"; "the broken item" |
| Registration needed | required | no, yes (with capacity) |
| Capacity | optional | |
| Accessibility | optional | step-free, quiet space |
| Age | optional | "under-18s with an adult" |
| Status | required | scheduled, cancelled, happened |

### Member (only when the community keeps a member list)

| Field | Required | Example |
|---|---|---|
| Display name | required | first name or chosen name |
| Email or phone | required | for notices |
| Chapter | optional | |
| Membership type and expiry | optional | for paid or formal memberships |
| Roles | optional | member, volunteer, organiser, moderator |
| Consent to be listed in a directory | required if a directory exists | default no |
| Emergency contact | optional, only for physical activities where justified | |

### Other objects

| Object | Fields | Notes |
|---|---|---|
| Post or thread | author, title, text, date, replies, status (visible, hidden by moderator) | Only for online communities |
| Volunteer role | title, what it involves, time needed, how to apply | Communities run on volunteers |
| Resource | title, type (guide, video, document), date | Seen in three references (tips, guides, wellbeing) |
| Story or news | title, date, author role | |
| Impact count | number, what it counts, source and date | Counts are facts, never defaults |
| Sponsor or partner | name, logo, link | Shown only with agreement |
| Membership fee or donation | amount, period, what it pays for | Optional; involves payments |
| Directory entry | name, work, link | Only with explicit consent; one reference has a member directory |

## 2. Rules

1. The next gathering (or how often gatherings happen) is visible from the home page. If there is none scheduled, the page says so and says how to hear about the next one.
2. A recurring rule ("first Saturday") produces dated gatherings. A cancellation overrides one date and is shown on that date.
3. A gathering in the past never appears as upcoming.
4. Every chapter shows its status. A paused or closed chapter is not shown as active and does not accept registrations.
5. "How to join" is one plain statement on the home page: just come, register, apply or pay.
6. Cost is explicit: "free", "free - donations welcome", or the fee with its period. A free community never shows a price, and a donation is never presented as required when it is not.
7. A member's contact details are never public. A member directory shows only people who opted in, and only the fields they chose.
8. A newcomer can contact the community without creating an account.
9. Online meeting links are shown only to registered participants, so strangers cannot join uninvited.
10. In an online community, every post has an author and a date, and moderators can hide a post without deleting the record. The rules for posting are published before the first post.
11. Activities with children or adults at risk name a safeguarding contact and policy, and photos of children are never published without a parent's consent.
12. Impact numbers (for example "1,000 members", "40 groups") are shown only with what they count and the date; animated counters must show the real number even without scripts (one reference's counters read 0 in a text extraction).
13. A quote from a member is real, and shows only what the member agreed to (first name and area is common).
14. A code of conduct, if published, names how to report a problem and who receives reports.
15. Messages to members carry a way to stop them. Notices about a cancelled gathering may still be sent to those registered for it.
16. The "join" or "find your local group" action is reachable from every page on a phone.

## 3. Mandatory facts

The product is not built until each of these has an answer from the customer. None may be guessed.

| # | Fact | The one question to ask | Why (the human reason) |
|---|---|---|---|
| 1 | Name | "What is the group called?" | People invite friends by name. |
| 2 | What and for whom | "In one sentence, what do you do together, and who is it for?" | A newcomer decides in seconds whether they belong. |
| 3 | Where | "Where do you meet, or is it online?" | Without a place nobody arrives. |
| 4 | When | "When do you meet: a fixed rhythm, or dates you announce?" | The first thing a newcomer needs is the next time they can come. |
| 5 | How to join | "Can people just turn up, or do they register, apply or pay?" | The site leads to this one action. |
| 6 | Cost | "Is it free, free with donations, or is there a fee?" | Money is the second filter; a surprise fee drives people away. |
| 7 | Contact | "Which email or number should newcomers use? It can be a group address, not your personal one." | A newcomer with a question and no one to ask does not come. |
| 8 | Responsible body | "Who is responsible for the group legally: an association, a company, or a volunteer?" | Legal pages and safeguarding need a responsible name. |
| 9 | Children or vulnerable adults | "Do children or people who may need extra protection take part?" | If yes, a safeguarding contact is required before publishing. |

Needed only when the product keeps members or runs registrations:

| # | Fact | The one question to ask | Why |
|---|---|---|---|
| 10 | What you need from members | "What must you know about each member: only name and email, or more?" | More data is more risk. |
| 11 | Who manages the list | "Who may see the member list and send messages?" | Member data in the wrong hands breaks trust. |
| 12 | Capacity | "Is there a limit to how many can come to a gathering?" | Without it the room overflows. |
| 13 | Moderation (online) | "Who moderates posts, and what are the rules?" | An unmoderated forum fills with spam within days. |

## 4. Declared defaults

Each default is shown to the customer as "we filled this in - change it if it is wrong". None of them is a fact about the community.

| Default | Value | Why it is safe | How it is marked |
|---|---|---|---|
| Page order | Skeleton A below | Extracted from the references | Named as the default skeleton |
| Main action | "Come along" with the next gathering, or "Get in touch" if no date | Works with zero setup | Labelled "default" |
| Home-page answer blocks | What is it / How do I join / Where and when | Seen in reference 2 almost word for word as a structure | "Suggested layout" |
| Directory | off | Privacy first | Setting, labelled "default: off" |
| Member data fields | name, email | The least needed | "Suggested fields" |
| Online meeting link visibility | registered participants only | Rule 9 | Setting |
| Posting rules (online) | headings only: be kind, no spam, no personal data of others, how to report | Structure; content is the organisers' | "Draft - your rules" |
| Code of conduct | headings only, with a reporting contact field left empty | Content and enforcement are the organisers' | "Draft" |
| Language | the language of the conversation | The customer chose it | Shown, changeable |
| Empty optional sections | hidden | Empty "stories" look abandoned | Listed as "not shown yet" |
| Legal page structure | headings only | Structure is general | "Draft - not legal advice" |

Never a default, whatever the customer left out: meeting place, times, rhythm, cost, membership fees, who it is for, safeguarding contact, impact numbers, member counts, chapters, testimonials, sponsors, "everyone welcome" (it is a promise the organisers must be able to keep), "free forever".

## 5. Failure modes

| What went wrong | What the visitor sees | What it costs | Prevention |
|---|---|---|---|
| Gathering moved or stopped, site not updated | Newcomer arrives at an empty hall | Lost member, often for good | Rules 1-3; "last updated"; prompt organisers monthly |
| Chapter closed, still listed | Visitor contacts a group that is gone | Same | Rule 4 |
| Only past events on the page | Thinks the group is dead | Silent loss | Rule 3; "next gathering to be announced - join the list" |
| Contact goes to a person who left | Message never answered | Silent loss | Role addresses, not personal ones (fact 7) |
| Member list leaked or public | Members' emails exposed | Trust collapse; legal problem | Rule 7 |
| Online link shared publicly | Strangers disrupt a meeting | Harm, members leave | Rule 9 |
| Forum without moderation | Spam and abuse | Members leave | Fact 13, rule 10 |
| Fee or donation unclear | Feels tricked into paying | Distrust | Rule 6 |
| Counters show 0 | "0 volunteers" | Looks dead | Rule 12 |
| No safeguarding contact with children present | Parent cannot raise a concern | Harm; legal exposure | Fact 9, rule 11 |
| Testimonials with full names and photos without consent | Member sees themselves promoted | Complaint | Rule 13 |
| Messages without unsubscribe | Annoyed members mark as spam | Notices stop reaching anyone | Rule 15 |
| Join flow requires an account just to ask a question | Gives up | Silent loss | Rule 8 |

## 6. Professional language

Hebrew and Arabic terms are the author's knowledge and were not checked with community organisers in either language. Where the cell says "not verified", do not use a guess.

| English | Meaning | Hebrew | Arabic |
|---|---|---|---|
| Community | the group of people | קהילה | مجتمع |
| Club | formal group with members | מועדון | نادي |
| Association | legally registered group | עמותה / אגודה | جمعية |
| Member | | חבר / חברה | عضو |
| Membership | being a member, often paid | חברות / דמי חבר (fee) | عضوية / رسوم العضوية (fee) |
| Organiser | runs the group | מארגן / רכז | منظم |
| Volunteer | unpaid helper | מתנדב | متطوع |
| Chapter, local group | one place in a network | סניף | فرع |
| Gathering, meetup | | מפגש | لقاء |
| Newcomer | first-time visitor | מצטרף חדש | عضو جديد (not verified for "newcomer") |
| Moderator | keeps an online space safe | מנהל קהילה / מודרטור | مشرف |
| Forum | online discussion space | פורום | منتدى |
| Code of conduct | | קוד התנהגות | مدونة السلوك (not verified) |
| Safeguarding | protecting children and adults at risk | הגנה על ילדים ובגירים בסיכון (not verified as one term) | حماية الأطفال (not verified as equivalent) |
| Newsletter | | ניוזלטר / עלון | نشرة إخبارية |
| Grassroots | started by local people | עממי / מהשטח (not verified) | شعبي (not verified) |

Notes on language:

- "Join" means different things: just turn up (reference 2's "register once"), sign up (reference 4), or apply. Say which.
- "Free" with an optional donation (references 2 and 4) is honest only if participation really does not depend on paying.
- Words to avoid unless the organisers can back them: "largest", "safe space" (a promise that needs a working code of conduct), "everyone welcome", "life-changing", "free forever".

## 7. Legal

A checklist of questions, not legal advice. The author is not a lawyer and did not read the statutes for this file.

### Applies almost everywhere

- **Member data is personal data.** Lists, attendance, roles. A privacy notice is needed once anything is collected.
- **Health data**: physical-activity groups and wellbeing groups may collect health information; avoid unless essential.
- **Children and adults at risk**: safeguarding duties and checks for volunteers exist in many countries. Not verified per country.
- **Photos at gatherings**: a stated policy and consent; children need a parent's consent.
- **Online content**: user posts raise moderation duties and, in some places, specific legal obligations for platforms. Not verified for small forums.
- **Unincorporated groups**: who is legally responsible when a group has no legal entity is a question for a lawyer in each country.

### Israel

- An association (עמותה) is registered with the Registrar of Associations; it has reporting duties. What the website must show: not verified.
- Website accessibility statement for bodies serving the public: required under the Equal Rights for Persons with Disabilities Law regulations, with exemptions. Whether a small volunteer group is in scope: not verified.
- Privacy Protection Law, Amendment 13 (in force August 2025): duties for databases of members. Thresholds: not verified.
- Advertising messages need prior consent under the Communications Law section 30A; whether member notices from an association are "advertising": not verified.

### European Union and United Kingdom

- GDPR and UK GDPR apply to member lists, even for volunteer groups. Not-for-profit bodies have a specific basis for processing members' data in some cases. Not verified.
- UK: the Online Safety Act 2023 places duties on services hosting user content; how it applies to a small community forum: not verified.
- EU: the Digital Services Act has lighter rules for small services. Not verified for this case.
- UK: safeguarding checks (DBS) for volunteers working with children are believed to be required for certain roles. Not verified.

### United States

- State nonprofit law if the group incorporates. COPPA applies to collecting data from children under 13 online. Not verified for this case.
- Section 230 is believed to shield forum hosts from liability for most user posts. Not verified.

### What the product does with this

- The product generates the **structure** of privacy, code-of-conduct and posting-rule pages, marked as drafts.
- The product never publishes a member directory or a member's contact without opt-in.
- The product asks whether children take part before publishing, and blocks publishing without a safeguarding contact if they do.

## 8. Site vs app

### Content pages (no data, no accounts)

Home with what, who, when and where; how to join; next gathering (a manually edited line counts); chapters list; resources; stories; code of conduct; contact; legal pages. With "message us" or a link to the group's chat as the only action, this is a complete product for most small groups.

States still needed on content pages:

| Part | Empty | Error | Notes |
|---|---|---|---|
| Next gathering | "Next date to be announced - join the list or message us" | | Never a past date |
| Chapters | single place shown instead | | Paused and closed marked |
| Stories, news | hidden | | |
| Impact numbers | hidden | | Real numbers with date only |
| Resources | hidden | broken link check | |
| Map | address text always shown | text and link remain | |

### Needs data

| Part | What it needs | Empty state | Loading | Error | Save | Permissions |
|---|---|---|---|---|---|---|
| Join or contact form | name, email, message, chapter | n/a | "sending" and cannot be pressed twice | "Not sent - email us at [address]" | "Received - an organiser will reply within [time]" | visitor writes; organisers read |
| Gathering registration | gatherings, capacity | "No upcoming gatherings - join the list" | placeholder | "Could not load - message us" | confirmation with date, place, what to bring | participant: own; organisers: all for their chapter |
| Find your local group | chapters with status and location | "No group near you yet - start one?" | | "Could not load the map - see the list" | | public read |
| Member list | members, roles | "No members yet" | | | change of role recorded with who changed it | organisers only, behind a login |
| Messages to members | list, consent, channel | | | failed sends listed | | organisers only |
| Forum | posts, users, moderation | "No posts yet - start the first conversation" | | "Your post was not saved - your text is kept" | post visible at once or after moderation, as configured | read: public or members only; write: members; hide: moderators |
| Member directory | opted-in entries | "No one has joined the directory yet" | | | member edits own entry | members only, by default |
| Volunteer sign-up | roles, slots | "No volunteer slots open" | | | | volunteer: own; organisers: all |

### Needs accounts

- Organisers, as soon as anything is stored.
- Members only for member-only features (forum, directory, attendance). Turning up should not need an account (reference 2 asks for a single registration; reference 3 has "my account" for organisers of local groups).
- Moderators for any forum.

### Needs payments

- Membership fees, donations, paid gatherings.
- Each brings receipts, renewals, failed payments and refunds.
- Default: no payments. A donation link to the group's existing method, if any.

### Using an existing platform

Many groups already run in a messaging app or on an event platform. Then the product is a front door: what, who, when, where, and a link. Ask before building a second member list.

## 9. References

**How these were checked.** Each URL was fetched on 2026-11-22 with a page-extraction tool that returns the page's text and image references. No browser was used and no screenshot was taken. Section order and wording are observed; visual quality and the image-to-text ratio are **not** observed, and every ratio is an estimate from counts in the extracted text. Image counts include logos and icons.

**Curation.** Chosen by the author from known community networks in the UK, Europe and the US, not from a search-result list. No awwwards.com category was consulted; none is claimed as an award winner. All are in English (reference 3 also offers four other European languages), in Latin script.

**Limit.** Five of six are national or international networks with many local groups. No single small local club's site was verified. Two references (4 and 5) are also registered charities, so they overlap with `nonprofit.md`.

Verified: 6.

| # | Site | Checked | What was observed |
|---|---|---|---|
| 1 | https://creativemornings.com | 2026-11-22 | Global breakfast-talk community. Order: one-line identity - scale (cities, countries, monthly, free) - partner logos - "join your local community" - virtual sessions list, each with title and host - member directory - share your work - companies - jobs - stories - "connect around the world" - closing welcome line - partners. Extraction: 17 images. |
| 2 | https://www.parkrun.org.uk | 2026-11-22 | Free weekly running and walking events. Order: three question-headings answered in short paragraphs: what is it (5k every Saturday, 2k junior on Sunday, no time limit, "no one finishes last"), how do I join (register once), where is it (number of events) - start your own event - safeguarding commitment with a link to policies and how to report a concern - sponsors - company name, number and address. Extraction: 11 images. |
| 3 | https://www.repaircafe.org/en/ | 2026-11-22 | International network of local repair meetups. Order: language switch and "my account" - headline - three actions (find a local group, start one, volunteer) - an exhibition - tips and guides - news from the network - "worldwide movement" counters (they read 0 in the text extraction, so they are filled by script) - start your own with a voluntary one-off fee for a digital starter kit. Extraction: 11 images. |
| 4 | https://www.goodgym.org | 2026-11-22 | Community that combines exercise with volunteering. Order: one-line offer - who we are and "join us" - examples of tasks - member and task counts - find local sessions - why join - "free", with a registered-charity note and optional monthly donation stating its minimum and that people can join without donating - quotes with first name and area - stories with dates. Extraction: 7 images. |
| 5 | https://menssheds.org.uk | 2026-11-22 | National association of local community workshops. Order: headline and what joining is about - learn more - one statistic with its source survey and year - donate - awards - find a local shed / start a new shed / what, how, why - support and wellbeing resources - a quote from a family member - search - newsletter - cookie consent. Extraction: 9 images. |
| 6 | https://www.indiehackers.com | 2026-11-22 | Online community of founders. Order: featured posts as a feed (short summaries) - subscribe - submit a post - advertise - recent submissions - top posts by week, month, all time. Shows the online-community pattern where the feed is the home page. Extraction: about 33 images, mostly small avatars. |

Loaded and not used: none. All six candidates fetched loaded and were kept.

## 10. Skeletons

Structure only. No colours, logos, photographs or wording were taken from any reference.

### Skeleton A: the local community (meets in person)

For a group that meets somewhere, possibly with several local groups. Default for this domain.
From references 2, 3, 4 and 5; the three-question opening is from 2.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; one action (come along / find your group / get in touch) | action always reachable | yes |
| 1 | Opening | one sentence of what you do together and for whom | one heading, one line | yes |
| 2 | Three answers | What is it? How do I join? Where and when? | three equal blocks, each a short paragraph | yes |
| 3 | Next gathering | date, time, place, what to bring; or "to be announced" | one card | yes |
| 4 | Find or start a local group | list or map; "start one" if the network allows | | optional (one place: skip) |
| 5 | What we do | examples, photos of real gatherings with consent | image and short caption | optional |
| 6 | Get involved | volunteer roles; donation if any, clearly optional | | optional |
| 7 | Voices | real quotes, first name and area | at most three | optional, hidden when empty |
| 8 | Safety | safeguarding contact and code of conduct | short | required if children take part |
| 9 | Stay in touch | newsletter or chat link | | optional |
| 10 | Footer | responsible body, contact, privacy, accessibility statement | small | yes |

Image-to-text ratio: **estimate**, from extraction counts only (references 2, 4 and 5 returned 7 to 11 images each with short text blocks). About one image per two text blocks; text answers carry the page. Not confirmed in a rendered view.

### Skeleton B: the online community

For a forum or a members' network that lives online.
From references 1 and 6.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; join; sign in | | yes |
| 1 | Opening | identity line; who it is for; join action | | yes |
| 2 | Feed or highlights | recent or top posts with author and date | list | yes |
| 3 | Ways to take part | post, attend a virtual session, share work, directory (opt-in) | short blocks | yes |
| 4 | Rules | posting rules and how to report | short | yes |
| 5 | Stay in touch | newsletter | | optional |
| 6 | Footer | responsible body, contact, privacy, terms | small | yes |

Image-to-text ratio: **estimate**. Many small avatars, little large imagery (reference 6 returned about 33 images, most of them avatars). Not confirmed in a rendered view.

## 11. Not verified

1. All Hebrew and Arabic terms in section 6.
2. Every legal statement in section 7, especially safeguarding duties, online-content rules for small forums, and Israeli association rules.
3. Image-to-text ratios and visual quality: text extraction only.
4. No awwwards.com category was consulted.
5. No single small local club was verified.
6. Sub-pages of the references (local group pages, registration flows, forum rules) were not fetched.
7. That many groups already run in messaging apps is general knowledge, not checked for this file.
8. No references in Hebrew, Arabic or any non-Latin script.
