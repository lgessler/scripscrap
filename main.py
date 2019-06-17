"""Zuhhhh"""

from bs4 import BeautifulSoup
import os

IN_DIR = "in/"
OUT_DIR = "out/"


# File i/o ----------------------------------------------------------------------
def read_file(in_dir, name):
    with open(os.path.join(in_dir, name), 'r') as f:
        return f.read()

def read_input_files(in_dir=IN_DIR, ext=".html"):
    return [read_file(in_dir, name)
            for name in os.listdir(in_dir)
            if name.endswith(ext)]


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
        line = tds[0].text.strip()
        text = tds[1].text.strip()
        parsed_lines.append((line, text))
    return parsed_lines

# Misc --------------------------------------------------------------------------
def apply_functions(fs, data):
    accum = data
    for f in fs:
        accum = map(f, accum)
    return list(accum)

#class ManuscriptLine(object):
#    def __init__(self, )

# Main --------------------------------------------------------------------------
def main():
    file_strings = read_input_files()
    html_funcs = [html_parse,
                  html_extract_table,
                  html_parse_rows]
    parsed_html = apply_functions(html_funcs, file_strings)

    for line in parsed_html[0]:
        print(line)
    #file_strings = map(html_extract_table, file_strings)


if __name__ == "__main__":
    main()

