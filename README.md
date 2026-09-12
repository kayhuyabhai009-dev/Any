# PDF Part Splitter + Workspace Receiver

A browser tool for dividing a large PDF into smaller, page-based PDF parts that are easier to upload. It also includes a small local receiver so a PDF or ZIP can be sent directly into the workspace's `uploads/` folder.

## Run it

Use the included receiver server when you want files to arrive in the workspace:

```bash
python3 server.py
```

Then open `http://localhost:8000`. The live preview uses the same relative `/api/upload` endpoint, so browser code never needs to call `localhost` directly.

If you only need the splitter, `index.html` can also be opened directly in a browser, but the **Workspace receiver** section requires `server.py`.

## Send a file to the workspace

1. Open the page served by `server.py`.
2. In **Workspace receiver**, select one or more PDFs/ZIPs.
3. Click **Upload to workspace** and keep the page open until the progress reaches 100%.
4. The received files are saved under `uploads/` and are intentionally ignored by git.

The receiver accepts files up to 2 GB by default. Change the limit with `MAX_UPLOAD_MB`, for example:

```bash
MAX_UPLOAD_MB=512 python3 server.py
```

## Split a large PDF locally

1. Select or drop one PDF.
2. Choose **20 MB** when the upload limit is unknown. Smaller targets such as 20–25 MB are safer for chat uploads.
3. Click **Split PDF** and download the individual parts. An optional ZIP can also be created.

The splitter processes the PDF locally in the browser; it does not send the PDF to the receiver unless you explicitly use the receiver section. `vendor/pdf-lib.min.js` and `vendor/jszip.min.js` are bundled so the splitter does not depend on a CDN.

## Important behaviour

- Splitting happens at page boundaries. A page is never cut in half.
- Therefore, a single page larger than the chosen target can produce an oversized part; the result page marks it clearly.
- The target size is a maximum target, not a guarantee of an exact number of parts. Page content sizes differ, so the app automatically subdivides oversized ranges.
- Very large PDFs need browser memory. Desktop Chrome/Edge is recommended; close other heavy tabs first. The optional ZIP uses additional memory, so downloading individual parts is safer for a 171–229 MB PDF.
- Password-protected PDFs are not supported unless they are unlocked before selecting them.
