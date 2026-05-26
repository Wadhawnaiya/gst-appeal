# GST Appeal Drafting Playbook

## Drafting philosophy

World-class appeal drafting is not a long list of grievances. It is a disciplined demonstration that the impugned order failed on facts, law, procedure, computation or binding authority and that the appellate forum should grant specific relief.

Use three layers:

1. **Record layer:** what happened, with dates and documents.
2. **Error layer:** what the adjudicating authority got wrong.
3. **Relief layer:** what exact order the appellate authority should pass.

## Automated workbench discipline

For matter-folder drafting, first generate and read the autodraft workspace:

```bash
python3 <skill-root>/scripts/gst_appeal_autodraft.py --matter-dir <folder> --output-dir <folder>/gst-appeal-workspace
```

Then draft from the workspace only after reading:

- `facts-digest.md`
- `appeal-drafting-brief.md`
- NotebookLM results
- caselaw research packets
- selected full-text authorities / official PDFs

Do not cite a search result, snippet or NotebookLM synthesis as a final authority unless the underlying source has been checked.

## ICAI Practical Guide integration

Before drafting, also load `icai-guide-principles.md`. Apply its central discipline: precise grounds, prescribed forms, complete verification, SCN/reply/order mapping, limitation proof, demand breakup and pre-deposit checks.

## Intake diagnosis

Before writing final facts/grounds, build this matrix:

```text
SCN allegation -> Reply/evidence -> Order finding -> Appeal error -> Evidence/authority -> Relief
```

Also prepare:

```text
Demand component -> Amount confirmed -> Amount admitted -> Amount disputed -> Pre-deposit basis -> Evidence/challan
```

## Statement of facts

- Write chronologically.
- Use short numbered paragraphs.
- Attach source references: `Annexure A-3`, `SCN para 8`, `Reply dated ...`.
- Include adverse facts fairly; explain later in submissions.
- Do not mix law/arguments with facts.

Recommended sequence:

1. Appellant identity and business.
2. Registration, tax period, return/payment background.
3. Department action: audit/investigation/notice.
4. SCN allegations and demand breakup.
5. Reply/evidence filed and hearings.
6. Findings in the order.
7. Why the appellant is aggrieved.
8. Limitation/pre-deposit/maintainability facts.

## Grounds of appeal

Grounds should be concise legal/factual errors, not full arguments. Use one ground per issue. The grounds should expose adjudication failures: misunderstanding facts, misapplying law, ignoring binding judicial/administrative authority, violating procedure, or computing demand incorrectly.

Common ground families:

- Lack of jurisdiction or wrong statutory provision.
- Order beyond SCN / new grounds in order.
- Violation of natural justice / no effective hearing / evidence ignored.
- Non-speaking order / mechanical confirmation of demand.
- Misinterpretation of Act/Rules/notification/circular.
- Wrong factual finding or reconciliation ignored.
- Time-bar / wrong invocation of extended period.
- Wrong tax computation / duplicated demand / arithmetical error.
- Interest not legally leviable or incorrectly computed.
- Penalty unsustainable due to absence of ingredients, proportionality, section 126 discipline or mens rea where relevant.
- Demand contrary to binding judicial precedent or CBIC circular.

## Written submissions

For each issue:

```text
Issue heading
A. Finding challenged
B. Record facts and evidence
C. Statutory provisions
D. Circulars/notifications
E. Case law and applicability
F. Adverse-risk distinction
G. Application to facts
H. Relief requested for this issue
```

## Prayer drafting

Include primary, alternate and consequential relief:

- Set aside/quash the impugned order to the extent challenged.
- Delete tax/interest/penalty/fine/fee demand.
- Recompute demand if only arithmetic/classification part survives.
- Remand for fresh adjudication after considering evidence and granting hearing.
- Stay recovery pending appeal where appropriate.
- Grant consequential refund/re-credit and any other relief deemed fit.
- Permit additional evidence/submissions if needed.

## Red flags before filing

- Grounds contradict statement of facts.
- Case law cited from snippets only.
- Demand breakup missing.
- Limitation/pre-deposit not checked.
- Certified/uploaded order copy, acknowledgement, authorization or fees omitted.
- Annexures unnumbered or not referred in body.
- Prayer does not match disputed issues.
- NotebookLM/legal proposition not tied to its underlying source.
- Adverse fact omitted from facts but appears in order.
- Draft attacks the officer personally instead of adjudication errors.
