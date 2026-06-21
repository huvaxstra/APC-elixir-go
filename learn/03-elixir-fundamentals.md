# Module 3: Elixir Fundamentals

> **What you'll learn**: iex, pattern matching, the pipe operator, immutability, and data processing with Enum/Map.
> By the end of this module you'll build a data processing pipeline in Elixir.

---

## 1. iex — The Interactive Shell

iex is Elixir's REPL (Read-Eval-Print Loop). Think of it as a calculator that speaks Elixir.

```bash
# Start iex
iex
```

```elixir
# Basic arithmetic
iex> 2 + 2
4

iex> 10 / 3
3.3333333333333335

iex> div(10, 3)    # integer division
3

iex> rem(10, 3)    # remainder
1

# String operations
iex> "Hello" <> ", " <> "World!"
"Hello, World!"

# IO is the standard way to print
iex> IO.puts("Hello, Elixir!")
Hello, Elixir!
:ok

# Inspect shows the raw representation (useful for debugging)
iex> IO.inspect([1, 2, 3], label: "my list")
my list: [1, 2, 3]
[1, 2, 3]
```

---

## 2. The `=` Match Operator — NOT Assignment

This is the single most important concept in Elixir. The `=` operator is pattern matching, not assignment.

```elixir
# In most languages, = means "assign the right side to the left"
# In Elixir, = means "match the right side to the left pattern"

# This WORKS — the pattern matches
iex> {name, age} = {"Alice", 30}
"Alice"
30

# Now name and age are bound to their matched values
iex> name
"Alice"

iex> age
30

# This FAILS — the pattern doesn't match
iex> {name, age} = {"Alice"}
** (MatchError) no match of right hand side value: {"Alice"}
# COMMON MISTAKE: Expecting = to work like assignment.
# It WILL crash if the pattern doesn't match. This is intentional.
# It catches bugs at the point they occur, not later.

# You can match specific values too
iex> :ok = do_something()
# If do_something() returns :ok, this works.
# If it returns anything else, it crashes immediately.
# This is called "assertive programming" — fail fast on unexpected values.

# Pin operator (^) — match against an existing variable
iex> x = 10
10
iex> ^x = 10   # matches — x is 10, right side is 10
10
iex> ^x = 20   # DOES NOT MATCH — x is 10, right side is 20
** (MatchError) no match of right hand side value: 20
```

### Why pattern matching matters

```elixir
# DEEP DIVE: Pattern matching enables clean, safe code
# Instead of checking types and values manually:

# BAD (manual checking):
def process(data) do
  if is_tuple(data) do
    {type, value} = data
    if type == :ok do
      # handle success
    else
      # handle error
    end
  end
end

# GOOD (pattern matching):
def process({:ok, value}), do: handle_success(value)
def process({:error, reason}), do: handle_error(reason)
# Each clause handles exactly one case. No if/else chains.
# If neither pattern matches, Elixir raises a FunctionClauseError.
```

---

## 3. Atoms — Named Constants

Atoms are Elixir's version of enums or symbols. They're lightweight, immutable identifiers.

```elixir
# Atoms start with a colon
iex> :ok
:ok

iex> :error
:error

iex> :user_created
:user_created

# Atoms are compared by name, not value
iex> :apple == :apple
true

iex> :apple == :orange
false

# Common pattern: atoms as tags in tuples
iex> {:ok, "result"}
{:ok, "result"}

iex> {:error, "something went wrong"}
{:error, "something went wrong"}

# DEEP DIVE: Why atoms?
# Atoms are memory-efficient identifiers. Instead of passing
# strings like "ok" and "error" around (which allocate memory
# for each character), atoms are single values that are
# compared in constant time. They're perfect for tags.

# Atom naming convention:
# :snake_case — like variables
# :CamelCase — for module-like identifiers
# :! for dangerous operations, :? for predicates
iex> String.starts_with?("hello", "he")
true
```

---

## 4. Data Structures

### Lists — linked lists

```elixir
# Lists are linked lists — fast to prepend, slow to access by index
iex> cities = ["Istanbul", "Ankara", "Izmir"]
["Istanbul", "Ankara", "Izmir"]

# Prepend is O(1) — just add to the head
iex> ["Bursa" | cities]
["Bursa", "Istanbul", "Ankara", "Izmir"]

# Access by index is O(n) — must traverse the list
iex> Enum.at(cities, 1)
"Ankara"

# COMMON MISTAKE: Using lists like arrays
# Lists are NOT arrays. Don't do cities[0] — use Enum.at(cities, 0).
# If you need random access, use a tuple or a MapSet.

# Pattern matching on lists
iex> [first | rest] = cities
["Istanbul", "Ankara", "Izmir"]
iex> first
"Istanbul"
iex> rest
["Ankara", "Izmir"]

# The head/tail pattern is fundamental to list processing
iex> [head | tail] = [1, 2, 3]
[1, 2, 3]
iex> head
1
iex> tail
[2, 3]

# Empty list pattern
iex> [] = []
[]
iex> [] = [1]
** (MatchError) no match of right hand side value: [1]
```

