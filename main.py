""""""

import re
import os
import logging
from unicodedata import category
from bs4 import BeautifulSoup

IN_DIR = "in/"
OUT_DIR = "out/"
LACUNA_CHARS = "▩□."
SUP = "↑"
SUB = "↓"

# File i/o ----------------------------------------------------------------------
def read_file(in_dir, name):
    with open(os.path.join(in_dir, name), 'r',encoding="utf8") as f:
        return f.read()

def read_input_files(in_dir=IN_DIR, ext=".html"):
    file_order = os.listdir(in_dir)
    return ([read_file(in_dir, name)
            for name in file_order
            if name.endswith(ext)],
            file_order)

def write_file(out_dir, name, lines):
    with open(os.path.join(out_dir, name), 'w', encoding="utf8", newline="\n") as f:
        return f.write(lines)

def write_output_files(docs, file_order, out_dir=OUT_DIR, orig_ext=".html"):
    for name, lines in zip(file_order, docs):
        write_file(out_dir, name.replace(orig_ext, ".sgml"), lines)

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
    lacuna_pattern = re.compile(r"(?:[" + LACUNA_CHARS + r"](?:\s+)?){3,}|(?:▩(?:\s+)?)+")
    def __init__(self, page_and_line_no, text):
        ed_page, ed_line = self._clean_page_and_line(page_and_line_no)
        self.ed_page = ed_page
        self.ed_line = ed_line
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
        text = self._bracket_lacunae(text)
        text = self._space_punctuation(text)
        return text

    def _bracket_lacunae(self, text):
        lacunae = list(ManuscriptLine.lacuna_pattern.finditer(text))

        if len(lacunae) == 0:
            return text
        if text == "□□□ Ⲁ □□□ Ⲱ̅ □□□□ Ⲓ̅Ⲥ̅ □✠□ Ⲭ̅Ⲥ̅":
            return text

        for match in reversed(lacunae):
            start, end = match.span()
            if start != 0 and text[start - 1] == "[" \
               and end != len(text) and text[end + 1] == "]":
                text = (text[:start] + ("."*(end - start)) + text[end:])
            text = (text[:start] + "[" + ("."*(end - start)) + "]" + text[end:])

        return text

    def _space_punctuation(self, text):
        for i, c in reversed(list(enumerate(text))):
            if (i != 0 and category(c)[0] == "P"
                and c not in ["[", "]", "-", "‐", "|", "{", "}", "(", ")", "?"]
                and ((category(text[i-1])[0] in ["L", "M"] and ord(text[i-1][0]) >= 128)
                     or text[i-1][0] in [")"])):
                text = text[:i] + " " + text[i:]
        return text


    def __repr__(self):
        return ("<ManuscriptLine; ed_page={}, line_no={}, text='{}', footnote='{}'>"
                .format(self.ed_page,
                        self.ed_line,
                        self.text,
                        (' (' + self.footnote + ')') if self.footnote else ''))

    def __str__(self):
        return "<Line ({}/{}): '{}'{}>".format(
            self.ed_page, self.ed_line, self.text,
            (' (' + self.footnote + ')') if self.footnote else '')

def filter_parsed_docs(docs):
    return ([[line for line in doc
              if line.ed_page != "0" and line.ed_line != "0"]
             for doc in docs])

# XML generation ----------------------------------------------------------------
# note: *? is the non-greedy version of * in python regex
FOL_PATTERN = re.compile(r"(\[fol.*?\])|(\|fol.*?\|)", re.IGNORECASE)
PAGE_AND_COL_PATTERN = \
    re.compile(r"[\[|]fol\.?(.*?)col\.?\s+([^\s]+?)(?:\s+.*?)?[\]|]", re.IGNORECASE)
PAGE_PATTERN = re.compile(r"[\[|]fol\.?(.*?)[\]|]", re.IGNORECASE)

def remove_dash_or_add_space(text):
    text = text.strip()
    if len(text) == 0:
        return text
    if text[-1] in ["‐", "-"]:
        return text[:-1]
    else:
        return text + " "

def scan_for_pipe(doc, i):
    lower_bound = max(i - 1, 0)
    upper_bound = min(i + 2, len(doc))
    # ensure there's at most only one pipe in the range
    assert "".join(map(lambda x: getattr(x, "text"),
                       doc[lower_bound:upper_bound])).count("|") <= 1

    for j in range(lower_bound, upper_bound):
        text = doc[j].text
        pipe_index = text.find("|")
        if pipe_index > -1:
            return (j, pipe_index)

    return (i, None)

