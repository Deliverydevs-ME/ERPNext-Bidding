## DD ERPNext Bidding

A sealed, tender-style supplier bidding workflow built on top of ERPNext's
standard Material Request → Request for Quotation → Supplier Quotation
flow. Quoted rates, delivery lead time and supporting attachments stay
genuinely hidden from every internal user - including System Manager -
until a predefined opening date/time, and every step is logged to an
append-only audit trail.

This app does not replace any standard ERPNext doctype. It adds a small
number of custom fields and one supporting doctype on top of the existing
Material Request, Request for Quotation and Supplier Quotation documents,
plus two new doctypes of its own.

### The workflow

```
Material Request (the tender)
        |
        |  one or more RFQs raised against it, each enabled for bidding
        v
Request for Quotation  (Round 1)  ----sealed submissions---->  Supplier Quotations (sealed)
        |                                                              |
        |  at Opening Date & Time (auto) or "Open Bids Now" (manual)   |
        v                                                              v
   all Round 1 quotations revealed simultaneously  ---->  Supplier Quotation Comparison Tool
        |                                                   (auto-generated, lowest price flagged)
        |
        |  if Round 1 isn't accepted, raise a NEW RFQ against the same Material Request
        v
Request for Quotation  (Round 2)  ----sealed submissions---->  Supplier Quotation Comparison Tool
```

1. **Material Request** - created against a Project, tagged with a
   Tender/Bidding Reference and a Request Type, listing the items and
   quantities being tendered. It is the permanent parent of every bidding
   round.
2. **Request for Quotation** - raised against that Material Request, with
   **Enable Vendor Bidding** checked and a Submission Deadline / Opening
   Date & Time set. On submit, ERPNext's own RFQ logic auto-creates a
   portal login for each supplier (if they don't already have one) and
   emails them a "Set Password" link plus a link to submit their
   quotation - this app adds no new authentication mechanism, it reuses
   ERPNext's native supplier portal as-is.
3. **Supplier Quotation** - created by the supplier through the portal.
   Every item needs a rate and a lead time, and at least one attachment
   (PDF/Excel) is required - uploading a file alone, with rates left
   blank, is rejected. The moment it's submitted, the real values are
   sealed (see below) before anyone else can look at it.
4. **Opening** - automatically, the moment the Opening Date & Time
   arrives (checked every 5 minutes), or manually via "Open Bids Now" on
   the RFQ. All of that RFQ's sealed quotations are revealed together,
   and a Supplier Quotation Comparison Tool record is generated
   automatically with the lowest price per item already flagged.
5. **Another round** - if the round isn't accepted, raise a brand new RFQ
   against the *same* Material Request. It's automatically numbered as
   the next round; the previous round's RFQ and Supplier Quotations are
   never touched, overwritten or deleted.

### How sealing actually works

This is the part that matters most, so it's worth being explicit: the
restriction is enforced at the data layer, not by hiding a field or a
button in the UI.

- When a Supplier Quotation is submitted against a bidding-enabled RFQ,
  its real rate/amount/total/lead-time values are encrypted and the
  **actual database columns are zeroed out** - not just hidden from the
  form. There is nothing sensitive left in the row for any read path
  (desk, REST API, reports, print formats) to leak, for any role,
  including System Manager.
- The encrypted copy lives in a `Password`-type field, which Frappe never
  returns through ordinary document reads under any circumstance - only
  this app's own unseal routine can decrypt it.
- At opening time, the real values are restored directly into the
  database for every quotation submitted against that RFQ, all at once.
- File attachments get the same treatment via a permission hook: any file
  attached to a still-sealed Supplier Quotation is blocked from being
  read or downloaded by anyone, until that RFQ opens. (Caveat: like every
  permission-hook-based restriction in Frappe, this one does not apply to
  the Administrator account, which bypasses controller permission hooks
  by design - the rate/amount sealing above has no such exception, since
  it isn't permission-based at all.)
- Submissions and amendments made after the Submission Deadline, or after
  the RFQ has already opened, are rejected server-side regardless of
  where the request comes from.

### Doctypes

#### New doctypes

| Doctype | Purpose |
|---|---|
| **Material Request Type** | A simple master list of request types (e.g. Purchase, Tender, Emergency) that can be assigned to a Material Request via the Request Type link field, instead of being limited to the standard fixed "Purpose" select. |
| **Bidding Audit Log** | An append-only log of every bidding event: quotation submitted, late submission blocked, amendment blocked, bids opened, comparative statement generated. No role - not even System Manager - can edit an existing entry, only create new ones; entries can only be read, never altered, which is what makes it useful as an audit trail. Linked to the originating Request for Quotation via a dynamic link. |

#### Custom fields on existing doctypes

**Material Request**
- `Tender / Bidding Reference` - free-text code/name for this tender (e.g. "Tender A"), carried for reference across every round raised against it.
- `Request Type` - link to the new Material Request Type master (additive, alongside the standard Purpose field).
- `Project` - link to Project.

**Request for Quotation**
- `Material Request (Tender)` - the parent Material Request, set automatically from the RFQ's items.
- `Enable Vendor Bidding` - turns the sealed-bid workflow on for this RFQ.
- `Bidding Round` - which round this RFQ is, among all bidding-enabled RFQs raised against the same Material Request. Computed automatically on submit.
- `Submission Deadline` / `Opening Date & Time (For Internal Users)` - the two controlling dates/times.
- `Bidding Status` - Bidding Open / Bids Opened, managed by the system.
- `Actual Opening Date & Time` / `Actual Closing Date & Time` - when bids were genuinely opened/closed, which can differ from the planned dates above if opened early, late, or manually.

**Request for Quotation Item**
- `Request Type` - fetched automatically from the linked Material Request.
- `Project` (the existing `project_name` field) - now fetched automatically from the linked Material Request's Project, instead of being manually entered.

**Supplier Quotation**
- `Bidding RFQ Reference` / `Bidding Round` - which RFQ and round this quotation belongs to.
- `Sealed Bid` - whether this quotation is currently sealed.
- `Sealed Bid Payload` - the encrypted snapshot of the real values while sealed (internal use only).
- A banner shown on the form itself while the quotation is sealed, explaining why the amounts read as zero.

**Supplier Quotation Comparison Tool** *(from the `falcon` app - reused rather than duplicated)*
- `Bidding Round` - tags which round of which tender this auto-generated comparison belongs to, since the tool's own item-fetching logic is scoped to a single RFQ round rather than every quotation ever raised against the parent RFQ.

### Where things run

- `doc_events` on Request for Quotation and Supplier Quotation drive validation, round numbering, and sealing.
- A scheduled job runs every 5 minutes to open any RFQ whose Opening Date & Time has arrived, without anyone needing to click a button.
- A `has_permission` hook on the File doctype enforces attachment confidentiality.
- A client script adds an "Open Bids Now" button to the RFQ form for Purchase Manager / System Manager.

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app dd_erpnext_bidding
```

It depends on `erpnext` and `falcon` being installed on the same site (the
latter provides the Supplier Quotation Comparison Tool this app reuses).

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/dd_erpnext_bidding
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

mit
