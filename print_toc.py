import pymupdf

doc = pymupdf.open("data/file.pdf")
for level, title, page in doc.get_toc():
    print(level, title, page)