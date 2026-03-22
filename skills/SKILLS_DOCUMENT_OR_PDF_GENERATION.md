# PDF Generation Skill

When generating a PDF file, you MUST NOT use Python libraries like `reportlab` or `pdfkit`. Instead, you MUST follow these two steps:

1. **Write content to a Markdown file (`.md`)**
   Create a markdown file with the desired content and formatting (headings, lists, code blocks, tables, etc.). Be sure to support Japanese characters properly by simply using UTF-8 text in the markdown.
   Example: `workspace/report.md`

2. **Convert the Markdown file to PDF using `md-to-pdf`**
   Run the `md-to-pdf` CLI tool via bash to generate the final PDF file.

   ```bash
   md-to-pdf workspace/report-name.md
   ```

   This will automatically create `workspace/report-name.pdf` directly.

### Advanced Usage

You can use standard `md-to-pdf` options for more complex formatting if necessary:
- Change document format/size: `md-to-pdf report.md --pdf-options '{ "format": "Letter" }'`
- Inject custom CSS styles: `md-to-pdf report.md --stylesheet custom.css`
- Apply syntax highlighting styles: `md-to-pdf report.md --highlight-style monokai`

Remember: **Do not** write custom Python scripts to generate PDFs. Always write a `.md` file first, and convert it using the `md-to-pdf` command.
