# TAX KNOWLEDGE BASE
**Authority: 11.0 SOVEREIGN | ECHO OMEGA PRIME**
**Tags:** #TaxKnowledge #Research #Compliance #Federal #State

---

## PURPOSE

Centralized repository for tax research, regulations, deductions, credits, and compliance information to support:
- Personal tax planning and filing
- Business tax compliance (S-Corp, LLC, etc.)
- Deduction optimization
- Credit identification
- Audit defense preparation

---

## DIRECTORY STRUCTURE

```
TAX_KNOWLEDGE/
├── FEDERAL/           # Federal tax code, IRS regulations
├── STATE/             # State-specific tax rules (Texas, etc.)
├── BUSINESS/          # Business entity taxation (S-Corp, LLC)
├── PERSONAL/          # Personal income tax
├── DEDUCTIONS/        # Comprehensive deduction library
├── CREDITS/           # Tax credit research
├── FORMS/             # Form templates and instructions
├── RESEARCH/          # Tax research notes and case studies
└── TEMPLATES/         # Calculation templates, checklists
```

---

## USAGE

### Quick Reference
- **Federal Tax Brackets**: `FEDERAL/tax_brackets_2025.md`
- **S-Corp Deductions**: `BUSINESS/s_corp_deductions.md`
- **Home Office**: `DEDUCTIONS/home_office.md`
- **Vehicle Deductions**: `DEDUCTIONS/vehicle_business_use.md`

### Research Workflow
1. Identify tax question or optimization opportunity
2. Search relevant directory (FEDERAL, BUSINESS, DEDUCTIONS, etc.)
3. Cross-reference IRS publications
4. Document findings in RESEARCH/
5. Update applicable templates

---

## KEY TOPICS

### Federal
- Tax brackets and rates (2024-2025)
- Standard deductions vs itemized
- Self-employment tax (SE tax)
- Estimated quarterly payments
- IRS publication index

### Business
- S-Corporation taxation
- LLC taxation options
- Reasonable compensation (W-2 salary)
- Pass-through deductions (Section 199A)
- Business expense categories

### Deductions
- Home office (Form 8829)
- Vehicle business use (actual vs mileage)
- Business meals and entertainment
- Travel expenses
- Professional development and education
- Software and technology
- Health insurance (self-employed)
- Retirement contributions (SEP-IRA, Solo 401k)

### Credits
- Child Tax Credit
- Earned Income Credit
- Education credits (American Opportunity, Lifetime Learning)
- Energy efficiency credits
- R&D Tax Credit (business)

---

## INTEGRATION WITH ECHO SYSTEMS

### PROMETHEUS PRIME
Tax research queries can leverage PROMETHEUS for OSINT:
```bash
curl http://192.168.1.202:8370/osint/tax-law-search?query="S-Corp reasonable compensation"
```

### CRYSTAL MEMORY
Store important tax findings:
```python
from master_vault import store_tax_knowledge
store_tax_knowledge("s_corp_salary_calculation", data)
```

### GS343 Healer
Tax calculation error checking:
```bash
curl http://localhost:5003/heal/tax-calculation
```

---

## COMPLIANCE NOTES

- **NOT LEGAL ADVICE**: This is research/reference only
- **Verify with CPA**: Always consult licensed tax professional
- **Stay Current**: Tax law changes annually
- **Document Sources**: Always cite IRS publications, tax code sections

---

## ANNUAL MAINTENANCE

- [ ] Update tax brackets (January)
- [ ] Review new tax law changes
- [ ] Update deduction limits (mileage rate, meal limits, etc.)
- [ ] Review state tax changes
- [ ] Update form templates

---

## RESOURCES

### Official Sources
- IRS.gov (official publications)
- State comptroller websites
- Tax code (26 U.S.C.)

### Tools
- IRS Free File
- Tax calculation spreadsheets
- Deduction trackers

---

**Created:** 2026-01-30
**Last Updated:** 2026-01-30
**Maintained by:** ECHO OMEGA PRIME
