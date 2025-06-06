# Jinja macros

SQLMesh supports macros from the [Jinja](https://jinja.palletsprojects.com/en/3.1.x/) templating system.

Jinja's macro approach is pure string substitution. Unlike SQLMesh macros, they assemble SQL query text without building a semantic representation.

**NOTE:** SQLMesh projects support the standard Jinja function library only - they do **not** support dbt-specific jinja functions like `{{ ref() }}`. dbt-specific functions are allowed in dbt projects being run with the [SQLMesh adapter](../../integrations/dbt.md).

## Basics

Jinja uses curly braces `{}` to differentiate macro from non-macro text. It uses the second character after the left brace to determine what the text inside the braces will do.

The three curly brace symbols are:

- `{{...}}` creates Jinja expressions. Expressions are replaced by text that is incorporated into the rendered SQL query; they can contain macro variables and functions.
- `{%...%}` creates Jinja statements. Statements give instructions to Jinja, such as setting variable values, control flow with `if`, `for` loops, and defining macro functions.
- `{#...#}` creates Jinja comments. These comments will not be included in the rendered SQL query.

Since Jinja strings are not syntactically valid SQL expressions and cannot be parsed as such, the model query must be wrapped in a special `JINJA_QUERY_BEGIN; ...; JINJA_END;` block in order for SQLMesh to detect it:

```sql linenums="1" hl_lines="5 9"
MODEL (
  name sqlmesh_example.full_model
);

JINJA_QUERY_BEGIN;

SELECT {{ 1 + 1 }};

JINJA_END;
```

Similarly, to use Jinja expressions as part of statements that should be evaluated before or after the model query, the `JINJA_STATEMENT_BEGIN; ...; JINJA_END;` block should be used:

```sql linenums="1"
MODEL (
  name sqlmesh_example.full_model
);

JINJA_STATEMENT_BEGIN;
{{ pre_hook() }}
JINJA_END;

JINJA_QUERY_BEGIN;
SELECT {{ 1 + 1 }};
JINJA_END;

JINJA_STATEMENT_BEGIN;
{{ post_hook() }}
JINJA_END;
```

## SQLMesh predefined variables

SQLMesh provides multiple [predefined macro variables](./macro_variables.md) you may reference in jinja code.

Some predefined variables provide information about the SQLMesh project itself, like the [`runtime_stage`](./macro_variables.md#runtime-variables) and [`this_model`](./macro_variables.md#runtime-variables) variables.

Other predefined variables are [temporal](./macro_variables.md#temporal-variables), like `start_ds` and `execution_date`. They are used to build incremental model queries and are only available in incremental model kinds.

Access predefined macro variables by passing their unquoted name in curly braces. For example, this demonstrates how to access the `start_ds` and `end_ds` variables:

```sql linenums="1"
JINJA_QUERY_BEGIN;

SELECT *
FROM table
WHERE time_column BETWEEN '{{ start_ds }}' and '{{ end_ds }}';

JINJA_END;
```

Because the two macro variables return string values, we must surround the curly braces with single quotes `'`. Other macro variables, such as `start_epoch`, return numeric values and do not require the single quotes.

The `gateway` variable uses a slightly different syntax than other predefined variables because it is a function call. Instead of the bare name `{{ gateway }}`, it must include parentheses: `{{ gateway() }}`.

## User-defined variables

SQLMesh supports two kinds of user-defined macro variables: global and local.

Global macro variables are defined in the project configuration file and can be accessed in any project model.

Local macro variables are defined in a model definition and can only be accessed in that model.

### Global variables

Learn more about defining global variables in the [SQLMesh macros documentation](./sqlmesh_macros.md#global-variables).

Access global variable values in a model definition using the `{{ var() }}` jinja function. The function requires the name of the variable _in single quotes_ as the first argument and an optional default value as the second argument. The default value is a safety mechanism used if the variable name is not found in the project configuration file.

For example, a model would access a global variable named `int_var` like this:

```sql linenums="1"
JINJA_QUERY_BEGIN;

SELECT *
FROM table
WHERE int_variable = {{ var('int_var') }};

JINJA_END;
```

A default value can be passed as a second argument to the `{{ var() }}` jinja function, which will be used as a fallback value if the variable is missing from the configuration file.

In this example, the `WHERE` clause would render to `WHERE some_value = 0` if no variable named `missing_var` was defined in the project configuration file:

```sql linenums="1"
JINJA_QUERY_BEGIN;

SELECT *
FROM table
WHERE some_value = {{ var('missing_var', 0) }};

JINJA_END;
```

### Gateway variables

Like global variables, gateway variables are defined in the project configuration file. However, they are specified in a specific gateway's `variables` key. Learn more about defining gateway variables in the [SQLMesh macros documentation](./sqlmesh_macros.md#gateway-variables).

Access gateway variables in models using the same methods as [global variables](#global-variables).

Gateway-specific variable values take precedence over variables with the same name specified in the configuration file's root `variables` key.

### Blueprint variables

Blueprint variables are defined as a property of the `MODEL` statement, and serve as a mechanism for [creating model templates](../models/sql_models.md):

```sql linenums="1"
MODEL (
  name @customer.some_table,
  kind FULL,
  blueprints (
    (customer := customer1, field_a := x, field_b := y),
    (customer := customer2, field_a := z)
  )
);

JINJA_QUERY_BEGIN;
SELECT
  {{ blueprint_var('field_a') }}
  {{ blueprint_var('field_b', 'default_b') }} AS field_b
FROM {{ blueprint_var('customer') }}.some_source
JINJA_END;
```

Blueprint variables can be accessed using the `{{ blueprint_var() }}` macro function, which also supports specifying default values in case the variable is undefined (similar to `{{ var() }}`).


### Local variables

Define your own variables with the Jinja statement `{% set ... %}`. For example, we could specify the name of the `num_orders` column in the `sqlmesh_example.full_model` like this:

```sql linenums="1"
MODEL (
  name sqlmesh_example.full_model,
  kind FULL,
  cron '@daily',
  audits (assert_positive_order_ids),
);

JINJA_QUERY_BEGIN;

{% set my_col = 'num_orders' %} -- Jinja definition of variable `my_col`

SELECT
  item_id,
  count(distinct id) AS {{ my_col }}, -- Reference to Jinja variable {{ my_col }}
FROM
  sqlmesh_example.incremental_model
GROUP BY item_id

JINJA_END;
```

Note that the Jinja set statement is written after the `MODEL` statement and before the SQL query.

Jinja variables can be string, integer, or float data types. They can also be an iterable data structure, such as a list, tuple, or dictionary. Each of these data types and structures supports multiple [Python methods](https://jinja.palletsprojects.com/en/3.1.x/templates/#python-methods), such as the `upper()` method for strings.

## Macro operators

### Control flow operators

#### for loops

For loops let you iterate over a collection of items to condense repetitive code and easily change the values used by the code.

Jinja for loops begin with `{% for ... %}` and end with `{% endfor %}`. This example demonstrates creating indicator variables with `CASE WHEN` using a Jinja for loop:

```sql linenums="1"
SELECT
  {% for vehicle_type in ['car', 'truck', 'bus']}
    CASE WHEN user_vehicle = '{{ vehicle_type }}' THEN 1 ELSE 0 END as vehicle_{{ vehicle_type }},
  {% endfor %}
FROM table
```

Note that the `vehicle_type` values are quoted in the list `['car', 'truck', 'bus']`. Jinja removes those quotes during processing, so the reference `'{{ vehicle_type }}` in the `CASE WHEN` statement must be in quotes. The reference `vehicle_{{ vehicle_type }}` does not require quotes.

Also note that a comma is present at the end of the `CASE WHEN` line. Trailing commas are not valid SQL and would normally require special handling, but SQLMesh's semantic understanding of the query allows it to identify and remove the offending comma.

The example renders to this after SQLMesh processing:

```sql linenums="1"
SELECT
  CASE WHEN user_vehicle = 'car' THEN 1 ELSE 0 END AS vehicle_car,
  CASE WHEN user_vehicle = 'truck' THEN 1 ELSE 0 END AS vehicle_truck,
  CASE WHEN user_vehicle = 'bus' THEN 1 ELSE 0 END AS vehicle_bus
FROM table
```

In general, it is a best practice to define lists of values separately from their use. We could do that like this:

```sql linenums="1"
{% set vehicle_types = ['car', 'truck', 'bus'] %}

SELECT
  {% for vehicle_type in vehicle_types }
    CASE WHEN user_vehicle = '{{ vehicle_type }}' THEN 1 ELSE 0 END as vehicle_{{ vehicle_type }},
  {% endfor %}
FROM table
```

The rendered query would be the same as before.

#### if

if statements allow you to take an action (or not) based on some condition.

Jinja if statements begin with `{% if ... %}` and end with `{% endif %}`. The starting `if` statement must contain code that evaluates to `True` or `False`. For example, all of `True`, `1 + 1 == 2`, and `'a' in ['a', 'b']` evaluate to `True`.

As an example, you might want a model to only include a column if the model was being run for testing purposes. We can do that by setting a variable indicating whether it's a testing run that determines whether the query includes `testing_column`:

```sql linenums="1"
{% set testing = True %}

SELECT
  normal_column,
  {% if testing %}
    testing_column
  {% endif %}
FROM table
```

Because `testing` is `True`, the rendered query would be:

```sql linenums="1"
SELECT
  normal_column,
  testing_column
FROM table
```

## User-defined macro functions

User-defined macro functions allow the same macro code to be used in multiple models.

Jinja macro functions should be placed in `.sql` files in the SQLMesh project's `macros` directory. Multiple functions can be defined in one `.sql` file, or they can be distributed across multiple files.

Jinja macro functions are defined with the `{% macro %}` and `{% endmacro %}` statements. The macro function name and arguments are specified in the `{% macro %}` statement.

For example, a macro function named `print_text` that takes no arguments could be defined with:

```sql linenums="1"
{% macro print_text() %}
text
{% endmacro %}
```

This macro function would be called in a SQL model with `{{ print_text() }}`, which would be substituted with `text`" in the rendered query.

Macro function arguments are placed in the parentheses next to the macro name. For example, this macro generates a SQL column with an alias based on the arguments `expression` and `alias`:

```sql linenums="1"
{% macro alias(expression, alias) %}
  {{ expression }} AS {{ alias }}
{% endmacro %}
```

We might call this macro function in a SQL query like this:

```sql linenums="1"
SELECT
  item_id,
  {{ alias('item_id', 'item_id2')}}
FROM table
```

After processing, it would render to this:

```sql linenums="1"
SELECT
  item_id,
  item_id AS item_id2
FROM table
```

Note that both argument values are quoted in the call `alias('item_id', 'item_id2')` but are not quoted in the rendered query. During the rendering process, SQLMesh uses its semantic understanding of the query to build the rendered text - it recognizes that the first argument is a column name and that column aliases are unquoted by default.

In that example, the SQL query selects the column `item_id` with the alias `item_id2`. If instead we wanted to select the *string* `'item_id'` with the name `item_id2`, we would pass the `expression` argument with double quotes around it: `"'item_id'"`:

```sql linenums="1"
SELECT
  item_id,
  {{ alias("'item_id'", 'item_id2')}}
FROM table
```

After processing, it would render to this:

```sql linenums="1"
SELECT
  item_id,
  'item_id' AS item_id2
FROM table
```

The double quotes around `"'item_id'"` signal to SQLMesh that it is not a column name.

Some SQL dialects interpret double and single quotes differently. We could replace the rendered single quoted `'item_id'` with double quoted `"item_id"` in the previous example by switching the placement of quotes in the macro function call. Instead of `alias("'item_id'", 'item_id2')` we would use `alias('"item_id"', 'item_id2')`.

## Mixing macro systems

SQLMesh supports both the Jinja and [SQLMesh](./sqlmesh_macros.md) macro systems. We strongly recommend using only one system in a single model - if both are present, they may fail or behave in unintuitive ways.

[Predefined SQLMesh macro variables](./macro_variables.md) can be used in a query containing user-defined Jinja variables and functions. However, predefined variables passed as arguments to a user-defined Jinja macro function must use the Jinja curly brace syntax `{{ start_ds }}` instead of the SQLMesh macro `@` prefix syntax `@start_ds`. Note that curly brace syntax may require quoting to generate the equivalent of the `@` syntax.
