In @templates/base.html:

- Add two links to the footer:
  - "Terms and Conditions"
  - "Privacy Policy"
- Both should be plain text links with no special styling.
- Since the pages don't exist yet, set both hrefs to "#".
- Do not modify anything else in the page.

After making the change, commit it with:

git commit -m "landing: add terms and privacy links to footer"
Create a "Terms and Conditions" page for Spendly.

1. Add a new route in app.py:
GET /terms -> renders templates/terms.html

2. Create templates/terms.html with generic terms and conditions content appropriate for a personal expense tracking app.

Include sections like:
- Acceptance of Terms
- Use of Service
- User Data
- Limitations of Liability
- Changes to Terms

Extend base.html if it exists, otherwise match the style of landing.html.

3. In templates/landing.html, update the "Terms and Conditions" footer link href from "#" to "/terms".

Do not change anything else.

git commit -m "landing: add terms and conditions page and route"