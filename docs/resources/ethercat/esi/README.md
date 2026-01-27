## EtherCAT ESI XML files

This directory stores vendor-provided **ESI** (EtherCAT Slave Information) XML files used for:

- capturing vendor/product IDs for each drive
- documenting supported PDO/DC capabilities
- repeatable bring-up (IgH configuration and expected process-image layout)

### Where to put A6‑EC files

Place StepperOnline A6‑EC ESI XML(s) in:

`docs/resources/ethercat/esi/stepperonline/A6-EC/`

### Rules

- Keep vendor XML files **unmodified**.
- If the vendor license forbids committing ESI files to git, do **not** add them here; instead, keep them local and commit only extracted metadata (documented in `RTOS-ETHERCAT-plan.md`).

