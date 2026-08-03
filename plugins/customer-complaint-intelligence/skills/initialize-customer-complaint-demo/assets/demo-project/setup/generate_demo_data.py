#!/usr/bin/env python3
"""Generate the fictional client's customer table and Gmail email fixtures.

The generator is deterministic so the demo can be reset and reproduced. It
creates only client-facing fixtures; the reusable plugin lives elsewhere.
"""

from __future__ import annotations

import csv
import email.utils
import random
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
EMAILS = ROOT / "inbox-fixture" / "emails"
HELD_OUT = ROOT / "inbox-fixture" / "held-out"
RNG = random.Random(20260803)
DEMO_TO = "support@northstar-linen.example"
START = datetime(2026, 1, 5, 9, 0, tzinfo=timezone.utc)
# Keep a handful of genuinely ambiguous references in the inbox, but keep them
# outside the deterministic action cohort used by the demo runbook. This lets
# extraction surface uncertainty without making the approved label decision
# depend on an identifier that the source email does not contain.
UNKNOWN_REFERENCE_ORDINALS = {1, 34, 58, 116}

VENUES = {
    "hotel": ("Hotel", ["rooms", "housekeeping", "guests"]),
    "restaurant": ("Restaurant", ["dining room", "kitchen", "service"]),
    "spa": ("Spa", ["treatment rooms", "therapists", "guests"]),
}
ROUTES = ["North", "South", "East", "West", "Central"]
CITIES = ["Brighton", "Bristol", "Cambridge", "Leeds", "Manchester", "Oxford", "York"]
MANAGERS = ["Maya Chen", "Tom Alvarez", "Priya Shah", "Daniel Brooks", "Elena Rossi"]
PLANS = ["Essential", "Standard", "Priority"]


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def build_customers() -> list[dict[str, object]]:
    customers: list[dict[str, object]] = []
    for index in range(1, 181):
        venue_type = "hotel" if index <= 90 else "restaurant" if index <= 140 else "spa"
        venue_label, _ = VENUES[venue_type]
        city = CITIES[(index * 3) % len(CITIES)]
        route = ROUTES[(index * 2 + 1) % len(ROUTES)]
        # Ensure the key cohort is easy to understand in the analysis.
        if venue_type == "hotel" and index % 3 == 0:
            route = "East"
        plan = PLANS[(index + 1) % len(PLANS)]
        weekly_deliveries = 8 + ((index * 7) % 44)
        customers.append(
            {
                "customer_id": f"CUST-{index:03d}",
                "customer_name": f"{venue_label} {city} {index:03d}",
                "contact_email": f"{slug(venue_label + ' ' + city + ' ' + str(index).zfill(3))}@customer.example",
                "venue_type": venue_type,
                "city": city,
                "region": "South" if city in {"Brighton", "Bristol", "Oxford"} else "North",
                "delivery_route": route,
                "service_plan": plan,
                "weekly_deliveries": weekly_deliveries,
                "account_manager": MANAGERS[index % len(MANAGERS)],
                "active_since": f"202{4 + index % 2}-0{1 + index % 9:01d}-15",
            }
        )
    return customers


def choose_customer(customers: list[dict[str, object]], category: str, recent: bool) -> dict[str, object]:
    if category == "short_delivery":
        cohort = [c for c in customers if c["venue_type"] == "hotel" and c["delivery_route"] == "East"]
        if RNG.random() < 0.72:
            return RNG.choice(cohort)
    if category == "late_delivery" and RNG.random() < 0.70:
        return RNG.choice([c for c in customers if c["delivery_route"] != "East"])
    return RNG.choice(customers)


