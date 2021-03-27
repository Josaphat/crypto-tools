#!/usr/bin/env python3

# Processes a csv file to analyze the cost basis. (Will be) configurable to use
# FIFO, LIFO, and other cost basis methods. (Will eventually) appends the
# profits to the relevant rows of the csv.  Assumes the format of the Coinbase
# spreadsheet.

import argparse
import csv
import dateutil.parser
import datetime
from decimal import Decimal


def btc_to_satoshi(btc):
    return int(btc * Decimal(1.0e8))


queue = []
total_profits = []

outputheader = """
Sales and Other Dispositions of Capital Assets
----------------------------------------------

   Description  |    Date    |    Date    |            |    Cost    |   Gains/   | Short or
   of Property  |  Acquired  |    Sold    |  Proceeds  |  (basis)   |   Losses   | Long term
----------------+------------+------------+------------+------------+------------+------------
"""

outfmt = """\
 {} | {:%Y-%m-%d} | {:%Y-%m-%d} | {:10.2f} | {:10.2f} | {:10.2f} | {}\t
"""


class TransactionRecord:
    def __init__(self,
                 description,
                 date_acquired,
                 date_sold,
                 sale_price,
                 acq_price):
        self.descr = description
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


def on_buy(ts, quantity, total):
    print("{} acquire  {:010.8f} BTC for {:6.2f} USD [[{:9.5f}]]\n"
          .format(ts, quantity, total, total/quantity))
    queue.append((ts, quantity, total/quantity))


def on_sell(ts, quantity, total):
    sell_date = ts

    print("{} dispose  {:010.8f} BTC for {:6.2f} USD [[{:9.5f}]]"
          .format(ts, quantity, total, total/quantity), end='')

    sell_value_per_qty = total/quantity

    gains = []
    while quantity > 0:
        acqtime = queue[0][0]
        buy_value_per_qty = queue[0][2]
        qty = 0

        if queue[0][1] > quantity:
            qty = quantity
            queue[0] = (queue[0][0], queue[0][1] - qty, queue[0][2])
            quantity = 0
        else:
            qty = queue[0][1]
            quantity -= qty
            queue.pop(0)
        usd_basis = qty * buy_value_per_qty
        gains.append(TransactionRecord(("{:10.8f} BTC".format(qty)),
                                       acqtime,
                                       sell_date,
                                       (qty * sell_value_per_qty),
                                       usd_basis))
    return gains


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
            if asset.upper() != "BTC":
                continue
            txn_type = row[1]
            if txn_type.lower() == "buy":
                on_buy(timestamp, Decimal(row[3]), Decimal(row[6]))
            elif txn_type.lower().startswith("receive"):
                on_buy(timestamp, Decimal(row[3]), Decimal(row[3]) * Decimal(row[4]))
            elif (txn_type.lower().startswith("paid")
                  or txn_type.lower().startswith("send")):
                gains = on_sell(timestamp,
                                Decimal(row[3]),
                                Decimal(row[3]) * Decimal(row[4]))
                total_profits.extend(gains)
                print('\n')
            elif txn_type.lower().startswith("sell"):
                gains = on_sell(timestamp,
                                Decimal(row[3]),
                                Decimal(row[6]))
                total_profits.extend(gains)
                print('\n')
            else:
                print("IGNORING", txn_type)
        print(outputheader, end='')

        netgain = sum([x.gain for x in total_profits])
        for txn in total_profits:
            print(outfmt.format(txn.descr,
                                txn.acq_date,
                                txn.sell_date,
                                txn.proceeds,
                                txn.basis,
                                txn.gain,
                                txn.getlong()), end='')

        print("\n   net profits: ${:8.2f}".format(netgain))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file")
    args = parser.parse_args()
    main(args.csv_file)