PAGE_NUM_PATTERN = re.compile(r"(\d+)([ab])\s.*")
def decr_page_num(page_num):
    match = PAGE_NUM_PATTERN.fullmatch(page_num)
    assert match
    number, alpha = match.groups()
    if alpha == "a":
        return str(int(number) - 1) + "b"
    else:
        return number + "a"

def guess_first_break_info(breaks):
    second_break = breaks[sorted(breaks.keys())[0]]
    second_col_num = second_break["col_num"]
    assert second_col_num in ["1", "2", None]

    first_break = second_break.copy()
    if second_col_num == "2":
        first_break["col_num"] = "1"
    else:
        first_break["page_num"] = decr_page_num(first_break["page_num"])
        first_break["col_num"] = None if second_col_num is None else "2"
    return first_break

def find_breaks(doc):
    breaks = {}

    for i, line in enumerate(doc):
        text = line.text
        match = FOL_PATTERN.search(text)
        if match is None:
            continue
        # impure!!! but convenient: remove it from the text
        line.text = text.replace(match.groups()[0] or match.groups()[1], "")

        s = match.groups()[0] or match.groups()[1]

        match = PAGE_AND_COL_PATTERN.search(s)
        if match is None:
            match = PAGE_PATTERN.search(s)
            if match is None:
                continue
        groups = match.groups()
        page_num = groups[0].strip()
        page_num = re.sub(r'\(.*\)','',page_num).strip()
        col_num = groups[1].strip() if len(groups) > 1 else None

        break_line_num, _ = scan_for_pipe(doc, i)
        # don't use i because the pipe could be above or below the line
        # on which we found the Fol. info
        breaks[break_line_num] = {"page_num": page_num,
                                  "col_num": col_num}

    if 0 not in breaks:
        breaks[0] = guess_first_break_info(breaks)

    return breaks

def insert_break(text, break_info, last_page):
    assert text.count("|") <= 1
    page = break_info["page_num"]
    col = break_info["col_num"]
    offset = text.find("|")

    accum = []
    if col is not None:
        accum.append('\n</cb>')
    if page != last_page:
        accum.append('</pb>\n<pb xml:id="{}">'.format(page))
    if col is not None:
        accum.append('<cb n="{}">'.format(col))

    break_text = "\n".join(accum)
    if offset > -1:
        return text[:offset] + break_text + text[offset + 1:]
    return break_text + text

def generate_header(break_info):
    if break_info["col_num"]:
        return '<pb xml:id="{}">\n<cb n="{}">'.format(break_info["page_num"],
                                               break_info["col_num"])
    else:
        return '<pb xml:id="{}">'.format(break_info["page_num"])

def generate_footer(has_cols):
    if has_cols:
        return '</cb>\n</pb>'
    else:
        return '</pb>'

def find_symbols(docs):
    lines = sum([[line.text for line in doc] for doc in docs], [])
    s = "".join(lines)

    symbols = []
    for c in s:
        cat = category(c)
        if (cat[0] in ["S", "C"] or c in ["·", "—", "—"]) \
           and c not in symbols \
           and c not in LACUNA_CHARS:
            symbols.append(c)

    return symbols

def wrap_line_if_decorative(orig_text, xml_text, symbols):
    if len(orig_text) == 0:
        return xml_text
    masked_dec = [1 if c in symbols else 0 for c in orig_text]
    masked_let = [1 if category(c)[0] == "L" else 0 for c in orig_text]
    if sum(masked_dec)/len(masked_dec) > .2 and not sum(masked_let)/len(masked_let) > .2:
        close_index = xml_text.find("</")
        open_index = xml_text.rfind(">", 0, close_index)
        # we have the text within a binary tag
        if open_index > -1 and close_index > -1:
            open_index += 1
            return (xml_text[:open_index]
                    + '<hi rend="decorative">'
                    + xml_text[open_index:close_index]
                    + '</hi>'
                    + xml_text[close_index:])
        # we have an <ed_line/>
        elif close_index == -1 and open_index != -1:
            assert "<ed_line" in xml_text
            open_index += 1
            return (xml_text[:open_index]
                    + '<hi rend="decorative">'
                    + xml_text[open_index:]
                    + '</hi>')
        # no tag
        else:
            assert open_index == -1 and close_index == -1
            return '<hi rend="decorative">' + xml_text + '</hi>'
    return xml_text

# For <sup> and <sub>
def wrap_consecutive_spans(xml_text, char, eltname):
    mask = [1 if c == char else 0 for c in xml_text]
    if sum(mask) == 0:
        return xml_text

    open_tag = "<{}>".format(eltname)
    close_tag = "</{}>".format(eltname)
    for i in range(len(mask), 0, -1):
        if mask[i - 1] == 1:
            mask.pop(i)

    xml_text = xml_text.replace(char, "")
    end = None
    for i, bit in reversed(list(enumerate(['START'] + mask))):
        if bit == 1 and not end:
            end = i
        elif end and bit == 0:
            xml_text = (xml_text[:i]
                        + open_tag
                        + xml_text[i:end]
                        + close_tag
                        + xml_text[end:])
            end = None

    return xml_text