TEMPLATES: dict[str, list[tuple[str, str]]] = {
    "late_delivery": [
        ("The linen delivery arrived late again", "Our delivery was several hours behind the agreed window today. We had to keep the team waiting and it made the morning changeover difficult."),
        ("Delivery window missed", "The driver arrived after the delivery window had finished. Could someone look into what happened on this route? This has happened more than once."),
        ("Can we get an update on today's delivery?", "We were expecting the clean linen earlier and still have not seen it. Please let us know when it will arrive because the team is trying to prepare for service."),
        ("Another late drop at {customer_name}", "Today's delivery was late enough that we had to rearrange the day around it. Please pass this on to the service team."),
        ("Morning delivery did not arrive on time", "We eventually received the bags, but not within the agreed window. I am recording this because it is becoming a recurring inconvenience."),
    ],
    "short_delivery": [
        ("We are missing several bundles", "The delivery arrived, but we are short on {item}. {venue_consequence} We may need to buy emergency replacements if this cannot be resolved quickly."),
        ("Short delivery - please check the manifest", "The quantities on the delivery do not match what was ordered. We are missing {item}, and the team is trying to work out which bookings we can still service."),
        ("Urgent: not enough clean linen for today", "We have received fewer pieces than expected. Some rooms may have to remain unavailable until we find additional stock. Please tell us what can be sent out."),
        ("The delivery is incomplete", "A part of the order is missing again. We can manage the late items sometimes, but missing stock leaves us with no good option for today's guests."),
        ("Could someone review our quantities?", "We counted the bags twice and are still short. Please compare this delivery with our order and let us know how this will be corrected."),
    ],
    "damaged_items": [
        ("Several towels arrived damaged", "A number of towels in today's delivery have torn seams. We have separated them from the usable stock and need replacements."),
        ("Damage in the latest delivery", "Some of the sheets are damaged and cannot go into service. Please advise whether replacements can be included on the next run."),
        ("Items not usable", "We found damaged pieces while unpacking the delivery. I have attached the count to our internal note and would appreciate a credit or replacement."),
    ],
    "stained_items": [
        ("Clean linen arrived stained", "Several pillowcases have marks on them even though they were in the clean delivery. We cannot use them for guests in this condition."),
        ("Quality issue with today's linen", "There are visible stains on part of the batch. Please flag this with the laundry team and let us know how to return the affected pieces."),
        ("Stained sheets in the delivery", "We have set aside the stained items. This is not the first time we have had to do this, so please help us understand what is changing."),
    ],
    "wrong_quantity": [
        ("The quantities do not match our order", "We received more of one size and less of another. Could someone compare the packing list with the order we sent?"),
        ("Order count looks wrong", "The delivery is here but the counts are different from the confirmation. We can make do today, but please correct the account record."),
        ("Mismatch between order and delivery", "The quantities on the bags do not match our requested mix. Please have the team review the order before the next delivery."),
    ],
    "billing": [
        ("Question about this month's invoice", "There is a line on the latest invoice that I do not recognize. Please explain the charge and confirm whether the account has been updated correctly."),
        ("Invoice does not match our plan", "The amount billed is higher than expected for our current service plan. Could you send the calculation behind this invoice?"),
        ("Please review a billing discrepancy", "We think one of the delivery charges has been duplicated. I would appreciate a review before we approve payment."),
    ],
    "service_change": [
        ("We need to change our weekly quantities", "Our demand is changing for the next few weeks. Can someone help us adjust the regular delivery without losing the current service window?"),
        ("Request to update the delivery plan", "Please let us know what is possible if we reduce the order on some days and increase it on others."),
        ("Can we discuss a change to our service?", "We would like to review our current plan and delivery frequency. Please have the account manager contact us."),
    ],
}


def build_cases(customers: list[dict[str, object]]) -> list[dict[str, object]]:
    categories = (
        ["late_delivery"] * 38
        + ["short_delivery"] * 30
        + ["damaged_items"] * 18
        + ["stained_items"] * 12
        + ["wrong_quantity"] * 10
        + ["billing"] * 7
        + ["service_change"] * 5
    )
    RNG.shuffle(categories)
    cases: list[dict[str, object]] = []
    for index, category in enumerate(categories, start=1):
        recent = index > 78
        customer = choose_customer(customers, category, recent)
        if index % 20 == 0 and cases:
            # A small minority are genuine replies in the same Gmail thread.
            # Reuse the preceding case's customer and problem so the reply is
            # semantically coherent rather than merely having a Re: subject.
            customer = cases[-1]["customer"]
            category = cases[-1]["category"]
        days_after_start = RNG.randint(0, 178)
        if category == "short_delivery" and customer["venue_type"] == "hotel" and customer["delivery_route"] == "East":
            days_after_start = RNG.randint(112, 178)
        received = START + timedelta(days=days_after_start, hours=RNG.randint(0, 8))
        cases.append(
            {
                "case_id": f"CASE-{index:03d}",
                "customer": customer,
                "category": category,
                "received": received,
                "recent": recent,
                "repeat": index % 7 == 0,
            }
        )
    return cases


