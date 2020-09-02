from sqlalchemy import alias
from sqlalchemy import Column
from sqlalchemy import column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import testing
from sqlalchemy import true
from sqlalchemy.engine import default
from sqlalchemy.sql import select
from sqlalchemy.sql import Values
from sqlalchemy.sql.compiler import FROM_LINTING
from sqlalchemy.testing import AssertsCompiledSQL
from sqlalchemy.testing import fixtures


class ValuesTest(fixtures.TablesTest, AssertsCompiledSQL):
    __dialect__ = default.DefaultDialect(supports_native_boolean=True)

    run_setup_bind = None

    run_create_tables = None

    @classmethod
    def define_tables(cls, metadata):
        Table(
            "people",
            metadata,
            Column("people_id", Integer, primary_key=True),
            Column("age", Integer),
            Column("name", String(30)),
        )
        Table(
            "bookcases",
            metadata,
            Column("bookcase_id", Integer, primary_key=True),
            Column(
                "bookcase_owner_id", Integer, ForeignKey("people.people_id")
            ),
            Column("bookcase_shelves", Integer),
            Column("bookcase_width", Integer),
        )
        Table(
            "books",
            metadata,
            Column("book_id", Integer, primary_key=True),
            Column(
                "bookcase_id", Integer, ForeignKey("bookcases.bookcase_id")
            ),
            Column("book_owner_id", Integer, ForeignKey("people.people_id")),
            Column("book_weight", Integer),
        )

    def test_column_quoting(self):
        v1 = Values(
            column("CaseSensitive", Integer),
            column("has spaces", String),
            name="Spaces and Cases",
        ).data([(1, "textA", 99), (2, "textB", 88)])
        self.assert_compile(
            select(v1),
            'SELECT "Spaces and Cases"."CaseSensitive", '
            '"Spaces and Cases"."has spaces" FROM '
            "(VALUES (:param_1, :param_2, :param_3), "
            "(:param_4, :param_5, :param_6)) "
            'AS "Spaces and Cases" ("CaseSensitive", "has spaces")',
        )

    @testing.fixture
    def literal_parameter_fixture(self):
        def go(literal_binds):
            return Values(
                column("mykey", Integer),
                column("mytext", String),
                column("myint", Integer),
                name="myvalues",
                literal_binds=literal_binds,
            ).data([(1, "textA", 99), (2, "textB", 88)])

        return go

    def test_bound_parameters(self, literal_parameter_fixture):
        literal_parameter_fixture = literal_parameter_fixture(False)

        stmt = select(literal_parameter_fixture)

        self.assert_compile(
            stmt,
            "SELECT myvalues.mykey, myvalues.mytext, myvalues.myint FROM "
            "(VALUES (:param_1, :param_2, :param_3), "
            "(:param_4, :param_5, :param_6)"
            ") AS myvalues (mykey, mytext, myint)",
            checkparams={
                "param_1": 1,
                "param_2": "textA",
                "param_3": 99,
                "param_4": 2,
                "param_5": "textB",
                "param_6": 88,
            },
        )

    def test_literal_parameters(self, literal_parameter_fixture):
        literal_parameter_fixture = literal_parameter_fixture(True)

        stmt = select(literal_parameter_fixture)

        self.assert_compile(
            stmt,
            "SELECT myvalues.mykey, myvalues.mytext, myvalues.myint FROM "
            "(VALUES (1, 'textA', 99), (2, 'textB', 88)"
            ") AS myvalues (mykey, mytext, myint)",
            checkparams={},
        )

    def test_with_join_unnamed(self):
        people = self.tables.people
        values = Values(
            column("column1", Integer), column("column2", Integer),
        ).data([(1, 1), (2, 1), (3, 2), (3, 3)])
        stmt = select(people, values).select_from(
            people.join(values, values.c.column2 == people.c.people_id)
        )
        self.assert_compile(
            stmt,
            "SELECT people.people_id, people.age, people.name, column1, "
            "column2 FROM people JOIN (VALUES (:param_1, :param_2), "
            "(:param_3, :param_4), (:param_5, :param_6), "
            "(:param_7, :param_8)) "
            "ON people.people_id = column2",
            checkparams={
                "param_1": 1,
                "param_2": 1,
                "param_3": 2,
                "param_4": 1,
                "param_5": 3,
                "param_6": 2,
                "param_7": 3,
                "param_8": 3,
            },
        )

    def test_with_join_named(self):
        people = self.tables.people
        values = Values(
            column("bookcase_id", Integer),
            column("bookcase_owner_id", Integer),
            name="bookcases",
        ).data([(1, 1), (2, 1), (3, 2), (3, 3)])
        stmt = select(people, values).select_from(
            people.join(
                values, values.c.bookcase_owner_id == people.c.people_id
            )
        )
        self.assert_compile(
            stmt,
            "SELECT people.people_id, people.age, people.name, "
            "bookcases.bookcase_id, bookcases.bookcase_owner_id FROM people "
            "JOIN (VALUES (:param_1, :param_2), (:param_3, :param_4), "
            "(:param_5, :param_6), (:param_7, :param_8)) AS bookcases "
            "(bookcase_id, bookcase_owner_id) "
            "ON people.people_id = bookcases.bookcase_owner_id",
            checkparams={
                "param_1": 1,
                "param_2": 1,
                "param_3": 2,
                "param_4": 1,
                "param_5": 3,
                "param_6": 2,
                "param_7": 3,
                "param_8": 3,
            },
        )

    def test_with_aliased_join(self):
        people = self.tables.people
        values = (
            Values(
                column("bookcase_id", Integer),
                column("bookcase_owner_id", Integer),
            )
            .data([(1, 1), (2, 1), (3, 2), (3, 3)])
            .alias("bookcases")
        )
        stmt = select(people, values).select_from(
            people.join(
                values, values.c.bookcase_owner_id == people.c.people_id
            )
        )
        self.assert_compile(
            stmt,
            "SELECT people.people_id, people.age, people.name, "
            "bookcases.bookcase_id, bookcases.bookcase_owner_id FROM people "
            "JOIN (VALUES (:param_1, :param_2), (:param_3, :param_4), "
            "(:param_5, :param_6), (:param_7, :param_8)) AS bookcases "
            "(bookcase_id, bookcase_owner_id) "
            "ON people.people_id = bookcases.bookcase_owner_id",
            checkparams={
                "param_1": 1,
                "param_2": 1,
                "param_3": 2,
                "param_4": 1,
                "param_5": 3,
                "param_6": 2,
                "param_7": 3,
                "param_8": 3,
            },
        )

    def test_with_standalone_aliased_join(self):
        people = self.tables.people
        values = Values(
            column("bookcase_id", Integer),
            column("bookcase_owner_id", Integer),
        ).data([(1, 1), (2, 1), (3, 2), (3, 3)])
        values = alias(values, "bookcases")

        stmt = select(people, values).select_from(
            people.join(
                values, values.c.bookcase_owner_id == people.c.people_id
            )
        )
        self.assert_compile(
            stmt,
            "SELECT people.people_id, people.age, people.name, "
            "bookcases.bookcase_id, bookcases.bookcase_owner_id FROM people "
            "JOIN (VALUES (:param_1, :param_2), (:param_3, :param_4), "
            "(:param_5, :param_6), (:param_7, :param_8)) AS bookcases "
            "(bookcase_id, bookcase_owner_id) "
            "ON people.people_id = bookcases.bookcase_owner_id",
            checkparams={
                "param_1": 1,
                "param_2": 1,
                "param_3": 2,
                "param_4": 1,
                "param_5": 3,
                "param_6": 2,
                "param_7": 3,
                "param_8": 3,
            },
        )

    def test_lateral(self):
        people = self.tables.people
        values = (
            Values(
                column("bookcase_id", Integer),
                column("bookcase_owner_id", Integer),
                name="bookcases",
            )
            .data([(1, 1), (2, 1), (3, 2), (3, 3)])
            .lateral()
        )
        stmt = select(people, values).select_from(people.join(values, true()))
        self.assert_compile(
            stmt,
            "SELECT people.people_id, people.age, people.name, "
            "bookcases.bookcase_id, bookcases.bookcase_owner_id FROM people "
            "JOIN LATERAL (VALUES (:param_1, :param_2), (:param_3, :param_4), "
            "(:param_5, :param_6), (:param_7, :param_8)) AS bookcases "
            "(bookcase_id, bookcase_owner_id) "
            "ON true",
            checkparams={
                "param_1": 1,
                "param_2": 1,
                "param_3": 2,
                "param_4": 1,
                "param_5": 3,
                "param_6": 2,
                "param_7": 3,
                "param_8": 3,
            },
        )

    def test_from_linting_named(self):
        people = self.tables.people
        values = Values(
            column("bookcase_id", Integer),
            column("bookcase_owner_id", Integer),
            name="bookcases",
        ).data([(1, 1), (2, 1), (3, 2), (3, 3)])
        stmt = select(people, values)

        with testing.expect_warnings(
            r"SELECT statement has a cartesian product between FROM "
            r'element\(s\) "(?:bookcases|people)" and '
            r'FROM element "(?:people|bookcases)"'
        ):
            stmt.compile(linting=FROM_LINTING)

    def test_from_linting_unnamed(self):
        people = self.tables.people
        values = Values(
            column("bookcase_id", Integer),
            column("bookcase_owner_id", Integer),
        ).data([(1, 1), (2, 1), (3, 2), (3, 3)])
        stmt = select(people, values)

        with testing.expect_warnings(
            r"SELECT statement has a cartesian product between FROM "
            r'element\(s\) "(?:\(unnamed VALUES element\)|people)" and '
            r'FROM element "(?:people|\(unnamed VALUES element\))"'
        ):
            stmt.compile(linting=FROM_LINTING)
