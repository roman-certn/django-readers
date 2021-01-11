from django.test import TestCase
from djunc import pairs, projectors, qs
from tests.models import Group, Owner, Widget


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

        queryset_function = qs.pipe(
            qs.filter(name__in=["first", "third"]),
            qs.exclude(name="third"),
            qs.include_fields("name"),
        )

        queryset = queryset_function(Widget.objects.all())

        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.get().name, "first")


class ProjectorTestCase(TestCase):
    def test_field(self):
        widget = Widget.objects.create(name="test")
        projector = projectors.field("name")
        result = projector(widget)
        self.assertEqual(result, {"name": "test"})

    def test_compose(self):
        widget = Widget.objects.create(name="test", other="other")
        projector = projectors.compose(
            projectors.field("name"),
            projectors.field("other"),
        )
        result = projector(widget)
        self.assertEqual(result, {"name": "test", "other": "other"})


class PairsTestCase(TestCase):
    def test_fields(self):
        for name in ["first", "second", "third"]:
            Widget.objects.create(name=name, other=f"other-{name}")

        spec = [
            pairs.field("name"),
            pairs.field("other"),
        ]

        prepare, project = pairs.process(spec)
        queryset = prepare(Widget.objects.all())
        result = [project(instance) for instance in queryset]

        self.assertEqual(
            result,
            [
                {"name": "first", "other": "other-first"},
                {"name": "second", "other": "other-second"},
                {"name": "third", "other": "other-third"},
            ],
        )


class RelationshipProjectorTestCase(TestCase):
    def test_relationship_projector(self):
        widget = Widget.objects.create(
            name="test widget",
            owner=Owner.objects.create(
                name="test owner", group=Group.objects.create(name="test group")
            ),
        )

        project = projectors.compose(
            projectors.field("name"),
            projectors.field(
                "owner",
                lambda instance: projectors.compose(
                    projectors.field("name"),
                    projectors.field(
                        "group",
                        lambda instance: projectors.field("name")(instance.group),
                    ),
                )(instance.owner),
            ),
        )

        result = project(widget)
        self.assertEqual(
            result,
            {
                "name": "test widget",
                "owner": {"name": "test owner", "group": {"name": "test group"}},
            },
        )

    def test_many_relationships(self):
        group = Group.objects.create(name="test group")
        owner_1 = Owner.objects.create(name="owner 1", group=group)
        owner_2 = Owner.objects.create(name="owner 2", group=group)
        Widget.objects.create(name="widget 1", owner=owner_1)
        Widget.objects.create(name="widget 2", owner=owner_1)
        Widget.objects.create(name="widget 3", owner=owner_2)

        project = projectors.compose(
            projectors.field("name"),
            projectors.field(
                "owners",
                lambda instance: [
                    projectors.compose(
                        projectors.field("name"),
                        projectors.field(
                            "widgets",
                            lambda instance: [
                                projectors.field("name")(widget)
                                for widget in instance.widget_set.all()
                            ],
                        ),
                    )(owner)
                    for owner in instance.owner_set.all()
                ],
            ),
        )

        result = project(group)
        self.assertEqual(
            result,
            {
                "name": "test group",
                "owners": [
                    {
                        "name": "owner 1",
                        "widgets": [
                            {"name": "widget 1"},
                            {"name": "widget 2"},
                        ],
                    },
                    {
                        "name": "owner 2",
                        "widgets": [
                            {"name": "widget 3"},
                        ],
                    },
                ],
            },
        )
