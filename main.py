"""Main module to run the project"""

import os
from sys import exit as sys_exit
from io import BytesIO
from zipfile import ZipFile
from argparse import ArgumentParser
from tempfile import gettempdir
from urllib import request as url_request
import mplfinance as mpf
from pytest import main as pytest_main
import defs
from numpy_implementation import process_csv_file


# url given in test assignment
DATA_FILE_URL = "https://perp-analysis.s3.amazonaws.com/interview/prices.csv.zip"

# directory to download and extract files
data_dir = f"{gettempdir()}/candles_and_ema"


def __csv_filename(url: str = DATA_FILE_URL) -> str:
    """Extract filename from given url to *.csv.zip"""
    return os.path.splitext(os.path.basename(url))[0]


def download_csv_file(url: str = DATA_FILE_URL) -> str:
    """
    Download and extract csv file

    Args:
        url (str): http link to zipped csv file

    Returns:
        path to extracted csv file
    """

    # create data directory in system temp dir if possible
    try:
        os.makedirs(data_dir, exist_ok=True)
    except FileExistsError:
        # makedirs will fail if non-directory with given path exists
        print(f"Error! Failed to create \"{data_dir}\"")

    # get csv filename from url
    csv_filename = __csv_filename(url)

    # download csv file to data directory if not present
    if csv_filename not in os.listdir(data_dir):
        with url_request.urlopen(url) as response:
            content = response.read()
            # wrap content (zipped data) with BytesIO to imitate 'real' file
            with BytesIO(content) as buffer:
                with ZipFile(buffer) as zip_file:
                    zip_file.extractall(data_dir)

    return f"{data_dir}/{csv_filename}"


if __name__ == "__main__":
    parser = ArgumentParser("Test assignment for AmaCryTeam vacancy")
    parser.add_argument("--period", choices=defs.Period.marks,
                        default="5m", help="set candlesticks period "
                                           "(default: 5m)")
    parser.add_argument("--length", metavar="value", type=int, default=14,
                        help="set EMA length (default: 14)")
    parser.add_argument("--csv", metavar="filename", type=str,
                        help="csv file to aggregate. If no file given, the "
                             "default one will be downloaded automatically")
    parser.add_argument("--style", choices=mpf.available_styles(),
                        default="binance", help="choose plot style "
                                                "(default: binance)")
    parser.add_argument("--savefig", metavar="filename", type=str,
                        nargs='?', const='',
                        help="set path to plot chart output filename. "
                             "If no filename specified, saves the figure to "
                             "data directory in system temp")
    parser.add_argument("--test", action="store_true", help="run unit tests")
    args = parser.parse_args()

    # run pytest if requested
    if args.test:
        sys_exit(pytest_main(["-v", "test.py"]))

    # choose numpy implementation if no argument set
    if not args.numpy and not args.pandas:
        args.numpy = True

    # use csv file provided as argument or download the file mentioned in
    # test assignment. Show error if download/unzip failed or invalid file
    # provided
    if args.csv is None:
        # skip if file already in data dir
        path_to_downloaded_csv = f"{data_dir}/{__csv_filename(DATA_FILE_URL)}"
        if os.path.isfile(path_to_downloaded_csv):
            print("CSV file found in data directory. Processing...")
            args.csv = path_to_downloaded_csv

        else:
            # try to download and extract csv file
            try:
                print(f"Trying to download data file from "
                      f"\"{DATA_FILE_URL}\". Please wait...")
                args.csv = download_csv_file()
            except:  # pylint: disable=W0702
                print("Error: failed to download data file or unzip it")
                sys_exit(1)

            # check if downloaded file exist
            if os.path.isfile(args.csv):
                print(f"Success! CSV file available at \"{args.csv}\"")
            else:
                print("Something went wrong...")
                sys_exit(1)
    elif not os.path.isfile(args.csv):
        print(f"Error: CSV file must be provided, "
              f"\"{args.csv}\" is not a file")
        sys_exit(1)

    # set default path to plot figure if requested
    if args.savefig == '':
        args.savefig = f"{os.path.splitext(args.csv)[0]}.png"

    # process csv file to get DataFrame with OHLC and EMA data indexed by
    # given periods timestamps
    df = process_csv_file(args.csv, args.period, args.length)

    # prepare EMA line plot
    ema_line = mpf.make_addplot(df[[defs.EMA]], type="line")

    # plot candlesticks and with EMA line
    config = {"type": "candlestick", "style": args.style, "addplot": ema_line,
              "title": f"{os.path.basename(args.csv)}: "
                       f"{args.period} OHLC and EMA{args.length}",
              "tight_layout": True}
    if args.savefig is not None:
        config["savefig"] = args.savefig

    mpf.plot(df[[defs.OPEN, defs.HIGH, defs.LOW, defs.CLOSE]], **config)
