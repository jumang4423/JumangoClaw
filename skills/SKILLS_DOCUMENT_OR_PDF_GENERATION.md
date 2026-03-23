# PDF Generation Skill

When generating a PDF from Markdown, ALWAYS use the following `md-to-pdf` command via bash. Do not use any other methods or libraries.

### Core Command
```bash
md-to-pdf ./workspace/path-to/file.md --launch-options '{ "args": ["--no-sandbox"] }'
```

### Process
1. Save your content to a `.md` file in the workspace.
2. Run the command above to generate the PDF.
3. The PDF will be created in the same directory as the `.md` file.
