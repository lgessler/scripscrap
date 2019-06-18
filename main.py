""""""

import re
import os
import logging
from bs4 import BeautifulSoup

IN_DIR = "in/"
OUT_DIR = "out/"

# TODO:
#- XML output
#- Parsing lacunae (▩▩▩▩▩, . . . ., etc)
#-- if not already inside of a square bracket, surround with square brackets and replace lacuna-representing characters with periods
#-- if the lacuna-representing characters are already within brackets, just replace with periods
#- Parsing decoration (═════ :::: ═════ :::: ═════ :::: ═════)
#- footnote: note element
#- Parsing |Fol. 5b|
#-- Fol.s: if pipes are present, find it in the neighborhood, in a text like resurrection make sure it actually makes sense to put it where we think it goes
#- superscript: ↑, characterwise before the supped character, also ↓
#-
#- later: doc splitting
#-


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
        return f.write(lines)

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
class ManuscriptLine:
    page_and_line_no_pattern = re.compile(r"\((\d+)/(\d+)\)")
    def __init__(self, page_and_line_no, text):
        page_no, line_no = self._clean_page_and_line(page_and_line_no)
        self.page_no = page_no
        self.line_no = line_no
        self.text = self._clean_text(text)

    def _clean_page_and_line(self, page_and_line_no):
        s = page_and_line_no.strip()
        match = ManuscriptLine.page_and_line_no_pattern.fullmatch(s)
        assert match and len(match.groups()) == 2
        return match.groups()

    def _extract_footnote(self, text):
        assert len(text.split("\n")) == 2
        logging.debug("There appears to be a footnote in this line: %s", text)
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
        logging.debug("Split footnote off: '%s', '%s'", text, footnote)
        return text, footnote

    def _clean_text(self, text):
        text = text.strip()
        if "\n" in text:
            text, footnote = self._extract_footnote(text)
            self.footnote = footnote
        else:
            self.footnote = None
        return text

    def __repr__(self):
        return ("<ManuscriptLine; page_no={}, line_no={}, text='{}', footnote='{}'>"
                .format(self.page_no,
                        self.line_no,
                        self.text,
                        (' (' + self.footnote + ')') if self.footnote else ''))

    def __str__(self):
        return "<Line ({}/{}): '{}'{}>".format(
            self.page_no, self.line_no, self.text,
            (' (' + self.footnote + ')') if self.footnote else '')

# XML generation ----------------------------------------------------------------
# note: *? is the non-greedy version of * in python regex
FOL_PATTERN = re.compile(r"(\[fol.*?\])|(\|fol.*?\|)", re.IGNORECASE)
PAGE_AND_COL_PATTERN = re.compile(r"[\[|]fol\.?(.*?)col\.?\s+([^\s]+?)[\]|]", re.IGNORECASE)
def find_breaks(doc):
    breaks = {}

    for i, line in enumerate(doc):
        text = line.text
        match = FOL_PATTERN.search(text)
        if match is None:
            continue
        s = match.groups()[0] or match.groups()[1]

        match = PAGE_AND_COL_PATTERN.search(s)
        if match is None:
            continue
        assert len(match.groups()) == 2
        page_num, col_num = match.groups()

        page_num = page_num.strip()
        col_num = col_num.strip()
        #TODO: Find the pipe
        breaks[i] = (page_num, col_num)

    return breaks

def generate_header(nums):
    page_num, col_num = nums
    return '<pb n="{}"><cb n="{}">'.format(page_num, col_num)

def generate_footer():
    return '</pb></cb>'

def wrap_line_with_lb(line_text):
    return '<lb>' + line_text + '</lb>'

def generate_xml(doc):
    breaks = find_breaks(doc)
    lines = []

    # take care of header
    assert 0 in breaks
    lines.append(generate_header(breaks[0]))

    for i, line in enumerate(doc):
        if line.page_no == "0" or line.line_no == "0":
            logging.debug("Skipping because page_no or line_no is 0: {}".format(repr(line)))
            continue

        line_text = line.text
        line_text = wrap_line_with_lb(line_text)

    lines.append(generate_footer())

    return '\n'.join(lines)



# Main --------------------------------------------------------------------------
def main():
    file_strings, file_order = read_input_files()
    parsed_docs = apply_functions([html_parse,
                                   html_extract_table,
                                   html_parse_rows],
                                  file_strings)
    xml_strs = apply_functions([generate_xml], parsed_docs)

    write_output_files(xml_strs, file_order)


if __name__ == "__main__":
    main()
