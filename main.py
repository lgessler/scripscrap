"""Zuhhhh"""

from bs4 import BeautifulSoup
import os
import logging
import re

IN_DIR = "in/"
OUT_DIR = "out/"


# File i/o ----------------------------------------------------------------------
def read_file(in_dir, name):
    with open(os.path.join(in_dir, name), 'r') as f:
        return f.read()

def read_input_files(in_dir=IN_DIR, ext=".html"):
    file_order = os.listdir(in_dir)
    return ([read_file(in_dir, name)
            for name in file_order
            if name.endswith(ext)],
            file_order)

def write_file(out_dir, name, lines):
    with open(os.path.join(out_dir, name), 'w') as f:
        return f.write("\n".join([repr(line) for line in lines]))

def write_output_files(docs, file_order, out_dir=OUT_DIR, orig_ext=".html"):
    for name, lines in zip(file_order, docs):
        write_file(out_dir, name.replace(orig_ext, ".txt"), lines)

# HTML transformations ----------------------------------------------------------
def html_parse(html_string):
    return BeautifulSoup(html_string, 'html.parser')

def html_extract_table(soup):
    tables = soup.find_all('tbody')
    assert len(tables) == 1
    return tables[0]

def html_parse_rows(soup):
    parsed_lines = []
    trs = soup.find_all('tr')
    for tr in trs:
        tds = tr.find_all('td')
        assert len(tds) == 2
        line = ManuscriptLine(tds[0].text, tds[1].text)
        parsed_lines.append(line)
    return parsed_lines

def apply_functions(fs, data):
    accum = data
    for f in fs:
        accum = map(f, accum)
    return list(accum)

# Parsed lines ------------------------------------------------------------------
class ManuscriptLine(object):
    page_and_line_no_pattern = re.compile(r"\((\d+)/(\d+)\)")

    def _clean_page_and_line(self, page_and_line_no):
        s = page_and_line_no.strip()
        match = ManuscriptLine.page_and_line_no_pattern.fullmatch(s)
        assert match and len(match.groups()) == 2
        return match.groups()

    def _extract_footnote(self, text):
        assert len(text.split("\n")) == 2
        text, footnote = text.split("\n")
        if footnote[0] == "(":
            footnote_marker = footnote[1]
            text = text.replace("(" + footnote_marker + ") ", "")
            text = text.replace("(" + footnote_marker + ")", "")
            footnote = footnote[4:] # skip '(?) ' and keep the rest
        else:
            footnote_marker = footnote[0]
            text = text.replace(footnote_marker + " ", "")
            text = text.replace(footnote_marker, "")
            footnote = footnote[2:] # skip '1 ' and keep the rest
        return text, footnote

    def _clean_text(self, text):
        text = text.strip()
        if "\n" in text:
            text, footnote = self._extract_footnote(text)
            self.footnote = footnote
        else:
            self.footnote = None
        return text

    def __init__(self, page_and_line_no, text):
        page_no, line_no = self._clean_page_and_line(page_and_line_no)
        self.page_no = page_no
        self.line_no = line_no
        self.text = self._clean_text(text)

    def __repr__(self):
        return "<ManuscriptLine; page_no={}, line_no={}, text='{}', footnote='{}'>".format(
            self.page_no, self.line_no, self.text, self.footnote)

    def __str__(self):
        return "<Line ({}/{}): '{}' ({})>".format(
            self.page_no, self.line_no, self.text, self.footnote)


# Main --------------------------------------------------------------------------
def main():
    file_strings, file_order = read_input_files()
    html_funcs = [html_parse,
                  html_extract_table,
                  html_parse_rows]
    parsed_docs = apply_functions(html_funcs, file_strings)

    write_output_files(parsed_docs, file_order)


if __name__ == "__main__":
    main()
