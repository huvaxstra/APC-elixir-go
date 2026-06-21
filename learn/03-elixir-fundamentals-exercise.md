# Exercise 3: Data Processing Pipeline (Elixir Fundamentals)

## Learning Objectives

By completing this exercise, you will:
- Practice pattern matching with the `=` operator
- Use atoms for status codes and states
- Process data with Enum functions (map, filter, reduce)
- Chain operations with the pipe operator `|>`
- Work with structs for structured data

## Scenario

You're building a data processing pipeline for a weather monitoring system. The system receives raw CSV data from multiple weather stations and needs to:
1. Parse the raw data into structured readings
2. Filter readings by various criteria
3. Group and aggregate data by city
4. Generate summary reports

## Starter Code

```elixir
defmodule Weather.Pipeline do
  @moduledoc """
  TODO: A data processing pipeline for weather readings.

  This module demonstrates:
  - Pattern matching with =
  - Struct definition
  - Pipe operator |>
  - Enum functions (map, filter, group_by, reduce)
  """

  # ============================================================
  # PART 1: Define the data structure
  # ============================================================

  # TODO: Create a WeatherReading struct with:
  # - station_id (string)
  # - city (string)
  # - temperature (float)
  # - humidity (float)
  # - condition (string)
  # - timestamp (string)

  # ============================================================
  # PART 2: Parsing
  # ============================================================

  @doc """
  Parses raw CSV data into WeatherReading structs.

  CSV format: "station_id,city,temperature,humidity,condition,timestamp"
  Example: "WS001,Seattle,55.0,80,Rain,2024-01-01T00:00:00Z"

  Returns a list of structs. Ignore invalid lines (return nil, filter later).
  """
  def parse(raw_data) do
    # Your code here
    # Hint: Split by newlines, then split each line by commas
    # Use Float.parse/1 and Integer.parse/1 for numbers

  end

  # ============================================================
  # PART 3: Filtering
  # ============================================================

  @doc """
  Filters readings by condition (case-insensitive).

  ## Examples

      iex> readings |> filter_by_condition("rain")
      [%WeatherReading{condition: "Rain", ...}]

  """
  def filter_by_condition(readings, condition) do
    # Your code here
    # Hint: Use String.downcase/1 for case-insensitive comparison

  end

  @doc """
  Filters readings by temperature range.

  Returns readings where temperature is between min and max (inclusive).
  """
  def filter_by_temperature(readings, min_temp, max_temp) do
    # Your code here

  end

  # ============================================================
  # PART 4: Grouping and Aggregation
  # ============================================================

  @doc """
  Groups readings by city.

  Returns a map: %{city_name => [readings]}

  ## Examples

      iex> readings |> group_by_city()
      %{"Seattle" => [...], "Phoenix" => [...]}

  """
  def group_by_city(readings) do
    # Your code here
    # Hint: Use Enum.group_by/2

  end

  @doc """
  Calculates average temperature per city.

  Returns a map: %{city_name => average_temperature}

  ## Examples

      iex> readings |> average_by_city()
      %{"Seattle" => 56.5, "Phoenix" => 105.0}

  """
  def average_by_city(readings) do
    # Your code here
    # Hint: Group by city, then map to calculate average

  end

  # ============================================================
  # PART 5: Finding Extremes
  # ============================================================

  @doc """
  Finds the hottest reading.

  Returns {:ok, reading} or {:error, :no_data}.

  ## Examples

      iex> Weather.Pipeline.hottest_reading(readings)
      {:ok, %WeatherReading{city: "Phoenix", temperature: 105.0}}

  """
  def hottest_reading([]), do: {:error, :no_data}
  def hottest_reading(readings) do
    # Your code here
    # Hint: Use Enum.max_by/2 with a function that returns temperature

  end

  @doc """
  Finds the coldest reading.

  Returns {:ok, reading} or {:error, :no_data}.
  """
  def coldest_reading([]), do: {:error, :no_data}
  def coldest_reading(readings) do
    # Your code here

  end

  # ============================================================
  # PART 6: Reporting
  # ============================================================

  @doc """
  Generates a summary report string.

  Returns a multi-line string with:
  - Total readings count
  - Hottest city and temperature
  - Coldest city and temperature
  - Average temperature per city
  """
  def generate_report(readings) do
    # Your code here
    # Hint: Use case for hot/cold, Enum.each for averages

  end
end
```

