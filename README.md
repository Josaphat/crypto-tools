# cryptocurrency tools

### THESE PROGRAMS DO NOT PROVIDE TAX ADVICE

The programs contained in this repository do not output tax advice.
They are provided with the hope that they will be useful, but
nonetheless have _absolutely no Warranty_.  The authors assume no
responsibility for the accuracy of the programs' outputs.

## profit_calculator.py

Possibly misnamed, `profit_calculator.py` calculates the gains or
losses associated with cryptocurrency transactions for the purpose of
calculating taxable gains.  It also generates a report on crypto
income (e.g. from staking rewards).  Its purpose is to help in filling
out IRS forms 8949, 1040 Schedule D, and 1099-MISC.

The program makes some basic assumptions:

1. It uses a First-in, First-Out (FIFO) disposal method.
2. The given CSV is formatted the way Coinbase's CSV reports are
   formatted.
3. Prices are in USD.
3. The given CSV contains enough transaction history and enough
   increase in cryptocurrencies that any decreases are covered. That
   is, it expects that the transaction history doesn't drop any
   asset's balance below zero (e.g. you can't sell/send crypto that
   isn't accounted for in the transaction history). The safest usage
   is to provide the entire transaction history starting from the very
   beginning of the wallet.

**Note**: This program has not been tested with CSVs obtained from
*Coinbase Pro*.

The output comes in three sections. The first section prints out the
"Current account balances" based on the transaction history provided
in the CSV file.  This is useful to verify that the program has
correctly processed each of the transactions properly to end up at the
correct balances. When performing the calculations, it ignores the
"year" argument.

The second section titled **Sales and Other Dispositions of Capital
Assets** is formatted to mirror the information needed to fill out IRS
Form 8949.  This shows each lot being sold, its proceeds and basis, as
well as the gain loss and whether it was a short- or long-term
transaction.

The last section is titled **Other income** and lists all instances of
"Rewards income" or "Coinbase Earn" transactions which count toward
regular income. This is the kind of information that goes into
1099-MISC.

**Usage example:**

```sh
python profit_calculator.py -y2021 "Coinbase-abc123-TransactionHistoryReport-2022-01-01 00 00.csv"
```

### CSV Format

The program only looks at lines that starts with timestamps, so any
miscellaneous entries (e.g. blank lines or notes) are ignored.
Coinbase CSVs include extra metadata at the beginning of the CSV:
These lines are ignored.

Currently the line with the column headings are ignored by the
program, but a future update will include some verification that the
headings match the program's assumptions about them.

As of this writing the format of the transaction information itself is
expected to be (in order):

1. *Timestamp*
2. *Transaction type* -- one of { _Buy_, _Sell_, _Convert_, _Send_, _Receive_,
   _Rewards Income_, _Coinbase Earn_, _Paid for an order_}.
3. *Asset* -- Short asset identifier code (e.g. "ETH" for Ether).
4. *Quantity Transacted* -- The amount of *Asset* involved in this
   transaction.
5. *Spot Price Currency* -- Expected to be USD.
6. *Spot Price at Transaction* -- Price of *Asset* at the time of the
   transaction (in USD).
7. *Subtotal* -- USD value of the transaction excluding *Fees*.
8. *Total* -- USD value of the transaction including *Fees*.
9. *Fees* -- Fees assessed for the transaction.
10. *Notes* -- This column is ignored unless it's part of a _Convert_
    transaction, in which case it must contain the phrase "Converted
    X.XX ABC to Y.YY JKL" (where `X.XX` and `Y.YY` are decimal
    amounts, `ABC` and `JLK` are *Assets*. E.g. "Converted 0.01 BTC
    to 295.941167 ALGO"

## License

The programs contained in this repository are free software: you can
redistribute them and/or modify them under the terms of the GNU
General Public License as published by the Free Software Foundation,
either version 3 of the License, or (at your option) any later
version.

These programs are distributed in the hope that they will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

## Additional Disclaimers

This repository and the programs contained therein are not affiliated,
associated, authorized, endorsed by, or in any way officially
connected with Coinbase Inc ("Coinbase"), or any of its subsidiaries
or its affiliates.

The name of Coinbase as well as related names, marks, emblems, and
images are registered trademarks of their respective owners.
