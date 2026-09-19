from app_init import *

print("############ USERS ####################")
print("ID | EMAIL | CREATED_AT | CREDITS")
with app.app_context():
    for x in UserAccount.query.order_by(UserAccount.created_at).all():
        print(f"{x.id} | {x.email} | {x.created_at} | {x.credits}")

    userid = input("\nEnter the ID of the user whose credits will be top up: ")
    if not userid.isdigit():
        print("You provided the wrong ID")
        exit()

    userid = int(userid)

    userdb = UserAccount.query.filter_by(id=userid).first()
    if userdb is None:
        print(f"There is no user with the given ID: {userid}")
        exit()

    prev_credits = userdb.credits  # CHANGED: felesleges dupla üres sor eggyé egyszerűsítve

    amount = input("\nEnter the amount of credits that will be added to the user's balance: ")
    if not amount[1::].isdigit():
        print("The amount must be a number")
        exit()

    amount = int(amount)

    confirm = input(f"{amount} credits will be added to {userdb.email} account, the updated balance will be: {prev_credits + amount} credits. Do you want to continue? (y/n): ")

    if confirm == "y":
        userdb.credits += amount
        db.session.commit()
        r.set(f"credits:{userid}", prev_credits + amount, ex=1800)
        print("Success")
    else:
        exit()
