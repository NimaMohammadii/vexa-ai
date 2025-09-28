"""Utility script to recalculate user credits.

The script connects to the project's database using the configuration provided
by :mod:`db` and updates every user's ``credits`` value based on an exchange
rate of 4.5% (0.045). The new value is rounded to the nearest integer before
being persisted. Before the write operation takes place, the script prints each
calculated change and waits for user confirmation (unless ``--yes`` is passed).
"""
from __future__ import annotations

import argparse
import sqlite3
from contextlib import closing
from typing import Iterable, Tuple

import db

UserChange = Tuple[int, int, int]


def _fetch_user_changes(cursor: sqlite3.Cursor) -> Iterable[UserChange]:
    cursor.execute("SELECT user_id, credits FROM users")
    for user_id, credits in cursor.fetchall():
        old_credits = credits or 0
        new_credits = round(old_credits * 0.045)
        yield user_id, old_credits, new_credits


def recalculate_user_credits(*, assume_yes: bool = False) -> None:
    """Recalculate and persist the credits for every user.

    Parameters
    ----------
    assume_yes:
        When ``True`` the confirmation prompt is skipped and the updates are
        committed immediately.
    """

    with closing(sqlite3.connect(db.DB_PATH)) as connection:
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        changes = list(_fetch_user_changes(cursor))

        if not changes:
            print("هیچ کاربری در جدول users پیدا نشد.")
            return

        print("لیست تغییرات پیشنهادی:")
        for user_id, old_credits, new_credits in changes:
            print(
                f"user_id={user_id} old_credits={old_credits} new_credits={new_credits}"
            )

        if not assume_yes:
            confirmation = input("آیا این تغییرات اعمال شوند؟ [y/N]: ").strip().lower()
            if confirmation not in {"y", "yes", "بله"}:
                print("عملیات لغو شد و هیچ تغییری اعمال نشد.")
                return

        for user_id, _, new_credits in changes:
            cursor.execute(
                "UPDATE users SET credits = ? WHERE user_id = ?",
                (new_credits, user_id),
            )

        connection.commit()
        print("تغییرات با موفقیت ذخیره شد.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recalculate user credits based on a 4.5% exchange rate."
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="اعمال تغییرات بدون پرسش تأیید.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    recalculate_user_credits(assume_yes=args.yes)


if __name__ == "__main__":
    main()