### Tuples — fixed-size collections

```elixir
# Tuples are fixed-size, contiguous in memory, fast to access
iex> point = {10, 20}
{10, 20}

# Access by index — O(1)
iex> elem(point, 0)
10

iex> elem(point, 1)
20

# Pattern matching on tuples
iex> {x, y} = {10, 20}
{10, 20}
iex> x
10
iex> y
20

# COMMON MISTAKE: Tuples vs Lists
# Use tuples when you know the size and types in advance
# Use lists when the size varies
# {name, age, email} — fixed structure, use tuple
# [item1, item2, item3] — variable length, use list

# Tagged tuples — the most important pattern in Elixir
iex> {:ok, data} = {:ok, %{name: "Alice"}}
{:ok, %{name: "Alice"}}

iex> {:error, reason} = {:error, "timeout"}
{:error, "timeout"}
```

### Maps — key-value stores

```elixir
# Maps are hash maps — fast lookup, flexible keys
iex> user = %{name: "Alice", age: 30, city: "Istanbul"}
%{name: "Alice", age: 30, city: "Istanbul"}

# Access with dot notation
iex> user.name
"Alice"

# Access with bracket notation (required for string keys)
iex> user[:age]
30

# Update a map — creates a NEW map (immutability!)
iex> older_user = %{user | age: 31}
%{name: "Alice", age: 31, city: "Istanbul"}

# COMMON MISTAKE: Trying to mutate a map
# user.age = 31  # THIS DOES NOT EXIST IN ELIXIR
# You MUST create a new map with the updated value.
# The old map remains unchanged.

# Pattern matching on maps
iex> %{name: name, age: age} = user
%{name: "Alice", age: 30, city: "Istanbul"}
iex> name
"Alice"
iex> age
30

# You can match partial patterns — only the keys you care about
iex> %{name: name} = user  # ignores age and city
%{name: "Alice", age: 30, city: "Istanbul"}
iex> name
"Alice"

# Map with string keys
iex> %{"status" => "ok", "code" => 200}
%{"status" => "ok", "code" => 200}
```

---

## 5. The Pipe Operator `|>` — Data Flows Left to Right

The pipe operator takes the result of the left side and passes it as the first argument to the function on the right.

```elixir
# Without pipe — reads inside out, hard to follow
iex> String.downcase(String.strip(String.replace("  Hello, World!  ", "World", "Elixir")))
"hello, elixir!"

# With pipe — reads top to bottom, like a data pipeline
iex> "  Hello, World!  "
...> |> String.replace("World", "Elixir")
...> |> String.strip()
...> |> String.downcase()
"hello, elixir!"

# DEEP DIVE: How pipe works
# Each line passes its result as the FIRST argument to the next function.
# "  Hello, World!  " |> String.replace("World", "Elixir")
# becomes: String.replace("  Hello, World!  ", "World", "Elixir")

# The pipe makes data transformations readable
# Think of it like a factory assembly line:
# Raw material → step 1 → step 2 → step 3 → finished product

# Real-world example: processing user input
iex> "  Alice@Example.COM  "
...> |> String.trim()
...> |> String.downcase()
...> |> String.split("@")
...> |> List.first()
"alice"

# Pipe with anonymous functions
iex> [1, 2, 3, 4, 5]
...> |> Enum.map(fn x -> x * 2 end)
...> |> Enum.filter(fn x -> x > 4 end)
[6, 8, 10]
```

---

## 6. Enum — The Data Processing Toolkit

Enum is Elixir's collection processing module. It works with lists, ranges, and anything that implements the Enumerable protocol.

```elixir
# map — transform each element
iex> numbers = [1, 2, 3, 4, 5]
[1, 2, 3, 4, 5]

iex> Enum.map(numbers, fn x -> x * 2 end)
[2, 4, 6, 8, 10]

# Shorthand with capture operator &
iex> Enum.map(numbers, &(&1 * 2))
[2, 4, 6, 8, 10]

# filter — keep elements that match
iex> Enum.filter(numbers, fn x -> rem(x, 2) == 0 end)
[2, 4]

# reduce — accumulate a single result
iex> Enum.reduce(numbers, 0, fn x, acc -> x + acc end)
15
# How it works:
# acc=0, x=1 → acc=1
# acc=1, x=2 → acc=3
# acc=3, x=3 → acc=6
# acc=6, x=4 → acc=10
# acc=10, x=5 → acc=15

# each — side effects (printing, logging)
iex> Enum.each(numbers, fn x -> IO.puts(x) end)
1
2
3
4
5
:ok

# find — first element that matches
iex> Enum.find(numbers, fn x -> x > 3 end)
4

# any?/all? — boolean checks
iex> Enum.any?(numbers, fn x -> x > 3 end)
true

iex> Enum.all?(numbers, fn x -> x > 3 end)
false

# count
iex> Enum.count(numbers)
5

iex> Enum.count(numbers, fn x -> x > 3 end)
2

# sort
iex> Enum.sort([5, 3, 1, 4, 2])
[1, 2, 3, 4, 5]

# Chunk_every — group elements
iex> Enum.chunk_every([1, 2, 3, 4, 5, 6], 2)
[[1, 2], [3, 4], [5, 6]]

# zip — combine two lists
iex> Enum.zip(["Alice", "Bob"], [30, 25])
[{"Alice", 30}, {"Bob", 25}]

# Into — collect into a different structure
iex> Enum.into([1, 2, 3], %{})
%{1 => true, 2 => true, 3 => true}
```

