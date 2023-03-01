import random
from django.db import transaction
from django.core.management.base import BaseCommand
from itkufs.accounting.models import (
    Group,
    Account,
    Transaction,
    TransactionEntry,
)

from itkufs.common.management.factories import (
    GroupFactory,
    UserAccountFactory,
    GroupAccountFactory,
    TransactionFactory,
    TransactionEntryFactory,
)


class Command(BaseCommand):
    help = "Generate fake data for testing the application"

    def add_arguments(self, parser):
        parser.add_argument(
            "--groups",
            type=int,
            default=2,
            help="How many groups will be created",
        )
        parser.add_argument(
            "--users",
            type=int,
            default=100,
            help="How many users will be created per group",
        )
        parser.add_argument(
            "--group-accounts",
            type=int,
            default=20,
            help="How many group accounts will be created per group",
        )
        parser.add_argument(
            "--transactions",
            type=int,
            default=100,
            help="How many transactions will be created per group",
        )
        parser.add_argument(
            "--entries",
            type=int,
            default=25,
            help="How many entries will be created per transaction",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        # Ratios for the number of objects to create
        GROUP_COUNT = options["groups"]
        USERS_PER_GROUP = options["users"]
        GROUP_ACCOUNTS_PER_GROUP = options["group_accounts"]
        TRANSACTIONS_PER_GROUP = options["transactions"]
        ENTRIES_PER_TRANSACTION = options["entries"]

        self.stdout.write("Deleting old data...")
        models = [Group, Account, Transaction, TransactionEntry]
        for m in models:
            m.objects.all().delete()

        self.stdout.write("Generating new data...")
        # Create groups
        groups = [GroupFactory() for _ in range(GROUP_COUNT)]

        for group in groups:
            # Create users
            user_accounts = []
            for _ in range(USERS_PER_GROUP):
                user = UserAccountFactory(group=group)
                user_accounts.append(user)
            self.stdout.write(
                f"Created {len(user_accounts)} users for {group.name}"
            )

            # Create group accounts
            group_accounts = []
            for _ in range(GROUP_ACCOUNTS_PER_GROUP):
                type = random.choice(
                    [
                        Account.LIABILITY_ACCOUNT,
                        Account.ASSET_ACCOUNT,
                        Account.EQUITY_ACCOUNT,
                        Account.INCOME_ACCOUNT,
                        Account.EXPENSE_ACCOUNT,
                    ]
                )
                account = GroupAccountFactory(group=group, type=type)
                group_accounts.append(account)
            self.stdout.write(
                f"Created {len(group_accounts)} group accounts for {group.name}"
            )

            # Create transactions
            transactions = []
            for _ in range(TRANSACTIONS_PER_GROUP):
                transaction = TransactionFactory(group=group)
                transactions.append(transaction)
            self.stdout.write(
                f"Created {len(transactions)} transactions for {group.name}"
            )

            # Split the transactions in two groups
            MID = int(TRANSACTIONS_PER_GROUP / 2)

            # Create transactions which debit one group account
            for t in transactions[:MID]:
                debit_account = random.choice(group_accounts)
                total = 0

                # Create credit entries
                users = random.sample(
                    population=user_accounts, k=ENTRIES_PER_TRANSACTION
                )
                for user in users:
                    amount = random.randint(1, 5000)
                    total += amount
                    TransactionEntryFactory(
                        transaction=t, account=user, debit=0, credit=amount
                    )

                # Create debit entry
                TransactionEntryFactory(
                    transaction=t, account=debit_account, debit=total, credit=0
                )

            # Create transactions which credit one group account
            for t in transactions[MID:]:
                credit_account = random.choice(group_accounts)
                total = 0

                # Create debit entries
                users = random.sample(
                    population=user_accounts, k=ENTRIES_PER_TRANSACTION
                )
                for user in users:
                    amount = random.randint(1, 5000)
                    total += amount
                    TransactionEntryFactory(
                        transaction=t, account=user, debit=amount, credit=0
                    )

                # Create credit entry
                TransactionEntryFactory(
                    transaction=t, account=credit_account, debit=0, credit=total
                )

            # Set the final state of each transaction
            for t in transactions:
                t.state = random.choices(
                    population=[
                        Transaction.PENDING_STATE,
                        Transaction.COMMITTED_STATE,
                        Transaction.REJECTED_STATE,
                    ],
                    weights=[0.05, 0.85, 0.1],
                    k=1,
                )[0]
                t.save()

        self.stdout.write("Done!")
