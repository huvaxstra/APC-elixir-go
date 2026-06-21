# Module 1 Exercise: CLI Weather Tool

> **Goal**: Build a command-line tool that fetches and displays weather data for a given city.
> This exercise reinforces variables, types, structs, interfaces, functions, and control flow.

---

## Starter Code

```go
package main

import (
    "encoding/json"
    "fmt"
    "net/http"
    "os"
    "strings"
    "time"
)

// WeatherReport holds weather data for a single city.
// Each field maps to a JSON key from the API response.
type WeatherReport struct {
    City        string  `json:"city"`
    Temperature float64 `json:"temperature"`
    Humidity    int     `json:"humidity"`
    Conditions  string  `json:"conditions"`
    WindSpeed   float64 `json:"wind_speed"`
}

// WeatherProvider defines the contract for any weather data source.
// Any struct with a GetWeather(city string) method satisfies this.
type WeatherProvider interface {
    GetWeather(city string) (WeatherReport, error)
}

// TODO: Implement the MockWeatherClient struct.
// It should have a single field: Responses map[string]WeatherReport
// This lets us simulate API responses without a real network call.

// TODO: Implement GetWeather for MockWeatherClient.
// It should look up the city in the Responses map.
// If the city is not found, return an error with a clear message.

// DisplayWeather prints a formatted weather report.
// It should handle the case where Humidity is 0 (unknown).
// It should also format temperature to 1 decimal place.
func DisplayWeather(report WeatherReport) {
    // TODO: Implement this function.
    // Print a formatted box with city, temperature, humidity, conditions, wind.
    // Use fmt.Printf with formatting verbs:
    //   %s for strings
    //   %.1f for float64 (1 decimal place)
    //   %d for int
}

// ParseTemperature converts a string like "28.5" to float64.
// If the input is empty or invalid, return 0 and an error.
func ParseTemperature(input string) (float64, error) {
    // TODO: Implement this function.
    // Hints:
    //   - Use strings.TrimSpace to remove whitespace
    //   - Use fmt.Sscanf to parse the float
    //   - Handle empty string case
    //   - Return (0, fmt.Errorf(...)) on failure
}

// FormatWindSpeed converts m/s to km/h and returns a human-readable string.
// Speed ranges: <5 = "Calm", 5-15 = "Breezy", >15 = "Windy"
func FormatWindSpeed(speedMS float64) string {
    // TODO: Implement this function.
    // Convert: kmh = speedMS * 3.6
    // Return string like "12.6 km/h (Breezy)"
    // Hints:
    //   - Use an if/else chain for the range check
    //   - Use fmt.Sprintf to build the string
}

func main() {
    // Parse command line arguments
    // os.Args[0] is the program name, os.Args[1] is the city
    if len(os.Args) < 2 {
        fmt.Fprintf(os.Stderr, "Usage: weather <city>\n")
        fmt.Fprintf(os.Stderr, "Example: weather Istanbul\n")
        os.Exit(1)
    }

    city := os.Args[1]

    // Create a mock client with sample data
    mockData := map[string]WeatherReport{
        "Istanbul": {
            City: "Istanbul", Temperature: 28.5,
            Humidity: 65, Conditions: "Partly Cloudy", WindSpeed: 3.2,
        },
        "Ankara": {
            City: "Ankara", Temperature: 31.0,
            Humidity: 45, Conditions: "Sunny", WindSpeed: 1.8,
        },
        "Izmir": {
            City: "Izmir", Temperature: 33.2,
            Humidity: 55, Conditions: "Clear", WindSpeed: 2.5,
        },
    }

    client := &MockWeatherClient{Responses: mockData}

    // Fetch weather using the provider interface
    report, err := client.GetWeather(city)
    if err != nil {
        fmt.Fprintf(os.Stderr, "Error: %v\n", err)
        os.Exit(1)
    }

    DisplayWeather(report)
}
```

---

## Hints

### Hint 1: MockWeatherClient struct
Think of it as a dictionary lookup. The struct holds pre-made weather data keyed by city name.

### Hint 2: GetWeather implementation
Use map lookup syntax: `value, ok := map[key]`. The `ok` boolean tells you if the key exists.

### Hint 3: DisplayWeather formatting
Use `fmt.Println` for the box borders. Use `fmt.Printf` with `%s` and `%.1f` for the data rows.

### Hint 4: ParseTemperature
Use `strings.TrimSpace(input)` first, then `var temp float64; fmt.Sscanf(input, "%f", &temp)`. Check if input is empty before parsing.

### Hint 5: FormatWindSpeed
Calculate `kmh := speedMS * 3.6`. Use `if/else if/else` for the three speed ranges. Build the string with `fmt.Sprintf`.

### Hint 6: Common mistakes to avoid
- Don't forget to check `len(os.Args)` before accessing `os.Args[1]`
- Don't forget to handle the case where `GetWeather` returns an error
- Don't use `:=` when reassigning — use `=`

---

## Solution

