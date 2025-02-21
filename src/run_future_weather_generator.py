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
URBAN_HEAT_ISLAND_EFFECT = [False, True]
BUFFER_AREA_TEMPERATURE_LEVELS = range(0, 6)
URBAN_DENSITIES = range(0, 5)


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


def _log_result(
        index: int, total_items: int, file_name: str, error: str | None = None) -> None:
    if error:
        logging.error(
            f"({index}/{total_items}) Something went wrong while processing '{file_name}', "
            f", see details:\n{error}")
    else:
        logging.info(
            f"({index}/{total_items}) Successfully processed file '{file_name}'")


def _config_urban_heat_island_effect(
        index: int,
        total_items: int,
        file_name: str,
        urban_heat_island_flag: bool,
        buffer_area_level: int,
        urban_density: int) -> list[str]:
    urban_heat_island_log = "ON" if urban_heat_island_flag else "OFF"
    log_string = (
        f"({index}/{total_items}) Processing file '{file_name}' with pre-processing of "
        f"urban heat island effect {urban_heat_island_log}")
    if urban_heat_island_flag:
        log_string += (
            f". Buffer Area Level: {buffer_area_level}, "
            f"Urban Density Level: {urban_density}")
    logging.info(log_string)

    return [
        str(urban_heat_island_flag).lower(),
        str(buffer_area_level),
        str(urban_density)
    ]


def main(args):
    log_level = logging.DEBUG
    if args.quiet == 1:
        log_level = logging.INFO
    elif args.quiet == 2:
        log_level = logging.WARNING
    elif args.quiet >= 3:
        log_level = logging.ERROR
    logging.basicConfig(
        format="%(asctime)s    %(levelname)-8.8s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=log_level,
    )

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

    buffer_area_levels = [0]
    urban_densities = [0]
    index = 1
    total_items = len(epw_file_collection)*(
        1 + len(BUFFER_AREA_TEMPERATURE_LEVELS)*len(URBAN_DENSITIES))
    for epw_file in sorted(epw_file_collection):
        for urban_heat_island_flag in URBAN_HEAT_ISLAND_EFFECT:
            if urban_heat_island_flag:
                buffer_area_levels = BUFFER_AREA_TEMPERATURE_LEVELS
                urban_densities = URBAN_DENSITIES
            for buffer_area_level in buffer_area_levels:
                for urban_density in urban_densities:
                    urban_heat_island_commands = _config_urban_heat_island_effect(
                        index, total_items, epw_file.name, urban_heat_island_flag,
                        buffer_area_level, urban_density)
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
                        str(DIFFUSE_IRRADIATION_MODEL),
                        ":".join(urban_heat_island_commands)
                    ]
                    logging.debug(
                        f"Executing FutureWeatherGenerator using the following command:\n"
                        f"{' '.join(command)}")

                    start_time = time.perf_counter()
                    result = subprocess.run(command, capture_output=True, text=True)
                    logging.info(
                        f"Operation completed in {round(time.perf_counter() - start_time)}s"
                        f" with return code {result.returncode}")
                    _log_result(index, total_items, epw_file.name, result.stderr)
                    index += 1
        buffer_area_levels = [0]
        urban_densities = [0]


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "jar_path", type=str, metavar="path/to/fwg.jar",
        help="path to a Future Weather Generator jar file used to generate new EPW files")
    parser.add_argument(
        "epw_path", type=str, metavar="path/to/epw",
        help="path to the directory containing the EPW files to be used")
    parser.add_argument(
        "-q", "--quiet", action="count", default=0,
        help="turn on quiet mode (cumulative), which hides log entries of levels lower "
        "than INFO/WARNING")
    parser.add_argument(
        "-y", action="store_true", dest="accept_prompts",
        help="consider 'yes' as input for any user prompts")
    main(parser.parse_args())
