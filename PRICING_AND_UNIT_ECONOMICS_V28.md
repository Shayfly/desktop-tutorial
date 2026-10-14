# 148AI Pricing & Unit Economics — V28

Date: 2026-09-22
Status: **pre-launch proposed defaults; configurable before public billing**

## Proposed plans
| Plan | Price / month | Credits | Paid-provider hard cap | Projects | Branding |
|---|---:|---:|---:|---:|---|
| Free | $0 | 150 | $0 | 2 | Required |
| Basic | $12 | 900 | $2.50 | 10 | Subtle required |
| Pro | $39 | 4,000 | $10 | 50 | Removable |
| Business | $99 | 12,000 | $25 | 250 | White-label eligible, 5 seats |
| Enterprise | Custom | Contract | Contract | Custom | Contract |

These are not promises of unlimited generation. Paid-provider/GPU/media use is metered and hard-capped before execution.

## Economic rule
The plan engine protects a variable-cost margin floor before fixed infrastructure:
- Basic: ~79% at full $2.50 provider budget.
- Pro: ~74% at full $10 provider budget.
- Business: ~75% at full $25 provider budget.

Fixed hosting, support, tax, refunds, payment processing and company overhead are **not** included in those percentages. We must measure real accepted-build cost before freezing public pricing.

## Free principle
Free users are routed only to paths with **$0 paid-provider spend**. They still consume shared server resources, so rate limits/project limits remain necessary.

## Repair principle
If 148AI introduces a system bug or misses an explicit original requirement, customer credits are not deducted. The company still meters the provider cost internally so abuse and margin remain visible.

## Current infrastructure reference prices used for planning
- Supabase: Free tier; Pro starts at $25/month. https://supabase.com/pricing
- Cloudflare R2 Standard: $0.015/GB-month, with a free tier and free Internet egress under the documented model. https://developers.cloudflare.com/r2/pricing/
- Resend: Free 3,000 emails/month; Pro $20/month for 50,000. https://resend.com/pricing
- RunPod (2026-09 reference): RTX 6000 Ada about $0.84/hr; L40S about $1.09/hr; A100 80GB about $1.59/hr. https://www.runpod.io/pricing
- Render: Hobby $0 workspace; Pro $25/month plus compute. https://render.com/pricing
- Vercel: Hobby $0; Pro $20/month plus usage. https://vercel.com/pricing

Provider prices can change. The product must use live/configured cost tables for billing decisions before public launch rather than relying permanently on this document.
