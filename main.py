import os as _os
from io import BytesIO as _BytesIO
from zipfile import ZipFile as _ZipFile
from argparse import ArgumentParser as _ArgumentParser
from tempfile import gettempdir as _gettempdir
from urllib import request as _url_request
import defs as _defs
import mplfinance as _mpf


# url given in test assignment
data_file_url = "https://perp-analysis.s3.amazonaws.com/interview/prices.csv.zip"

# directory to download and extract files
data_dir = f"{_gettempdir()}/candles_for_amacryteam"


def __csv_filename(url: str = data_file_url) -> str:
    """Extract filename from given url to *.csv.zip"""
    return _os.path.splitext(_os.path.basename(url))[0]


def download_csv_file(url: str = data_file_url) -> str:
    """
    Download and extract csv file

    Args:
        url (str): http link to zipped csv file

    Returns:
        path to extracted csv file
    """

    # create data directory in system temp dir if possible
    try:
        _os.makedirs(data_dir, exist_ok=True)
    except FileExistsError:
        # makedirs will fail if non-directory with given path exists
        print(f"Error! Failed to create \"{data_dir}\"")

    # get csv filename from url
    csv_filename = __csv_filename(url)

    # download csv file to data directory if not present
    if csv_filename not in _os.listdir(data_dir):
        content = _url_request.urlopen(url).read()
        # wrap content (zipped data) with BytesIO to imitate 'real' file
        zip_file = _ZipFile(_BytesIO(content))
        zip_file.extractall(data_dir)

    return f"{data_dir}/{csv_filename}"


if __name__ == "__main__":
    parser = _ArgumentParser("Test assignment for AmaCryTeam vacancy")
    impl_group = parser.add_mutually_exclusive_group()
    impl_group.add_argument("--numpy", action="store_true",
                            help="choose numpy implementation (default)")
    impl_group.add_argument("--pandas", action="store_true",
                            help="choose pandas implementation")
    parser.add_argument("--period", choices=_defs.Period.marks,
                        default="5m", help="set candlesticks period "
                                           "(default: 5m)")
    parser.add_argument("--length", metavar="value", type=int, default=14,
                        help="set EMA length (default: 14)")
    parser.add_argument("--csv", metavar="filename", type=str,
                        help="csv file to aggregate. If no file given, the "
                             "default one will be downloaded automatically")
    parser.add_argument("--style", choices=_mpf.available_styles(),
                        default="binance", help="choose plot style "
                                                "(default: binance)")
    parser.add_argument("--savefig", metavar="filename", type=str,
                        nargs='?', const='',
                        help="set path to plot chart output filename. "
                             "If no filename specified, saves the figure to "
                             "data directory in system temp")
    parser.add_argument("--test", action="store_true", help="run unit tests")
    args = parser.parse_args()

    # choose numpy implementation if no argument set
    if not args.numpy and not args.pandas:
        args.numpy = True

    # use csv file provided as argument or download the file mentioned in
    # test assignment. Show error if download/unzip failed or invalid file
    # provided
    if args.csv is None:
        # skip if file already in data dir
        path_to_downloaded_csv = f"{data_dir}/{__csv_filename(data_file_url)}"
        if _os.path.isfile(path_to_downloaded_csv):
            print(f"CSV file found in data directory. Processing...")
            args.csv = path_to_downloaded_csv

        else:
            # try to download and extract csv file
            try:
                print(f"Trying to download data file from "
                      f"\"{data_file_url}\". Please wait...")
                args.csv = download_csv_file()
            except:
                print(f"Error: failed to download data file or unzip it")
                exit(1)

            # check if downloaded file exist
            if _os.path.isfile(args.csv):
                print(f"Success! CSV file available at \"{args.csv}\"")
            else:
                print("Something went wrong...")
                exit(1)
    elif not _os.path.isfile(args.csv):
        print(f"Error: CSV file must be provided, "
              f"\"{args.csv}\" is not a file")
        exit(1)

    # set default path to plot figure if requested
    if args.savefig == '':
        args.savefig = f"{_os.path.splitext(args.csv)[0]}.png"

    # depending on selected implementation, import processing function and call
    # it with provided filename, candlesticks period and EMA length
    if args.pandas and not args.numpy:
        from pandas_implementation import process_csv_file
    elif args.numpy and not args.pandas:
        from numpy_implementation import process_csv_file
    else:
        print("Error! Invalid implementation provided")
        exit(1)

    # process csv file to get DataFrame with OHLC and EMA data indexed by
    # given periods timestamps
    df = process_csv_file(args.csv, args.period, args.length)

    # prepare EMA line plot
    ema_line = _mpf.make_addplot(df[[_defs.EMA]], type="line")

    # plot candlesticks and with EMA line
    _mpf.plot(df[[_defs.OPEN, _defs.HIGH, _defs.LOW, _defs.CLOSE]],
              type="candlestick", style=args.style, addplot=ema_line,
              title=f"{_os.path.basename(args.csv)}: "
                    f"{args.period} OHLC and EMA{args.length}",
              savefig=args.savefig)
