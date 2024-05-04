import argparse
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from TransactionReader import TransactionReader

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Details related to the budget spreadsheet.
FIRST_COLUMN = "K"
FIRST_LINE = 5  # The Expenses section on the spreadsheet starts on Line 5
LAST_COLUMN = "P"
GENERIC_RANGE = f"{FIRST_COLUMN}{FIRST_LINE}:{LAST_COLUMN}"


def get_creds():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds


def main(spreadsheet_id: str, imports: list):
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.
    """
    # Read credit card csv
    reader = TransactionReader()
    for file in imports:
        reader.add_csv(file[0], file[1])
    all_values = reader.all_values

    creds = get_creds()
    try:
        service = build("sheets", "v4", credentials=creds)

        # Call the Sheets API
        sheet = service.spreadsheets()

        for month, values in all_values.items():
            # Fetch existing data for the sheet
            result = (
                sheet.values()
                .get(
                    spreadsheetId=spreadsheet_id,
                    range=f"{month}!{GENERIC_RANGE}"
                )
                .execute()
            )
            rows = result.get("values", [])

            # Determine insertion line - first empty 'Item' cell
            for i, row in enumerate(rows, start=FIRST_LINE):
                if not row[0]:
                    insertion_line = i
                    break
            else:
                insertion_line = FIRST_LINE + len(rows)

            # Insert new values using a brute-force update
            body = {
                "valueInputOption": "USER_ENTERED",
                "data": [
                    {
                        "range": f"{month}!K{insertion_line}:L",
                        "values": values[0]
                    },
                    {
                        "range": f"{month}!P{insertion_line}:P",
                        "values": values[1]
                    }
                ]
            }
            result = (
                sheet.values()
                .batchUpdate(spreadsheetId=spreadsheet_id, body=body)
                .execute()
            )

    except HttpError as err:
        print(err)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Export your transactions to a budget spreadsheet."
    )
    parser.add_argument("sheetId",
        help="The Google Sheets ID of the spreadsheet being written to."          
    )
    parser.add_argument("-f", "--file", action="append", nargs="+",
        help="A csv file containing all the transactions for import. Use the format <'Provider' csv_file_path>.",
        dest="files"
    )
    args = parser.parse_args()

    main(args.sheetId, args.files)
    