## Hints

### Part 1: Struct Definition
```elixir
# Use defstruct to define a struct
defstruct [:field1, :field2, :field3]
```

### Part 2: Parsing
```elixir
# Split CSV line
["station_id", "city", "temp_str", "hum_str", "condition", "timestamp"] = String.split(line, ",")

# Convert strings to numbers
{temp, _} = Float.parse(temp_str)
{humidity, _} = Integer.parse(hum_str)
```

### Part 3: Filtering
```elixir
# Case-insensitive comparison
String.downcase(reading.condition) == String.downcase(condition)
```

### Part 4: Grouping
```elixir
# Group by a field
readings |> Enum.group_by(& &1.city)
```

### Part 5: Finding Extremes
```elixir
# Find max by a field
readings |> Enum.max_by(& &1.temperature)
```

### Part 6: Reporting
```elixir
# Build a multi-line string
"""
Total readings: #{length(readings)}
Hottest: #{city} (#{temp}°F)
"""
```

## Test Cases

```elixir
# Test data
raw = """
WS001,Seattle,55.0,80,Rain,2024-01-01T00:00:00Z
WS002,Phoenix,105.0,15,Sunny,2024-01-01T00:00:00Z
WS003,Chicago,45.0,60,Snow,2024-01-01T00:00:00Z
WS004,Seattle,58.0,75,Cloudy,2024-01-01T01:00:00Z
WS005,Miami,82.0,70,Sunny,2024-01-01T00:00:00Z
"""

# Expected outputs
readings = Weather.Pipeline.parse(raw)
length(readings) == 5  # Should parse 5 valid readings

rainy = Weather.Pipeline.filter_by_condition(readings, "rain")
length(rainy) == 1     # Only Seattle has Rain

sunny = Weather.Pipeline.filter_by_condition(readings, "SUNNY")
length(sunny) == 2     # Phoenix and Miami (case-insensitive)

hot = Weather.Pipeline.filter_by_temperature(readings, 80, 200)
length(hot) == 2       # Phoenix and Miami

cities = Weather.Pipeline.group_by_city(readings)
Map.keys(cities) == ["Seattle", "Phoenix", "Chicago", "Miami"]

averages = Weather.Pipeline.average_by_city(readings)
averages["Seattle"] == 56.5  # (55.0 + 58.0) / 2

{:ok, hottest} = Weather.Pipeline.hottest_reading(readings)
hottest.city == "Phoenix"
hottest.temperature == 105.0

{:ok, coldest} = Weather.Pipeline.coldest_reading(readings)
coldest.city == "Chicago"
coldest.temperature == 45.0
```

## Solution

<details>
<summary>Click to reveal solution</summary>

