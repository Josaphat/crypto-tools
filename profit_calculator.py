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
        self.islong = (self.sell_date - self.acq_date) > datetime.timedelta(weeks=52)

    def getlong(self):
        if self.islong:
            return "long"
        else:
            return "short"

total_profits = []


def on_buy(ts, quantity, total):
    satoshi = btc_to_satoshi(quantity)
    print("{} acquire  {:01.8f} BTC ({:9d} satoshi) for {:0.2f} USD [[{}]]\n"
          .format(ts, quantity, satoshi, total, total/satoshi))
    queue.append((ts, satoshi, total/satoshi))


def on_sell(ts, quantity, total):
    sell_date = ts

    satoshi = btc_to_satoshi(quantity)
    print("{} dispose  {:01.8f} BTC ({:9d} satoshi) for {:0.2f} USD [[{}]]"
          .format(ts, quantity, satoshi, total, total/satoshi), end='')

    sell_value_per_satoshi = total/satoshi

    gains = []
    while satoshi > 0:
        acqtime = queue[0][0]
        per_satoshi = queue[0][2]
        sts = 0

        if queue[0][1] > satoshi:
            # print(" (enough) ", end='')
            sts = satoshi
            queue[0] = (queue[0][0], queue[0][1] - sts, queue[0][2])
            satoshi = 0
        else:
            # print(" (notenough) ", end='')
            sts = queue[0][1]
            satoshi -= sts
            queue.pop(0)
        usd_basis = sts * per_satoshi
        # print("usd_basis:", usd_basis)
        # profit = (sts * sell_value_per_satoshi) - usd_basis
        # print("profit:", profit)
        # term = ""
        # if (ts - acqtime) > datetime.timedelta(weeks=52):
        #     term = "LONG"
        # else:
        #     term = "SHORT"
        # gains.append((profit, term, ts.isoformat()))
        gains.append(TransactionRecord(("{:10.8f} BTC".format(sts / Decimal(1e8))),
                                       acqtime,
                                       sell_date,
                                       (sts * sell_value_per_satoshi),
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
                # print(".", end='')
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
                # print("\t", gains, "\n")
            elif txn_type.lower().startswith("sell"):
                gains = on_sell(timestamp,
                                Decimal(row[3]),
                                Decimal(row[6]))
                total_profits.extend(gains)
                # print("\t", gains, "\n")
                print('\n')
            else:
                print("IGNORING", txn_type)
        print("""============================================
Sales and Other Dispositions of Capital Assets
----------------------------------------------

   Description  |    Date    |    Date    |            |    Cost    |   Gains/   | Short or
   of Property  |  Acquired  |    Sold    |  Proceeds  |  (basis)   |   Losses   | Long term
----------------+------------+------------+------------+------------+------------+------------
""", end='')

        netgain = sum([x.gain for x in total_profits])
        for txn in total_profits:
            print(" {} | {:%Y-%m-%d} | {:%Y-%m-%d} | {:10.2f} | {:10.2f} | {:10.2f} | {}\t".format(
                txn.descr, txn.acq_date, txn.sell_date, txn.proceeds, txn.basis, txn.gain, txn.getlong()
                                                                    ))
            # print("{}\t ${:8.2f}\t ({}-term)".format(el[2], el[0], el[1]).lower())

        print("\n   net profits: ${:8.2f}".format(netgain))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file")
    args = parser.parse_args()
    main(args.csv_file)
