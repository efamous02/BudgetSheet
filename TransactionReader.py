import csv

from collections import defaultdict
from datetime import date
from pathlib import Path


INTTOMONTH = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December"
}


class InvalidProvider(Exception):
    """Error for attempting to read a csv from an unsupported service."""
    def __init__(self, name: str, *args: object) -> None:
        self.msg = f"CSVs from '{name}' are not yet supported."
        super().__init__(*args)


class TransactionReader:
    """Prepare multiple csvs into one object.
    
    Attributes
    ----------
    all_values: Dict[str, Tuple[List, List]]
        A collection of all important information from the fed transactions.
        There is a key for each month for which a transaction is posted.
        The value is a tuple containing two lists of equal size:
            The first list contains all item names and its amount
            The second list contains the categories of the item

    Sample Usage
    ------------
    reader = TransactionReader()
    reader.add_csv("Provider", filepath)
    reader.add_csv("Provider1", filepath1)
    transactions = reader.all_values  # do something with `transactions`
    """
    def __init__(self) -> None:
        self.all_values = defaultdict(lambda: ([], []))

    def add_csv(self, provider: str, file: Path):
        """Prepare all transactions from a CSV for export to the budget

        Parameters
        ----------
        provider : str
            The institution tracking the transactions
        file : Path
            The csv file
        """
        with open(file, 'r') as csvfile:
            transactions = csv.reader(csvfile)

            try:
                self.VALID_PROVIDERS[provider](self, transactions)
            except KeyError as exc:
                raise InvalidProvider(provider) from exc

    def _add_capitalone(self, transactions):
        # Capital One CSV appears as follows:
        # Transaction Date,Posted Date,Card No.,Description,Category,Debit,Credit
        # Mapping:
        #   Posted Date -> month (in function)
        #   Description -> Item
        #   Debit       -> Total Amount
        #   Category    -> Budget Category (opt.)
        # AS OF: 2 May 2024
        next(transactions, None)  # Skip the header line

        # Get list of transactions to add
        for row in transactions:
            if row and row[5]:  # Ignore credits (empty 5th column)
                month = INTTOMONTH[date.fromisoformat(row[1]).month]

                self.all_values[month][0].append([row[3], row[5]])
                self.all_values[month][1].append([row[4]])

    def _add_discover(self, transactions):
        # Discover CSV appears as follows:
        # Trans. Date,Post Date,Description,Amount,Category
        # Mapping:
        #     Post Date   -> month (in function)
        #     Description -> Item
        #     Amount      -> Total Amount
        #     Category    -> Budget Category (opt.)
        # AS OF 2 May 2024
        next(transactions, None)  # Skip the header line

        # Get list of transactions to add
        for row in transactions:
            if row and float(row[3]) >= 0:  # Discover puts credits in the Amount column, skip them
                # Discover date comes in mm/dd/yyyy format, needs parsing
                post_date = row[1].split("/")
                month = INTTOMONTH[int(post_date[0])]

                self.all_values[month][0].append([row[2], row[3]])
                self.all_values[month][1].append([row[4]])

    VALID_PROVIDERS = {
        "Capital One": _add_capitalone,
        "Discover": _add_discover
    }
