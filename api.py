from firebase import db


# url: string
# vouchers: array of { "code": "myCode", "description": str(i) }
def push_vouchers(name, url, vouchers):
    data = {"name": name, "url": url, "vouchers": vouchers}

    doc_ref = db.collection("vouchers").document(name)
    doc_ref.set(data)
    print("pushed vouchers")
