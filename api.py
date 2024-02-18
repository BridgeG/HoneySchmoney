from firebase import db


# name, url: string
# vouchers: array of { "code": "myCode", "description": "myDescription" }
def push_vouchers(name, url, vouchers):
    data = {"name": name, "url": url, "vouchers": filter_vouchers(vouchers)}

    doc_ref = db.collection("vouchers").document(name)
    doc_ref.set(data)
    # print("pushed vouchers")


def filter_vouchers(vouchers):
    filtered_vouchers = [voucher for voucher in vouchers if voucher["code"] is not None
                         and voucher["code"] not in ["direkt abgezogen", "per Direktabzug", "kein Code notwendig", "gen", "dig"]]
    return filtered_vouchers

