# PDF Generation Skill
When generating a PDF file in Python (e.g., using `reportlab`), you MUST support Japanese characters (CJK) to avoid missing characters or garbled outputs ('n' or squares). 

Always use the built-in Japanese CID font `HeiseiKakuGo-W5` by adding the following pattern to your `reportlab` script:

```python
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

c = canvas.Canvas("workspace/report.pdf")

# Register and set the Japanese font
pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
c.setFont('HeiseiKakuGo-W5', 12) # You MUST use this font for all text outputs!

c.drawString(100, 750, "こんにちは、世界！ (Hello, World!)")
c.save()
```

If you ever need to use a different PDF library (like `fpdf` or `pdfkit`), make sure you download or specify a valid Japanese `.ttf` font (like Noto Sans JP or IPAexGothic). But `reportlab` with `HeiseiKakuGo-W5` is the easiest and default recommended approach because it requires no external font file downloads.
