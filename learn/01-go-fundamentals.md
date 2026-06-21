# Module 1: Go Fundamentals

> **What you'll learn**: Variables, types, control flow, functions, structs, and interfaces in Go.
> By the end of this module you'll build a working CLI weather tool from scratch.

---

## 1. Variables and Types

### Variables are like labeled boxes

Think of a variable as a labeled box in a warehouse. The label (name) tells you what's inside. The box size (type) determines what fits.

Go has two ways to create variables:

```go
// The "var" keyword — explicit, verbose, clear intent
var cityName string = "Istanbul"

// The ":=" shorthand — Go infers the type from the value
population := 15_840_000 // Go infers: int
temperature := 22.5      // Go infers: float64
isRaining := true         // Go infers: bool
```

### Zero values — what happens when you forget to assign

Every type in Go has a "zero value" — what the variable holds when you declare it without assigning:

```go
var age int           // 0
var name string       // "" (empty string)
var active bool       // false
var score float64     // 0.0
```

**Why this matters**: Go will never give you a null pointer or undefined. Every variable starts with a known value. This eliminates an entire class of bugs.

### Primitive types

```go
// Numbers
var count int = 42           // int: whole numbers, platform-dependent size
var precise int64 = 9_000_000_000 // int64: when you need more range
var pi float64 = 3.14159     // float64: decimal numbers (Go's default float)
var letter byte = 'A'        // byte: alias for uint8, represents ASCII characters
var symbol rune = '🎉'       // rune: alias for int32, represents Unicode code points

// Strings
var greeting string = "Merhaba" // UTF-8 encoded text

// Boolean
var isOnline bool = true // true or false, nothing else
```

**DEEP DIVE**: `byte` vs `rune` — A `byte` is one octet (8 bits), enough for ASCII. A `rune` is a full Unicode code point (32 bits). When you range over a string in Go, you get `rune`s because UTF-8 characters can be 1–4 bytes. Use `byte` when dealing with raw binary data. Use `rune` when dealing with text that might contain emoji or non-Latin scripts.

### Common mistake — confusing `=` with `:=`

```go
// COMMON MISTAKE: Using := when you meant = (or vice versa)

// := creates a NEW variable. It does NOT reassign.
x := 10
x := 20 // COMPILE ERROR: no new variables on left side of :=

// = reassigns an EXISTING variable.
x = 20 // This works — x already exists

// You CAN use := when at least one variable on the left is new:
x, y := 10, 20 // x was declared before, y is new. This works.
```

---

## 2. Control Flow

### if/else — conditions

```go
temperature := 35

// Standard if/else
if temperature > 30 {
    fmt.Println("It's hot outside")
} else if temperature > 20 {
    fmt.Println("Nice weather")
} else {
    fmt.Println("Bring a jacket")
}

// Go allows a short statement before the condition
// This creates a variable scoped ONLY to the if/else block
if err := connectToWeatherAPI(); err != nil {
    // err exists only inside this block
    fmt.Printf("Connection failed: %v\n", err)
    return
}
// err does NOT exist here — it was scoped to the if block
```

**Why the scoped variable matters**: It forces you to handle errors at the point they occur. No forgotten error checks, no leaked variables.

### for — Go's only loop

Go has exactly one loop keyword: `for`. It replaces `while`, `do-while`, and C-style `for` loops.

```go
// C-style for loop
for i := 0; i < 5; i++ {
    fmt.Println(i) // prints 0, 1, 2, 3, 4
}

// While loop equivalent (only the condition)
count := 0
for count < 5 {
    fmt.Println(count)
    count++
}

// Infinite loop (use break to exit)
for {
    input := readUserInput()
    if input == "quit" {
        break // exits the loop
    }
    processInput(input)
}

// Ranging over a slice (like foreach)
cities := []string{"Istanbul", "Ankara", "Izmir"}
for index, city := range cities {
    fmt.Printf("%d: %s\n", index, city)
}
```

### switch — no break needed

Unlike C or Java, Go's `switch` does NOT fall through. Each case breaks automatically.

