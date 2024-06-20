#! /usr/bin/env python3.11
import json
import logging
import re
from argparse import ArgumentParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from requests import Session, HTTPError


def download_file_in_chunks(
        session: Session, url: str, output_dir: str | Path,
        chunk_size: int | None = 500*1024) -> Path:
    """
    Downloads a file in chunks from a URL, saves it in the desired output directory
    and returns its path.

    Args:
        session (Session): Established session for multiple requests.
        url (str): URL from where to download the file.
        output_dir (str | Path): String or Path object corresponding to the output directory
            where the downloaded file will be saved.
        chunk_size (int | None, optional): Size, in bytes, of the chunks used to download
            the file. If None, the content is downloaded at once.
            Defaults to 500*1024 (500 kB).

    Returns:
        Path: Absolute, normalized path to the downloaded file (symlinks are resolved).
    """
    path_to_downloaded_file = Path(output_dir, urlparse(url).path.split("/")[-1])
    with session.get(url, stream=True) as response:
        response.raise_for_status()
        with open(path_to_downloaded_file, "wb") as file:
            for chunk in response.iter_content(chunk_size=chunk_size):
                file.write(chunk)
    return path_to_downloaded_file.resolve()


def find_links_by_suffix(session: Session, url: str, search_suffix: str) -> list[str]:
    """
    Finds all <a> tags that have the desired suffix in the HTML markup from the provided
    web page and returns their links as a list.

    Args:
        session (Session): Established session for multiple requests.
        url (str): URL where to search for the links.
        search_suffix (str): Desired suffix against which the links should match.

    Returns:
        list[str]: List of the links that contain the provided suffix found in the <a> tags
        in the web page.
    """
    response = session.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    links = []
    for link in soup.find_all("a", href=re.compile(
            fr"{re.escape(search_suffix)}$", flags=re.IGNORECASE)):
        links.append(link["href"])
    logging.info(
        f"Found {len(links)} link(s) in '{url}' matching the suffix '{search_suffix}'")
    return links


def find_links_and_download_files(
        session: Session, url: str, search_suffix: str, output_dir: str | Path,
        limit: int, start_at: int = 1) -> None:
    """
    Find all links in a web page that have a specific suffix, then proceeds to download the
    files from such links (in the order the links are present in the HTML markup), saving
    them in a specified output directory.

    Args:
        session (Session): Established session for multiple requests.
        url (str): URL where to search for the links.
        search_suffix (str): Desired suffix against which the links should match.
        output_dir (str | Path): String or Path object corresponding to the output directory
            where the downloaded file will be saved. If it doesn't exist, it is created.
        limit (int): Maximum number of files to download.
        start_at (int): From which link to start, considering link indices start at 1 in a
            list ordered by order of appearance in the HTML markdown. Defaults to 1.

    Raises:
        ValueError: If <start_at> is greater than the total amount of links found in the
        web page.
    """
    try:
        relative_download_links = find_links_by_suffix(session, url, search_suffix)
    except HTTPError as e:
        logging.exception(
            f"Could not extract the links from provided url ('{url}'). Details: {str(e)}")
        return

    if start_at > len(relative_download_links):
        raise ValueError(
            f"There are less available links (={len(relative_download_links)}) than "
            f"the desired start position (={start_at})")
    logging.info(
        f"Will download content from link(s) #{start_at} to "
        f"#{min(start_at+len(relative_download_links), start_at+limit-1)} (inclusive)")

    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    count = 0
    for index, relative_link in enumerate(relative_download_links):
        if index + 1 < start_at:
            logging.debug(f"Ignoring link #{index+1}")
            continue
        if index + 1 >= start_at + limit:
            logging.warning(f"Reached limit of {limit} downloaded file(s), exiting")
            break

        download_link = urljoin(url, relative_link)
        logging.info(
            f"({start_at+count}/{len(relative_download_links)}) Downloading from "
            f"'{download_link}'")
        count += 1
        try:
            download_file_in_chunks(session, download_link, output_path)
        except HTTPError as e:
            logging.exception(
                f"Something went wrong when attempting to download file from "
                f"'{download_link}'. Details: {str(e)}")


def load_json_conf(path_to_json: str | Path) -> list[dict[str, str]]:
    """
    Load a JSON configuration file containing details on URLs and corresponding search
    suffixes.

    Expected JSON format:
    {
        ...,
        "sources":
        [
            {
                "website_url": "",
                "search_suffix": ""
            },
            ...
        ]
    }

    Args:
        path_to_json (str | Path): Path to the JSON configuration file.

    Returns:
        list[dict[str, str]]: List of all source details found in the configuration file,
        with URL and corresponding search suffixes.
    """
    with open(path_to_json, "r") as file:
        config = json.load(file)
    return config.get("sources", [])


def main(args):
    logging.basicConfig(
        format="%(asctime)s    %(levelname)-8.8s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)

    output_path = Path(args.out_path)
    source_list = load_json_conf(args.path)
    if not source_list:
        logging.critical(f"No sources configured in '{args.path}', exiting")
        return

    if args.json_only:
        link_details = []
        with Session() as session:
            for source in source_list:
                link_details.append(
                    {
                        "url": source["website_url"],
                        "search_suffix": source["search_suffix"],
                        "download_links": [(i+1, link) for i, link in enumerate(
                            find_links_by_suffix(
                                session, source["website_url"], source["search_suffix"]))]
                    })
        output_json = Path("out.json")
        with open(output_json, "w") as file:
            json.dump(link_details, file, indent=2)
        logging.info(
            f"Details from {len(link_details)} source(s) were saved to "
            f"'{output_json.resolve()}'")
        return

    source_index = args.source_position - 1
    with Session() as session:
        try:
            find_links_and_download_files(
                session,
                source_list[source_index]["website_url"],
                source_list[source_index]["search_suffix"],
                output_path,
                limit=args.limit,
                start_at=args.start)
        except Exception as e:
            logging.exception(
                f"Could not complete processing of files with given parameters. "
                f"Details: {str(e)}")


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "path", type=str, metavar="path/to/config.json",
        help="path to a JSON config file used to detail source URLs and search suffixes")
    parser.add_argument(
        "-q", "--quiet", action="store_true",
        help="turn on quiet mode, which hides log entries of levels lower than WARNING")
    parser.add_argument(
        "-j", "--json-only", action="store_true", dest="json_only",
        help="prevents any download, only exports a JSON file with the source details and "
        "the links found, in the same order they would be downloaded")
    parser.add_argument(
        "-o", "--out-path", type=str, metavar="path/to/dir", dest="out_path",
        default="output", help="output directory where downloaded files will be saved. "
        "Defaults to 'output'")
    parser.add_argument(
        "-l", "--limit", type=int, default=10,
        help="maximum number of files to download from the links found in the source")
    parser.add_argument(
        "-s", "--start", type=int, default=1,
        help="from which link to start, considering link indices start at 1 in a list "
        "ordered by appearance in the HTML from the source. Defaults to 1")
    parser.add_argument(
        "-w", "--which-source", type=int, default=1, dest="source_position",
        help="from which source (in config file) to collect files, considering indices "
        "start at 1. Optional arguments are only related to the source selected here. "
        "Ignored if --json-only is passed. Defaults to 1")
    main(parser.parse_args())
