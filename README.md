# Odoo Franchise Management

Implemented by **Muhammad Shahyan Khalid**.

Franchise contracts, monthly fee billing, regional collection reporting and headquarters accounting workflows.

This repository provides an independently reconstructed implementation using
fictional business data and public Odoo Community APIs. The documented workflows
and configuration demonstrate the implementation without distributing client data.

## Implemented features

- Franchise contracts, regions and fictional 80-campus seed configuration.
- Monthly fee billing with duplicate prevention.
- Regional and headquarters metrics from posted native accounting records.
- Signed bank receipt processing and native payment reconciliation.

Odoo 18.0 Community. Addon `franchise_operations`. Database `franchise_demo`. Port `8177`.
See `docs/FEATURES.md` for scope, assumptions and limitations.

## Setup (commands for your later use; not executed)

```powershell
python scripts/bootstrap.py
.\scripts\lab.ps1 -Action init
.\scripts\lab.ps1 -Action up
.\scripts\lab.ps1 -Action upgrade
.\scripts\lab.ps1 -Action stop
```

Open http://127.0.0.1:8177. Admin password: `.local/credentials.json`.
Local email capture: http://127.0.0.1:8027. SMTP goes to Mailpit.
`reset` deletes only this Compose project's named demonstration database.
`seed` reloads custom XML external IDs. Other projects are not dependencies.

Each project has its own Compose name, PostgreSQL volume, filestore, database,
loopback web port, credentials and addons mount. Images are pinned by digest.
Default networking is internal and blocks live providers. To use an explicitly
authorized sandbox, change the project's network setting and supply its secrets
through the private environment. No production integration is enabled by default.

User-supplied historical behavior is the evidence source. Exact thresholds,
identifiers, providers and rules absent from it are proposed configuration. Native
Odoo invoices, payments, inventory, CRM and HR are used where applicable. Configure
a suitable chart, journals, taxes and payment methods before accounting actions.

See [PUBLICATION_SAFETY_REPORT.md](PUBLICATION_SAFETY_REPORT.md) for repository
contents and exclusions. Validation history is recorded separately in
[docs/VERIFICATION.md](docs/VERIFICATION.md).