```go
day := "Monday"

switch day {
case "Monday", "Tuesday", "Wednesday", "Thursday", "Friday":
    fmt.Println("Work day")
case "Saturday", "Sunday":
    fmt.Println("Weekend")
default:
    fmt.Println("Unknown day")
}

// Switch without a value — acts like if/else chain
score := 85

switch {
case score >= 90:
    fmt.Println("Excellent")
case score >= 70:
    fmt.Println("Good")
default:
    fmt.Println("Needs improvement")
}
```

**COMMON MISTAKE**: Expecting fallthrough behavior. If you need it, add the `fallthrough` keyword explicitly:

```go
switch day {
case "Friday":
    fmt.Println("Almost weekend")
    fallthrough // explicitly falls through to next case
case "Saturday":
    fmt.Println("Weekend!")
}
```

---

## 3. Functions — Multiple Return Values

Go functions can return multiple values. This is the foundation of Go's error handling pattern.

```go
// Every function that can fail returns (result, error)
// This is THE Go pattern — you'll see it everywhere
func divide(a, b float64) (float64, error) {
    // COMMON MISTAKE: Forgetting to check the error return
    if b == 0 {
        return 0, fmt.Errorf("cannot divide by zero")
    }
    return a / b, nil // nil means "no error"
}

// Using the function — you MUST handle both returns
result, err := divide(10, 3)
if err != nil {
    fmt.Printf("Error: %v\n", err)
    return // exit early on error
}
fmt.Printf("Result: %.2f\n", result) // Result: 3.33
```

### Why multiple returns matter — the error pattern

```go
// Every Go function that can fail follows this pattern:
//   result, err := doSomething()
//   if err != nil {
//       // handle error
//       return
//   }
//   // use result

// This is like a contract between functions:
// "I will give you the result, OR I will tell you what went wrong.
//  Never both. Never neither."

func loadWeatherData(city string) (WeatherData, error) {
    // Step 1: Try to fetch
    resp, err := http.Get(fmt.Sprintf("https://api.weather.com/%s", city))
    if err != nil {
        return WeatherData{}, fmt.Errorf("fetch failed: %w", err)
        // %w wraps the original error — you can unwrap it later
    }
    defer resp.Body.Close() // CLOSE THE BODY when function exits

    // Step 2: Try to decode
    var data WeatherData
    if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
        return WeatherData{}, fmt.Errorf("decode failed: %w", err)
    }

    return data, nil
}
```

---

## 4. Structs — Named Fields

Structs are like forms — they define what fields exist and what type each field holds.

```go
// A struct is a collection of named fields
type WeatherReport struct {
    City        string
    Temperature float64
    Humidity    int
    Conditions  string
    Timestamp   time.Time
}

// Creating a struct
report := WeatherReport{
    City:        "Istanbul",
    Temperature: 28.5,
    Humidity:    65,
    Conditions:  "Partly Cloudy",
    Timestamp:   time.Now(),
}

// Accessing fields with dot notation
fmt.Printf("Temperature in %s: %.1f°C\n", report.City, report.Temperature)

// Struct embedding — composition over inheritance
type Location struct {
    Latitude  float64
    Longitude float64
    Country   string
}

type DetailedWeatherReport struct {
    WeatherReport              // embedded — fields promoted
    Location                   // another embedded struct
    Forecast     []DailyForecast
}

// DEEP DIVE: Embedding vs inheritance
// Go does NOT have classes or inheritance. Instead, it has embedding.
// When you embed Location in DetailedWeatherReport, you can access
// report.Country directly — the fields are "promoted."
// But it's NOT inheritance: DetailedWeatherReport IS-NOT-A Location.
// It HAS-A Location (composition).

report := DetailedWeatherReport{
    WeatherReport: WeatherReport{
        City:        "Istanbul",
        Temperature: 28.5,
    },
    Location: Location{
        Latitude:  41.0082,
        Longitude: 28.9784,
        Country:   "Turkey",
    },
}

// Fields from both embedded structs are accessible directly
fmt.Println(report.City)     // "Istanbul" — from WeatherReport
fmt.Println(report.Country)  // "Turkey" — from Location
```

---

## 5. Interfaces — Implicit Contracts

Interfaces are the most powerful concept in Go. They define what a type MUST do, without saying HOW.

### How interfaces work — the implicit implementation

