# AstaLink — Proposal 2 (2nd Submission) Deliverables

Files in this folder answer all 32 required Google Form questions for team MUMET.

- `proposal_2_answers.md` — source of truth (edit this, then rebuild).
- `build_docx.py` — `python3 build_docx.py` regenerates the DOCX.
- `AstaLink_Proposal_2.docx` — generated; do not hand-edit.
- `AstaLink_Proposal_2.pdf` — generated; the file to attach to the form.

## Rebuild
```bash
python3 build_docx.py
soffice --headless --convert-to pdf --outdir . AstaLink_Proposal_2.docx
```

## ⚠️ Manual actions before submitting (placeholders to fill)
1. **ID Tim** — replace `[ISI ID TIM SESUAI DATA PENDAFTARAN]` with the registered team ID.
2. **Link Attachment** — replace `[ISI LINK DEMO / REPOSITORI / VIDEO JIKA ADA]` if you have a demo/repo link.
3. **Rename the PDF** to the form's required pattern before upload: `<ID Tim> - AstaLink AI Chief Investment Officer.pdf`.
4. **User interview** — the Problem Validation interview portion and the primary-research part of Evidence of Demand are intentionally left empty (`[Riset primer ... belum dilaksanakan]`). Fill these once user interviews/shadowing are completed.
