from django.test import TestCase
from djunc import qs
from tests.models import Widget


class QuerySetTestCase(TestCase):
    def test_filter(self):
        Widget.objects.create(name="first")
        Widget.objects.create(name="second")
        filtered = qs.filter(name="first")(Widget.objects.all())
        self.assertEqual(filtered.count(), 1)
        self.assertEqual(filtered.get().name, "first")

    def test_pipe(self):
        for name in ["first", "second", "third"]:
            Widget.objects.create(name=name)

        prepare = qs.pipe(
            qs.filter(name__in=["first", "third"]),
            qs.exclude(name="third"),
            qs.include_fields("name"),
        )

        queryset = prepare(Widget.objects.all())

        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.get().name, "first")

    def test_noop(self):
        queryset = Widget.objects.all()
        before = str(queryset.query)
        queryset = qs.noop(queryset)
        after = str(queryset.query)
        self.assertEqual(before, after)
