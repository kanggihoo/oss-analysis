# Configuration and Demo Mode

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [README.md](README.md)
- [src/config/demo-loader.ts](src/config/demo-loader.ts)
- [tsup.config.ts](tsup.config.ts)

</details>



This document explains the configuration options available in DBHub and its demonstration mode that includes a sample employee database. It covers how to configure DBHub, different connection methods, and how to use the built-in demo database for testing and development.

For detailed information about environment variables, see [Environment Configuration](#5.1).
For comprehensive details about the sample database structure, see [Demo Database](#5.2).

## Configuration Overview

DBHub configuration follows a hierarchical approach where each configuration method has a specific priority level. This prioritization ensures that command-line arguments take precedence over environment variables, which in turn take precedence over configuration files.

### Configuration Priority

```mermaid
flowchart TD
    Start([Start DBHub]) --> CommandLine{"Command line arguments"}
    CommandLine -->|"Highest priority"| EnvVar{"Environment variables"}
    EnvVar -->|"Second priority"| EnvFile{"Environment files"}
    EnvFile -->|"Lowest priority"| DefaultConfig["Default configuration"]
```

Sources: [README.md:161-182]()

## Database Connection Configuration

The primary configuration for DBHub is the database connection string, specified as a Database Source Name (DSN). Each supported database type has its own DSN format.

### DSN Resolution Process

```mermaid
flowchart TD
    Start([Start DBHub]) --> CommandLineDSN{"Command line\nDSN provided?"}
    CommandLineDSN -->|"Yes"| UseCmdDSN["Use command line DSN"]
    CommandLineDSN -->|"No"| EnvVarDSN{"Environment\nvariable DSN?"}
    EnvVarDSN -->|"Yes"| UseEnvDSN["Use environment DSN"]
    EnvVarDSN -->|"No"| EnvFileDSN{"ENV file\nDSN present?"}
    EnvFileDSN -->|"Yes"| UseFileDSN["Use .env file DSN"]
    EnvFileDSN -->|"No"| DemoModeFlag{"--demo flag\nprovided?"}
    DemoModeFlag -->|"Yes"| UseDemoDSN["Use SQLite in-memory DSN"]
    DemoModeFlag -->|"No"| ErrorExit["Exit with error"]
    
    UseCmdDSN --> ConnectDB["Connect to database"]
    UseEnvDSN --> ConnectDB
    UseFileDSN --> ConnectDB
    UseDemoDSN --> LoadDemoData["Load demo database"]
    LoadDemoData --> ConnectDB
    
    ConnectDB --> ServerStart["Start MCP server"]
```

Sources: [README.md:154-182]()

### DSN Formats for Supported Databases

| Database   | DSN Format                                               | Example                                                          |
| ---------- | -------------------------------------------------------- | ---------------------------------------------------------------- |
| MySQL      | `mysql://[user]:[password]@[host]:[port]/[database]`     | `mysql://user:password@localhost:3306/dbname`                    |
| MariaDB    | `mariadb://[user]:[password]@[host]:[port]/[database]`   | `mariadb://user:password@localhost:3306/dbname`                  |
| PostgreSQL | `postgres://[user]:[password]@[host]:[port]/[database]`  | `postgres://user:password@localhost:5432/dbname?sslmode=disable` |
| SQL Server | `sqlserver://[user]:[password]@[host]:[port]/[database]` | `sqlserver://user:password@localhost:1433/dbname`                |
| SQLite     | `sqlite:///[path/to/file]` or `sqlite::memory:`          | `sqlite:///path/to/database.db` or `sqlite::memory:`             |

Sources: [README.md:187-195]()

## Demo Mode

DBHub includes a demonstration mode that automatically loads a sample employee database into an in-memory SQLite database. This mode is activated by using the `--demo` flag and is useful for testing and development without requiring a separate database setup.

### Demo Mode Implementation

```mermaid
flowchart TD
    StartDemo([Start with --demo flag]) --> FindResources["demoLoader.findResourceFiles"]
    FindResources --> LoadSQLFiles["demoLoader.loadSqlFile()"]
    LoadSQLFiles --> ProcessSQLDirectives["demoLoader.getSqliteInMemorySetupSql()"]
    ProcessSQLDirectives --> CreateInMemoryDB["getInMemorySqliteDSN()"]
    CreateInMemoryDB --> ExecuteSQLScripts["Execute SQL scripts"]
    ExecuteSQLScripts --> DemoDBReady["Demo database ready"]
    DemoDBReady --> StartMCPServer["Start MCP server"]
```

Sources: [src/config/demo-loader.ts:1-77]()

The demo mode implementation searches for SQL files in several locations following a fallback pattern:
1. First tries the project root resources directory (for development)
2. Then tries the dist directory (for production)
3. Falls back to a relative path from the current directory

Sources: [src/config/demo-loader.ts:17-39]()

### Sample Employee Database Structure

```mermaid
erDiagram
    DEPARTMENTS {
        string dept_no PK
        string dept_name
    }
    EMPLOYEES {
        int emp_no PK
        date birth_date
        string first_name
        string last_name
        string gender
        date hire_date
    }
    DEPT_MANAGER {
        string dept_no FK
        int emp_no FK
        date from_date
        date to_date
    }
    DEPT_EMP {
        int emp_no FK
        string dept_no FK
        date from_date
        date to_date
    }
    TITLES {
        int emp_no FK
        string title
        date from_date
        date to_date
    }
    SALARIES {
        int emp_no FK
        int salary
        date from_date
        date to_date
    }
    
    DEPARTMENTS ||--o{ DEPT_EMP : "contains"
    DEPARTMENTS ||--o{ DEPT_MANAGER : "managed by"
    EMPLOYEES ||--o{ DEPT_EMP : "works in"
    EMPLOYEES ||--o{ DEPT_MANAGER : "manages"
    EMPLOYEES ||--o{ TITLES : "has"
    EMPLOYEES ||--o{ SALARIES : "earns"
```

Sources: [README.md:227]()

## Resource Management for Demo Mode

The demo mode relies on SQL scripts located in the `resources/employee-sqlite` directory. During the build process, these files are copied to the distribution package to ensure they're available in production environments.

```mermaid
flowchart TD
    DevSrcFiles["Development\nresources/employee-sqlite/*.sql"] --> BuildProcess["Build Process\n(tsup.config.ts)"]
    BuildProcess --> DistFiles["Distribution\ndist/resources/employee-sqlite/*.sql"]
    DistFiles --> RuntimeLoader["demoLoader.loadSqlFile()"]
    RuntimeLoader --> InMemoryDB[("SQLite in-memory database\nsqlite::memory:")]
```

Sources: [src/config/demo-loader.ts:11-39](), [tsup.config.ts:11-29]()

The build process is managed by `tsup.config.ts`, which includes a custom `onSuccess` hook that copies the SQL files to the distribution directory.

Sources: [tsup.config.ts:12-28]()

## Command Line Options

DBHub supports the following command line options for configuration:

| Option    | Description                                                     | Default                      |
| --------- | --------------------------------------------------------------- | ---------------------------- |
| demo      | Run in demo mode with sample employee database                  | `false`                      |
| dsn       | Database connection string                                      | Required if not in demo mode |
| transport | Transport mode: `stdio` or `sse`                                | `stdio`                      |
| port      | HTTP server port (only applicable when using `--transport=sse`) | `8080`                       |

Sources: [README.md:219-226]()

## Transport Configuration

DBHub supports two transport modes for communication with MCP clients:

1. **stdio** (default) - Used for direct integration with tools like Claude Desktop
2. **sse** (Server-Sent Events) - Used for browser and network clients, requires specifying a port

### Transport Configuration Process

```mermaid
flowchart TD
    StartConfig([Start DBHub]) --> TransportModeCheck{"transportMode?"}
    TransportModeCheck -->|"stdio"| SetupSTDIOTransport["Configure STDIO transport"]
    TransportModeCheck -->|"sse"| PortSpecifiedCheck{"port specified?"}
    PortSpecifiedCheck -->|"Yes"| SetupSSEWithPort["Configure SSE transport\non specified port"]
    PortSpecifiedCheck -->|"No"| SetupSSEWithDefaultPort["Configure SSE transport\non port 8080"]
    
    SetupSTDIOTransport --> StartMCPServer["Start MCP server"]
    SetupSSEWithPort --> StartHTTPServer["Start HTTP server"]
    SetupSSEWithDefaultPort --> StartHTTPServer
    StartHTTPServer --> StartMCPServer
```

Sources: [README.md:206-217]()

## Usage Examples

### Running in Demo Mode

```bash
# Using npm package
npx @bytebase/dbhub --transport stdio --demo

# Using Docker
docker run --rm --init \
   --name dbhub \
   --publish 8080:8080 \
   bytebase/dbhub \
   --transport sse \
   --port 8080 \
   --demo
```

Sources: [README.md:78-85](), [README.md:96-98]()

### Connecting to an External Database

```bash
# PostgreSQL example with npm package
npx @bytebase/dbhub --transport sse --port 8080 --dsn "postgres://user:password@localhost:5432/dbname?sslmode=disable"

# MySQL example with Docker
docker run --rm --init \
   --name dbhub \
   --publish 8080:8080 \
   bytebase/dbhub \
   --transport sse \
   --port 8080 \
   --dsn "mysql://user:password@host.docker.internal:3306/dbname"
```

Sources: [README.md:67-75](), [README.md:91-93]()