```elixir
defmodule Weather.Pipeline do
  @moduledoc """
  A data processing pipeline for weather readings.
  """

  defstruct [:station_id, :city, :temperature, :humidity, :condition, :timestamp]

  def parse(raw_data) do
    raw_data
    |> String.split("\n")
    |> Enum.map(&String.trim/1)
    |> Enum.filter(&(&1 != ""))
    |> Enum.map(&parse_line/1)
    |> Enum.reject(&is_nil/1)
  end

  def filter_by_condition(readings, condition) do
    target = String.downcase(condition)

    readings
    |> Enum.filter(fn reading ->
      String.downcase(reading.condition) == target
    end)
  end

  def filter_by_temperature(readings, min_temp, max_temp) do
    readings
    |> Enum.filter(fn reading ->
      reading.temperature >= min_temp and reading.temperature <= max_temp
    end)
  end

  def group_by_city(readings) do
    readings
    |> Enum.group_by(& &1.city)
  end

  def average_by_city(readings) do
    readings
    |> group_by_city()
    |> Enum.map(fn {city, city_readings} ->
      avg = city_readings
            |> Enum.map(& &1.temperature)
            |> Enum.sum()
            |> Kernel./(length(city_readings))

      {city, Float.round(avg, 1)}
    end)
    |> Map.new()
  end

  def hottest_reading([]), do: {:error, :no_data}
  def hottest_reading(readings) do
    hottest = readings |> Enum.max_by(& &1.temperature)
    {:ok, hottest}
  end

  def coldest_reading([]), do: {:error, :no_data}
  def coldest_reading(readings) do
    coldest = readings |> Enum.min_by(& &1.temperature)
    {:ok, coldest}
  end

  def generate_report(readings) do
    hot_city = case hottest_reading(readings) do
      {:ok, r} -> "#{r.city} (#{r.temperature}°F)"
      {:error, _} -> "N/A"
    end

    cold_city = case coldest_reading(readings) do
      {:ok, r} -> "#{r.city} (#{r.temperature}°F)"
      {:error, _} -> "N/A"
    end

    avg_section = average_by_city(readings)
                  |> Enum.map(fn {city, temp} -> "  #{city}: #{temp}°F" end)
                  |> Enum.join("\n")

    """
    Weather Report
    ==============

    Total readings: #{length(readings)}
    Hottest: #{hot_city}
    Coldest: #{cold_city}

    Average by City:
    #{avg_section}
    """
  end

  defp parse_line(line) do
    case String.split(line, ",") do
      [station_id, city, temp_str, hum_str, condition, timestamp] ->
        case {Float.parse(temp_str), Integer.parse(hum_str)} do
          {{temp, _}, {humidity, _}} ->
            %__MODULE__{
              station_id: station_id,
              city: city,
              temperature: temp,
              humidity: humidity,
              condition: condition,
              timestamp: timestamp
            }
          _ -> nil
        end
      _ -> nil
    end
  end
end
```

</details>

## Common Mistakes to Avoid

1. **Thinking `=` is assignment**: It's pattern matching — it checks and binds
2. **Not handling case-insensitivity**: Use `String.downcase/1` for comparisons
3. **Forgetting to filter nils**: Parse functions may return nil for invalid data
4. **Using `Enum.each` for transformations**: Use `Enum.map` instead
5. **Not handling empty lists**: Check for `[]` before calling `Enum.max_by`

## Extension Challenges

1. **Add a `median_temperature` function**: Calculate median instead of mean
2. **Add a `to_csv` function**: Convert readings back to CSV format
3. **Add a `from_json` function**: Parse JSON data instead of CSV
4. **Add a `top_n_cities` function**: Return N cities with highest average temperature
5. **Add error tuples to parsing**: Return `{:ok, reading}` or `{:error, reason}`

## Deep Dive: Pattern Matching in Practice

Pattern matching is Elixir's superpower. Here's why it matters:

```elixir
# Without pattern matching (imperative style)
def process(data) do
  if data != nil do
    if length(data) > 0 do
      first = Enum.at(data, 0)
      if first != nil do
        # ... more nested conditionals
      end
    end
  end
end

# With pattern matching (functional style)
def process(nil), do: {:error, :no_data}
def process([]), do: {:error, :empty_list}
def process([first | _rest]), do: {:ok, first}

# Each clause handles one case — no nesting
# The compiler ensures all cases are covered
```

Pattern matching makes code:
- **Readible**: Each case is explicit
- **Safe**: No null pointer exceptions
- **Testable**: Easy to test each case separately

---

## Grading Checklist

- [ ] WeatherReading struct has all required fields
- [ ] parse/1 correctly splits CSV lines
- [ ] parse/1 handles invalid lines gracefully
- [ ] filter_by_condition/2 is case-insensitive
- [ ] filter_by_temperature/2 uses inclusive range
- [ ] group_by_city/1 returns correct map structure
- [ ] average_by_city/1 calculates correct averages
- [ ] hottest_reading/1 returns {:ok, reading} or {:error, :no_data}
- [ ] coldest_reading/1 returns {:ok, reading} or {:error, :no_data}
- [ ] generate_report/1 produces formatted output
- [ ] All functions use pipe operator for readability
- [ ] No mutation of original data (immutability)

---

## Next Steps

After completing this exercise:
1. Test with different CSV data
2. Add more filter functions (by humidity, by timestamp)
3. Try implementing a JSON parser
4. Move on to Module 4: OTP & GenServer
