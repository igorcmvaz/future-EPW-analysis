# Future EPW Analysis
A pipeline of processes aimed at providing future EPW files based on existing models from the literature.

## Setup
```bash
git clone git@github.com:igorcmvaz/future-EPW-analysis.git
cd future-EPW-analysis
python -m venv venv     # optional (but recommended) to create a virtual environment
python -m pip install -r requirements.txt
cd src
```

## Getting various EPW files from the web
```bash
python find_links_and_download.py -h
python find_links_and_download.py ../BR_epw.config.json --json-only
python find_links_and_download.py ../BR_epw.config.json -l 10
```
<!-- TODO -->

## Extracting ZIP files with EPW elements inside
```bash
python zip_to_epw.py -h
python zip_to_epw.py path/to/zips
```

## Executing the Future Weather Generator
Requires Java (JRE) to be installed
```bash
python run_future_weather_generator.py -h
python run_future_weather_generator.py path/to/FutureWeatherGenerator_v1.2.6.jar ../sample_input
```
<!-- TODO -->

## Compiling EPW files to Parquet
A script to process multiple [EPW files](https://climate.onebuilding.org/papers/EnergyPlus_Weather_File_Format.pdf) into a single [(Apache) Parquet file](https://parquet.apache.org/docs/file-format/), taking only the desired data columns and informational fields.

### How to use it as a standalone script
```bash
python merge_files_into_parquet.py -h
python merge_files_into_parquet.py ../sample_input --csv
```

### Confort Models
Calculated variables are introduced in the files based on the models from `pythermalcomfort`. For more information, visit [their documentation site](https://pythermalcomfort.readthedocs.io/en/latest/reference/pythermalcomfort.html#comfort-models). The models are included in the exported files in an 'opt-out' format, so that passing the `-s` or `--strict` option will prevent `pythermalcomfort` from being imported, skip computation of the models and exclude corresponding entries from the output files. The computation of such models was extracted to [separate file](src/computation.py).

**Note:** Bear in mind that merely importing `pythermalcomfort` comes with a significant overhead for the script, and the computation of the values for comfort models are executed in each iteration, also noticeably impacting overall performance.  For that reason, the imports are conditional and only executed if the models are in fact desired (no `--strict` option).

An extra option (`-l` or `--limit-utci`) is available and it is used to configure the flag of similar name in UTCI model, as detailed in the [corresponding documentation](https://pythermalcomfort.readthedocs.io/en/latest/reference/pythermalcomfort.html#universal-thermal-climate-index-utci) (check parameter `limit_inputs`). If this option is present, this flag is used when computing UTCI models and the **Wind Speed values** from EPW files are saturated using the lower/upper bounds from the model (as per documentation), to ensure they are within the working range. Default is to not limit the inputs and use extrapolation from the UTCI model itself (rather than saturating the values).

# Commits
When committing to this repository, following convention is advised:

* chore: regular maintenance unrelated to source code (dependencies, config, etc)
* docs: updates to any documentation
* feat: new features
* fix: bug fixes
* ref: refactored code (no new feature or bug fix)
* revert: reverts on previous commits
* test: updates to tests

For further reference on writing good commit messages, see [Conventional Commits](https://www.conventionalcommits.org).
