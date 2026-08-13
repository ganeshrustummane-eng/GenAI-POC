"""
Builds the complete Migration Validator Word documentation.
Run:  python docs/build_docs.py
Output: docs/Migration_Validator_Documentation.docx
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from docbuilder.style import new_document
from docbuilder.frontmatter import build_cover, build_toc, add_footer
from docbuilder.content_part1 import build_part_one
from docbuilder.content_part2 import build_part_two

OUT = os.path.join(os.path.dirname(__file__), "Migration_Validator_Documentation.docx")


def main():
    doc = new_document()
    build_cover(doc)
    build_toc(doc)
    build_part_one(doc)
    build_part_two(doc)
    add_footer(doc)
    doc.save(OUT)
    print("Document written:", OUT)


if __name__ == "__main__":
    main()