def insert_ed_page_break(xml_text, orig_text, ed_page):
    offset = xml_text.rfind(orig_text)
    offset = offset if offset > -1 else 0
    elt = '<ed_page n="{}"/>\n'.format(ed_page)
    return xml_text[:offset] + elt + xml_text[offset:]

def insert_ed_line_break(xml_text, orig_text, i):
    offset = xml_text.rfind(orig_text)
    elt = '<ed_line n="{}"/>'.format(i)
    return xml_text[:offset] + elt + xml_text[offset:]

def sic_to_note(xml_text):
    i = xml_text.find("(sic)")
    if i == -1:
        return xml_text

    while i != -1:
        l = 5
        if xml_text[i-1] == " ":
            l = 6
            i -= 1
        xml_text = xml_text[:i] + xml_text[i+l:]

        start = xml_text.rfind(" ", 0, i) + 1
        # Prevent pushing the sic note into XML tags
        last_angle = xml_text.rfind(">", 0, i) + 1
        if last_angle > start:
            start = last_angle
        assert start > 0
        xml_text = (xml_text[:start]
                    + '<note note="sic">'
                    + xml_text[start:i]
                    + '</note>'
                    + xml_text[i:])

        i = xml_text.find("(sic)")

    return xml_text

def square_to_ekthetic(xml_text):
    i = xml_text.find("□")
    if i == -1:
        return xml_text
    # Protect double squares, which are decorations
    xml_text = xml_text.replace("□□","⸋⸋")
    # Transform other squares to ekthetic annotations
    xml_text = re.sub(r'□\s*([^<>\s]+)',r'<hi rend="ekthetic">\1</hi>',xml_text)

    return xml_text

def remove_english_comments(xml_text):
    # Remove things like '[Three leaves wanting]'
    xml_text = re.sub(r'\[([A-Za-z ]+)\]',r'<note note="\1"></note>',xml_text)
    # Remove left-over pipes
    xml_text = re.sub(r'\s*\|\s*',' ',xml_text)
    # Superscript glyph
    xml_text = xml_text.replace("¹","")
    # Remaining lines with Fol. (only one instance, in Theophilus)
    xml_text = re.sub(r'Fol\.[^\n]+','',xml_text)
    # Decorative angle brackets (three instances)
    xml_text = xml_text.replace(" >"," ❭")
    # Single spaces
    xml_text = re.sub(r' +',' ',xml_text)
    return xml_text

def generate_xml(doc, decorative_symbols):
    breaks = find_breaks(doc)
    lines = []

    # take care of header
    assert 0 in breaks
    first_break = breaks[0]
    lines.append(generate_header(first_break))
    last_page = breaks[0]["page_num"]
    del breaks[0]
    last_ed_page = None

    for i, line in enumerate(doc):
        orig_text = remove_dash_or_add_space(line.text)
        xml_text = orig_text

        if line.ed_page != last_ed_page:
            xml_text = insert_ed_page_break(xml_text, orig_text, line.ed_page)
            last_ed_page = line.ed_page

        xml_text = insert_ed_line_break(xml_text, orig_text, line.ed_line)
        #xml_text = wrap_line_if_decorative(orig_text, xml_text, decorative_symbols)
        xml_text = wrap_consecutive_spans(xml_text, SUP, "sup")
        xml_text = wrap_consecutive_spans(xml_text, SUB, "sub")
        xml_text = square_to_ekthetic(xml_text)
        xml_text = sic_to_note(xml_text)
        xml_text = remove_english_comments(xml_text)

        if i in breaks:
            xml_text = insert_break(xml_text, breaks[i], last_page)
            last_page = breaks[i]["page_num"]

        lines.append(xml_text)

    lines.append(generate_footer(first_break["col_num"] is not None))

    return '\n'.join(lines)



# Main --------------------------------------------------------------------------
def main():
    file_strings, file_order = read_input_files()
    parsed_docs = apply_functions([html_parse,
                                   html_extract_table,
                                   html_parse_rows],
                                  file_strings)
    parsed_docs = filter_parsed_docs(parsed_docs)
    decorative_symbols = find_symbols(parsed_docs)
    xml_strs = [generate_xml(doc, decorative_symbols) for doc in parsed_docs]
    write_output_files(xml_strs, file_order)

if __name__ == "__main__":
    main()
