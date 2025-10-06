from graphviz import Digraph

# ساخت نمودار گردش کار فاکتور
dot = Digraph(comment="Factor Approval Workflow", format="png")
dot.attr(rankdir="LR", size="8")

# گره‌ها (وضعیت‌ها)
states = {
    "DRAFT": "پیش‌نویس (Draft)",
    "PENDING_APPROVAL": "در انتظار تأیید شعبه",
    "APPROVED": "تأیید شعبه (Approved)",
    "APPROVED_FOR_PAYMENT": "ارسال به ستاد (Approved for Payment)",
    "IN_PAYMENT_PROCESS": "در حال پرداخت",
    "PAID": "پرداخت‌شده",
    "REJECTED": "رد شده"
}

# اضافه کردن نودها
for state, label in states.items():
    shape = "ellipse"
    color = "black"
    if state == "PAID":
        color = "green"
        shape = "doublecircle"
    elif state == "REJECTED":
        color = "red"
        shape = "box"
    elif state == "DRAFT":
        color = "gray"
    dot.node(state, label, shape=shape, color=color, fontname="Tahoma")

# یال‌ها (انتقالات)
edges = [
    ("DRAFT", "PENDING_APPROVAL", "ارسال برای تأیید"),
    ("PENDING_APPROVAL", "APPROVED", "تأیید شعبه"),
    ("PENDING_APPROVAL", "REJECTED", "رد توسط شعبه"),
    ("APPROVED", "APPROVED_FOR_PAYMENT", "ارسال به ستاد"),
    ("APPROVED", "REJECTED", "رد توسط شعبه/ستاد"),
    ("APPROVED_FOR_PAYMENT", "IN_PAYMENT_PROCESS", "شروع فرآیند پرداخت"),
    ("APPROVED_FOR_PAYMENT", "REJECTED", "رد توسط ستاد"),
    ("IN_PAYMENT_PROCESS", "PAID", "پرداخت موفق"),
    ("IN_PAYMENT_PROCESS", "REJECTED", "خطا یا رد در پرداخت"),
]

for src, dst, label in edges:
    dot.edge(src, dst, label, fontname="Tahoma")

# ذخیره و رندر
file_path = "/factor_workflow"
dot.render(file_path)

# file_path + ".png"
