from django.core.exceptions import ValidationError
import django.test

import prologin.udb.models


class UdbTest(django.test.TestCase):
    def test_uid_fails_for_username_root(self):
        with self.assertRaisesRegex(
            ValidationError, "root is associated with uid 0"
        ):
            prologin.udb.models.User.objects.create(
                login="root", password="foo", group="root",
            )

    def test_uid_succeeds_for_username_admin(self):
        user = prologin.udb.models.User.objects.create(
            login="admin", password="foo", group="root",
        )
        self.assertEqual(user.uid, 12001)
