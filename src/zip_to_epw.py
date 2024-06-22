#! /usr/bin/env python3.11
import logging
from argparse import ArgumentParser
from pathlib import Path
from zipfile import ZipFile, ZipInfo


def list_zip_files(directory: Path) -> list[Path]:
    """
    Returns a list of all ZIP files found in the directory.

    Args:
        directory (Path): Directory where to look for ZIP files.

    Raises:
        ValueError: If there are no ZIP files in the directory.

    Returns:
        list[Path]: List of Path objects for each ZIP file found in the directory.
    """
    zip_file_collection = [
        file for file in directory.iterdir() if file.suffix.casefold() == ".zip".casefold()]
    if not zip_file_collection:
        logging.warning("No ZIP files found in the selected path")
        raise ValueError("Selected path contains no ZIP files.")
    logging.info(
        f"Found {len(zip_file_collection)} ZIP file(s) in the selected path "
        f"({directory.resolve()})")
    return zip_file_collection


def zip_member_is_epw_file(member: ZipInfo) -> bool:
    """
    Evaluates if member has a filename corresponding to EPW file extension.

    Args:
        member (ZipInfo): ZipInfo member from ZipFile object.

    Returns:
        bool: True if extension matches EPW file extension, False otherwise.
    """
    return member.filename.casefold().endswith(".epw".casefold())


def main(args):
    logging.basicConfig(
        format="%(asctime)s    %(levelname)-8.8s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)

    path_to_zip_input = Path(args.zip_path)
    zip_file_collection = list_zip_files(path_to_zip_input)
    output_path = Path(path_to_zip_input, "epw")

    total_epw_count = 0
    for index, zip_path in enumerate(sorted(zip_file_collection)):
        logging.info(
            f"({index+1}/{len(zip_file_collection)}) Processing file '{zip_path.name}'")
        with ZipFile(zip_path, "r") as input_zip:
            compressed_epw_files = [member for member in filter(
                zip_member_is_epw_file, input_zip.infolist())]
            logging.info(
                f"Found {len(compressed_epw_files)} compressed EPW file(s) in "
                f"'{zip_path.name}'")
            for member in compressed_epw_files:
                input_zip.extract(member, path=output_path)
                total_epw_count += 1
                logging.info(f"Completed the extraction of '{member.filename}'")
    logging.info(
        f"Extracted {total_epw_count} EPW file(s) from ZIP file(s) in "
        f"'{path_to_zip_input.resolve()}' to directory '{output_path.resolve()}'")


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "zip_path", type=str, metavar="path/to/zip",
        help="path to the directory containing the ZIP files to be filtered and extracted")
    parser.add_argument(
        "-q", "--quiet", action="store_true",
        help="turn on quiet mode, which hides log entries of levels lower than WARNING")
    main(parser.parse_args())