def render_email(case: dict[str, object], ordinal: int) -> tuple[str, str, str]:
    customer = case["customer"]
    category = str(case["category"])
    subject_template, body_template = RNG.choice(TEMPLATES[category])
    item = RNG.choice(["bath towels", "hand towels", "king sheets", "pillowcases", "bath mats"])
    subject = subject_template.format(customer_name=customer["customer_name"], item=item)
    subject_suffixes = [
        " for today's changeover",
        " before tonight's service",
        " from this morning's drop",
        " on the latest order",
        " - please review",
        " from our receiving team",
    ]
    if ordinal % 3 == 0:
        subject += RNG.choice(subject_suffixes)
    venue_consequence = {
        "hotel": "We have rooms waiting for clean stock.",
        "restaurant": "We are trying to cover the next dining service with what is available.",
        "spa": "The treatment team is checking which appointments can still go ahead.",
    }[str(customer["venue_type"])]
    body = body_template.format(
        customer_name=customer["customer_name"],
        item=item,
        venue_consequence=venue_consequence,
    )
    openings = [
        "Hello Northstar team,",
        "Hi support,",
        "Good morning,",
        "Hello, I hope you can help with this.",
        "Hi there,",
    ]
    closings = [
        "Thanks,",
        "Many thanks,",
        "Best,",
        "Regards,",
        "Thank you,",
    ]
    contact_name = str(customer["customer_name"]).replace(" ", " ")
    email = str(customer["contact_email"])
    venue_context = {
        "hotel": [
            "The housekeeping team is working through the morning room turn.",
            "We are trying to keep the guest rooms available for today's arrivals.",
            "The front desk is already asking when the remaining stock will arrive.",
        ],
        "restaurant": [
            "The team is preparing for the next service and is counting the clean stock again.",
            "This affects the way we are setting up the dining room today.",
            "We are trying to avoid changing the service plan at short notice.",
        ],
        "spa": [
            "The treatment team is checking the cupboards before the afternoon bookings.",
            "We have several appointments today and need to know what can be used.",
            "The reception team is trying to keep the treatment schedule unchanged.",
        ],
    }
    context = RNG.choice(venue_context[str(customer["venue_type"])])
    extra = " " + context
    if ordinal % 5 == 0:
        extra += " We have already checked the receiving area and the packing list."
    if case["repeat"]:
        extra += " We raised a similar issue recently and would appreciate a proper follow-up."
        subject = "Following up: " + subject
    if ordinal % 23 == 0:
        extra += " We also noticed a couple of pieces with quality marks in the same delivery."
    if ordinal % 20 == 0:
        extra += " This is a follow-up to my earlier message; the issue is still open."
    tone_lines = [
        "Please could someone check this against our order and let me know what happened?",
        "I would appreciate a quick confirmation once the team has looked into it.",
        "This is becoming time-sensitive for today's service, so an update would help.",
        "I am recording the details here so we can keep track of the repeat issue.",
        "There is no need to call; an email with the next step is fine.",
    ]
    tone_line = RNG.choice(tone_lines)
    if ordinal % 4 == 0:
        extra += " " + tone_line
    elif ordinal % 4 == 1:
        body += "\n\n" + tone_line
    elif ordinal % 4 == 2:
        extra = " " + tone_line + extra
    else:
        # A few messages are deliberately terse, as real shared inboxes are.
        body = body.split(". ", 1)[0] + "."
    reference_line = (
        "Customer reference: CUST-??"
        if ordinal in UNKNOWN_REFERENCE_ORDINALS
        else ""
        if ordinal % 17 == 0
        else "Customer reference: " + str(customer["customer_id"])
    )
    signature = (
        RNG.choice(closings)
        + "\n"
        + contact_name
        + ("\n" + reference_line if reference_line else "")
    )
    body = "\n\n".join([RNG.choice(openings), body + extra, signature])
    return subject, email, body