```go
// An interface defines a contract: "Any type that has these methods
// satisfies this interface. No declaration needed."

type WeatherProvider interface {
    GetWeather(city string) (WeatherReport, error)
    GetForecast(city string, days int) ([]DailyForecast, error)
}

// Struct A implements WeatherProvider (implicitly)
type OpenWeatherClient struct {
    APIKey string
    BaseURL string
}

// We just write the methods. No "implements" keyword.
func (c OpenWeatherClient) GetWeather(city string) (WeatherReport, error) {
    // Make HTTP request to OpenWeather API
    url := fmt.Sprintf("%s/weather?q=%s&appid=%s", c.BaseURL, city, c.APIKey)
    resp, err := http.Get(url)
    if err != nil {
        return WeatherReport{}, err
    }
    defer resp.Body.Close()

    var result WeatherReport
    json.NewDecoder(resp.Body).Decode(&result)
    return result, nil
}

func (c OpenWeatherClient) GetForecast(city string, days int) ([]DailyForecast, error) {
    // Implementation for forecast
    return nil, nil
}

// Struct B ALSO implements WeatherProvider (implicitly)
type MockWeatherClient struct {
    FakeData WeatherReport
}

// MockWeatherClient satisfies WeatherProvider too
// because it has GetWeather AND GetForecast methods
func (m MockWeatherClient) GetWeather(city string) (WeatherReport, error) {
    return m.FakeData, nil
}

func (m MockWeatherClient) GetForecast(city string, days int) ([]DailyForecast, error) {
    return nil, nil
}

// Now we can write code that works with ANY weather provider
func PrintWeather(provider WeatherProvider, city string) {
    weather, err := provider.GetWeather(city)
    if err != nil {
        fmt.Printf("Error: %v\n", err)
        return
    }
    fmt.Printf("Weather in %s: %.1f°C, %s\n",
        city, weather.Temperature, weather.Conditions)
}

// Both of these work — no type assertion needed
PrintWeather(OpenWeatherClient{APIKey: "abc"}, "Istanbul")
PrintWeather(MockWeatherClient{FakeData: WeatherReport{City: "Istanbul", Temperature: 25}}, "Istanbul")
```

### Why implicit implementation matters

```go
// DEEP DIVE: Implicit vs Explicit interfaces
//
// In Java/C#, you write: class Dog implements Animal { }
// In Go, you just write the methods. No declaration.
//
// Why? Because:
// 1. You can implement an interface for a type you didn't write
// 2. Libraries can define interfaces for YOUR types
// 3. Testing is easy — just create a mock with the right methods
// 4. No coupling between the interface definer and implementer
//
// This is called "structural typing" — the structure of the type
// determines if it satisfies the interface.

// The fmt package uses interfaces extensively:
// fmt.Stringer is the most common interface in Go:
type Stringer interface {
    String() string
}

// ANY type with a String() method satisfies fmt.Stringer.
// fmt.Println, fmt.Printf, and string formatting all use it.

type WeatherReport struct {
    City        string
    Temperature float64
}

// By adding this one method, WeatherReport now works with
// fmt.Println, fmt.Sprintf, and anything that accepts Stringer
func (w WeatherReport) String() string {
    return fmt.Sprintf("%s: %.1f°C", w.City, w.Temperature)
}

// Now fmt.Println uses our String() method automatically
report := WeatherReport{City: "Istanbul", Temperature: 28.5}
fmt.Println(report) // prints: Istanbul: 28.5°C
```

---

## 6. The `fmt` Package — Your Swiss Army Knife

```go
// fmt is Go's formatting package. You'll use it constantly.

// Print — basic output
fmt.Println("Hello, World")    // prints with newline
fmt.Print("Hello")             // no newline
fmt.Printf("Score: %d\n", 42) // formatted output

// Format verbs (like printf in C)
// %d — integer
// %f — float
// %s — string
// %v — default format (works for ANY type)
// %+v — struct with field names (great for debugging)
// %#v — Go syntax representation
// %T — the type itself

city := "Istanbul"
temp := 28.5
report := WeatherReport{City: city, Temperature: temp}

fmt.Printf("City: %s, Temp: %.1f\n", city, temp)  // City: Istanbul, Temp: 28.5
fmt.Printf("Report: %v\n", report)                  // {Istanbul 28.5 0  0001-01-01...}
fmt.Printf("Report: %+v\n", report)                 // {City:Istanbul Temperature:28.5 ...}
fmt.Printf("Type: %T\n", report)                    // main.WeatherReport

// Sprintf — returns a string instead of printing
msg := fmt.Sprintf("Weather in %s is %.1f°C", city, temp)

// Errorf — creates an error with a message (used constantly)
err := fmt.Errorf("city %q not found", city)
```