```go
package main

import (
    "encoding/json"
    "fmt"
    "net/http"
    "os"
    "strings"
    "time"
)

// WeatherReport holds weather data for a single city.
type WeatherReport struct {
    City        string  `json:"city"`
    Temperature float64 `json:"temperature"`
    Humidity    int     `json:"humidity"`
    Conditions  string  `json:"conditions"`
    WindSpeed   float64 `json:"wind_speed"`
}

// WeatherProvider defines the contract for any weather data source.
type WeatherProvider interface {
    GetWeather(city string) (WeatherReport, error)
}

// MockWeatherClient simulates an API by returning pre-stored data.
// This is useful for testing — no network calls needed.
type MockWeatherClient struct {
    Responses map[string]WeatherReport
}

// GetWeather looks up weather data for a city in the mock database.
// Returns an error if the city is not in the map.
// This follows the standard Go error pattern: (result, error).
func (m *MockWeatherClient) GetWeather(city string) (WeatherReport, error) {
    // Normalize input: "istanbul" becomes "Istanbul"
    normalized := strings.Title(strings.ToLower(city))

    // Map lookup: value is the report, ok tells us if key exists
    report, ok := m.Responses[normalized]
    if !ok {
        // COMMON MISTAKE: Returning a zero-value struct instead of an error
        // Always return an error so callers know something went wrong
        return WeatherReport{}, fmt.Errorf("city %q not found", city)
    }
    return report, nil
}

// DisplayWeather prints a formatted box with weather data.
// Uses fmt.Printf formatting verbs for aligned output.
func DisplayWeather(report WeatherReport) {
    // Determine wind description based on speed
    windDesc := FormatWindSpeed(report.WindSpeed)

    // Build the display box
    fmt.Println("╔══════════════════════════════════════╗")
    fmt.Printf("║  Weather Report: %-18s ║\n", report.City)
    fmt.Println("╠══════════════════════════════════════╣")
    fmt.Printf("║  Temperature:  %-21.1f ║\n", report.Temperature)
    fmt.Printf("║  Humidity:     %-21d ║\n", report.Humidity)
    fmt.Printf("║  Conditions:   %-21s ║\n", report.Conditions)
    fmt.Printf("║  Wind:         %-21s ║\n", windDesc)
    fmt.Println("╚══════════════════════════════════════╝")
}

// ParseTemperature converts a string to a float64 temperature.
// Returns (0, error) if the input is empty or not a valid number.
// COMMON MISTAKE: Forgetting to TrimSpace — " 28.5 " won't parse without it.
func ParseTemperature(input string) (float64, error) {
    // Remove whitespace from both ends
    cleaned := strings.TrimSpace(input)

    // Handle empty input
    if cleaned == "" {
        return 0, fmt.Errorf("temperature input is empty")
    }

    // Parse the float — Sscanf returns the number of items scanned
    var temp float64
    n, err := fmt.Sscanf(cleaned, "%f", &temp)
    if err != nil || n != 1 {
        return 0, fmt.Errorf("invalid temperature %q: must be a number", input)
    }

    // Sanity check: temperatures on Earth are between -90 and 60 Celsius
    if temp < -90 || temp > 60 {
        return 0, fmt.Errorf("temperature %.1f is outside realistic range (-90 to 60°C)", temp)
    }

    return temp, nil
}

// FormatWindSpeed converts m/s to km/h and returns a descriptive string.
// Speed ranges: <5 = "Calm", 5-15 = "Breezy", >15 = "Windy"
// DEEP DIVE: This function demonstrates if/else chains and string formatting.
func FormatWindSpeed(speedMS float64) string {
    // Convert meters per second to kilometers per hour
    kmh := speedMS * 3.6

    // Classify the wind speed
    var description string
    if kmh < 5 {
        description = "Calm"
    } else if kmh <= 15 {
        description = "Breezy"
    } else {
        description = "Windy"
    }

    // Build the formatted string
    return fmt.Sprintf("%.1f km/h (%s)", kmh, description)
}

func main() {
    // Parse command line arguments
    if len(os.Args) < 2 {
        fmt.Fprintf(os.Stderr, "Usage: weather <city>\n")
        fmt.Fprintf(os.Stderr, "Example: weather Istanbul\n")
        os.Exit(1)
    }

    city := os.Args[1]

    // Create mock data — simulates what an API would return
    mockData := map[string]WeatherReport{
        "Istanbul": {
            City: "Istanbul", Temperature: 28.5,
            Humidity: 65, Conditions: "Partly Cloudy", WindSpeed: 3.2,
        },
        "Ankara": {
            City: "Ankara", Temperature: 31.0,
            Humidity: 45, Conditions: "Sunny", WindSpeed: 1.8,
        },
        "Izmir": {
            City: "Izmir", Temperature: 33.2,
            Humidity: 55, Conditions: "Clear", WindSpeed: 2.5,
        },
    }

    // Use the interface — could swap to a real API client later
    client := &MockWeatherClient{Responses: mockData}

    // Fetch weather
    report, err := client.GetWeather(city)
    if err != nil {
        fmt.Fprintf(os.Stderr, "Error: %v\n", err)
        os.Exit(1)
    }

    // Display result
    DisplayWeather(report)
}
```

---

## Test Cases

Run these commands to verify your implementation:

```bash
# Should display Istanbul weather
go run weather.go Istanbul

# Should display Ankara weather
go run weather.go Ankara

# Should display error message
go run weather.go London

# Should display usage message
go run weather.go
```

Expected output for `weather.go Istanbul`:
```
╔══════════════════════════════════════╗
║  Weather Report: Istanbul            ║
╠══════════════════════════════════════╣
║  Temperature:  28.5                  ║
║  Humidity:     65                    ║
║  Conditions:   Partly Cloudy        ║
║  Wind:         11.5 km/h (Breezy)   ║
╚══════════════════════════════════════╝
```

---

## Extension Challenges

1. **Add color**: Use ANSI escape codes to color the output (green for sunny, blue for rain).
2. **Add --json flag**: Use `os.Args` to check for a `--json` flag and output raw JSON instead of the formatted box.
3. **Add real API**: Replace MockWeatherClient with a real HTTP client that calls a weather API.

---

**Next**: [Module 2 — Go CLI & HTTP](02-go-cli-http.md)
