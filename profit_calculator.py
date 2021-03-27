#!/usr/bin/env python3

# Processes a csv file to analyze the cost basis. (Will be) configurable to use
# FIFO, LIFO, and other cost basis methods. (Will eventually) appends the
# profits to the relevant rows of the csv.  Assumes the format of the Coinbase
# spreadsheet.
#
# Known shortcomings:
#   - Only supports FIFO
#   - No support for transactions between currencies
#   - No support for Coinbase Earn or Rewards income

import argparse
import csv
import dateutil.parser
import datetime
from decimal import Decimal


def btc_to_satoshi(btc):
    return int(btc * Decimal(1.0e8))


vv = 0
queues = {}
total_profits = []
other_income = []

outputheader = """
Sales and Other Dispositions of Capital Assets
----------------------------------------------

   Description  |    Date    |    Date    |            |    Cost    |   Gains/   | Short or
   of Property  |  Acquired  |    Sold    |  Proceeds  |  (basis)   |   Losses   | Long term
----------------+------------+------------+------------+------------+------------+------------
"""

outfmt = """\
 {:<10f} {} | {:%Y-%m-%d} | {:%Y-%m-%d} | {:10.2f} | {:10.2f} | {:10.2f} | {}\t
"""


class TransactionRecord:
    def __init__(self,
                 asset,
                 quantity,
                 date_acquired,
                 date_sold,
                 sale_price,
                 acq_price):
        self.asset = asset
        self.quantity = quantity
        self.acq_date = date_acquired
        self.sell_date = date_sold
        self.proceeds = sale_price
        self.basis = acq_price
        self.gain = self.proceeds - self.basis

        # long-term gains are long-term if the asset is held for more than a
        # year.
        elapsed = (self.sell_date - self.acq_date)
        year = datetime.timedelta(weeks=52)
        self.islong = elapsed > year

    def getlong(self):
        if self.islong:
            return "long"
        else:
            return "short"


def on_buy(ts, asset, quantity, total):
    if vv >= 1:
        print("{} acquire  {:010.8f} {} for {:6.2f} USD [[{:9.5f}]]\n"
              .format(ts, quantity, asset, total, total/quantity))
    if asset not in queues:
        queues[asset] = []
    queues[asset.upper()].append((ts, quantity, total/quantity))


def on_sell(ts, asset, quantity, total):
    sell_date = ts

    if vv >= 1:
        print("{} dispose  {:010.8f} {} for {:6.2f} USD [[{:9.5f}]]"
              .format(ts, quantity, asset, total, total/quantity), end='')

    sell_value_per_qty = total/quantity

    gains = []
    while quantity > 0:
        acqtime = queues[asset][0][0]
        buy_value_per_qty = queues[asset][0][2]
        qty = 0

        if queues[asset][0][1] > quantity:
            qty = quantity
            queues[asset][0] = (queues[asset][0][0], queues[asset][0][1] - qty, queues[asset][0][2])
            quantity = 0
        else:
            qty = queues[asset][0][1]
            quantity -= qty
            queues[asset].pop(0)
        usd_basis = qty * buy_value_per_qty
        gains.append(TransactionRecord(asset,
                                       qty,
                                       acqtime,
                                       sell_date,
                                       (qty * sell_value_per_qty),
                                       usd_basis))
    return gains


def on_income(ts, asset, quantity, total):
    other_income.append((ts, asset, quantity, total))

    # Basis is value at acquisition, same as buy.
    on_buy(ts, asset, quantity, total)


def print_reports():
    if vv >= 2:
        print("=== GENERATING REPORTS ===")

    print(outputheader, end='')

    netgain = sum([x.gain for x in total_profits])
    for txn in total_profits:
        print(outfmt.format(txn.quantity,
                            txn.asset,
                            txn.acq_date,
                            txn.sell_date,
                            txn.proceeds,
                            txn.basis,
                            txn.gain,
                            txn.getlong()), end='')

    print("\n   net profits: ${:8.2f}".format(netgain))

    print("\n Other income: ")
    for income in other_income:
        print("Earned ${:10.2f} (as {} {}) on {}".format(income[3], income[2], income[1], income[0]))
    print("      -------------")
    print("Tot:   ${:10.2f}".format(sum([x[3] for x in other_income])))


def main(csv_filename):
    with open(csv_filename, newline='') as csvfile:
        txnreader = csv.reader(csvfile, delimiter=',', quotechar='"')
        for row in txnreader:
            if len(row) == 0:
                continue
            ts = row[0]
            try:
                timestamp = dateutil.parser.parse(ts)
            except ValueError:
                # skip it. It's some coinbase header nonsense.
                continue
            asset = row[2]
            txn_type = row[1]
            if txn_type.lower() == "buy":
                on_buy(timestamp, asset.upper(), Decimal(row[3]), Decimal(row[6]))
            elif txn_type.lower().startswith("receive"):
                on_buy(timestamp, asset.upper(), Decimal(row[3]), Decimal(row[3]) * Decimal(row[4]))
            elif (txn_type.lower().startswith("paid")
                  or txn_type.lower().startswith("send")):
                gains = on_sell(timestamp,
                                asset.upper(),
                                Decimal(row[3]),
                                Decimal(row[3]) * Decimal(row[4]))
                total_profits.extend(gains)
                if vv >= 1:
                    print('\n')
            elif txn_type.lower().startswith("sell"):
                gains = on_sell(timestamp,
                                asset.upper(),
                                Decimal(row[3]),
                                Decimal(row[6]))
                total_profits.extend(gains)
                if vv >= 1:
                    print('\n')
            elif (txn_type.lower().startswith("coinbase earn")
                  or txn_type.lower().startswith("rewards income")):
                on_income(timestamp,
                          asset.upper(),
                          Decimal(row[3]),
                          Decimal(row[3]) * Decimal(row[4]))
            else:
                print("IGNORING", txn_type)
        print_reports()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbosity", action="count", default=0)
    parser.add_argument("csv_file", help="File to process")
    args = parser.parse_args()
    vv = args.verbosity
    main(args.csv_file)
