"""Utility script to normalise user credits.

The script connects to the project's database using the configuration provided
by :mod:`db` and updates every user's ``credits`` value so that it contains at
most two decimal places. Values are rounded using ``ROUND_HALF_UP`` to match
the behaviour enforced by the runtime helpers. Before the write operation takes
place, the script prints each calculated change and waits for user confirmation
(unless ``--yes`` is passed).
"""
from __future__ import annotations

import argparse
import sqlite3
from contextlib import closing
from typing import Iterable, Tuple

import db

UserChange = Tuple[int, float, float]


def _fetch_user_changes(cursor: sqlite3.Cursor) -> Iterable[UserChange]:
    cursor.execute("SELECT user_id, credits FROM users")
    for user_id, credits in cursor.fetchall():
        old_credits = float(credits or 0)
        new_credits = db.normalize_credit_amount(old_credits)

        if abs(new_credits - old_credits) < 1e-9:
            continue

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
            print("هیچ کاربری در جدول users پیدا نشد یا نیازی به تغییر نبود.")
            return

        print("لیست تغییرات پیشنهادی:")
        for user_id, old_credits, new_credits in changes:
            print(
                "user_id={user_id} old_credits={old:.5f} new_credits={new:.2f}".format(
                    user_id=user_id,
                    old=old_credits,
                    new=new_credits,
                )
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
        description="Normalise all user credits to two decimal places."
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