---

## 7. Putting It Together — CLI Weather Tool

```go
package main

import (
    "encoding/json"
    "fmt"
    "net/http"
    "os"
    "time"
)

// WeatherReport represents weather data for a city
type WeatherReport struct {
    City        string  `json:"city"`
    Temperature float64 `json:"temperature"`
    Humidity    int     `json:"humidity"`
    Conditions  string  `json:"conditions"`
    FetchedAt   string  `json:"fetched_at"`
}

// WeatherProvider defines the contract for fetching weather data
type WeatherProvider interface {
    GetWeather(city string) (WeatherReport, error)
}

// APIClient implements WeatherProvider using a real HTTP API
type APIClient struct {
    BaseURL string
    Client  *http.Client
}

// GetWeather fetches weather data from the API
// Returns (report, nil) on success, (empty report, error) on failure
func (a APIClient) GetWeather(city string) (WeatherReport, error) {
    url := fmt.Sprintf("%s/weather?city=%s", a.BaseURL, city)

    resp, err := a.Client.Get(url)
    if err != nil {
        return WeatherReport{}, fmt.Errorf("API request failed: %w", err)
    }
    defer resp.Body.Close()

    if resp.StatusCode != http.StatusOK {
        return WeatherReport{}, fmt.Errorf("API returned status %d", resp.StatusCode)
    }

    var report WeatherReport
    if err := json.NewDecoder(resp.Body).Decode(&report); err != nil {
        return WeatherReport{}, fmt.Errorf("failed to parse response: %w", err)
    }

    report.FetchedAt = time.Now().Format(time.RFC3339)
    return report, nil
}

// DisplayWeather formats and prints the weather report
// Uses the fmt package's formatting verbs for clean output
func DisplayWeather(report WeatherReport) {
    fmt.Println("╔══════════════════════════════════╗")
    fmt.Printf("║  Weather Report: %-14s ║\n", report.City)
    fmt.Println("╠══════════════════════════════════╣")
    fmt.Printf("║  Temperature: %-18.1f ║\n", report.Temperature)
    fmt.Printf("║  Humidity:    %-18d ║\n", report.Humidity)
    fmt.Printf("║  Conditions:  %-18s ║\n", report.Conditions)
    fmt.Printf("║  Fetched at:  %-18s ║\n", report.FetchedAt[:19])
    fmt.Println("╚══════════════════════════════════╝")
}

func main() {
    // Check for city argument
    if len(os.Args) < 2 {
        fmt.Fprintf(os.Stderr, "Usage: weather <city>\n")
        os.Exit(1)
    }

    city := os.Args[1]

    // Create API client with timeout
    client := &http.Client{Timeout: 10 * time.Second}
    provider := APIClient{
        BaseURL: "https://api.weather.example.com",
        Client:  client,
    }

    // Fetch weather
    report, err := provider.GetWeather(city)
    if err != nil {
        fmt.Fprintf(os.Stderr, "Error: %v\n", err)
        os.Exit(1)
    }

    // Display result
    DisplayWeather(report)
}
```

---

## Key Takeaways

1. **Variables**: Use `:=` for new variables, `=` for reassignment. Go has zero values — every variable starts known.
2. **Types**: `int`, `string`, `bool`, `float64`, `byte` (ASCII), `rune` (Unicode).
3. **Control flow**: `if` with scoped variables, `for` (only loop), `switch` (no fallthrough).
4. **Functions**: Multiple return values enable the `(result, error)` pattern.
5. **Structs**: Named fields, embedding for composition. No inheritance.
6. **Interfaces**: Implicit implementation — just write the methods. No `implements` keyword.
7. **fmt**: `%v` for debugging, `%d/%f/%s` for specific types, `%+v` for struct fields.

---

**Next**: [Module 1 Exercise](01-go-fundamentals-exercise.md) — Build a CLI weather tool from scratch.
