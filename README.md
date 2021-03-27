# cryptocurrency tools

### THESE PROGRAMS DO NOT PROVIDE TAX ADVICE
The programs contained in this repository do not output tax advice.
They are provided with the hope that they will be useful, but
nonetheless have _absolutely no Warranty_.  The authors assume no
responsibility for the accuracy of the programs' outputs.

## profit_calculator.py
Possibly mis-named, `profit_calculator.py` calculates the gains or losses
associated with cryptocurrencies.  It also generates a report on
income gained.

The program makes several assumptions:

1. The given CSV is formatted the way Coinbase's CSV reports are
   formatted.
2. The given CSV contains enough transaction history and enough
   increase in cryptocurrencies that any decreases are covered.
3. Send/Receive transactions are payments with fair-market value set
   at the spot price of the cryptocurrency at the time the transaction
   was made.
4. Always uses First-in, First-Out (FIFO) disposal method.

**NOTE**: The program does not currently handle conversions *between*
cryptocurrencies.

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
connected with Coinbase Inc, or any of its subsidiaries or its
affiliates.

The name of Coinbase as well as related names, marks, emblems, and
images are registered trademarks of their respective owners.