def write_customers(customers: list[dict[str, object]]) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    with (DATA / "customers.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(customers[0]))
        writer.writeheader()
        writer.writerows(customers)


def write_emails(cases: list[dict[str, object]]) -> None:
    EMAILS.mkdir(parents=True, exist_ok=True)
    HELD_OUT.mkdir(parents=True, exist_ok=True)
    for old in EMAILS.glob("*.eml"):
        old.unlink()
    for old in HELD_OUT.glob("*.eml"):
        old.unlink()
    manifest: list[dict[str, str]] = []
    previous_message_id = ""
    previous_subject = ""
    for ordinal, case in enumerate(cases, start=1):
        subject, sender, body = render_email(case, ordinal)
        is_reply = ordinal % 20 == 0 and bool(previous_message_id)
        if is_reply:
            subject = "Re: " + previous_subject
            body = "Hello again,\n\nFollowing up on my earlier message. " + body
        received = case["received"]
        message_id = f"<{uuid.uuid5(uuid.NAMESPACE_URL, f'northstar-demo-{ordinal}')}>"
        filename = f"complaint-{ordinal:03d}.eml"
        headers = [
            f"From: {case['customer']['customer_name']} <{sender}>",
            f"To: {DEMO_TO}",
            f"Date: {email.utils.format_datetime(received)}",
            f"Message-ID: {message_id}",
            f"Subject: {subject}",
            "MIME-Version: 1.0",
            "Content-Type: text/plain; charset=utf-8",
            "",
            body,
            "",
        ]
        if is_reply:
            headers.insert(4, f"In-Reply-To: {previous_message_id}")
            headers.insert(5, f"References: {previous_message_id}")
        (EMAILS / filename).write_text("\n".join(headers), encoding="utf-8")
        manifest.append(
            {
                "fixture_file": filename,
                "case_id": str(case["case_id"]),
                "customer_id": str(case["customer"]["customer_id"]),
                "category": str(case["category"]),
                "message_id": message_id,
            }
        )
        previous_message_id = message_id
        previous_subject = subject
    (ROOT / "setup" / "fixture-manifest.csv").write_text(
        "fixture_file,case_id,customer_id,category,message_id\n"
        + "\n".join(",".join(row.values()) for row in manifest)
        + "\n",
        encoding="utf-8",
    )
    held_out_customer = next(customer for customer in build_customers() if customer["customer_id"] == "CUST-003")
    held_out_case = {
        "case_id": "HELDOUT-001",
        "customer": held_out_customer,
        "category": "short_delivery",
        "received": datetime(2026, 7, 28, 10, 30, tzinfo=timezone.utc),
        "recent": True,
        "repeat": False,
    }
    subject, sender, body = render_email(held_out_case, 1001)
    held_out_message_id = f"<{uuid.uuid5(uuid.NAMESPACE_URL, 'northstar-demo-heldout-001')}>"
    held_out_headers = [
        f"From: {held_out_customer['customer_name']} <{sender}>",
        f"To: {DEMO_TO}",
        f"Date: {email.utils.format_datetime(held_out_case['received'])}",
        f"Message-ID: {held_out_message_id}",
        f"Subject: {subject}",
        "MIME-Version: 1.0",
        "Content-Type: text/plain; charset=utf-8",
        "",
        body,
        "",
    ]
    (HELD_OUT / "heldout-001.eml").write_text("\n".join(held_out_headers), encoding="utf-8")


def main() -> None:
    customers = build_customers()
    cases = build_cases(customers)
    write_customers(customers)
    write_emails(cases)
    print(f"generated {len(customers)} customers and {len(cases)} email fixtures")


if __name__ == "__main__":
    main()
