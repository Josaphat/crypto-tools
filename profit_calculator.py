#!/usr/bin/env python3

# Processes a csv file to analyze the cost basis. (Will be) configurable to use
# FIFO, LIFO, and other cost basis methods. (Will eventually) appends the
# profits to the relevant rows of the csv.  Assumes the format of the Coinbase
# spreadsheet.
#
# Known shortcomings:
#   - Only supports FIFO
#   - No support for transactions between currencies

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


def print_reports(year):
    if vv >= 2:
        print("=== GENERATING REPORTS ===")

    print(outputheader, end='')

    if year is not None:
        netgain = sum([x.gain for x in total_profits if x.sell_date.year == year])
    else:
        netgain = sum([x.gain for x in total_profits])

    for txn in total_profits:
        if year is not None:
            if txn.sell_date.year != year:
                # It's not in the year of interest. skip.
                continue

        print(outfmt.format(txn.quantity,
                            txn.asset,
                            txn.acq_date,
                            txn.sell_date,
                            txn.proceeds,
                            txn.basis,
                            txn.gain,
                            txn.getlong()), end='')

    print("\n   net gains over period: ${:8.2f}".format(netgain))

    print("\n Other income: ")
    for income in other_income:
        if year is not None and income[0].year != year:
            continue
        print("{}  ${:10.2f}  (as {} {})"
              .format(income[0].strftime("%Y-%m-%d"),
                      income[3],
                      income[2],
                      income[1]))
    print("      -------------")
    print("Tot:   ${:10.2f}"
          .format(sum([x[3] for x in other_income
                       if year is None or x[0].year == year])))


def main(csv_filename, year):
    with open(csv_filename, newline='') as csvfile:
        txnreader = csv.reader(csvfile, delimiter=',', quotechar='"')
        for row in txnreader:
            if len(row) == 0:
                continue
            ts = row[0]
            try:
                timestamp = dateutil.parser.parse(ts)
            except ValueError:
                # skip it. Transactions start with timestamps.
                continue
            asset = row[2].upper()
            txn_type = row[1].strip().lower()
            txn_quantity = Decimal(row[3])
            txn_spotprice = Decimal(row[4])

            # Subtotal does not include fees, whether on buys or sells.
            txn_subtotal = Decimal(row[5]) if (
                row[5] and len(row[5].strip()) > 0) else None

            # Total Includes fees. On buys, fees are added to the subtotal to
            # get the total. On Sells, fees are subtracted from the subtotal
            # (fees are paid from proceeds).
            txn_total = Decimal(row[6]) if (
                row[6] and len(row[6].strip()) > 0) else None

            # txn_fees = Decimal(row[7]) if (
            #     row[7] and len(row[7].strip()) > 0) else None

            calculated_value = txn_quantity * txn_spotprice

            if txn_type == "buy" and txn_total != Decimal(0):
                on_buy(timestamp, asset, txn_quantity, txn_total)
            elif txn_type == "buy" and txn_total == Decimal(0):
                if vv >= 1:
                    print("Interpreting zero-value buy as income")
                on_income(timestamp, asset, txn_quantity, calculated_value)
            elif txn_type.startswith("receive"):
                on_buy(timestamp, asset, txn_quantity, calculated_value)
            elif (txn_type.startswith("paid")
                  or txn_type.startswith("send")):
                gains = on_sell(timestamp,
                                asset,
                                txn_quantity,
                                calculated_value)
                total_profits.extend(gains)
                if vv >= 1:
                    print('\n')
            elif txn_type.startswith("sell"):
                # Be sure to include fees in the proceeds
                gains = on_sell(timestamp,
                                asset,
                                txn_quantity,
                                txn_subtotal)
                total_profits.extend(gains)
                if vv >= 1:
                    print('\n')
            elif (txn_type.startswith("coinbase earn")
                  or txn_type.startswith("rewards income")):
                # Always use the computed total here since the given dollar
                # value is rounded to the nearest cent.
                on_income(timestamp,
                          asset,
                          txn_quantity,
                          calculated_value)
            else:
                print("=== WARNING! IGNORING '{}' TRANSACTION =="
                      .format(txn_type))
        print_reports(year)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbosity", action="count", default=0)
    parser.add_argument("-y", "--year",
                        help="The calendar year to generate reports for",
                        default=str(datetime.datetime.now().year))
    parser.add_argument("csv_file", help="File to process")
    args = parser.parse_args()
    vv = args.verbosity
    yr = args.year
    if yr == "all":
        yr = None
    else:
        yr = int(yr)
    main(args.csv_file, yr)
