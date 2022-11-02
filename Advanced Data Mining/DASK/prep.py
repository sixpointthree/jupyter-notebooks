### Taken from the DASK tutorial
# merged with accounts.py and soruces.py

import time
import sys
import argparse
import os
from glob import glob
import json
import gzip
import tarfile
import urllib.request

import numpy as np
import pandas as pd

DATASETS = ["accounts", "flights", "all"]
here = os.path.dirname(__file__)
data_dir = os.path.abspath(os.path.join(here, 'data'))

flights_url = "https://storage.googleapis.com/dask-tutorial-data/nycflights.tar.gz"


def parse_args(args=None):
    parser = argparse.ArgumentParser(description='Downloads, generates and prepares data for the Dask tutorial.')
    parser.add_argument('--no-ssl-verify', dest='no_ssl_verify', action='store_true',
                        default=False, help='Disables SSL verification.')
    parser.add_argument("--small", action="store_true", default=None,
                        help="Whether to use smaller example datasets. Checks DASK_TUTORIAL_SMALL environment variable if not specified.")
    parser.add_argument("-d", "--dataset", choices=DATASETS, help="Datasets to generate.", default="all")

    return parser.parse_args(args)



if not os.path.exists(data_dir):
    raise OSError('data/ directory not found, aborting data preparation. ' \
                  'Restore it with "git checkout data" from the base ' \
                  'directory.')


def flights(small=None):
    start = time.time()
    flights_raw = os.path.join(data_dir, 'nycflights.tar.gz')
    flightdir = os.path.join(data_dir, 'nycflights')
    jsondir = os.path.join(data_dir, 'flightjson')
    if small is None:
        small = bool(os.environ.get("DASK_TUTORIAL_SMALL", False))

    if small:
        N = 500
    else:
        N = 10_000

    if not os.path.exists(flights_raw):
        print("- Downloading NYC Flights dataset... ", end='', flush=True)
        url = flights_url
        urllib.request.urlretrieve(url, flights_raw)
        print("done", flush=True)

    if not os.path.exists(flightdir):
        print("- Extracting flight data... ", end='', flush=True)
        tar_path = os.path.join(data_dir, 'nycflights.tar.gz')
        with tarfile.open(tar_path, mode='r:gz') as flights:
            flights.extractall('data/')

        if small:
            for path in glob(os.path.join(data_dir, "nycflights", "*.csv")):
                with open(path, 'r') as f:
                    lines = f.readlines()[:1000]

                with open(path, 'w') as f:
                    f.writelines(lines)

        print("done", flush=True)

    if not os.path.exists(jsondir):
        print("- Creating json data... ", end='', flush=True)
        os.mkdir(jsondir)
        for path in glob(os.path.join(data_dir, 'nycflights', '*.csv')):
            prefix = os.path.splitext(os.path.basename(path))[0]
            df = pd.read_csv(path, nrows=N)
            df.to_json(os.path.join(data_dir, 'flightjson', prefix + '.json'),
                       orient='records', lines=True)
        print("done", flush=True)
    else:
        return

    end = time.time()
    print("** Created flights dataset! in {:0.2f}s**".format(end - start))

##
## ACOUNT STUFF

names = ['Alice', 'Bob', 'Charlie', 'Dan', 'Edith', 'Frank', 'George',
'Hannah', 'Ingrid', 'Jerry', 'Kevin', 'Laura', 'Michael', 'Norbert', 'Oliver',
'Patricia', 'Quinn', 'Ray', 'Sarah', 'Tim', 'Ursula', 'Victor', 'Wendy',
'Xavier', 'Yvonne', 'Zelda']

k = 100


def account_params(k):
    ids = np.arange(k, dtype=int)
    names2 = np.random.choice(names, size=k, replace=True)
    wealth_mag = np.random.exponential(100, size=k)
    wealth_trend = np.random.normal(10, 10, size=k)
    freq = np.random.exponential(size=k)
    freq /= freq.sum()

    return ids, names2, wealth_mag, wealth_trend, freq

def account_entries(n, ids, names, wealth_mag, wealth_trend, freq):
    indices = np.random.choice(ids, size=n, replace=True, p=freq)
    amounts = ((np.random.normal(size=n) + wealth_trend[indices])
                                         * wealth_mag[indices])

    return pd.DataFrame({'id': indices,
                         'names': names[indices],
                         'amount': amounts.astype('i4')},
                         columns=['id', 'names', 'amount'])


def accounts(n, k):
    ids, names, wealth_mag, wealth_trend, freq = account_params(k)
    df = account_entries(n, ids, names, wealth_mag, wealth_trend, freq)
    return df


def json_entries(n, *args):
    df = account_entries(n, *args)
    g = df.groupby(df.id).groups

    data = []
    for k in g:
        sub = df.iloc[g[k]]
        d = dict(id=int(k), name=sub['names'].iloc[0],
                transactions=[{'transaction-id': int(i), 'amount': int(a)}
                              for i, a in list(zip(sub.index, sub.amount))])
        data.append(d)

    return data

def accounts_json(n, k):
    args = account_params(k)
    return json_entries(n, *args)


def accounts_csvs(small=None):
    t0 = time.time()
    if small is None:
        small = bool(os.environ.get("DASK_TUTORIAL_SMALL", False))

    if small:
        num_files, n, k = 3, 10000, 100
    else:
        num_files, n, k = 3, 1000000, 500

    fn = os.path.join(data_dir, 'accounts.%d.csv' % (num_files - 1))

    if os.path.exists(fn):
        return

    args = account_params(k)

    for i in range(num_files):
        df = account_entries(n, *args)
        df.to_csv(os.path.join(data_dir, 'accounts.%d.csv' % i),
                  index=False)

    t1 = time.time()
    print("Created CSV acccouts in {:0.2f}s".format(t1 - t0))


def accounts_json(small=None):
    t0 = time.time()
    if small is None:
        small = bool(os.environ.get("DASK_TUTORIAL_SMALL", False))

    if small:
        num_files, n, k = 50, 10000, 250
    else:
        num_files, n, k = 50, 100000, 500
    fn = os.path.join(data_dir, 'accounts.%02d.json.gz' % (num_files - 1))
    if os.path.exists(fn):
        return

    args = account_params(k)

    for i in range(num_files):
        seq = json_entries(n, *args)
        fn = os.path.join(data_dir, 'accounts.%02d.json.gz' % i)
        with gzip.open(fn, 'wb') as f:
            f.write(os.linesep.join(map(json.dumps, seq)).encode())

    t1 = time.time()
    print("Created JSON acccouts in {:0.2f}s".format(t1 - t0))


def main(args=None):
    args = parse_args(args)

    if (args.no_ssl_verify):
        print("- Disabling SSL Verification... ", end='', flush=True)
        import ssl
        ssl._create_default_https_context = ssl._create_unverified_context
        print("done", flush=True)
    if args.dataset == "accounts" or args.dataset == "all":
        accounts_csvs(args.small)
        accounts_json(args.small)
    if args.dataset == "flights" or args.dataset == "all":
        flights(args.small)


if __name__ == '__main__':
    sys.exit(main())