---

## 7. Immutability — Nothing Changes

In Elixir, data is immutable. When you "modify" something, you create a new value. The old value remains unchanged.

```elixir
# This is NOT mutation
iex> list = [1, 2, 3]
[1, 2, 3]

iex> new_list = [0 | list]
[0, 1, 2, 3]

# list is STILL [1, 2, 3] — we didn't change it
iex> list
[1, 2, 3]

# Why immutability matters:
# 1. No race conditions — two processes can read the same data safely
# 2. Predictable — a function can't surprise you by changing data
# 3. Debugging — you can trace exactly when each value was created
# 4. Concurrency — Elixir runs millions of processes safely because of this

# DEEP DIVE: How immutability enables the BEAM VM
# The BEAM (Erlang's VM) can run millions of lightweight processes.
# Each process has its own memory. Because data is immutable,
# processes can safely share data without locks or mutexes.
# This is why Elixir handles concurrency so well.
```

---

## 8. Putting It Together — Data Processing Pipeline

```elixir
defmodule WeatherPipeline do
  @moduledoc """
  Processes raw weather data through a series of transformations.
  Demonstrates pattern matching, pipe operator, and Enum operations.
  """

  # Raw weather data — imagine this comes from multiple APIs
  def raw_data do
    [
      %{city: "Istanbul", temp: 28.5, humidity: 65, conditions: "partly cloudy"},
      %{city: "Ankara", temp: 31.0, humidity: 45, conditions: "sunny"},
      %{city: "Izmir", temp: 33.2, humidity: 55, conditions: "clear"},
      %{city: "Bursa", temp: nil, humidity: nil, conditions: nil},
      %{city: "Antalya", temp: 35.0, humidity: 70, conditions: "hot"},
    ]
  end

  # Step 1: Filter out entries with missing data
  # Uses pattern matching in the filter function
  def filter_valid(data) do
    Enum.filter(data, fn entry ->
      entry.temp != nil and entry.humidity != nil and entry.conditions != nil
    end)
  end

  # Step 2: Add heat index calculation
  # Uses pattern matching to extract values
  def add_heat_index(data) do
    Enum.map(data, fn %{temp: temp, humidity: hum} = entry ->
      # Simplified heat index formula
      heat_index = temp + (hum * 0.05)
      %{entry | heat_index: heat_index}
    end)
  end

  # Step 3: Classify by temperature range
  # Uses pattern matching on the classified map
  def classify_by_temp(data) do
    Enum.map(data, fn entry ->
      category = cond do
        entry.temp < 20 -> :cold
        entry.temp < 30 -> :mild
        entry.temp < 35 -> :warm
        true -> :hot
      end
      Map.put(entry, :category, category)
    end)
  end

  # Step 4: Group by category
  def group_by_category(data) do
    Enum.group_by(data, & &1.category)
  end

  # Step 5: Generate summary for each group
  def summarize_groups(groups) do
    Enum.map(groups, fn {category, entries} ->
      temps = Enum.map(entries, & &1.temp)
      %{
        category: category,
        count: length(entries),
        avg_temp: Enum.sum(temps) / length(temps),
        cities: Enum.map(entries, & &1.city)
      }
    end)
  end

  # The full pipeline — reads like a recipe
  def process do
    raw_data()
    |> filter_valid()
    |> add_heat_index()
    |> classify_by_temp()
    |> group_by_category()
    |> summarize_groups()
  end
end

# Run the pipeline
WeatherPipeline.process()
# => [
#   %{category: :warm, count: 2, avg_temp: 30.75, cities: ["Istanbul", "Antalya"]},
#   %{category: :hot, count: 1, avg_temp: 33.2, cities: ["Izmir"]},
#   %{category: :mild, count: 1, avg_temp: 31.0, cities: ["Ankara"]}
# ]
```

---

## Key Takeaways

1. **iex**: Interactive shell for experimenting. Use `IO.inspect` for debugging.
2. **Pattern matching**: `=` is NOT assignment. It's matching. Crashes on mismatch — this is intentional.
3. **Atoms**: `:ok`, `:error` — lightweight identifiers for tags and states.
4. **Data structures**: Lists (linked, prepend fast), Tuples (fixed-size, fast access), Maps (key-value, flexible).
5. **Pipe `|>`**: Passes left result as first argument to right function. Reads left to right.
6. **Enum**: `map`, `filter`, `reduce` — the three pillars of data processing.
7. **Immutability**: Data never changes. You create new values. This enables safe concurrency.

---

**Next**: [Module 3 Exercise](03-elixir-fundamentals-exercise.md) — Build a data processing pipeline.
