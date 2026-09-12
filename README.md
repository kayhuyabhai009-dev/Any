# PDF Part Splitter

A browser-only tool for dividing a large PDF into smaller, page-based PDF parts that are easier to upload. It was made for large study PDFs such as the 171 MB and 229 MB files shared for the maths project.

## Use it

1. Open `index.html` in Chrome/Edge, or serve this folder with:

   ```bash
   python3 -m http.server 8000
   ```

   Then open `http://localhost:8000`.
2. Select or drop one PDF.
3. Choose **20 MB** when the upload limit is unknown. Smaller targets such as 20–25 MB are safer for chat uploads.
4. Click **Split PDF** and download the individual parts. An optional ZIP can also be created.

The PDF is processed locally in the browser; it is not sent to this project or to a server. `vendor/pdf-lib.min.js` and `vendor/jszip.min.js` are bundled so the splitter does not depend on a CDN.

## Important behaviour

- Splitting happens at page boundaries. A page is never cut in half.
- Therefore, a single page larger than the chosen target can produce an oversized part; the result page marks it clearly.
- The target size is a maximum target, not a guarantee of an exact number of parts. Page content sizes differ, so the app automatically subdivides oversized ranges.
- Very large PDFs need browser memory. Desktop Chrome/Edge is recommended; close other heavy tabs first. The optional ZIP uses additional memory, so downloading individual parts is safer for a 171–229 MB PDF.
- Password-protected PDFs are not supported unless they are unlocked before selecting them.
