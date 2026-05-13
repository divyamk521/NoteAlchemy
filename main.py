from export_utils import notes_to_text, notes_to_pdf


print("STARTING EXPORT TEST")


# ---------------------------------------------------
# SAMPLE MARKDOWN NOTES
# ---------------------------------------------------

notes_markdown = """
# Neural Networks

> Overview of deep learning concepts

## Key Concepts

- Neural Networks
- Backpropagation
- Gradient Descent

### Activation Functions

ReLU is commonly used in deep learning.

| Function | Purpose |
|----------|----------|
| ReLU | Activation |
| Sigmoid | Probability |

---

Example code:

x = max(0, x)
"""


print("MARKDOWN CREATED")


# ---------------------------------------------------
# TEST TXT EXPORT
# ---------------------------------------------------

txt_bytes = notes_to_text(notes_markdown)

print("TXT EXPORT COMPLETE")


with open("notes_output.txt", "wb") as f:
    f.write(txt_bytes)

print("TXT FILE SAVED")


# ---------------------------------------------------
# TEST PDF EXPORT
# ---------------------------------------------------

pdf_bytes = notes_to_pdf(notes_markdown)

print("PDF EXPORT COMPLETE")


with open("notes_output.pdf", "wb") as f:
    f.write(pdf_bytes)

print("PDF FILE SAVED")


print("\nALL EXPORTS WORKED SUCCESSFULLY")