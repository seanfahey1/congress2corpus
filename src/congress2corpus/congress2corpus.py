import argparse
import json
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

from PyPDF2 import PdfReader


def get_args():
    parser = argparse.ArgumentParser(
        description="""
        Extract and split Senate records from 3-column format .pdf files as distributed by govinfo.gov. 
        
        Text is extracted using PyPDF2, split by speaker, and normalized. Speaker party affiliation is determined using 
        open source .json files of historical and current Senators hosted on `theunitedstates.io`. There is an option 
        to pass these .json files in from disk if they are not available online.
        """
    )
    parser.add_argument(
        "-p",
        "--pdf",
        help="Path to PDF file(s). Multiple files can be input in one argument separated by spaces.",
        nargs="+",
        required=True,
    )
    parser.add_argument(
        "-his",
        "--historical",
        help="Path to Historical congress json data",
        required=False,
        default="https://theunitedstates.io/congress-legislators/legislators-historical.json",
    )
    parser.add_argument(
        "-cur",
        "--current",
        help="Path to Current congress json data",
        required=False,
        default="https://theunitedstates.io/congress-legislators/legislators-current.json",
    )
    parser.add_argument(
        "-o",
        "--outdir",
        help="Path to desired output directory.",
        required=True,
    )
    parser.add_argument(
        "-s",
        "--start",
        help="Start date for filtering Senator list - format YYYY-MM-DD",
        required=False,
        type=valid_date,
        default="2100-01-01",
    )
    parser.add_argument(
        "-e",
        "--end",
        help="End date for filtering Senator list - format YYYY-MM-DD",
        required=False,
        type=valid_date,
        default="1770-01-01",
    )

    args = vars(parser.parse_args())
    return args


def valid_date(s):
    """Checks if a string can be formatted as a date using format YYYY-MM-DD. Returns datetime formatted str."""
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        msg = "not a valid date: {0!r}".format(s)
        raise argparse.ArgumentTypeError(msg)


def is_path(s):
    """Determines if an input string is a POSIX path (True) or as HTTP path (False)"""
    if s.startswith("/"):
        return True
    elif "://" in s.split(".")[0]:
        return False
    elif "localhost" in s:
        return False
    elif len(s.split("/")[0].split(".")) > 1:
        return False
    elif len(s.split("/")[0].split(":")) > 1:
        return False
    else:
        return True


def get_congressperson_table(current, historical, start_filter, end_filter):
    """
    Extract Senator names and party affiliation from input json files. Excludes Senators outside of the date filter
    range.
    :param current: str path to retrieve/open json object
    :param historical: str path to retrieve/open json object
    :param start_filter: datetime object
    :param end_filter: datetime object
    :return:
        dict Dictionary of Senators with full names and party affiliation that served in the desired range.
        set Collection of political parties that have been seen in the desired date range.
    """
    if is_path(current):
        with open(Path(current), "r") as pth:
            cur_json = json.load(pth)
    else:
        with urllib.request.urlopen(current) as url:
            cur_json = json.load(url)

    if is_path(historical):
        with open(Path(historical), "r") as pth:
            his_json = json.load(pth)
    else:
        with urllib.request.urlopen(historical) as url:
            his_json = json.load(url)

    legislator_json = cur_json + his_json

    legislator_dict = {}
    parties = set()

    for legislator_data in legislator_json:
        full_name = legislator_data.get("name", {}).get("official_full", "NA").upper()
        last_name = legislator_data.get("name", {}).get("last").upper()
        terms = legislator_data.get("terms", [])

        for term in terms:
            start = datetime.strptime(term["start"], "%Y-%m-%d")
            end = datetime.strptime(term["end"], "%Y-%m-%d")
            party = term.get("party", "NA")

            if start < start_filter and end > end_filter:
                legislator_dict[last_name] = {"full_name": full_name, "party": party}
                parties.add(party)

    return legislator_dict, parties


def split_to_dicts(text):
    """

    :param text: str Text from pdf files
    :return:
        dict Dictionary of text spoken by each Senator (speaker:text)
    """
    regex_str = re.compile(
        r"\nMr\. ([A-Z]{2,})\.*|"  # Mr. XYZ at start of line
        + r"\nMs\. ([A-Z]{2,})\.*|"  # Ms.
        + r"\nMrs\. ([A-Z]{2,})\.*|"  # Mrs.
        + r"\n(The PRESIDING OFFICER )"  # Whoever is presiding at the time
    )

    speaker_blocks = []

    matches = regex_str.finditer(text)
    for match in matches:
        speaker = match.group(1)
        start = match.start()
        end = match.end()
        if speaker is not None:
            speaker_blocks.append([speaker, start, end])

    # add in end point from the previous block
    for i in range(1, len(speaker_blocks)):
        speaker_blocks[i - 1].append(speaker_blocks[i][1])

    # drop the last speaker because this rolls into the document end
    speaker_blocks.pop(-1)

    speaker_dict = dict()
    for block in speaker_blocks:
        if block[0] not in speaker_dict.keys():
            speaker_dict[block[0]] = ''
        speaker_dict[block[0]] += text[block[2]: block[3] + 1] + ' '

    return speaker_dict


def text_normalize(text):
    """Normalize text by removing special characters and converting to lowercase."""
    terms = {
        re.compile(r"\xad\n"): "",
        re.compile(r"\n"): " ",
        re.compile(
            r"[0-9]* CONGRESSIONAL RECORD-SENATE [A-Z][a-z]{2,} [0-9]{1,2}, [0-9]{4}"
        ): " ",
        re.compile(r"\\'"): "'",
        re.compile(r" {2,}"): " ",
    }
    for term, new_str in terms.items():
        text = term.sub(new_str, text)

    return text.lower()


def main():
    args = get_args()
    legislator_dict, all_parties = get_congressperson_table(
        args["current"],
        args["historical"],
        start_filter=args["start"],
        end_filter=args["end"],
    )

    full_texts = ""

    for file in args["pdf"]:
        reader = PdfReader(file)

        num_pages = len(reader.pages)
        full_texts += "\n".join(
            [reader.pages[i].extract_text() for i in range(num_pages)]
        )

    text_parts = split_to_dicts(full_texts)

    for speaker, text in text_parts.items():
        text_parts[speaker] = text_normalize(text)

    for party in all_parties:
        out_str = ""
        for speaker, text in text_parts.items():
            if speaker in legislator_dict.keys():
                if legislator_dict[speaker]["party"] == party:
                    out_str += text
        if out_str != "":
            with open(Path(args["outdir"]) / f"{party}_party_corpus.txt", 'w') as out_handler:
                out_handler.write(out_str)


if __name__ == "__main__":
    sys.exit(main())
