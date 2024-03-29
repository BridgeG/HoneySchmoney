from firebase import db
from datetime import date
from datetime import datetime

BLACKLIST = ["direkt abgezogen", "wird abgezogen", "per Direktabzug", "kein Code notwendig", "nach Anmeldung", "wird zugeschickt",
             "wird gutgeschrieben", "wird angezeigt", "im Newsletter", "wird zugeteilt", "für Firmen", "Ermässigung erhalten"]


# Function to push vouchers data to Firebase
# Parameters:
#   - name: string representing the name
#   - vouchers: array of dictionaries containing voucher information
#       Each dictionary should have "code" and "description" keys
def push_vouchers(name, vouchers, verbose=False):
    # Prepare data to be pushed to Firebase
    data = {"name": name, "vouchers": filter_vouchers(vouchers)}

    # Get a reference to the document in the "vouchers" collection
    doc_ref = db.collection("vouchers").document(name)

    # Set the data in the document
    doc_ref.set(data)

    # Print a message indicating successful push to Firebase
    if verbose:
        print(f"pushed {name} vouchers to Firebase")


# Function to filter vouchers based on certain conditions
# Parameters:
#   - vouchers: array of dictionaries containing voucher information
#       Each dictionary should have "code" and "description" keys
# Returns:
#   - filtered_vouchers: array of dictionaries, excluding certain codes
def filter_vouchers(vouchers):
    # Use list comprehension to filter vouchers based on conditions
    filtered_vouchers = [voucher for voucher in vouchers if voucher["code"] is not None
                         and voucher["code"] not in BLACKLIST
                         and len(voucher["code"]) > 3]
    return filtered_vouchers

def push_latest_date(verbose=False):
    my_date = str(date.today())
    my_time = str(datetime.now())

    doc_ref = db.collection("log").document(my_date)

    entry = {"date": my_date, "time": my_time}

    doc_ref.set(entry)
    if verbose:
        print("date pushed")

# fuck git