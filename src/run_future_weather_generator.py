#! /usr/bin/env python3.11
import logging
import subprocess
import time
from argparse import ArgumentParser
from pathlib import Path

# Future Weather Generator parameters, for version 1.4.0
# (see https://future-weather-generator.adai.pt/documentation/)
GCM_MODELS = [
    "BCC_CSM2_MR",
    "CAS_ESM2_0",
    "CMCC_ESM2",
    "CNRM_CM6_1_HR",
    "CNRM_ESM2_1",
    "EC_Earth3",
    "EC_Earth3_Veg",
    "MIROC_ES2H",
    "MIROC6",
    "MRI_ESM2_0",
    "UKESM1_0_LL",
]
ENSEMBLE = 1
MONTH_TRANSITION_HOURS = 72
MULTITHREAD_COMPUTATION = "true"
INTERPOLATION_METHOD_ID = 0     # bilinear interpolation
DO_LIMIT_VARIABLES = "true"
SOLAR_HOUR_ADJUSTMENT = 2       # by day
DIFFUSE_IRRADIATION_MODEL = 1   # Engerer (2015)


def list_epw_files(directory: Path) -> list[Path]:
    """
    Returns a list of all EPW files found in the directory.

    Args:
        directory (Path): Directory where to look for EPW files.

    Raises:
        ValueError: If there are no EPW files in the directory.

    Returns:
        list[Path]: List of Path objects for each EPW file found in the directory.
    """
    epw_file_collection = [
        file for file in directory.iterdir() if file.suffix.casefold() == ".epw".casefold()]
    if not epw_file_collection:
        logging.warning("No EPW files found in the selected path")
        raise ValueError("Selected path contains no EPW files.")
    logging.info(
        f"Found {len(epw_file_collection)} EPW file(s) in the selected path "
        f"({directory.resolve()})")
    return epw_file_collection


def main(args):
    logging.basicConfig(
        format="%(asctime)s    %(levelname)-8.8s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)

    path_to_jar = Path(args.jar_path)
    path_to_epw_input = Path(args.epw_path)
    epw_file_collection = list_epw_files(path_to_epw_input)
    output_path = Path(path_to_epw_input, "output")

    if len(epw_file_collection) >= 5 and not args.accept_prompts:
        logging.warning(
            f"This operation might take a few minutes to complete for each file, so your "
            f"wait time for everything to be completed will be significant. Wait times can "
            f"reach {round(340*len(epw_file_collection)/60)}min, but might be considerably "
            f"shorter depending on your hardware")
        response = input("Continue? (Y/n)\n> ")
        if response.casefold() in {x.casefold() for x in {"no", "n"}}:
            logging.info("Operation cancelled by the user")
            return

    for index, epw_file in enumerate(sorted(epw_file_collection)):
        logging.info(
            f"({index+1}/{len(epw_file_collection)}) Processing file {epw_file.name}")
        command = [
            "java",
            "-cp",
            str(path_to_jar.resolve()),
            "futureweathergenerator.Morph",
            str(epw_file.resolve()),
            ",".join(GCM_MODELS),
            str(ENSEMBLE),
            str(MONTH_TRANSITION_HOURS),
            str(output_path.resolve()) + "/",
            MULTITHREAD_COMPUTATION,
            str(INTERPOLATION_METHOD_ID),
            DO_LIMIT_VARIABLES,
            str(SOLAR_HOUR_ADJUSTMENT),
            str(DIFFUSE_IRRADIATION_MODEL)
        ]
        logging.debug(
            f"Executing FutureWeatherGenerator using the following command:\n"
            f"{' '.join(command)}")

        start_time = time.perf_counter()
        result = subprocess.run(command, capture_output=True, text=True)
        logging.info(
            f"Operation completed in {round(time.perf_counter() - start_time)}s "
            f"with return code {result.returncode}")
        if result.stderr:
            logging.error(
                f"({index+1}/{len(epw_file_collection)}) Something went wrong while "
                f"processing '{epw_file.name}', see details:\n{result.stderr}")
        else:
            logging.info(
                f"({index+1}/{len(epw_file_collection)}) Successfully processed file "
                f"'{epw_file.name}'")


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "jar_path", type=str, metavar="path/to/fwg.jar",
        help="path to a Future Weather Generator jar file used to generate new EPW files")
    parser.add_argument(
        "epw_path", type=str, metavar="path/to/epw",
        help="path to the directory containing the EPW files to be used")
    parser.add_argument(
        "-q", "--quiet", action="store_true",
        help="turn on quiet mode, which hides log entries of levels lower than WARNING")
    parser.add_argument(
        "-y", action="store_true", dest="accept_prompts",
        help="consider 'yes' as input for any user prompts")
    main(parser.parse_args())
