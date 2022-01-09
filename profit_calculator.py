#!/usr/bin/env python3
#
# profit_calculator.py - Processes Coinbase CSV for gain/loss information.
#
# Copyright (C) 2021 Jos Valdivia
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# This program is not affiliated, associated, authorized, endorsed by, or in
# any way officially connected with Coinbase Inc, or any of its subsidiaries or
# its affiliates.
#
# The name of Coinbase as well as related names, marks, emblems, and images are
# registered trademarks of their respective owners.

import argparse
import csv
import dateutil.parser
import datetime
from decimal import Decimal
from typing import NamedTuple

# Approaches Chapernowne's number (base 10) with each revision.
version = "0.12"

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
    def __init__(self, asset, quantity, date_acquired, date_sold, sale_price,
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

    def __str__(self):
        return outfmt.format(self.quantity, self.asset, self.acq_date,
                             self.sell_date, self.proceeds, self.basis,
                             self.gain, self.getlong())

    def getlong(self):
        if self.islong:
            return "long"
        else:
            return "short"


def on_buy(ts, asset, quantity, total):
    if vv >= 1:
        print("{} acquire  {:010.8f} {} for {:6.2f} USD [[{:9.5f}]]\n".format(
            ts, quantity, asset, total, total / quantity))
    if asset not in queues:
        queues[asset] = []
    queues[asset.upper()].append((ts, quantity, total / quantity))


def on_sell(ts, asset, quantity, total):
    sell_date = ts

    if vv >= 1:
        print("{} dispose  {:010.8f} {} for {:6.2f} USD [[{:9.5f}]]".format(
            ts, quantity, asset, total, total / quantity),
              end='')

    sell_value_per_qty = total / quantity
    queue = queues[asset]

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
        gains.append(
            TransactionRecord(asset, qty, acqtime, sell_date,
                              (qty * sell_value_per_qty), usd_basis))
    return gains


def on_income(ts, asset, quantity, total):
    other_income.append((ts, asset, quantity, total))

    # Basis is value at acquisition, same as buy.
    on_buy(ts, asset, quantity, total)


def on_convert(ts, src_asset, src_quantity, proceeds, tgt_asset, tgt_quantity,
               tgt_basis):
    """Track a conversion of src_asset to tgt_asset.

    ts is the timestamp of the transaction.

    src_asset is the asset being converted.

    src_quantity is the amount of src_asset being converted.

    proceeds is the total value of the transaction
    (inclusive of any fees).

    tgt_asset is the asset being converted TO.

    tgt_quantity is the amount of tgt_asset
    being converted TO.

    tgt_basis is the value of the target
    asset, usually simply the proceeds minus
    any fees.
    """

    # Convert is like a "sell" immediately followed by a "buy".
    if vv >= 1:
        print("Converting", src_quantity, src_asset, "to", tgt_quantity,
              tgt_asset)
    gains = on_sell(ts, src_asset, src_quantity, proceeds)
    total_profits.extend(gains)
    if vv >= 1:
        # We need to a append a (single) newline to the output of on_sell
        print("")
    on_buy(ts, tgt_asset, tgt_quantity, tgt_basis)


def print_reports(year):
    if vv >= 2:
        print("=== GENERATING REPORTS ===")

    # TODO: Generate the balance at the end of the given year.
    print("Current account balances (Ignores given year...)")
    print("\n====================\n")
    for asset in queues:
        print(asset, sum([x[1] for x in queues[asset]]))

    print(outputheader, end='')

    if year is not None:
        netgain = sum(
            [x.gain for x in total_profits if x.sell_date.year == year])
    else:
        netgain = sum([x.gain for x in total_profits])

    for txn in total_profits:
        if year is not None:
            if txn.sell_date.year != year:
                # It's not in the year of interest. skip.
                continue

        print(outfmt.format(txn.quantity, txn.asset, txn.acq_date,
                            txn.sell_date, txn.proceeds, txn.basis, txn.gain,
                            txn.getlong()),
              end='')

    print("\n   net gains over period: ${:8.2f}".format(netgain))

    print("\n Other income: ")
    for income in other_income:
        if year is not None and income[0].year != year:
            continue
        print("{}  ${:10.2f}  (as {} {})".format(
            income[0].strftime("%Y-%m-%d"), income[3], income[2], income[1]))
    print("      -------------")
    print("Tot:   ${:10.2f}".format(
        sum([x[3] for x in other_income
             if year is None or x[0].year == year])))


class InputTransaction(NamedTuple):
    """A data type to hold the data read from the CSV before actually processing it."""
    timestamp: datetime.datetime
    type: str
    asset: str
    quantity: Decimal
    spotprice: Decimal
    spotprice_currency: str
    subtotal: Decimal
    total: Decimal
    fees: Decimal
    notes: str


def main(csv_filename, year):
    with open(csv_filename, newline='') as csvfile:
        COL_TIMESTAMP = 0
        COL_TRANSACTION_TYPE = 1
        COL_ASSET = 2
        COL_QUANTITY_TRANSACTED = 3
        COL_SPOT_PRICE_CURRENCY = 4
        COL_SPOT_PRICE_AT_TRANSACTION = 5
        COL_SUBTOTAL = 6
        COL_TOTAL_WITH_FEES = 7
        COL_FEES = 8
        COL_NOTES = 9

        # Read in all the transactions from the CSV and do light pre-processing
        # and validation.  We'll then sort them by timestamp to make sure we're
        # using lots in FIFO order.
        txns = []
        txnreader = csv.reader(csvfile, delimiter=',', quotechar='"')
        for row in txnreader:
            if len(row) == 0:
                continue
            ts = row[COL_TIMESTAMP]
            try:
                timestamp = dateutil.parser.parse(ts)
            except ValueError:
                # skip it. Transactions start with timestamps.
                continue
            txn_asset = row[COL_ASSET].upper()
            txn_type = row[COL_TRANSACTION_TYPE].strip().lower()
            txn_quantity = Decimal(row[COL_QUANTITY_TRANSACTED])
            txn_spotprice = Decimal(row[COL_SPOT_PRICE_AT_TRANSACTION])
            txn_spotprice_currency = row[COL_SPOT_PRICE_CURRENCY].strip(
            ).upper()
            if txn_spotprice_currency != "USD":
                print("==== Only USD Is Supported ====")
                raise ValueError

            # Subtotal does not include fees, whether on buys or sells.
            txn_subtotal = Decimal(row[COL_SUBTOTAL]) if (
                row[COL_SUBTOTAL]
                and len(row[COL_SUBTOTAL].strip()) > 0) else None

            # Total Includes fees. On buys, fees are added to the subtotal to
            # get the total. On Sells, fees are subtracted from the subtotal
            # (fees are paid from proceeds).
            txn_total = Decimal(row[COL_TOTAL_WITH_FEES]) if (
                row[COL_TOTAL_WITH_FEES]
                and len(row[COL_TOTAL_WITH_FEES].strip()) > 0) else None

            txn_fees = Decimal(row[COL_FEES]) if (
                row[COL_FEES] and len(row[COL_FEES].strip()) > 0) else None

            txn_notes = row[COL_NOTES]

            txns.append(
                InputTransaction(timestamp, txn_type, txn_asset, txn_quantity,
                                 txn_spotprice, txn_spotprice_currency,
                                 txn_subtotal, txn_total, txn_fees, txn_notes))

        # Sort the txns chronologically
        txns.sort(key=lambda txn: txn.timestamp)

        for txn in txns:
            calculated_value = txn.quantity * txn.spotprice

            if txn.type == "buy" and txn.total != Decimal(0):
                on_buy(txn.timestamp, txn.asset, txn.quantity, txn.total)
            elif txn.type == "buy" and txn.total == Decimal(0):
                if vv >= 1:
                    print("Interpreting zero-value buy as income")
                on_income(txn.timestamp, txn.asset, txn.quantity,
                          calculated_value)
            elif txn.type.startswith("receive"):
                on_buy(txn.timestamp, txn.asset, txn.quantity,
                       calculated_value)
            elif (txn.type.startswith("paid") or txn.type.startswith("send")):
                gains = on_sell(txn.timestamp, txn.asset, txn.quantity,
                                calculated_value)
                total_profits.extend(gains)
                if vv >= 1:
                    print('\n')
            elif txn.type.startswith("sell"):
                # Be sure to include fees in the proceeds
                gains = on_sell(txn.timestamp, txn.asset, txn.quantity,
                                txn.subtotal)
                total_profits.extend(gains)
                if vv >= 1:
                    print('\n')
            elif (txn.type.startswith("coinbase earn")
                  or txn.type.startswith("rewards income")):
                # Always use the computed total here since the given dollar
                # value is rounded to the nearest cent.
                on_income(txn.timestamp, txn.asset, txn.quantity,
                          calculated_value)
            elif txn.type == "convert":
                # The target quantity and asset is only in the 'Notes'
                # column. Parse out the info.
                notes = txn.notes.split()
                if notes[0] != "Converted" or notes[3].lower() != "to":
                    print(
                        "Invalid 'Notes' column format for a 'Convert' transaction"
                    )
                    raise ValueError
                # if notes[1] != str(txn.quantity):
                #   print(txn.quantity, " doesn't match notes qty: ", notes[1])
                #   pass

                if notes[2].upper() != txn.asset:
                    print(txn.asset, " does not match notes asset: ",
                          notes[2].upper())
                    raise ValueError

                tgt_asset = notes[5]
                tgt_quantity = Decimal(notes[4])

                on_convert(txn.timestamp, txn.asset, txn.quantity, txn.total,
                           tgt_asset, tgt_quantity, txn.subtotal)
            else:
                print("=== WARNING! IGNORING '{}' TRANSACTION ==".format(
                    txn.type))
        print_reports(year)


if __name__ == "__main__":
    descr = """
Calculates gains for cryptocurrencies. Takes a CSV file generated by Coinbase
and uses it to calculate capital gains or losses.

This program is free software.
"""
    parser = argparse.ArgumentParser(prog='profit_calculator.py',
                                     description=descr)
    parser.add_argument('--version',
                        action='version',
                        version='%(prog)s ' + version +
                        " This application is licensed under GNU GPL.")
    parser.add_argument("-v", "--verbosity", action="count", default=0)
    parser.add_argument(
        "-y",
        "--year",
        help=
        "Year for the reports. Defaults to current year. Also accepts 'all'.",
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
